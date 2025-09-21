import subprocess

class Command:
    def execute(self, params: dict) -> str:
        pattern = params.get("pattern")
        if not pattern:
            return "Error: No pattern provided to ripgrep."
        
        cmd = ["rg", "--json"]
        
        # Store max_count for later use (we'll limit total output, not per-file)
        max_count = params.get("max_count", 300)
        
        # Add file extension filter
        extension = params.get("extension")
        if extension:
            cmd.extend(["-g", f"*.{extension}"])
        
        cmd.append(pattern)
        
        # Add search directory if specified
        search_directory = params.get("search_directory")
        if search_directory:
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
            if len(output_lines) > max_count:
                limited_lines = output_lines[:max_count]
                return '\n'.join(limited_lines) + f"\n... (truncated to {max_count} lines)"
            
            return result.stdout
            
        except FileNotFoundError:
            return "Error: ripgrep (rg) not found. Please install ripgrep."
        except subprocess.TimeoutExpired:
            return "Error: Search timed out."
        except Exception as e:
            return f"Error: {str(e)}"