import json
import asyncio
from typing import Tuple, Optional, List

from src.llm.client import LLMClient
from src.config.settings import AppSettings


class CommandClassifier:
    
    def __init__(self):
        self.llm_client = LLMClient(AppSettings.LLM_CONFIG)
        self.classification_cache = {}
        
        self.classification_tools = [{
            "type": "function",
            "function": {
                "name": "classify_input",
                "description": "Determine if input is a Linux command or natural language",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "is_command": {
                            "type": "boolean",
                            "description": "True if input is a Linux command, False if natural language"
                        },
                        "confidence": {
                            "type": "number",
                            "description": "Confidence level 0-1",
                            "minimum": 0,
                            "maximum": 1
                        },
                        "reasoning": {
                            "type": "string",
                            "description": "Brief explanation of the classification"
                        }
                    },
                    "required": ["is_command", "confidence"]
                }
            }
        }]
        
        self.obvious_commands = [
            'ls', 'cd', 'pwd', 'git', 'vim', 'vi', 'nano', 'cat', 'grep', 
            'ps', 'top', 'htop', 'df', 'du', 'cp', 'mv', 'rm', 
            'mkdir', 'rmdir', 'touch', 'echo', 'export', 'source', 'chmod',
            'chown', 'tar', 'gzip', 'gunzip', 'ssh', 'scp', 'curl', 'wget',
            'python', 'python3', 'pip', 'npm', 'docker', 'make', 'gcc',
            'apt', 'apt-get', 'sudo', 'which', 'clear', 'history', 'man'
        ]
        
        self.command_patterns = ['|', '&&', '||', '>', '>>', '<', ';', '$(', '`', '&']
        
        self.nl_starters = [
            'what', 'how', 'why', 'when', 'where', 'who', 'which',
            'can you', 'could you', 'please', 'help', 'explain', 
            'show me', 'tell me', 'fix', 'debug', 'solve', 'find',
            'list the', 'display the', 'get the', 'give me'
        ]
    
    def is_obvious_command(self, text: str) -> bool:
        
        text = text.strip()
        if not text:
            return False
        
        first_word = text.split()[0] if text.split() else ""
        
        # Special handling for "find" - check if it's actually a command vs natural language
        if first_word == "find":
            # If it's followed by typical find patterns, it's a command
            if len(text.split()) > 1:
                second_word = text.split()[1]
                # Command patterns: find . find / find ~ find -name find -type
                if second_word.startswith(('.', '/', '~', '-')) or second_word in ['/', '.', '~']:
                    return True
                # Natural language patterns: find the, find my, find all
                elif second_word.lower() in ['the', 'my', 'all', 'a', 'an', 'some']:
                    return False
            # Default to natural language for ambiguous "find"
            return False
        
        if first_word in self.obvious_commands:
            return True
        
        if any(pattern in text for pattern in self.command_patterns):
            return True
        
        if text.startswith('./') or text.startswith('/') or text.startswith('~'):
            return True
        
        if '=' in first_word and not ' ' in text.split('=')[0]:
            return True
        
        return False
    
    def is_obvious_natural_language(self, text: str) -> bool:
        
        text = text.strip().lower()
        if not text:
            return False
        
        if text.endswith('?'):
            return True
        
        if any(text.startswith(starter) for starter in self.nl_starters):
            return True
        
        error_keywords = ['error', 'fail', 'wrong', 'broken', 'issue', 'problem']
        if any(keyword in text for keyword in error_keywords):
            return True
        
        conversational_phrases = ['thanks', 'thank you', 'hi', 'hello', 'please help']
        if any(phrase in text for phrase in conversational_phrases):
            return True
        
        return False
    
    async def classify(self, user_input: str, command_history: Optional[List[dict]] = None) -> Tuple[bool, float]:
        
        user_input = user_input.strip()
        
        cache_key = f"{user_input}:{len(command_history) if command_history else 0}"
        if cache_key in self.classification_cache:
            return self.classification_cache[cache_key]
        
        if self.is_obvious_command(user_input):
            result = (True, 0.95)
            self.classification_cache[cache_key] = result
            return result
        
        if self.is_obvious_natural_language(user_input):
            result = (False, 0.95)
            self.classification_cache[cache_key] = result
            return result
        
        try:
            is_command, confidence = await self._classify_with_ai(user_input, command_history)
            result = (is_command, confidence)
            self.classification_cache[cache_key] = result
            return result
        except Exception as e:
            print(f"Classification error: {e}")
            return (True, 0.1)
    
    async def _classify_with_ai(self, user_input: str, command_history: Optional[List[dict]] = None) -> Tuple[bool, float]:
        
        context = ""
        if command_history:
            recent = command_history[-3:]
            context = "\nRecent commands:\n"
            for cmd in recent:
                context += f"$ {cmd['command']} (exit: {cmd.get('exit_code', 'N/A')})\n"
        
        messages = [
            {
                "role": "system", 
                "content": """Classify if user input is a Linux command or natural language request.
                
Commands include: shell commands, scripts, program names, file paths.
Natural language includes: questions, requests for help, conversational text, error descriptions.

Consider the context of recent commands when classifying ambiguous input."""
            },
            {
                "role": "user", 
                "content": f"Classify this input: '{user_input}'{context}"
            }
        ]
        
        response = await self.llm_client.get_response(
            messages=messages, 
            tools=self.classification_tools
        )
        
        if response and response.choices and response.choices[0].message.tool_calls:
            tool_call = response.choices[0].message.tool_calls[0]
            args = json.loads(tool_call.function.arguments)
            return args.get("is_command", True), args.get("confidence", 0.5)
        
        return True, 0.1
