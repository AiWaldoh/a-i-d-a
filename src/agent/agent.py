import json
import yaml
import time
from typing import List, Dict, Any, Optional, Tuple

from src.llm.client import LLMClient
from src.agent.tool_executor import ToolExecutor
from src.agent.memory import MemoryPort, Message
from src.agent.prompt_builder import PromptBuilder
from src.utils.paths import get_absolute_path

# Try to import tiktoken for accurate token counting. If unavailable, fall back to a
# conservative character-based estimate (4 chars ~= 1 token).
try:
    import tiktoken
except Exception:
    tiktoken = None


def count_tokens_for_model(text: str, model: str = "gpt-4") -> int:
    """Count tokens for `text` using tiktoken if available.

    Defaults to the encoding appropriate for `model` (gpt-4). If tiktoken is not
    available, uses a conservative fallback estimate.
    """
    if not text:
        return 0
    if tiktoken:
        try:
            enc = tiktoken.encoding_for_model(model)
        except Exception:
            # Fall back to a general-purpose encoding if model-specific encoding fails
            enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    # Conservative fallback: assume ~4 characters per token
    return max(1, len(text) // 4)


def format_params_with_color(params: Dict[str, Any]) -> str:
    def format_value(v):
        if isinstance(v, str):
            return f"\033[93m'{v}'\033[0m"  # Yellow for strings
        elif isinstance(v, bool):  # Check bool before int/float since bool is subclass of int
            return f"\033[95m{v}\033[0m"  # Magenta for booleans
        elif isinstance(v, (int, float)):
            return f"\033[96m{v}\033[0m"  # Cyan for numbers
        elif isinstance(v, dict):
            return "{" + ", ".join([f"\033[94m{k}\033[0m: {format_value(v2)}" for k, v2 in v.items()]) + "}"
        elif isinstance(v, list):
            return "[" + ", ".join([format_value(item) for item in v]) + "]"
        else:
            return str(v)
    
    formatted_items = []
    for k, v in params.items():
        formatted_items.append(f"\033[94m{k}\033[0m: {format_value(v)}")
    
    return "{" + ", ".join(formatted_items) + "}"


class Agent:
    """
    The main orchestrator for the ReAct agent. It manages the conversation
    and the Reason-Act loop to fulfill user requests.
    """

    def __init__(self, thread_id: str, memory: MemoryPort, llm_client: LLMClient, 
                 tool_executor: ToolExecutor, prompt_builder: PromptBuilder,
                 max_steps: int = None, keep_last: int = None):
        from src.config.settings import AppSettings
        
        self.thread_id = thread_id
        self.memory = memory
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.prompt_builder = prompt_builder
        self.max_steps = max_steps if max_steps is not None else AppSettings.MAX_STEPS
        self.keep_last = keep_last if keep_last is not None else AppSettings.KEEP_LAST
        self._scratch: List[Dict[str, Any]] = []
        self.tools = self._load_tools()
    
    def _load_tools(self) -> List[Dict[str, Any]]:
        """Load tools from tools.yaml and convert to OpenAI format."""
        try:
            with open(get_absolute_path("tools.yaml"), 'r') as f:
                tools_config = yaml.safe_load(f)
            
            openai_tools = []
            for tool in tools_config.get("tools", []):
                openai_tool = {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool["description"],
                        "parameters": tool["schema"]
                    }
                }
                openai_tools.append(openai_tool)
            
            return openai_tools
        except Exception as e:
            print(f"Error loading tools: {e}")
            return []

    async def step(self, user_prompt: str, repo_context: str = "") -> Tuple[str, int]:
        """
        Runs the agent's ReAct loop to process a user prompt.
        Returns a tuple of (response, tokens_used).
        """
        self.memory.append(self.thread_id, Message(role="user", content=user_prompt))
        
        summary = self.memory.summary(self.thread_id)
        recent = self.memory.last_events(self.thread_id, self.keep_last)
        
        self._scratch = []
        total_tokens = 0

        for i in range(self.max_steps):
            # 1. Build the structured list of messages for the LLM
            messages = self.prompt_builder.build(summary, recent, self.tools, user_prompt, repo_context)
            
            # 2. Get the full response object from the LLM with tools
            response = await self.llm_client.get_response(messages=messages, tools=self.tools)
            
            if not response or not response.choices:
                error_message = "❌ Agent failed to get a valid response from the LLM. Stopping."
                print(error_message)
                self.memory.append(self.thread_id, Message(role="assistant", content=error_message))
                return error_message, total_tokens
            
            if response.usage:
                total_tokens += response.usage.total_tokens
            
            message = response.choices[0].message
            
            # Check if the model wants to use tools
            if hasattr(message, 'tool_calls') and message.tool_calls:
                # Track tool calls in memory
                tool_calls_data = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    } for tc in message.tool_calls
                ]
                
                recent.append(Message(
                    role="assistant",
                    content=message.content or "",
                    meta={"tool_calls": tool_calls_data}
                ))
                
                # Execute each tool call
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        # Parse the arguments (they come as JSON string)
                        params = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        error_msg = f"Failed to parse arguments for {tool_name}: {tool_call.function.arguments}"
                        print(f"❌ {error_msg}")
                        recent.append(Message(
                            role="tool",
                            content=error_msg,
                            meta={"tool_call_id": tool_call.id}
                        ))
                        continue
                    
                    # Extract and display reasoning
                    reasoning = params.get('reasoning', 'No reasoning provided')
                    colored_params = format_params_with_color(params)
                    print(f"🎬 \033[92mAction\033[0m: Executing tool \033[91m'{tool_name}'\033[0m with params: {colored_params}")
                    
                    # Execute the tool
                    tool_start_time = time.time()
                    tool_output = self.tool_executor.execute_tool(tool_name, params)
                    tool_duration = time.time() - tool_start_time
                    
                    # Track in scratch memory
                    self._scratch.append({
                        "action": tool_name,
                        "args": params,
                        "observation": str(tool_output),
                        "duration": tool_duration,
                        "timestamp": time.time()
                    })
                    
                    # Add tool result to recent messages
                    recent.append(Message(
                        role="tool",
                        content=str(tool_output),
                        meta={"tool_call_id": tool_call.id}
                    ))
                
                # Continue to next iteration to get the model's response after tool execution
                continue
            
            # If no tool calls, check if there's a regular response
            if message.content:
                # This is the final answer
                final_response = message.content
                
                # Save to memory with scratch trace
                self.memory.append(self.thread_id, Message(
                    role="assistant",
                    content=final_response,
                    meta={"scratch": self._scratch}
                ))
                
                # Maybe roll up summary if conversation getting long
                self._maybe_rollup_summary()
                
                # Clear scratch for next turn
                self._scratch = []
                
                return final_response, total_tokens
            else:
                print("⚠️ LLM provided neither tool calls nor content. Stopping.")
                error_msg = "Agent stopped due to empty LLM response."
                self.memory.append(self.thread_id, Message(
                    role="assistant",
                    content=error_msg,
                    meta={"scratch": self._scratch}
                ))
                return error_msg, total_tokens

        # Reached max steps
        timeout_msg = f"Agent stopped after reaching max steps ({self.max_steps})."
        self.memory.append(self.thread_id, Message(
            role="assistant",
            content=timeout_msg,
            meta={"scratch": self._scratch}
        ))
        return timeout_msg, total_tokens
    
    def _maybe_rollup_summary(self):
        # NOTE: user requested we do not automatically trim the conversation. We still
        # compute an accurate token count (using gpt-4 encoding when possible) for
        # diagnostics, but we do not modify the stored summary.
        events = self.memory.last_events(self.thread_id, 40)
        tokens = sum(count_tokens_for_model(m.content, model="gpt-4") for m in events)
        # Token count tracked internally - removed verbose logging
