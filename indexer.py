import asyncio
import hashlib
import json
import os
from pathlib import Path
from typing import Dict, List, Tuple, Set

import chromadb.utils.embedding_functions as embedding_functions
from gitignore_parser import parse_gitignore

from src.config.settings import AppSettings
from src.llm.client import LLMClient
from src.llm.types import LLMConfig
from src.rag.chunker import CodeChunker, CodeChunk
from src.rag.embedding import EmbeddingGenerator
from src.rag.prompt_templates import PromptTemplateManager
from src.rag.vector_store import VectorStore
from src.rag.embedding_factory import get_embedding_function


class Indexer:
    def __init__(self, root_dir: str = ".", db_path: str = "db"):
        self.root_dir = Path(root_dir)
        self.db_path = db_path
        self.state_file = self.root_dir / "index_state.json"
        self.ignored_dirs = {'.git', '__pycache__', '.venv', 'venv', 'env', 'node_modules', '.pytest_cache', 'db'}
        
        # Supported file extensions
        self.supported_extensions = {'.py', '.tsx', '.ts', '.js'}
        
        # Load gitignore matchers
        self.gitignore_matchers = self._load_gitignore_matchers()
        
        self.chunker = CodeChunker()
        self.embedding_function = get_embedding_function()
        
        summarization_config = LLMConfig(
            api_key=AppSettings.API_KEY,
            base_url=AppSettings.BASE_URL,
            model="mistralai/mistral-7b-instruct",
            timeout=30,
            max_retries=3,
            reasoning_effort="low",
            verbosity="quiet"
        )
        summarization_client = LLMClient(config=summarization_config)
        
        prompt_manager = PromptTemplateManager()
        
        self.embedding_generator = EmbeddingGenerator(
            embedding_function=self.embedding_function,
            summarization_client=summarization_client,
            prompt_manager=prompt_manager
        )
        
        self.vector_store = VectorStore(
            db_path=self.db_path,
            collection_name="codebase",
            embedding_function=self.embedding_function
        )
    
    def _load_index_state(self) -> Dict[str, str]:
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_index_state(self, state: Dict[str, str]):
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    def _load_gitignore_matchers(self) -> List:
        """Load gitignore matchers from all .gitignore files in the project hierarchy"""
        matchers = []
        
        # Look for .gitignore files starting from root and going up
        current = self.root_dir
        while current != current.parent:
            gitignore_path = current / '.gitignore'
            if gitignore_path.exists():
                matcher = parse_gitignore(gitignore_path)
                matchers.append(matcher)
            current = current.parent
        
        # Also check for .gitignore in the root directory
        root_gitignore = self.root_dir / '.gitignore'
        if root_gitignore.exists() and root_gitignore not in [m for m in matchers]:
            matchers.append(parse_gitignore(root_gitignore))
        
        return matchers
    
    def _is_ignored(self, file_path: Path) -> bool:
        """Check if a file should be ignored based on gitignore rules"""
        # Ensure we have an absolute path
        abs_path = file_path.absolute()
        
        # Check each gitignore matcher
        for matcher in self.gitignore_matchers:
            # gitignore-parser expects absolute paths
            if matcher(str(abs_path)):
                return True
        
        return False
    
    def _scan_code_files(self) -> List[Path]:
        """Scan for code files with supported extensions, respecting gitignore"""
        code_files = []
        
        for root, dirs, files in os.walk(self.root_dir):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if d not in self.ignored_dirs]
            
            # Also filter directories based on gitignore
            dirs[:] = [d for d in dirs if not self._is_ignored(Path(root) / d)]
            
            for file in files:
                file_path = Path(root) / file
                
                # Check if file has supported extension
                if file_path.suffix not in self.supported_extensions:
                    continue
                
                # Check if file is ignored by gitignore
                if self._is_ignored(file_path):
                    continue
                
                code_files.append(file_path)
        
        return sorted(code_files)
    
    def _categorize_files(self, current_state: Dict[str, str]) -> Tuple[List[Path], List[Path], List[str]]:
        new_files = []
        modified_files = []
        deleted_files = list(current_state.keys())
        
        for file_path in self._scan_code_files():
            str_path = str(file_path.relative_to(self.root_dir))
            file_hash = self._calculate_file_hash(file_path)
            
            if str_path in deleted_files:
                deleted_files.remove(str_path)
            
            if str_path not in current_state:
                new_files.append(file_path)
            elif current_state[str_path] != file_hash:
                modified_files.append(file_path)
        
        return new_files, modified_files, deleted_files
    
    async def _process_file(self, file_path: Path) -> List[Tuple[CodeChunk, str]]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Only use AST chunking for Python files
            if file_path.suffix == '.py':
                chunks = self.chunker.chunk(file_path, content)
            else:
                # For JS/TS files, treat the whole file as one chunk for now
                # TODO: Add proper JS/TS parsing in the future
                file_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
                chunk = CodeChunk(
                    id=f"{file_path}::file::{file_path.stem}",
                    file_path=str(file_path),
                    symbol_name=file_path.name,
                    symbol_type="file",
                    content=content,
                    content_hash=file_hash
                )
                chunks = [chunk]
            
            processed_results = []
            for chunk in chunks:
                processed_chunk = await self.embedding_generator.generate(chunk)
                processed_results.append((processed_chunk, self._calculate_file_hash(file_path)))
            
            return processed_results
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return []
    
    async def run(self):
        print("🚀 Starting code indexing...")
        
        current_state = self._load_index_state()
        new_files, modified_files, deleted_files = self._categorize_files(current_state)
        
        print(f"📊 Found: {len(new_files)} new, {len(modified_files)} modified, {len(deleted_files)} deleted files")
        
        for deleted_file in deleted_files:
            print(f"🗑️  Removing chunks for deleted file: {deleted_file}")
            self.vector_store.delete_for_file(deleted_file)
            del current_state[deleted_file]
        
        for modified_file in modified_files:
            relative_path = str(modified_file.relative_to(self.root_dir))
            print(f"🔄 Updating chunks for modified file: {relative_path}")
            self.vector_store.delete_for_file(relative_path)
        
        all_files_to_process = new_files + modified_files
        
        if all_files_to_process:
            print(f"\n📝 Processing {len(all_files_to_process)} files...")
            
            sem = asyncio.Semaphore(10)
            
            async def process_with_semaphore(file_path):
                async with sem:
                    return await self._process_file(file_path)
            
            tasks = [process_with_semaphore(f) for f in all_files_to_process]
            results = await asyncio.gather(*tasks)
            
            all_processed_chunks = []
            for file_path, file_results in zip(all_files_to_process, results):
                relative_path = str(file_path.relative_to(self.root_dir))
                
                for processed_chunk, file_hash in file_results:
                    all_processed_chunks.append(processed_chunk)
                
                if file_results:
                    current_state[relative_path] = file_results[0][1]
                    print(f"✅ Processed {len(file_results)} chunks from {relative_path}")
            
            if all_processed_chunks:
                print(f"\n💾 Storing {len(all_processed_chunks)} chunks in vector database...")
                self.vector_store.upsert(all_processed_chunks)
        
        self._save_index_state(current_state)
        print("\n✨ Indexing complete!")


async def main():
    import sys
    root_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    indexer = Indexer(root_dir=root_dir)
    await indexer.run()


if __name__ == "__main__":
    asyncio.run(main())
