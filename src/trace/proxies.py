from datetime import datetime
import time
from typing import Optional, Dict, Any, List

from openai.types.chat import ChatCompletion

from src.llm.client import LLMClient
from src.agent.tool_executor import ToolExecutor
from src.trace.events import TraceContext, TaskEvent, EventSink


class LLMProxy:
    def __init__(self, real_client: LLMClient, trace_context: TraceContext, event_sink: EventSink):
        self.real_client = real_client
        self.trace_context = trace_context
        self.event_sink = event_sink
    
    async def get_response(
        self,
        messages: list,
        tools: list = None
    ) -> Optional[ChatCompletion]:
        self.event_sink.emit(TaskEvent(
            event_type="llm_request",
            trace_id=self.trace_context.trace_id,
            timestamp=datetime.now(),
            data={
                "messages": messages,
                "tools": tools
            }
        ))
        
        start_time = time.monotonic()
        response = await self.real_client.get_response(messages, tools)
        end_time = time.monotonic()
        duration = end_time - start_time

        response_data = {
            "response": None,
            "error": None,
            "duration_seconds": duration
        }
        
        if response:
            response_data["response"] = {
                "model": response.model,
                "choices": [
                    {
                        "message": {
                            "content": choice.message.content,
                            "role": choice.message.role
                        },
                        "finish_reason": choice.finish_reason
                    } for choice in response.choices
                ],
                "usage": response.usage.model_dump() if response.usage else None
            }
        else:
            response_data["error"] = "Failed to get response from LLM"
        
        self.event_sink.emit(TaskEvent(
            event_type="llm_response",
            trace_id=self.trace_context.trace_id,
            timestamp=datetime.now(),
            data=response_data
        ))
        
        return response


class ToolProxy:
    def __init__(self, real_executor: ToolExecutor, trace_context: TraceContext, event_sink: EventSink):
        self.real_executor = real_executor
        self.trace_context = trace_context
        self.event_sink = event_sink
    
    def execute_tool(self, tool_name: str, params: dict) -> str:
        self.event_sink.emit(TaskEvent(
            event_type="tool_request",
            trace_id=self.trace_context.trace_id,
            timestamp=datetime.now(),
            data={
                "tool_name": tool_name,
                "params": params
            }
        ))
        
        start_time = time.monotonic()
        output = self.real_executor.execute_tool(tool_name, params)
        end_time = time.monotonic()
        duration = end_time - start_time

        self.event_sink.emit(TaskEvent(
            event_type="tool_response",
            trace_id=self.trace_context.trace_id,
            timestamp=datetime.now(),
            data={
                "tool_name": tool_name,
                "output": output,
                "duration_seconds": duration
            }
        ))
        
        return output
