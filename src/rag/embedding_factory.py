import chromadb.utils.embedding_functions as embedding_functions
from src.config.settings import AppSettings


def get_embedding_function():
    """Get embedding function based on config - shared between indexer and web UI."""
    model_name = AppSettings.EMBEDDING_MODEL
    
    if model_name == "all-MiniLM-L6-v2":
        return embedding_functions.DefaultEmbeddingFunction()
    elif model_name.startswith("text-embedding-"):
        return embedding_functions.OpenAIEmbeddingFunction(
            api_key=AppSettings.API_KEY,
            model_name=model_name
        )
    else:
        return embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=model_name
        )
