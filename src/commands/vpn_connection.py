import subprocess
import threading
import time
from pathlib import Path


class Command:
    def execute(self, params: dict) -> str:
        config_file = params.get("config_file")
        if not config_file:
            return "Error: No config_file provided to openvpn."
        
        config_path = Path(config_file)
        if not config_path.exists():
            return f"Error: Config file '{config_file}' not found."
        
        try:
            # Start OpenVPN process
            process = subprocess.Popen(
                ["sudo", "openvpn", "--config", str(config_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Monitor output for success/failure
            success = False
            output_lines = []
            start_time = time.time()
            timeout = 30  # 30 second timeout
            
            while time.time() - start_time < timeout:
                line = process.stdout.readline()
                if line:
                    output_lines.append(line.strip())
                    
                    # Check for success indicator
                    if "Initialization Sequence Completed" in line:
                        success = True
                        break
                    
                    # Check for common failure indicators
                    if any(fail_str in line.lower() for fail_str in [
                        "auth failed", "authentication failed", 
                        "connection refused", "network unreachable",
                        "tls handshake failed", "certificate verify failed"
                    ]):
                        break
                
                # Check if process has terminated
                if process.poll() is not None:
                    break
                
                time.sleep(0.1)
            
            if success:
                # Kill the process since we just wanted to test connection
                process.terminate()
                return "✅ VPN connection successful"
            else:
                # Process failed or timed out
                process.terminate()
                error_output = "\n".join(output_lines[-5:])  # Last 5 lines
                return f"❌ VPN connection failed:\n{error_output}"
                
        except Exception as e:
            return f"Error connecting to VPN: {str(e)}"
