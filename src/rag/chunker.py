import ast
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import List


@dataclass(frozen=True)
class CodeChunk:
    id: str
    file_path: str
    symbol_name: str
    symbol_type: str
    content: str
    content_hash: str


class CodeChunker:
    def chunk(self, file_path: Path, file_content: str) -> List[CodeChunk]:
        chunks = []
        
        try:
            tree = ast.parse(file_content)
        except SyntaxError:
            return chunks
        
        lines = file_content.splitlines(keepends=True)
        
        def extract_chunk(node, hierarchy_path=None):
            if hierarchy_path is None:
                hierarchy_path = []
            
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                symbol_name = node.name
                symbol_type = "class" if isinstance(node, ast.ClassDef) else "function"
                
                start_line = node.lineno - 1
                end_line = node.end_lineno if hasattr(node, 'end_lineno') and node.end_lineno else start_line + 1
                
                content = ''.join(lines[start_line:end_line])
                content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
                
                # Build the full hierarchy path
                current_path = hierarchy_path + [(symbol_type, symbol_name)]
                
                # Generate ID from the full path
                path_parts = [str(file_path)]
                for sym_type, sym_name in current_path:
                    path_parts.extend([sym_type, sym_name])
                chunk_id = "::".join(path_parts)
                
                # Generate display name from the path
                display_parts = [name for _, name in current_path]
                display_name = ".".join(display_parts)
                
                chunk = CodeChunk(
                    id=chunk_id,
                    file_path=str(file_path),
                    symbol_name=display_name,
                    symbol_type=symbol_type,
                    content=content.strip(),
                    content_hash=content_hash
                )
                
                chunks.append(chunk)
                
                # Process nested definitions (both classes and functions can have nested defs)
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                    for child in node.body:
                        extract_chunk(child, current_path)
        
        for node in tree.body:
            extract_chunk(node)
        
        return chunks
