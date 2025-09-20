from typing import List, Dict, Any
import yaml

from src.agent.memory import Message


class PromptBuilder:
    def __init__(self, context_mode: str = "none"):
        self.context_mode = context_mode
        self._load_prompts()
    
    def _load_prompts(self):
        try:
            with open("prompts.yaml", 'r') as f:
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
        
        messages.append({"role": "user", "content": user_text})
        
        return messages
    
    def _build_system_prompt(self, tools: List[Dict[str, Any]], repo_context: str) -> str:
        base_prompt = self.prompts.get("agent", {}).get("system_prompt", "You are a helpful AI assistant.")
        
        if self.context_mode == "ast" and repo_context:
            base_prompt = f"{repo_context}\n\n{base_prompt}"
        
        return base_prompt

