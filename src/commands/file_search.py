import os
from pathlib import Path


class Command:
    def execute(self, params: dict) -> str:
        pattern = params.get("pattern")
        if not pattern:
            return "Error: No pattern was provided to file_search."
        
        search_dir = params.get("search_dir", os.getcwd())
        max_results = params.get("max_results", 100)
        
        try:
            search_path = Path(search_dir).expanduser().resolve()
            if not search_path.exists():
                return f"Error: Directory '{search_dir}' does not exist."
            
            results = []
            count = 0
            
            # Use rglob for recursive pattern matching
            for path in search_path.rglob(pattern):
                if count >= max_results:
                    results.append(f"\n... (truncated at {max_results} results)")
                    break
                
                # Skip hidden directories and common ignored paths
                parts = path.parts
                if any(part.startswith('.') for part in parts) or '__pycache__' in parts:
                    continue
                
                if path.is_file():
                    results.append(str(path))
                    count += 1
                elif path.is_dir() and params.get("include_dirs", True):
                    results.append(str(path) + "/")
                    count += 1
            
            if not results:
                return f"No files matching '{pattern}' found in {search_path}"
            
            return "\n".join(results)
            
        except Exception as e:
            return f"Error searching for files: {str(e)}"
