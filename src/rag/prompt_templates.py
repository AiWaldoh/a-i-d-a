import yaml
from pathlib import Path
from typing import Dict, Any

from src.utils.paths import get_absolute_path


class PromptTemplateManager:
    def __init__(self, file_path: str = None):
        if file_path is None:
            self.file_path = get_absolute_path("prompts.yaml")
        else:
            self.file_path = Path(file_path)
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, str]:
        try:
            from src.utils.paths import read_config_file
            # Extract just the filename from the path
            filename = self.file_path.name if hasattr(self.file_path, 'name') else str(self.file_path).split('/')[-1]
            content = read_config_file(filename)
            data = yaml.safe_load(content)
            if not isinstance(data, dict):
                raise ValueError(f"Invalid prompt template file format: {self.file_path}")
            return data
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt template file not found: {self.file_path}")
    
    def get(self, template_name: str, **kwargs) -> str:
        if template_name not in self.templates:
            available = ", ".join(self.templates.keys())
            raise KeyError(f"Template '{template_name}' not found. Available templates: {available}")
        
        template = self.templates[template_name]
        
        try:
            return template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing required template variable: {e}")
    
    def reload(self):
        self.templates = self._load_templates()
    
    def list_templates(self) -> list[str]:
        return list(self.templates.keys())
