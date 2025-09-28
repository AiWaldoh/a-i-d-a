import subprocess
import shutil


class Command:
    def execute(self, params: dict) -> str:
        ip_address = params.get("ip_address")
        if not ip_address:
            return "Error: No IP address provided for autorecon_scan."
        
        # Get autorecon path
        autorecon_path = shutil.which("autorecon")
        if not autorecon_path:
            return "Error: AutoRecon not found."
        
        # Build command: sudo $(which autorecon) <ip>
        command = f"sudo {autorecon_path} {ip_address}"
        
        try:
            process = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                check=False
            )
            
            output = ""
            if process.stdout:
                output += process.stdout
            if process.stderr:
                output += process.stderr
            
            if process.returncode != 0:
                output = f"❌ COMMAND FAILED\n{output}\nExit Code: {process.returncode}"
            
            return output.strip() if output.strip() else "✓ AutoRecon completed"
            
        except Exception as e:
            return f"Error running AutoRecon: {str(e)}"
