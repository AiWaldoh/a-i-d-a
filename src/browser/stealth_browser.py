import asyncio
from playwright.async_api import async_playwright, Page
from typing import List, Dict, Optional
from abc import ABC, abstractmethod

class StealthBrowser(ABC):
    def __init__(self, headless: bool = False, user_agent: Optional[str] = None):
        self.headless = headless
        self.user_agent = user_agent or 'Mozilla/5.0 (X11; Linux x86_64; rv:142.0) Gecko/20100101 Firefox/142.0'
        self.firefox_prefs = {
            'dom.webdriver.enabled': False,
            'useAutomationExtension': False,
            'privacy.trackingprotection.enabled': False,
            'geo.enabled': False,
            'permissions.default.desktop-notification': 1,
            'dom.push.enabled': False,
            'dom.webnotifications.enabled': False,
            'media.navigator.enabled': True,
            'media.peerconnection.enabled': True,
            'media.navigator.video.enabled': True,
            'dom.webaudio.enabled': True
        }
        self.context_options = {
            'viewport': {'width': 1366, 'height': 768},
            'locale': 'en-US',
            'timezone_id': 'America/New_York',
            'geolocation': None,
            'permissions': [],
            'accept_downloads': False
        }
    
    async def _create_stealth_page(self, playwright) -> tuple:
        browser = await playwright.firefox.launch(
            headless=self.headless,
            firefox_user_prefs=self.firefox_prefs
        )
        
        context = await browser.new_context(
            user_agent=self.user_agent,
            **self.context_options
        )
        
        await context.add_init_script("delete Object.getPrototypeOf(navigator).webdriver;")
        
        page = await context.new_page()
        
        return browser, page
    
    @abstractmethod
    async def execute(self, *args, **kwargs):
        pass

class GoogleSearch(StealthBrowser):
    def __init__(self, headless: bool = False, user_agent: Optional[str] = None):
        super().__init__(headless, user_agent)
    
    async def execute(self, query: str, num_results: int = 20) -> List[Dict[str, str]]:
        async with async_playwright() as p:
            browser, page = await self._create_stealth_page(p)
            
            url = f'https://www.google.com/search?q={"+".join(query.split())}&num={num_results}'
            await page.goto(url)
            await page.wait_for_load_state('networkidle')
            
            results = await self._parse_results(page)
            
            await browser.close()
            
            return results
    
    async def _parse_results(self, page: Page) -> List[Dict[str, str]]:
        results = []
        containers = await page.locator('div[data-ved]:has(h3)').all()
        
        for container in containers:
            result = await self._extract_result(container)
            if result:
                results.append(result)
        
        return results
    
    async def _extract_result(self, container) -> Optional[Dict[str, str]]:
        try:
            title = await container.locator('h3').first.text_content()
            url = await container.locator('a:has(h3)').first.get_attribute('href')
            snippet = await self._extract_snippet(container, title)
            
            if title and url:
                return {
                    'title': title.strip(),
                    'url': url,
                    'snippet': snippet
                }
        except:
            pass
        return None
    
    async def _extract_snippet(self, container, title: str) -> Optional[str]:
        snippet_elements = await container.locator('span').all()
        for span in snippet_elements:
            text = await span.text_content()
            if text and len(text.strip()) > 30 and title not in text:
                return text.strip()
        return None

class WebpageFetcher(StealthBrowser):
    def __init__(self, headless: bool = False, user_agent: Optional[str] = None):
        super().__init__(headless, user_agent)
    
    async def execute(self, url: str, output_file: Optional[str] = None) -> str:
        async with async_playwright() as p:
            browser, page = await self._create_stealth_page(p)
            
            await page.goto(url)
            await page.wait_for_load_state('networkidle')
            
            await self._handle_popups(page)
            
            html_content = await page.content()
            
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)
            
            await browser.close()
            
            return html_content
    
    async def _handle_popups(self, page: Page):
        cookie_selectors = [
            'button:has-text("Accept all")',
            'button:has-text("Accept")',
            'button:has-text("I agree")',
            'button:has-text("OK")',
            '[id*="accept"]',
            '[class*="accept"]'
        ]
        
        for selector in cookie_selectors:
            try:
                button = page.locator(selector).first
                if await button.count() > 0:
                    await button.click()
                    await asyncio.sleep(1)
                    break
            except:
                continue
