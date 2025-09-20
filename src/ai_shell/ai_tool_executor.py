from src.agent.tool_executor import ToolExecutor
from src.utils.paths import get_absolute_path


class AIShellToolExecutor(ToolExecutor):
    
    def __init__(self, commands_dir=None):
        # Use absolute path to commands directory
        if commands_dir is None:
            commands_dir = str(get_absolute_path("src/commands"))
        super().__init__(commands_dir)
    
    def execute_tool(self, tool_name: str, params: dict) -> str:
        # Let all tools use the standard execution path
        # This ensures working_directory and other params are respected
        return super().execute_tool(tool_name, params)
