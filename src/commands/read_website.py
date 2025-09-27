import asyncio
import sys
import os

# Add the parent directory to the path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from browser import WebpageFetcher

class Command:
    def execute(self, params: dict) -> str:
        url = params.get("url")
        
        if not url:
            return "Error: 'url' parameter is required"
        
        try:
            fetcher = WebpageFetcher(headless=True)
            
            # Always save to /tmp/html-results/
            os.makedirs("/tmp/html-results", exist_ok=True)
            from urllib.parse import urlparse
            domain = urlparse(url).netloc.replace('www.', '').replace('.', '_')
            output_file = f"/tmp/html-results/{domain}.html"
            
            # Always run in a separate thread to avoid event loop conflicts
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, fetcher.execute(url, output_file))
                result = future.result(timeout=60)
            
            format_explanation = """
STRUCTURED JSON FORMAT:
- structured_text: Array of text elements with their HTML tags (h1, h2, p, li, etc.)
- link_map: Array of all links found, referenced as [LINK:N] in text

USEFUL JQ QUERIES for run_command tool:
- Get all text: jq '.structured_text[].text' file.json
- Get all links: jq '.link_map[] | "\\(.text): \\(.href)"' file.json
- Get headings only: jq '.structured_text[] | select(.tag | test("h[1-6]")) | .text' file.json
- Get paragraphs: jq '.structured_text[] | select(.tag == "p") | .text' file.json
"""
            
            return f"Successfully fetched {url} (Status: {result['status_code']})\nHTML saved to: {result['html_file']}\nStructured content saved to: {result['structured_file']}\nExtracted {result['text_elements']} text elements and {result['links_found']} links\n{format_explanation}"
            
        except Exception as e:
            return f"Error fetching webpage: {str(e)}"
