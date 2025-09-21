from src.agent.tool_executor import ToolExecutor
from src.utils.paths import get_absolute_path


class AIShellToolExecutor(ToolExecutor):
    
    def __init__(self, commands_dir=None, command_executor=None):
        # Use absolute path to commands directory
        if commands_dir is None:
            commands_dir = str(get_absolute_path("src/commands"))
        super().__init__(commands_dir)
        self.command_executor = command_executor
    
    def execute_tool(self, tool_name: str, params: dict) -> str:
        # Auto-inject current working directory for tools that support it
        if self.command_executor:
            current_dir = self.command_executor.get_current_directory()
            
            # For run_command: inject run_in_directory if not specified
            if tool_name == 'run_command' and 'run_in_directory' not in params:
                params = params.copy()
                params['run_in_directory'] = current_dir
            
            # For file_search: inject search_dir if not specified
            elif tool_name == 'file_search' and 'search_dir' not in params:
                params = params.copy()
                params['search_dir'] = current_dir
        
        return super().execute_tool(tool_name, params)
