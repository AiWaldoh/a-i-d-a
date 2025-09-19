class Command:
    def execute(self, params: dict) -> str:
        file_path = params.get("file_path")
        start_line = params.get("start_line", 1)
        max_lines = params.get("max_lines", 200)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            end_line = min(start_line + max_lines - 1, len(lines))
            content_lines = lines[start_line-1:end_line]
            
            result = f"=== {file_path} (lines {start_line}-{end_line}) ===\n"
            result += ''.join(content_lines)
            
            if end_line < len(lines):
                result += f"\n... ({len(lines) - end_line} more lines available)"
            
            return result
            
        except Exception as e:
            return f"Error reading {file_path}: {str(e)}"
