import uuid
from typing import Optional, Tuple

from src.agent.agent import Agent
from src.agent.memory import MemoryPort, InMemoryMemory
from src.agent.prompt_builder import PromptBuilder
from src.llm.client import LLMClient
from src.agent.tool_executor import ToolExecutor

_DEFAULT = object()

class ChatSession:
    def __init__(self, memory: Optional[MemoryPort] = None, llm_client: Optional[LLMClient] = None,
                 tool_executor = _DEFAULT, prompt_builder: Optional[PromptBuilder] = None,
                 thread_id: Optional[str] = None, context_mode: str = "none", max_steps: int = 50,
                 personality_llm: Optional[LLMClient] = None):
        self.thread_id = thread_id or str(uuid.uuid4())
        self.memory = memory or InMemoryMemory()
        self.llm_client = llm_client or LLMClient()
        self.tool_executor = ToolExecutor() if tool_executor is _DEFAULT else tool_executor
        self.prompt_builder = prompt_builder or PromptBuilder(context_mode=context_mode)
        self.context_mode = context_mode
        self.total_tokens = 0
        
        self.agent = Agent(
            thread_id=self.thread_id,
            memory=self.memory,
            llm_client=self.llm_client,
            tool_executor=self.tool_executor,
            prompt_builder=self.prompt_builder,
            max_steps=max_steps,
            personality_llm=personality_llm
        )
    
    async def ask(self, user_text: str, repo_context: str = "") -> Tuple[str, int]:
        response, tokens_used = await self.agent.step(user_text, repo_context)
        self.total_tokens += tokens_used
        return response, tokens_used
    
    def get_history(self):
        return self.memory.last_events(self.thread_id, n=100)
    
    def get_summary(self):
        return self.memory.summary(self.thread_id)

