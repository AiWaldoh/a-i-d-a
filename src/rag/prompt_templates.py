import yaml
from pathlib import Path
from typing import Dict, Any


class PromptTemplateManager:
    def __init__(self, file_path: str = "prompts.yaml"):
        self.file_path = Path(file_path)
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, str]:
        if not self.file_path.exists():
            raise FileNotFoundError(f"Prompt template file not found: {self.file_path}")
        
        with open(self.file_path, 'r') as f:
            data = yaml.safe_load(f)
            if not isinstance(data, dict):
                raise ValueError(f"Invalid prompt template file format: {self.file_path}")
            return data
    
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
