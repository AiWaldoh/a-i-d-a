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
        output_file = params.get("output_file")
        headless = params.get("headless", False)
        
        if not url:
            return "Error: 'url' parameter is required"
        
        try:
            fetcher = WebpageFetcher(headless=headless)
            
            # Create output directory if not provided
            if not output_file:
                os.makedirs("/tmp/html-results", exist_ok=True)
                from urllib.parse import urlparse
                domain = urlparse(url).netloc.replace('www.', '').replace('.', '_')
                output_file = f"/tmp/html-results/{domain}.html"
            
            # Always run in a separate thread to avoid event loop conflicts
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, fetcher.execute(url, output_file))
                html_content = future.result(timeout=60)
            
            return f"Successfully fetched {url} and saved to {output_file}"
            
        except Exception as e:
            return f"Error fetching webpage: {str(e)}"
