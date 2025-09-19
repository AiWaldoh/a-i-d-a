from abc import ABC, abstractmethod
from typing import Optional

from src.agent.repo_map import RepoMapBuilder
from src.rag.embedding_factory import get_embedding_function
from src.config.settings import AppSettings


class ContextStrategy(ABC):
    @abstractmethod
    async def build(self, user_prompt: str) -> str:
        pass


class NullContextStrategy(ContextStrategy):
    async def build(self, user_prompt: str) -> str:
        return ""


class ASTContextStrategy(ContextStrategy):
    def __init__(self, workspace_root: str = "."):
        self.repo_map_builder = RepoMapBuilder(workspace_root)
    
    async def build(self, user_prompt: str) -> str:
        return self.repo_map_builder.build_repo_map()


class RAGContextStrategy(ContextStrategy):
    def __init__(self, db_path: str = "db", collection_name: str = "codebase"):
        self.db_path = db_path
        self.collection_name = collection_name
        self._vector_store = None
    
    async def build(self, user_prompt: str) -> str:
        from src.rag.vector_store import VectorStore
        
        if self._vector_store is None:
            embedding_function = get_embedding_function()
            self._vector_store = VectorStore(
                db_path=self.db_path,
                collection_name=self.collection_name,
                embedding_function=embedding_function
            )
        
        # Get more results initially for filtering
        results = self._vector_store.query(user_prompt, top_k=20)
        
        if not results:
            return ""
        
        # Apply smart filtering logic
        selected_results = self._apply_smart_filtering(results)
        
        if not selected_results:
            return ""
        
        # Format context from selected results
        context_parts = ["### Relevant Code Context:\n"]
        for result in selected_results:
            chunk = result['chunk']
            similarity = result.get('similarity_score', 0)
            context_parts.append(f"\n📄 {chunk.file_path} - {chunk.symbol_type} {chunk.symbol_name} (similarity: {similarity:.1%})")
            context_parts.append(f"```python\n{chunk.content}\n```")
        
        return "\n".join(context_parts)
    
    def _apply_smart_filtering(self, results):
        """Apply smart filtering logic based on similarity threshold."""
        threshold = AppSettings.RAG_SIMILARITY_THRESHOLD
        max_chunks = AppSettings.RAG_MAX_CHUNKS
        fallback_chunks = AppSettings.RAG_FALLBACK_CHUNKS
        
        # Filter by similarity threshold
        high_quality = [r for r in results if r.get('similarity_score', 0) >= threshold]
        
        # Adaptive selection logic
        if len(high_quality) < max_chunks:
            # Not enough high-quality results, use fallback strategy
            print(f"🔍 RAG: Only {len(high_quality)} results above {threshold:.1%} threshold, using top {fallback_chunks} results")
            selected = results[:fallback_chunks]
        else:
            # Plenty of good results, take the best ones that meet threshold
            print(f"🎯 RAG: Found {len(high_quality)} results above {threshold:.1%} threshold, selecting top {max_chunks}")
            selected = high_quality[:max_chunks]
        
        return selected
