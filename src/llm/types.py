from dataclasses import dataclass

@dataclass
class LLMConfig:
    api_key: str
    base_url: str
    model: str
    timeout: int
    max_retries: int
    reasoning_effort: str = None
    verbosity: str = None
    temperature: float = None
    top_p: float = None
    max_tokens: int = None
    response_parser: str = None
