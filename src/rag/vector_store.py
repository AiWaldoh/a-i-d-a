import chromadb
from pathlib import Path
from typing import List, Any, Dict

from src.rag.chunker import CodeChunk
from src.rag.embedding import ProcessedChunk
from src.config.settings import AppSettings


class VectorStore:
    def __init__(self, db_path: str, collection_name: str, embedding_function: Any):
        self.db_path = Path(db_path)
        self.db_path.mkdir(exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=str(self.db_path))
        
        # Configure collection metadata based on distance metric
        collection_metadata = {
            "hnsw:space": AppSettings.CHROMADB_HNSW_SPACE,
            "hnsw:construction_ef": AppSettings.CHROMADB_HNSW_CONSTRUCTION_EF,
            "hnsw:M": AppSettings.CHROMADB_HNSW_M,
            "hnsw:search_ef": AppSettings.CHROMADB_HNSW_SEARCH_EF
        }
        
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=embedding_function,
            metadata=collection_metadata
        )
    
    def upsert(self, processed_chunks: List[ProcessedChunk]):
        if not processed_chunks:
            return
        
        ids = [chunk.chunk.id for chunk in processed_chunks]
        documents = [chunk.document for chunk in processed_chunks]
        metadatas = [
            {
                "file_path": chunk.chunk.file_path,
                "symbol_name": chunk.chunk.symbol_name,
                "symbol_type": chunk.chunk.symbol_type,
                "content_hash": chunk.chunk.content_hash,
                "summary": chunk.summary,
            }
            for chunk in processed_chunks
        ]
        
        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
    
    def delete_for_file(self, file_path: str):
        self.collection.delete(
            where={"file_path": {"$eq": file_path}}
        )
    
    def query(self, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Query with similarity scores for RAG filtering."""
        return self.query_with_scores(query_text, top_k)
    
    def query_chunks_only(self, query_text: str, top_k: int = 5) -> List[CodeChunk]:
        """Legacy method that returns only CodeChunk objects."""
        results = self.query_with_scores(query_text, top_k)
        return [result['chunk'] for result in results]
    
    def query_with_scores(self, query_text: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Query with full metadata including similarity scores and distances."""
        results = self.collection.query(
            query_texts=[query_text],
            n_results=top_k,
            include=['metadatas', 'documents', 'distances']
        )
        
        detailed_results = []
        if results['ids'] and results['ids'][0]:
            for i, chunk_id in enumerate(results['ids'][0]):
                metadata = results['metadatas'][0][i]
                document = results['documents'][0][i]
                distance = results['distances'][0][i] if results.get('distances') else None
                
                # Calculate similarity score based on distance metric
                if distance is not None:
                    if AppSettings.CHROMADB_DISTANCE_METRIC == "cosine":
                        # Cosine distance: similarity = 1 - distance (clamped to [0,1])
                        similarity_score = max(0, min(1, 1 - distance))
                    elif AppSettings.CHROMADB_DISTANCE_METRIC == "l2":
                        # Euclidean distance: convert to similarity (inverse relationship)
                        # Use exponential decay: similarity = exp(-distance)
                        import math
                        similarity_score = math.exp(-distance)
                    elif AppSettings.CHROMADB_DISTANCE_METRIC == "ip":
                        # Inner product: higher values = more similar (already similarity-like)
                        similarity_score = max(0, distance)  # IP can be negative, clamp to 0
                    else:
                        # Fallback: assume cosine
                        similarity_score = max(0, min(1, 1 - distance))
                else:
                    similarity_score = None
                
                summary = metadata.get('summary', '')
                content = document.replace(summary, '').strip()
                if content.startswith('\n\n'):
                    content = content[2:]
                
                detailed_results.append({
                    'chunk': CodeChunk(
                        id=chunk_id,
                        file_path=metadata['file_path'],
                        symbol_name=metadata['symbol_name'],
                        symbol_type=metadata['symbol_type'],
                        content=content,
                        content_hash=metadata['content_hash']
                    ),
                    'metadata': metadata,
                    'distance': distance,
                    'similarity_score': similarity_score,
                    'summary': summary,
                    'rank': i + 1
                })
        
        return detailed_results