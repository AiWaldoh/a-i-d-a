import os
import sys
import subprocess
import shutil
from datetime import datetime
from pathlib import Path


class Command:
    def execute(self, params: dict) -> str:
        reasoning = params.get('reasoning', 'Restarting shell')
        backup_current = params.get('backup_current', True)
        preserve_session = params.get('preserve_session', False)
        
        try:
            # Get project root
            project_root = os.environ.get('AI_CODER_PROJECT_ROOT', os.getcwd())
            
            # Create backup if requested
            if backup_current:
                self._create_backup(project_root)
            
            # Determine the correct restart command
            aida_shell_path = os.path.join(project_root, 'aida-shell')
            
            if not os.path.exists(aida_shell_path):
                return f"Error: aida-shell not found at {aida_shell_path}"
            
            # Prepare restart command
            restart_cmd = [aida_shell_path]
            
            # Add debug flag if currently in debug mode
            if os.environ.get('AI_SHELL_DEBUG') == 'true':
                restart_cmd.append('--debug')
            
            # Print restart message
            print(f"\n🔄 Restarting AI Shell: {reasoning}")
            print("📦 New tools and configurations will be loaded...")
            
            # Use os.execv to replace the current process
            # This ensures a clean restart without subprocess overhead
            os.execv(aida_shell_path, restart_cmd)
            
            # This line should never be reached
            return "Restart initiated"
            
        except Exception as e:
            return f"Error restarting shell: {e}"
    
    def _create_backup(self, project_root: str) -> None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(project_root, "tmp", f"backup_{timestamp}")
        
        os.makedirs(backup_dir, exist_ok=True)
        
        # Backup critical files
        files_to_backup = [
            "tools.yaml",
            "config.yaml", 
            "prompts.yaml",
            "src/commands/",
            "src/ai_shell/"
        ]
        
        for item in files_to_backup:
            src_path = os.path.join(project_root, item)
            if os.path.exists(src_path):
                dst_path = os.path.join(backup_dir, item)
                
                if os.path.isdir(src_path):
                    shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    shutil.copy2(src_path, dst_path)
        
        print(f"💾 Backup created: {backup_dir}")
