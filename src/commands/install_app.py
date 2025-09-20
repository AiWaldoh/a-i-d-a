import subprocess

class Command:
    def execute(self, params: dict) -> str:
        packages = params.get("packages")
        if not packages:
            return "Error: No packages provided to install_app."
        
        if isinstance(packages, str):
            package_list = [packages]
        elif isinstance(packages, list):
            package_list = packages
        else:
            return "Error: packages must be a string or list of strings."
        
        cmd = [
            "sudo",
            "apt",
            "install",
            "-y",
            "--no-install-recommends",
            "--quiet"
        ] + package_list
        
        try:
            env = {
                **subprocess.os.environ,
                "DEBIAN_FRONTEND": "noninteractive"
            }
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                env=env
            )
            
            output = ""
            if result.stdout:
                output += f"STDOUT:\n{result.stdout.strip()}\n"
            if result.stderr:
                output += f"STDERR:\n{result.stderr.strip()}\n"
            
            output += f"Return Code: {result.returncode}"
            
            if result.returncode == 0:
                output += f"\n\nSuccessfully installed: {', '.join(package_list)}"
            else:
                output += f"\n\nFailed to install: {', '.join(package_list)}"
            
            return output.strip()
            
        except subprocess.TimeoutExpired:
            return "Error: Installation timed out after 300 seconds."
        except Exception as e:
            return f"Error installing packages: {str(e)}"
