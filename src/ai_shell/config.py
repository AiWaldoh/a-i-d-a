import os
import yaml
from dataclasses import dataclass
from pathlib import Path
from src.utils.paths import get_absolute_path


@dataclass
class AIShellConfig:
    max_history: int = 1000
    max_command_history: int = 50
    
    prompt_color: bool = True
    
    classification_confidence_threshold: float = 0.7
    context_commands: int = 5
    classifier_commands: int = 3
    max_output_length: int = 1000
    
    ssh_host: str = "localhost"
    ssh_user: str = os.getenv('USER', 'user')
    
    cache_ttl_seconds: int = 3600
    
    api_timeout_seconds: int = 10
    command_timeout_seconds: int = 30
    
    dangerous_commands_require_confirmation: bool = True
    dangerous_patterns = [
        r'rm\s+-rf\s+/',
        r'sudo\s+rm',
        r'>\s*/dev/sd[a-z]',
        r'mkfs\.',
        r'dd\s+if=.*of=/dev'
    ]
    
    history_file: Path = Path.home() / ".ai_shell_history"
    
    show_token_usage: bool = True
    
    enable_suggestions: bool = True
    
    debug_mode: bool = os.getenv('AI_SHELL_DEBUG', '').lower() == 'true'


def _load_ai_shell_config() -> AIShellConfig:
    """Load AI Shell configuration from main config.yaml"""
    try:
        config_path = get_absolute_path("config.yaml")
        with open(config_path, "r") as f:
            yaml_config = yaml.safe_load(f) or {}
        
        ai_shell_config = yaml_config.get("ai_shell", {})
        
        return AIShellConfig(
            context_commands=ai_shell_config.get("context_commands", 5),
            classifier_commands=ai_shell_config.get("classifier_commands", 3),
            max_command_history=ai_shell_config.get("max_history", 50),
            max_output_length=ai_shell_config.get("max_output_length", 1000),
            classification_confidence_threshold=ai_shell_config.get("classification_confidence_threshold", 0.7),
        )
    except Exception as e:
        print(f"Warning: Could not load AI Shell config from config.yaml: {e}")
        return AIShellConfig()


ai_shell_config = _load_ai_shell_config()
