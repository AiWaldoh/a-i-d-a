import subprocess

class Command:
    def execute(self, params: dict) -> str:
        pattern = params.get("pattern")
        if not pattern:
            return "Error: No pattern provided to ripgrep."
        
        cmd = ["rg", "--json"]
        
        # Add max count limit
        max_count = params.get("max_count", 300)
        cmd.extend(["--max-count", str(max_count)])
        
        # Add file extension filter
        extension = params.get("extension")
        if extension:
            cmd.extend(["-g", f"*.{extension}"])
        
        cmd.append(pattern)
        
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
            
            return result.stdout
            
        except FileNotFoundError:
            return "Error: ripgrep (rg) not found. Please install ripgrep."
        except subprocess.TimeoutExpired:
            return "Error: Search timed out."
        except Exception as e:
            return f"Error: {str(e)}"