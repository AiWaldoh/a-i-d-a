#!/usr/bin/env python3
"""
Test script to verify command history integration
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['AI_CODER_PROJECT_ROOT'] = os.path.dirname(os.path.abspath(__file__))

from src.ai_shell.executor import CommandExecutor
from src.ai_shell.ai_tool_executor import AIShellToolExecutor


def test_command_history_integration():
    """Test that tool execution updates command history"""
    print("🧪 Testing Command History Integration\n")
    
    # Create executor and tool executor
    command_executor = CommandExecutor()
    tool_executor = AIShellToolExecutor(command_executor=command_executor)
    
    print("Initial command history:")
    history = command_executor.get_recent_history()
    print(f"  {len(history)} commands in history")
    
    print("\nExecuting command via tool executor:")
    result = tool_executor.execute_tool("run_command", {"command": "echo 'Test command'"})
    print(f"  Result: {result}")
    
    print("\nCommand history after tool execution:")
    history = command_executor.get_recent_history()
    print(f"  {len(history)} commands in history")
    
    if history:
        latest = history[-1]
        print(f"  Latest command: {latest['command']}")
        print(f"  Exit code: {latest['exit_code']}")
        print(f"  Output: {latest['output'][:50]}...")
    
    print("\nExecuting another command:")
    result = tool_executor.execute_tool("run_command", {"command": "pwd"})
    print(f"  Result: {result}")
    
    print("\nFinal command history:")
    history = command_executor.get_recent_history()
    print(f"  {len(history)} commands in history")
    
    for i, cmd in enumerate(history, 1):
        print(f"  {i}. {cmd['command']} (exit: {cmd['exit_code']})")


if __name__ == "__main__":
    test_command_history_integration()
