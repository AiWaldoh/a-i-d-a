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
                result = future.result(timeout=60)
            
            return f"""<webpage_fetch_result>
    <operation_status>success</operation_status>
    <target_url>{url}</target_url>
    <http_status>{result['status_code']}</http_status>
    
    <files_created>
        <raw_html_file>{result['html_file']}</raw_html_file>
        <structured_data_file>{result['structured_file']}</structured_data_file>
    </files_created>
    
    <extraction_summary>
        <text_elements_found>{result['text_elements']}</text_elements_found>
        <links_discovered>{result['links_found']}</links_discovered>
    </extraction_summary>
    
    <structured_format_guide>
        <description>
            The structured JSON contains two main arrays:
            - structured_text: Text content with semantic HTML tags (h1-h6, p, li, etc.)
            - link_map: All hyperlinks found, referenced as [LINK:N] placeholders in text
        </description>
        
        <jq_extraction_patterns>
            <all_text_content>jq '.structured_text[].text' {result['structured_file']}</all_text_content>
            <all_hyperlinks>jq '.link_map[] | "\\(.text): \\(.href)"' {result['structured_file']}</all_hyperlinks>
            <headings_only>jq '.structured_text[] | select(.tag | test("h[1-6]")) | .text' {result['structured_file']}</headings_only>
            <paragraph_content>jq '.structured_text[] | select(.tag == "p") | .text' {result['structured_file']}</paragraph_content>
        </jq_extraction_patterns>
    </structured_format_guide>
</webpage_fetch_result>"""
            
        except Exception as e:
            return f"Error fetching webpage: {str(e)}"
