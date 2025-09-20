import readline
import os
import signal
import glob
import asyncio
import re
from pathlib import Path
from datetime import datetime
from typing import Optional

from src.ai_shell.classifier import CommandClassifier
from src.ai_shell.executor import CommandExecutor
from src.ai_shell.config import ai_shell_config
from src.ai_shell.ai_tool_executor import AIShellToolExecutor
from src.agent.session import ChatSession
from src.config.settings import AppSettings


class AIShell:
    
    def __init__(self):
        print("🤖 Initializing AI Shell...")
        
        # Store original working directory
        self.original_cwd = os.getcwd()
        
        # Store project root for later use
        project_root = os.environ.get('AI_CODER_PROJECT_ROOT', os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        
        self.classifier = CommandClassifier()
        self.executor = CommandExecutor()
        
        # Create custom tool executor that integrates with our command executor
        tool_executor = AIShellToolExecutor(command_executor=self.executor)
        
        # Create chat session (this will use get_absolute_path to find tools.yaml)
        self.chat_session = ChatSession(
            context_mode="none",
            tool_executor=tool_executor
        )
        
        self.running = True
        self.config = ai_shell_config
        
        self._setup_readline()
        self._setup_signals()
        
        print("✅ AI Shell ready! Type commands or ask questions naturally.")
        print("💡 Examples: 'ls', 'what files are here?', 'fix the last error'")
        print("🚪 Type 'exit' or Ctrl-D to quit\n")
    
    def _setup_readline(self):
        
        readline.parse_and_bind("tab: complete")
        readline.parse_and_bind("set editing-mode emacs")
        readline.parse_and_bind("set completion-ignore-case on")
        readline.set_completer(self._complete)
        readline.set_completer_delims(" \t\n`!@#$%^&*()=+[{]}\\|;:'\",<>?")
        
        try:
            readline.read_history_file(str(self.config.history_file))
            readline.set_history_length(self.config.max_history)
        except FileNotFoundError:
            pass
        
        import atexit
        atexit.register(self._save_history)
    
    def _save_history(self):
        
        try:
            readline.write_history_file(str(self.config.history_file))
        except Exception as e:
            if self.config.debug_mode:
                print(f"Could not save history: {e}")
    
    def _setup_signals(self):
        
        def signal_handler(sig, frame):
            print()  # New line after ^C
            # Don't exit, just return to prompt
        
        signal.signal(signal.SIGINT, signal_handler)
    
    def _complete(self, text, state):
        
        try:
            if not text:
                matches = [f for f in os.listdir('.') if not f.startswith('.')]
            elif text.startswith('/') or text.startswith('./') or text.startswith('~/'):
                expanded = os.path.expanduser(text)
                matches = glob.glob(expanded + '*')
                if text.startswith('./'):
                    matches = [m[2:] if m.startswith('./') else m for m in matches]
            else:
                matches = []
                
                for path_dir in os.environ.get('PATH', '').split(':'):
                    if os.path.isdir(path_dir):
                        try:
                            executables = [
                                f for f in os.listdir(path_dir) 
                                if f.startswith(text) and 
                                os.access(os.path.join(path_dir, f), os.X_OK)
                            ]
                            matches.extend(executables)
                        except (PermissionError, OSError):
                            continue
                
                local_files = [f for f in os.listdir('.') if f.startswith(text)]
                matches.extend(local_files)
                
                matches = list(set(matches))
            
            matches.sort()
            return matches[state] if state < len(matches) else None
            
        except (OSError, IndexError):
            return None
    
    def _get_prompt(self):
        
        cwd = self.executor.get_current_directory()
        home = os.path.expanduser("~")
        if cwd.startswith(home):
            cwd = cwd.replace(home, "~", 1)
        
        user = os.getenv('USER', 'user')
        host = os.uname().nodename.split('.')[0]  # Short hostname
        
        if self.config.prompt_color:
            GREEN = '\033[32m'
            CYAN = '\033[36m'
            RESET = '\033[0m'
            return f"{GREEN}{user}@{host}{CYAN}:{cwd}{RESET}$ "
        else:
            return f"{user}@{host}:{cwd}$ "
    
    async def _process_input(self, user_input: str):
        
        user_input = user_input.strip()
        
        if not user_input:
            return
        
        readline.add_history(user_input)
        
        if user_input == 'exit':
            self.running = False
            return
        
        if user_input == 'history':
            self._show_history()
            return
        
        if user_input == 'help':
            self._show_help()
            return
        
        try:
            command_history = self.executor.get_recent_history()
            is_command, confidence = await self.classifier.classify(user_input, command_history)
            
            if self.config.debug_mode:
                print(f"[DEBUG] Classification: is_command={is_command}, confidence={confidence}")
            
            if is_command:
                await self._execute_command(user_input)
            else:
                await self._ask_ai(user_input)
                
        except Exception as e:
            print(f"❌ Error processing input: {e}")
            if self.config.debug_mode:
                import traceback
                traceback.print_exc()
    
    async def _execute_command(self, command: str):
        
        if self._is_dangerous_command(command):
            print(f"⚠️  WARNING: This command appears dangerous: {command}")
            confirm = input("Are you sure you want to execute it? (yes/no): ")
            if confirm.lower() != 'yes':
                print("Command cancelled.")
                return
        
        try:
            output, exit_code = await asyncio.to_thread(
                self.executor.execute_command, command
            )
            
            if output and output.strip():
                print(output)
            
            if exit_code != 0 and self.config.enable_suggestions:
                recent_error = self.executor.get_recent_history(1)[0]
                if recent_error and recent_error['exit_code'] != 0:
                    print(f"\n💡 Command failed. Type 'fix' or 'what went wrong?' for help.")
                    
        except Exception as e:
            print(f"❌ Command execution failed: {e}")
    
    async def _ask_ai(self, prompt: str):
        
        try:
            context = self._build_context_from_history()
            
            if context:
                full_prompt = f"{prompt}\n\nContext:\n{context}"
            else:
                full_prompt = prompt
            
            response, tokens_used = await self.chat_session.ask(full_prompt)
            
            print(f"\n🤖 {response}")
            
            if self.config.show_token_usage:
                print(f"\n💡 Tokens used: {tokens_used}")
            
        except Exception as e:
            print(f"❌ AI request failed: {e}")
            if self.config.debug_mode:
                import traceback
                traceback.print_exc()
    
    def _build_context_from_history(self) -> str:
        
        recent_history = self.executor.get_recent_history(self.config.context_commands)
        
        if not recent_history:
            return f"Current directory: {self.executor.get_current_directory()}"
        
        context_parts = [f"Current directory: {self.executor.get_current_directory()}\n"]
        context_parts.append("Recent commands:")
        
        for h in recent_history:
            context_parts.append(f"\n$ {h['command']}")
            
            if h['output']:
                output = h['output']
                if len(output) > 200:
                    output = output[:200] + "... (truncated)"
                context_parts.append(output)
            
            if h['exit_code'] != 0:
                context_parts.append(f"(exit code: {h['exit_code']})")
        
        return "\n".join(context_parts)
    
    def _is_dangerous_command(self, command: str) -> bool:
        
        if not self.config.dangerous_commands_require_confirmation:
            return False
        
        for pattern in self.config.dangerous_patterns:
            if re.search(pattern, command, re.IGNORECASE):
                return True
        
        return False
    
    def _show_history(self):
        
        history = self.executor.get_recent_history(20)
        
        if not history:
            print("No command history available")
            return
        
        print("\nRecent commands:")
        print("-" * 60)
        
        for i, h in enumerate(history, 1):
            timestamp = datetime.fromisoformat(h['timestamp']).strftime("%H:%M:%S")
            status = "✅" if h['exit_code'] == 0 else "❌"
            directory = h['directory'].replace(os.path.expanduser("~"), "~")
            
            print(f"{i:2d}. [{timestamp}] {status} {directory}> {h['command']}")
    
    def _show_help(self):
        
        print("""
🤖 AI Shell Help

This is an AI-enhanced shell that understands both Linux commands and natural language.

Examples:
  ls -la                    # Regular command
  what files are here?      # Natural language query
  fix the last error        # AI analyzes recent failed commands
  go to my home directory   # AI might suggest: cd ~
  
Features:
  • Arrow keys for history navigation
  • Tab completion for files and commands  
  • Ctrl-R for reverse history search
  • Ctrl-C to cancel current input
  • Full command history tracking
  • Context-aware AI assistance

Built-in commands:
  exit     - Quit the shell
  history  - Show recent commands with timestamps
  help     - Show this help

Tips:
  • The AI remembers your recent commands and their output
  • Ask "what went wrong?" after a failed command
  • Say "fix" to get help with the last error
  • Natural language questions work naturally
        """)
    
    async def run(self):
        
        while self.running:
            try:
                user_input = await asyncio.to_thread(input, self._get_prompt())
                await self._process_input(user_input)
                
            except EOFError:
                print("\n👋 Goodbye!")
                break
            except KeyboardInterrupt:
                continue
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                if self.config.debug_mode:
                    import traceback
                    traceback.print_exc()
        
        self.executor.cleanup()
        print("✨ AI Shell session ended.")


async def main():
    
    shell = AIShell()
    await shell.run()


if __name__ == "__main__":
    asyncio.run(main())
