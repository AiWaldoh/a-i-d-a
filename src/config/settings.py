import os
import yaml
from pathlib import Path
from dataclasses import asdict
from dotenv import load_dotenv

from src.llm.types import LLMConfig
from src.utils.paths import get_absolute_path


class AppSettings:
    load_dotenv(get_absolute_path('.env'))

    _config_path = get_absolute_path("config.yaml")
    if not _config_path.exists():
        raise FileNotFoundError(f"Configuration file not found at: {_config_path}")

    with open(_config_path, "r") as f:
        _yaml = yaml.safe_load(f) or {}

    if "llm_configs" not in _yaml or "llm_providers" not in _yaml:
        raise ValueError("'config.yaml' is missing 'llm_configs' or 'llm_providers'.")

    # Get the worker_llm model name from llm_configs (used as default for all execution tasks)
    if "worker_llm" not in _yaml["llm_configs"]:
        raise ValueError("'llm_configs' is missing 'worker_llm' configuration.")
    
    _agent_model_name = _yaml["llm_configs"]["worker_llm"]
    if _agent_model_name not in _yaml["llm_providers"]:
        raise ValueError(f"Model '{_agent_model_name}' referenced by worker_llm not found in llm_providers.")
    
    _llm_yaml = _yaml["llm_providers"][_agent_model_name]


    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    API_KEY = OPENROUTER_API_KEY or OPENAI_API_KEY
    if not API_KEY:
        raise ValueError("API key not found. Set OPENROUTER_API_KEY or OPENAI_API_KEY.")

    BASE_URL = os.getenv("OPENROUTER_BASE_URL", _llm_yaml["base_url"])
    MODEL = os.getenv("GPT_MODEL", _llm_yaml["model"])
    TIMEOUT = int(os.getenv("GPT_TIMEOUT", _llm_yaml["timeout"]))
    MAX_RETRIES = int(os.getenv("GPT_MAX_RETRIES", _llm_yaml.get("max_retries", 3)))
    REASONING_EFFORT = os.getenv("REASONING_EFFORT", _llm_yaml.get("reasoning_effort"))
    VERBOSITY = os.getenv("VERBOSITY", _llm_yaml.get("verbosity"))
    
    # New model-specific params
    TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", _llm_yaml.get("temperature"))) if _llm_yaml.get("temperature") is not None else None
    TOP_P = float(os.getenv("LLM_TOP_P", _llm_yaml.get("top_p"))) if _llm_yaml.get("top_p") is not None else None
    MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", _llm_yaml.get("max_tokens"))) if _llm_yaml.get("max_tokens") is not None else None
    RESPONSE_PARSER = os.getenv("LLM_RESPONSE_PARSER", _llm_yaml.get("response_parser"))
    
    # Agent configuration
    MAX_STEPS = int(os.getenv("MAX_STEPS", _yaml.get("max_steps", 10)))
    KEEP_LAST = int(os.getenv("KEEP_LAST", _yaml.get("keep_last", 20)))
    
    # Embedding configuration
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", _yaml.get("embedding", {}).get("model", "all-MiniLM-L6-v2"))
    
    # ChromaDB configuration
    _chromadb_config = _yaml.get("chromadb", {})
    CHROMADB_DISTANCE_METRIC = os.getenv("CHROMADB_DISTANCE_METRIC", _chromadb_config.get("distance_metric", "cosine"))
    CHROMADB_HNSW_SPACE = os.getenv("CHROMADB_HNSW_SPACE", _chromadb_config.get("hnsw_space", "cosine"))
    CHROMADB_HNSW_CONSTRUCTION_EF = int(os.getenv("CHROMADB_HNSW_CONSTRUCTION_EF", _chromadb_config.get("hnsw_construction_ef", 200)))
    CHROMADB_HNSW_M = int(os.getenv("CHROMADB_HNSW_M", _chromadb_config.get("hnsw_m", 16)))
    CHROMADB_HNSW_SEARCH_EF = int(os.getenv("CHROMADB_HNSW_SEARCH_EF", _chromadb_config.get("hnsw_search_ef", 10)))
    
    # RAG configuration
    _rag_config = _yaml.get("rag", {})
    RAG_SIMILARITY_THRESHOLD = float(os.getenv("RAG_SIMILARITY_THRESHOLD", _rag_config.get("similarity_threshold", 0.3)))
    RAG_MAX_CHUNKS = int(os.getenv("RAG_MAX_CHUNKS", _rag_config.get("max_chunks", 10)))
    RAG_FALLBACK_CHUNKS = int(os.getenv("RAG_FALLBACK_CHUNKS", _rag_config.get("fallback_chunks", 10)))
    
    # Brain configuration
    _brain_config = _yaml.get("brain", {})
    BRAIN_MAX_ITERATIONS = int(os.getenv("BRAIN_MAX_ITERATIONS", _brain_config.get("max_iterations", 50)))
    BRAIN_DEFAULT_GOAL = os.getenv("BRAIN_DEFAULT_GOAL", _brain_config.get("default_goal", "Complete penetration test"))
    BRAIN_DETAILED_LOGGING = os.getenv("BRAIN_DETAILED_LOGGING", str(_brain_config.get("enable_detailed_logging", True))).lower() == 'true'
    BRAIN_PAUSE_ITERATIONS = int(os.getenv("BRAIN_PAUSE_ITERATIONS", _brain_config.get("pause_between_iterations", 1)))


    # Default LLM_CONFIG (uses agent_llm configuration)
    # Used by default LLMClient() instantiations in main.py, session.py, etc.
    LLM_CONFIG = LLMConfig(
        api_key=API_KEY,
        base_url=BASE_URL,
        model=MODEL,
        timeout=TIMEOUT,
        max_retries=MAX_RETRIES,
        reasoning_effort=REASONING_EFFORT,
        verbosity=VERBOSITY,
        temperature=TEMPERATURE,
        top_p=TOP_P,
        max_tokens=MAX_TOKENS,
        response_parser=RESPONSE_PARSER,
    )

    @classmethod
    def get_llm_config_by_model(cls, model_name: str) -> LLMConfig:
        """Get LLM configuration for a specific model"""
        if model_name not in cls._yaml["llm_providers"]:
            raise ValueError(f"Model '{model_name}' not found in llm_providers.")
        
        model_config = cls._yaml["llm_providers"][model_name]
        
        return LLMConfig(
            api_key=cls.API_KEY,
            base_url=model_config["base_url"],
            model=model_config["model"],
            timeout=model_config["timeout"],
            max_retries=model_config.get("max_retries", 3),
            reasoning_effort=model_config.get("reasoning_effort"),
            verbosity=model_config.get("verbosity"),
            temperature=float(model_config["temperature"]) if model_config.get("temperature") is not None else None,
            top_p=float(model_config["top_p"]) if model_config.get("top_p") is not None else None,
            max_tokens=int(model_config["max_tokens"]) if model_config.get("max_tokens") is not None else None,
            response_parser=model_config.get("response_parser"),
        )
    
    @classmethod
    def get_llm_config(cls, situation: str) -> LLMConfig:
        """Get LLM configuration for a specific situation/use case"""
        if situation not in cls._yaml["llm_configs"]:
            raise ValueError(f"Situation '{situation}' not found in llm_configs.")
        
        model_name = cls._yaml["llm_configs"][situation]
        return cls.get_llm_config_by_model(model_name)

    @classmethod
    def as_dict(cls) -> dict:
        return {
            "agent": {
                "max_steps": cls.MAX_STEPS,
            },
            "llm": {
                "base_url": cls.BASE_URL,
                "model": cls.MODEL,
                "timeout": cls.TIMEOUT,
                "max_retries": cls.MAX_RETRIES,
                "reasoning_effort": cls.REASONING_EFFORT,
                "verbosity": cls.VERBOSITY,
                "temperature": cls.TEMPERATURE,
                "top_p": cls.TOP_P,
                "max_tokens": cls.MAX_TOKENS,
                "response_parser": cls.RESPONSE_PARSER,
            }
        }
