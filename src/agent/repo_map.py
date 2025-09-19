import ast
import os
from pathlib import Path
from typing import Dict, List, Tuple


class RepoMapBuilder:
    def __init__(self, workspace_root: str = "."):
        self.workspace_root = Path(workspace_root)
        self.ignored_dirs = {'.git', '__pycache__', '.venv', 'venv', 'env', 'node_modules', '.pytest_cache'}
        
    def build_repo_map(self) -> str:
        python_files = self._scan_python_files()
        
        if not python_files:
            return "No Python files found in the repository."
        
        file_symbols = {}
        for file_path in python_files:
            symbols = self._parse_file(file_path)
            if symbols:
                file_symbols[file_path] = symbols
                
        return self._format_repo_map(file_symbols)
    
    def _scan_python_files(self) -> List[Path]:
        python_files = []
        
        for root, dirs, files in os.walk(self.workspace_root):
            dirs[:] = [d for d in dirs if d not in self.ignored_dirs]
            
            for file in files:
                if file.endswith('.py'):
                    file_path = Path(root) / file
                    python_files.append(file_path)
                    
        return sorted(python_files)
    
    def _parse_file(self, file_path: Path) -> Dict[str, List[str]]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            functions = []
            classes = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    args = []
                    for arg in node.args.args:
                        args.append(arg.arg)
                    
                    defaults_count = len(node.args.defaults)
                    if defaults_count > 0:
                        for i in range(len(args) - defaults_count, len(args)):
                            args[i] = f"{args[i]}=..."
                            
                    sig = f"{node.name}({', '.join(args)})"
                    functions.append(sig)
                    
                elif isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                    
            return {"functions": functions, "classes": classes}
            
        except Exception:
            return {}
    
    def _format_repo_map(self, file_symbols: Dict[Path, Dict[str, List[str]]]) -> str:
        lines = ["=== Repository Structure ===\n"]
        
        for file_path, symbols in file_symbols.items():
            relative_path = file_path.relative_to(self.workspace_root)
            lines.append(f"\n📄 {relative_path}")
            
            if symbols.get("classes"):
                lines.append("  Classes:")
                for class_name in symbols["classes"]:
                    lines.append(f"    - {class_name}")
                    
            if symbols.get("functions"):
                lines.append("  Functions:")
                for func_sig in symbols["functions"]:
                    lines.append(f"    - {func_sig}")
                    
        return "\n".join(lines)
