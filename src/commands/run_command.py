import subprocess

class Command:
    """
    This class is dynamically loaded by the ToolExecutor.
    The name of the file (e.g., 'run_command.py') is the tool name.
    """
    def execute(self, params: dict) -> str:
        """
        Executes a shell command and returns its output.
        
        Args:
            params: A dictionary containing:
                    - command (str): The shell command to run (supports shell operators like &&, ||, |)
                    - run_in_directory (str, optional): Directory to execute the command in
                    - timeout (int, optional): Timeout in seconds (default: 30)
        
        Returns:
            The formatted output of the command, including stdout, stderr, and return code.
        """
        command = params.get("command")
        if not command:
            return "Error: No command was provided to run_command."
            
        # Check if we have a run_in_directory parameter
        run_in_directory = params.get("run_in_directory")
        
        try:
            # Always use shell=True - simple and works with all commands
            process = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                check=False,
                timeout=params.get("timeout", 30),
                cwd=run_in_directory
            )
            
            output = ""
            if process.stdout:
                output += f"{process.stdout.strip()}\n"
            if process.stderr:
                output += f"ERROR OUTPUT:\n{process.stderr.strip()}\n"
            
            if process.returncode != 0:
                output += f"Exit Code: {process.returncode}"
                
            # Mark as failed if non-zero exit code
            if process.returncode != 0:
                output = f"❌ COMMAND FAILED\n{output}"
            
            return output.strip()

        except subprocess.TimeoutExpired:
            timeout_val = params.get("timeout", 30)
            return f"Error: The command timed out after {timeout_val} seconds."
        except Exception as e:
            return f"An unexpected error occurred while running the command: {str(e)}"
