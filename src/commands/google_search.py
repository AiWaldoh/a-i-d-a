import asyncio
import json
import sys
import os

# Add the parent directory to the path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from browser import GoogleSearch

class Command:
    def execute(self, params: dict) -> str:
        query = params.get("query")
        num_results = params.get("num_results", 20)
        
        if not query:
            return json.dumps({"error": "'query' parameter is required"})
        
        try:
            searcher = GoogleSearch(headless=False)
            
            # Always run in a separate thread to avoid event loop conflicts
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, searcher.execute(query, num_results))
                results = future.result(timeout=60)
            
            structured_results = []
            for i, result in enumerate(results, 1):
                structured_results.append({
                    "order": i,
                    "title": result['title'],
                    "url": result['url'],
                    "snippet": result['snippet'] if result['snippet'] else ""
                })
            
            response = {
                "query": query,
                "results": structured_results,
                "total_found": len(structured_results)
            }
            
            return json.dumps(response, indent=2)
            
        except Exception as e:
            return json.dumps({"error": f"Error searching Google: {str(e)}"})
