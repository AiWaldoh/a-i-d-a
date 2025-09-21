from typing import List, Dict, Any
import yaml

from src.agent.memory import Message
from src.utils.paths import get_absolute_path


class PromptBuilder:
    def __init__(self, context_mode: str = "none"):
        self.context_mode = context_mode
        self._load_prompts()
    
    def _load_prompts(self):
        try:
            with open(get_absolute_path("prompts.yaml"), 'r') as f:
                self.prompts = yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading prompts: {e}")
            self.prompts = {}
    
    def build(self, summary: str, recent: List[Message], tools: List[Dict[str, Any]], 
              user_text: str, repo_context: str = "") -> List[Dict[str, str]]:
        messages = []
        
        system_prompt = self._build_system_prompt(tools, repo_context)
        messages.append({"role": "system", "content": system_prompt})
        
        if summary:
            messages.append({
                "role": "system", 
                "content": f"Previous conversation summary:\n{summary}"
            })
        
        for msg in recent:
            if msg.role == "tool":
                messages.append({
                    "role": "tool",
                    "tool_call_id": msg.meta.get("tool_call_id", ""),
                    "content": msg.content
                })
            elif msg.role == "assistant" and msg.meta and "tool_calls" in msg.meta:
                messages.append({
                    "role": "assistant",
                    "content": msg.content,
                    "tool_calls": msg.meta["tool_calls"]
                })
            else:
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        # Don't add user_text again - it's already in recent messages
        
        return messages
    
    def _build_system_prompt(self, tools: List[Dict[str, Any]], repo_context: str) -> str:
        prompt_key = f"agent_system_prompt_{self.context_mode}"
        base_prompt = self.prompts.get(prompt_key, "You are a helpful AI assistant.")
        
        if self.context_mode == "ast" and repo_context:
            base_prompt = base_prompt.replace("{repo_map}", repo_context)
        
        return base_prompt

