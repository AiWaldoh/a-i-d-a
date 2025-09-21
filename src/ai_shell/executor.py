import os
import tempfile
import subprocess
import paramiko
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Tuple, Dict, List, Optional
from src.ai_shell.config import ai_shell_config


class CommandExecutor:
    
    def __init__(self):
        self.ssh = self._setup_ssh()
        self.command_history: List[Dict] = []
        self.current_directory = os.getcwd()
        self.max_history = ai_shell_config.max_command_history
        
        self.stateful_commands = ['cd', 'export', 'alias', 'unalias', 'source', '.']
        
        self._sync_initial_state()
    
    def _setup_ssh(self) -> Optional[paramiko.SSHClient]:
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            ssh.connect(
                hostname="localhost",
                username=os.getenv('USER'),
                look_for_keys=True,
                allow_agent=True
            )
            
            return ssh
        except Exception as e:
            print(f"⚠️  SSH setup failed: {e}")
            print("Falling back to local execution mode")
            return None
    
    def _sync_initial_state(self):
        
        if self.ssh:
            try:
                # Don't change the local directory - just sync SSH to match local
                self.ssh.exec_command(f"cd {self.current_directory}")
            except Exception as e:
                print(f"Initial SSH directory sync failed: {e}")
    
    def execute_command(self, command: str) -> Tuple[str, int]:
        
        if self.is_stateful_command(command):
            return self.execute_stateful_command(command)
        
        if self.ssh:
            return self._execute_via_ssh(command)
        else:
            return self._execute_locally(command)
    
    def _execute_via_ssh(self, command: str) -> Tuple[str, int]:
        
        try:
            full_command = f"cd {self.current_directory} && {command}"
            
            stdin, stdout, stderr = self.ssh.exec_command(full_command, get_pty=True)
            
            stdout_text = stdout.read().decode('utf-8', errors='replace')
            stderr_text = stderr.read().decode('utf-8', errors='replace')
            exit_code = stdout.channel.recv_exit_status()
            
            output = stdout_text
            if stderr_text:
                output += stderr_text
            
            self._add_to_history(command, output, exit_code)
            
            return output, exit_code
            
        except Exception as e:
            error_msg = f"SSH execution failed: {e}"
            self._add_to_history(command, error_msg, 1)
            return error_msg, 1
    
    def _execute_locally(self, command: str) -> Tuple[str, int]:
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=self.current_directory,
                timeout=30
            )
            
            output = result.stdout
            if result.stderr:
                output += result.stderr
            
            self._add_to_history(command, output, result.returncode)
            
            return output, result.returncode
            
        except subprocess.TimeoutExpired:
            error_msg = "Command timed out after 30 seconds"
            self._add_to_history(command, error_msg, 1)
            return error_msg, 1
        except Exception as e:
            error_msg = f"Local execution failed: {e}"
            self._add_to_history(command, error_msg, 1)
            return error_msg, 1
    
    def execute_stateful_command(self, command: str) -> Tuple[str, int]:
        
        if command.strip().startswith('cd'):
            return self._handle_cd_command(command)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write(f"#!/bin/bash\n")
            f.write(f"cd {self.current_directory}\n")
            f.write(f"{command}\n")
            f.write(f"pwd\n")
            f.write(f"echo '---ENV_START---'\n")
            f.write(f"env\n")
            f.write(f"echo '---ENV_END---'\n")
            temp_file = f.name
        
        try:
            result = subprocess.run(
                f"bash {temp_file}",
                shell=True,
                capture_output=True,
                text=True
            )
            
            self._parse_state_changes(result.stdout)
            
            self._add_to_history(command, result.stdout, result.returncode)
            
            if self.ssh:
                self._sync_ssh_state()
            
            return result.stdout, result.returncode
            
        finally:
            os.unlink(temp_file)
    
    def _handle_cd_command(self, command: str) -> Tuple[str, int]:
        
        parts = command.strip().split(maxsplit=1)
        
        if len(parts) == 1:
            target = os.path.expanduser("~")
        else:
            target = parts[1]
            target = os.path.expanduser(target)
        
        if not os.path.isabs(target):
            target = os.path.join(self.current_directory, target)
        
        target = os.path.normpath(target)
        
        try:
            if os.path.exists(target) and os.path.isdir(target):
                old_dir = self.current_directory
                self.current_directory = target
                os.chdir(target)
                
                if self.ssh:
                    self.ssh.exec_command(f"cd {target}")
                
                output = f"Changed directory from {old_dir} to {target}"
                self._add_to_history(command, output, 0)
                return "", 0
            else:
                error = f"cd: {target}: No such file or directory"
                self._add_to_history(command, error, 1)
                return error, 1
                
        except Exception as e:
            error = f"cd: {e}"
            self._add_to_history(command, error, 1)
            return error, 1
    
    def _parse_state_changes(self, output: str):
        
        lines = output.strip().split('\n')
        
        for i, line in enumerate(lines):
            if line and os.path.exists(line):
                potential_pwd = line.strip()
                if os.path.isdir(potential_pwd):
                    self.current_directory = potential_pwd
                    os.chdir(potential_pwd)
                    break
        
        if '---ENV_START---' in output and '---ENV_END---' in output:
            start = output.find('---ENV_START---') + len('---ENV_START---')
            end = output.find('---ENV_END---')
            env_section = output[start:end].strip()
            
    def _sync_ssh_state(self):
        
        if not self.ssh:
            return
        
        try:
            self.ssh.exec_command(f"cd {self.current_directory}")
        except Exception as e:
            print(f"SSH state sync failed: {e}")
    
    def _add_to_history(self, command: str, output: str, exit_code: int):
        
        entry = {
            'command': command,
            'output': output[:ai_shell_config.max_output_length],  # Limit output size
            'exit_code': exit_code,
            'directory': self.current_directory,
            'timestamp': datetime.now().isoformat()
        }
        
        self.command_history.append(entry)
        
        if len(self.command_history) > self.max_history:
            self.command_history = self.command_history[-self.max_history:]
    
    def is_stateful_command(self, command: str) -> bool:
        
        first_word = command.strip().split()[0] if command.strip() else ""
        return first_word in self.stateful_commands
    
    def get_recent_history(self, n: int = 10) -> List[Dict]:
        
        return self.command_history[-n:] if self.command_history else []
    
    def get_current_directory(self) -> str:
        
        return self.current_directory
    
    def cleanup(self):
        
        if self.ssh:
            try:
                self.ssh.close()
            except:
                pass
