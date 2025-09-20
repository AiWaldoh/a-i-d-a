from src.agent.tool_executor import ToolExecutor
from src.ai_shell.executor import CommandExecutor
from typing import Optional


class AIShellToolExecutor(ToolExecutor):
    
    def __init__(self, command_executor: Optional[CommandExecutor] = None, commands_dir="src/commands"):
        super().__init__(commands_dir)
        self.command_executor = command_executor
    
    def execute_tool(self, tool_name: str, params: dict) -> str:
        
        if tool_name == "run_command" and self.command_executor:
            command = params.get("command")
            if command:
                output, exit_code = self.command_executor.execute_command(command)
                
                formatted_output = ""
                if output:
                    formatted_output += f"STDOUT:\n{output.strip()}\n"
                if exit_code != 0:
                    formatted_output += f"STDERR:\nCommand failed\n"
                formatted_output += f"Return Code: {exit_code}"
                
                return formatted_output.strip()
        
        return super().execute_tool(tool_name, params)
