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
    
    async def execute(self, url: str, output_file: Optional[str] = None) -> Dict[str, str]:
        async with async_playwright() as p:
            browser, page = await self._create_stealth_page(p)
            
            response = await page.goto(url, timeout=20000)
            status_code = response.status if response else "Unknown"
            
            # Try networkidle first, fallback to domcontentloaded if it times out
            try:
                await page.wait_for_load_state('networkidle', timeout=10000)
            except:
                try:
                    await page.wait_for_load_state('domcontentloaded', timeout=5000)
                except:
                    # If all else fails, just wait a bit for content to load
                    await asyncio.sleep(3)
            
            await self._handle_popups(page)
            
            html_content = await page.content()
            structured_data = await self._extract_structured_content(page)
            
            # Save full HTML
            html_file = output_file
            if not html_file:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc.replace('www.', '').replace('.', '_')
                html_file = f"{domain}.html"
            
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Save structured content
            structured_file = html_file.replace('.html', '_structured.json')
            import json
            with open(structured_file, 'w', encoding='utf-8') as f:
                json.dump(structured_data, f, indent=2, ensure_ascii=False)
            
            await browser.close()
            
            return {
                'html_file': html_file,
                'structured_file': structured_file,
                'url': url,
                'status_code': status_code,
                'text_elements': len(structured_data['structured_text']),
                'links_found': len(structured_data['link_map'])
            }
    
    async def _extract_structured_content(self, page: Page) -> Dict:
        # Remove unwanted elements
        selectors_to_remove = [
            'header',
            'footer', 
            'nav',
            '[role="navigation"]',
            '.sidebar',
            '#sidebar',
            'aside',
            'script',
            'style',
            'noscript'
        ]
        
        for selector in selectors_to_remove:
            await page.evaluate(f'''
                document.querySelectorAll('{selector}').forEach(el => el.remove())
            ''')
        
        # Extract structured content
        semantic_tags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'li', 'td', 'th', 'blockquote', 'pre', 'code', 'span']
        
        result = await page.evaluate(f'''
            () => {{
                const tags = {semantic_tags};
                const selector = tags.join(',');
                const elements = document.querySelectorAll(selector);
                const structured_text = [];
                const link_map = [];
                
                elements.forEach(el => {{
                    let text = el.innerText?.trim();
                    if (!text) return;
                    
                    // Filter out elements with 3 words or less
                    const wordCount = text.split(/\s+/).filter(word => word.length > 0).length;
                    if (wordCount <= 3) return;
                    
                    // Find all links within this element
                    const links = el.querySelectorAll('a[href]');
                    links.forEach(link => {{
                        const linkText = link.innerText.trim();
                        const href = link.href;
                        
                        if (linkText && href) {{
                            const linkIndex = link_map.length;
                            link_map.push({{
                                index: linkIndex,
                                text: linkText,
                                href: href
                            }});
                            
                            // Replace link text with placeholder in the element's text
                            text = text.replace(linkText, `[LINK:${{linkIndex}}]`);
                        }}
                    }});
                    
                    structured_text.push({{
                        tag: el.tagName.toLowerCase(),
                        text: text
                    }});
                }});
                
                return {{
                    structured_text: structured_text,
                    link_map: link_map
                }};
            }}
        ''')
        
        return result
    
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
