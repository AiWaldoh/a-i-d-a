import yaml
from typing import List, Dict, Any
from src.agent.repo_map import RepoMapBuilder
from src.rag.prompt_templates import PromptTemplateManager

class PromptManager:
    """
    Manages the creation and formatting of prompts sent to the LLM,
    separating the logic of the agent from the art of prompt engineering.
    """
    
    def __init__(self, context_mode: str = "none"):
        self.context_mode = context_mode
        self.repo_map_builder = RepoMapBuilder() if context_mode == "ast" else None
        self.template_manager = PromptTemplateManager()

    def build_messages(self, history: List[Dict[str, Any]], tools_yaml_path: str = "tools.yaml") -> List[Dict[str, Any]]:
        """
        Builds a structured list of messages for the LLM, including the system prompt.

        Args:
            history: A list of messages representing the conversation so far.
            tools_yaml_path: The path to the YAML file defining the available tools.

        Returns:
            A list of message dictionaries ready to be sent to the LLM.
        """
        system_prompt = self._get_system_prompt(tools_yaml_path)
        
        # The system prompt is the first message, followed by the entire conversation history.
        return [{"role": "system", "content": system_prompt}] + history


    def _get_system_prompt(self, tools_yaml_path: str) -> str:
        """Constructs the main system prompt based on context mode."""
        if self.context_mode == "none":
            return self.template_manager.get("agent_system_prompt_none")
        elif self.context_mode == "ast":
            repo_map = self.repo_map_builder.build_repo_map()
            return self.template_manager.get("agent_system_prompt_ast", repo_map=repo_map)
        elif self.context_mode == "rag":
            return self.template_manager.get("agent_system_prompt_rag")
        else:
            # Fallback to none mode for unknown context modes
            return self.template_manager.get("agent_system_prompt_none")
