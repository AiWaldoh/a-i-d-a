import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AIShellConfig:
    max_history: int = 1000
    max_command_history: int = 50
    
    prompt_color: bool = True
    
    classification_confidence_threshold: float = 0.7
    context_commands: int = 5
    
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


ai_shell_config = AIShellConfig()
