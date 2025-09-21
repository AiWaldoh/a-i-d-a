import subprocess
import os

class Command:
    def execute(self, params: dict) -> str:
        pattern = params.get("pattern")
        if not pattern:
            return "Error: No pattern provided to ripgrep."
        
        # Validate required parameters to prevent excessive token usage
        search_directory = params.get("search_directory")
        if not search_directory:
            return "Error: search_directory is required. Please specify which directory to search in."
        
        extension = params.get("extension")
        if not extension:
            return "Error: extension is required. Please specify file extension (e.g., 'py', 'js', 'txt')."
        
        max_count = params.get("max_count")
        if not max_count:
            return "Error: max_count is required. Please specify maximum number of results (recommended: 50-100)."
        
        # Validate max_count bounds
        if max_count < 1 or max_count > 500:
            return "Error: max_count must be between 1 and 500 to prevent excessive token usage."
        
        # Validate search directory exists
        if not os.path.exists(search_directory):
            return f"Error: Search directory '{search_directory}' does not exist."
        
        cmd = ["rg", "--json"]
        
        # Add file extension filter (now required)
        cmd.extend(["-g", f"*.{extension}"])
        
        cmd.append(pattern)
        cmd.append(search_directory)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 1:
                return "No matches found."
            elif result.returncode != 0:
                return f"Error: {result.stderr.strip()}"
            
            # Limit output to max_count lines to control response size
            output_lines = result.stdout.strip().split('\n')
            
            # Add search parameters info for transparency
            search_info = f"=== Ripgrep Search Results ===\nPattern: '{pattern}' | Directory: '{search_directory}' | Extension: '*.{extension}' | Max results: {max_count}\n\n"
            
            if len(output_lines) > max_count:
                limited_lines = output_lines[:max_count]
                return search_info + '\n'.join(limited_lines) + f"\n\n... (truncated to {max_count} lines out of {len(output_lines)} total matches)"
            
            return search_info + result.stdout
            
        except FileNotFoundError:
            return "Error: ripgrep (rg) not found. Please install ripgrep."
        except subprocess.TimeoutExpired:
            return "Error: Search timed out."
        except Exception as e:
            return f"Error: {str(e)}"