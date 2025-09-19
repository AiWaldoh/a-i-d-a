import chromadb.utils.embedding_functions as embedding_functions

from src.rag.vector_store import VectorStore


class Command:
    def execute(self, params: dict) -> str:
        query = params.get("query")
        if not query:
            return "Error: No query was provided to semantic_search."
        
        top_k = params.get("top_k", 5)
        
        try:
            embedding_function = embedding_functions.DefaultEmbeddingFunction()
            vector_store = VectorStore(
                db_path="db",
                collection_name="codebase",
                embedding_function=embedding_function
            )
            
            chunks = vector_store.query(query, top_k=top_k)
            
            if not chunks:
                return "No relevant code snippets found for your query."
            
            results = ["=== Semantic Search Results ===\n"]
            for i, chunk in enumerate(chunks, 1):
                results.append(f"{i}. {chunk.file_path} - {chunk.symbol_type} {chunk.symbol_name}")
                results.append(f"```python\n{chunk.content}\n```\n")
            
            return "\n".join(results)
            
        except Exception as e:
            return f"Error performing semantic search: {str(e)}"
