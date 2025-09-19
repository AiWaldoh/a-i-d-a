import subprocess
import shlex

class Command:
    """
    This class is dynamically loaded by the ToolExecutor.
    The name of the file (e.g., 'run_command.py') is the tool name.
    """
    def execute(self, params: dict) -> str:
        """
        Executes a shell command and returns its output.
        
        Args:
            params: A dictionary containing the command to execute.
                    - command (str): The shell command to run.
        
        Returns:
            The formatted output of the command, including stdout, stderr, and return code.
        """
        command = params.get("command")
        if not command:
            return "Error: No command was provided to run_command."
            
        try:
            process = subprocess.run(
                shlex.split(command),
                capture_output=True,
                text=True,
                check=False,
                timeout=90
            )
            
            output = ""
            if process.stdout:
                output += f"STDOUT:\n{process.stdout.strip()}\n"
            if process.stderr:
                output += f"STDERR:\n{process.stderr.strip()}\n"
            
            output += f"Return Code: {process.returncode}"
            
            return output.strip()

        except FileNotFoundError:
            return f"Error: The command '{command.split()[0]}' was not found."
        except subprocess.TimeoutExpired:
            return "Error: The command timed out after 90 seconds."
        except Exception as e:
            return f"An unexpected error occurred while running the command: {str(e)}"
