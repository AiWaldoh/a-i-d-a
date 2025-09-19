from pathlib import Path


class Command:
    def execute(self, params: dict) -> str:
        file_path = params.get('file_path')
        content = params.get('content', '')
        
        if not file_path:
            return "Error: file_path parameter is required"
        
        try:
            # Convert to Path object for better handling
            path = Path(file_path)
            
            # Create parent directories if they don't exist
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write content to file
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return f"Successfully wrote {len(content)} characters to {file_path}"
            
        except Exception as e:
            return f"Error writing to file {file_path}: {str(e)}"
