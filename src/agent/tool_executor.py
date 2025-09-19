import os
import importlib.util
from pathlib import Path

class ToolExecutor:
    """
    Dynamically loads and executes tools from a specified command directory.
    This class acts as a plugin loader and dispatcher.
    """
    def __init__(self, commands_dir="src/commands"):
        self.commands_dir = Path(commands_dir)
        self.commands = self._load_commands()

    def _load_commands(self) -> dict:
        """
        Scans the commands directory, dynamically imports the Python files,
        and loads the Command class from each.
        """
        loaded_commands = {}
        for file_path in self.commands_dir.glob("*.py"):
            if file_path.name == "__init__.py":
                continue

            command_name = file_path.stem
            
            try:
                spec = importlib.util.spec_from_file_location(command_name, file_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                if hasattr(module, "Command"):
                    loaded_commands[command_name] = module.Command()
                else:
                    print(f"Warning: No 'Command' class found in {file_path.name}")

            except Exception as e:
                print(f"Error loading command from {file_path.name}: {e}")

        print(f"✅ Loaded {len(loaded_commands)} commands: {list(loaded_commands.keys())}")
        return loaded_commands

    def execute_tool(self, tool_name: str, params: dict) -> str:
        """
        Executes a specified tool by finding it in the loaded commands
        and calling its execute method.
        """
        if tool_name in self.commands:
            command = self.commands[tool_name]
            try:
                return command.execute(params)
            except Exception as e:
                return f"Error executing tool '{tool_name}': {e}"
        else:
            return f"Error: Unknown tool '{tool_name}'"
