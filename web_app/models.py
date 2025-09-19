from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from datetime import datetime

class WorkflowContext(BaseModel):
    user_request: str
    current_step: int
    total_steps_completed: int

class Usage(BaseModel):
    completion_tokens: int
    prompt_tokens: int
    total_tokens: int
    completion_tokens_details: Optional[Dict[str, Any]] = None
    prompt_tokens_details: Optional[Dict[str, Any]] = None

class Message(BaseModel):
    role: str
    content: str

class Choice(BaseModel):
    index: int
    message: Message
    finish_reason: str

class FullResponse(BaseModel):
    id: str
    object: str
    created: int
    model: str
    choices: List[Choice]
    usage: Usage
    system_fingerprint: Optional[str] = None

class LLMMetrics(BaseModel):
    api_call_id: int
    timestamp: str
    duration_seconds: float
    model: str
    reasoning_effort: str
    verbosity: str
    workflow_context: WorkflowContext
    usage: Usage
    full_response: FullResponse

class MetricsFile(BaseModel):
    metrics: List[LLMMetrics]
    total_calls: int
    total_duration: float
    total_tokens: int
    avg_duration_per_call: float
    models_used: List[str]
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
