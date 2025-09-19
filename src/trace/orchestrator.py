import uuid
import time
from datetime import datetime

from src.agent.agent import Agent
from src.agent.tool_executor import ToolExecutor
from src.llm.client import LLMClient
from src.trace.events import EventSink, TraceContext, TaskEvent
from src.trace.proxies import LLMProxy, ToolProxy
from src.rag.strategy import ContextStrategy, NullContextStrategy, ASTContextStrategy, RAGContextStrategy
from src.config.settings import AppSettings


class TaskOrchestrator:
    def __init__(self, event_sink: EventSink, context_mode: str = "none"):
        self.event_sink = event_sink
        self.context_mode = context_mode
        self.strategy = self._create_strategy(context_mode)
    
    def _create_strategy(self, mode: str) -> ContextStrategy:
        if mode == "ast":
            return ASTContextStrategy()
        elif mode == "rag":
            return RAGContextStrategy()
        else:
            return NullContextStrategy()
    
    async def execute_task(self, user_request: str) -> str:
        trace_id = str(uuid.uuid4())
        
        trace_context = TraceContext(
            trace_id=trace_id,
            user_request=user_request,
            start_time=datetime.now()
        )
        
        self.event_sink.emit(TaskEvent(
            event_type="task_started",
            trace_id=trace_id,
            timestamp=datetime.now(),
            data={
                "user_request": user_request,
                "context_mode": self.context_mode
            }
        ))
        
        try:
            context_start_time = time.monotonic()
            context = await self.strategy.build(user_request)
            context_duration = time.monotonic() - context_start_time
            
            self.event_sink.emit(TaskEvent(
                event_type="context_build_completed",
                trace_id=trace_id,
                timestamp=datetime.now(),
                data={
                    "strategy": self.context_mode,
                    "duration_seconds": context_duration,
                    "context_length": len(context),
                    "context": context  # Include the actual context
                }
            ))
            
            augmented_request = user_request
            if context:
                augmented_request = f"{context}\n\n### User Request:\n{user_request}"
            
            real_llm_client = LLMClient()
            real_tool_executor = ToolExecutor()
            
            llm_proxy = LLMProxy(real_llm_client, trace_context, self.event_sink)
            tool_proxy = ToolProxy(real_tool_executor, trace_context, self.event_sink)
            
            agent = Agent(
                llm_client=llm_proxy,
                tool_executor=tool_proxy,
                max_steps=AppSettings.MAX_STEPS,
                context_mode=self.context_mode
            )
            
            result = await agent.run(augmented_request)
            
            self.event_sink.emit(TaskEvent(
                event_type="task_completed",
                trace_id=trace_id,
                timestamp=datetime.now(),
                data={
                    "result": result,
                    "duration_seconds": (datetime.now() - trace_context.start_time).total_seconds()
                }
            ))
            
            return result
            
        except Exception as e:
            self.event_sink.emit(TaskEvent(
                event_type="task_failed",
                trace_id=trace_id,
                timestamp=datetime.now(),
                data={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "duration_seconds": (datetime.now() - trace_context.start_time).total_seconds()
                }
            ))
            raise
