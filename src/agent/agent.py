import json
import yaml
from typing import List, Dict, Any, Optional

from src.llm.client import LLMClient
from src.agent.tool_executor import ToolExecutor
from src.agent.prompt_manager import PromptManager


# --- Main Agent Class ---

class Agent:
    """
    The main orchestrator for the ReAct agent. It manages the conversation
    and the Reason-Act loop to fulfill user requests.
    """

    def __init__(self, llm_client: LLMClient, tool_executor: ToolExecutor, max_steps: int = 50, context_mode: str = "none"):
        """
        Initializes the Agent.

        Args:
            llm_client: The client for interacting with the Language Model.
            tool_executor: The executor for running tools.
            max_steps: The maximum number of steps the agent can take.
            context_mode: The context strategy mode (none, ast, rag).
        """
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.prompt_manager = PromptManager(context_mode=context_mode)
        self.max_steps = max_steps
        self.history: List[Dict[str, Any]] = []
        self.tools = self._load_tools()
    
    def _load_tools(self) -> List[Dict[str, Any]]:
        """Load tools from tools.yaml and convert to OpenAI format."""
        try:
            with open("tools.yaml", 'r') as f:
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

    async def run(self, user_prompt: str) -> Optional[str]:
        """
        Runs the agent's ReAct loop to process a user prompt.
        """
        # print(f"🚀 Starting agent with request: '{user_prompt}'")
        self.history.append({"role": "user", "content": user_prompt})

        for i in range(self.max_steps):
            # print(f"\n--- Step {i + 1}/{self.max_steps} ---")

            # 1. Build the structured list of messages for the LLM
            messages = self.prompt_manager.build_messages(self.history)
            
            # 2. Get the full response object from the LLM with tools
            response = await self.llm_client.get_response(messages=messages, tools=self.tools)
            
            if not response or not response.choices:
                error_message = "❌ Agent failed to get a valid response from the LLM. Stopping."
                print(error_message)
                return error_message
            
            message = response.choices[0].message
            
            # Check if the model wants to use tools
            if hasattr(message, 'tool_calls') and message.tool_calls:
                # Add the assistant's message with tool calls to history
                self.history.append({
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in message.tool_calls
                    ]
                })
                
                # Execute each tool call
                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        # Parse the arguments (they come as JSON string)
                        params = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        error_msg = f"Failed to parse arguments for {tool_name}: {tool_call.function.arguments}"
                        print(f"❌ {error_msg}")
                        self.history.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": error_msg
                        })
                        continue
                    
                    # Extract and display reasoning
                    reasoning = params.get('reasoning', 'No reasoning provided')
                    print(f"🤔 Reasoning: {reasoning}")
                    print(f"🎬 Action: Executing tool '{tool_name}' with params: {params}")
                    
                    # Execute the tool
                    tool_output = self.tool_executor.execute_tool(tool_name, params)
                    
                    # Add tool result to history
                    self.history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(tool_output)
                    })
                
                # Continue to next iteration to get the model's response after tool execution
                continue
            
            # If no tool calls, check if there's a regular response
            if message.content:
                # Add the assistant's response to history
                self.history.append({"role": "assistant", "content": message.content})
                
                # For now, treat any non-tool response as final answer
                # (In a more sophisticated system, you might parse for specific markers)
                return message.content
            else:
                print("⚠️ LLM provided neither tool calls nor content. Stopping.")
                return "Agent stopped due to empty LLM response."

        # print(f"\n🚫 Agent stopped after reaching max steps ({self.max_steps}).")
        return "Agent stopped after reaching max steps."
