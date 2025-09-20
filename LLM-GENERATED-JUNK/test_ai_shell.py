#!/usr/bin/env python3
"""
Test script to demonstrate AI Shell capabilities
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ai_shell.classifier import CommandClassifier
from src.ai_shell.executor import CommandExecutor


async def test_classification():
    """Test the command classification system"""
    print("🧪 Testing Command Classification\n")
    
    classifier = CommandClassifier()
    
    test_inputs = [
        # Obvious commands
        ("ls -la", "Obvious command"),
        ("git status", "Obvious command"),
        ("cd /tmp", "Obvious command"),
        ("python3 script.py", "Obvious command"),
        
        # Obvious natural language
        ("what files are here?", "Obvious natural language"),
        ("how do I list files?", "Obvious natural language"),
        ("fix the last error", "Obvious natural language"),
        ("help me with git", "Obvious natural language"),
        
        # Ambiguous cases
        ("show logs", "Ambiguous - could be command or request"),
        ("restart server", "Ambiguous - could be script name"),
        ("check status", "Ambiguous - needs context"),
    ]
    
    for input_text, description in test_inputs:
        # Check heuristics first
        if classifier.is_obvious_command(input_text):
            classification = "Command (heuristic)"
            confidence = 0.95
        elif classifier.is_obvious_natural_language(input_text):
            classification = "Natural Language (heuristic)"
            confidence = 0.95
        else:
            # Would use AI classification for ambiguous cases
            classification = "Ambiguous (would use AI)"
            confidence = 0.5
        
        print(f"Input: '{input_text}'")
        print(f"  → {classification} (confidence: {confidence})")
        print(f"  Description: {description}\n")


def test_execution():
    """Test command execution"""
    print("\n🧪 Testing Command Execution\n")
    
    executor = CommandExecutor()
    
    # Test basic commands
    test_commands = [
        "echo 'Hello from AI Shell'",
        "pwd",
        "ls -la | head -5",
        "date",
    ]
    
    for command in test_commands:
        print(f"Executing: {command}")
        output, exit_code = executor.execute_command(command)
        print(f"Exit code: {exit_code}")
        if output:
            print(f"Output:\n{output}")
        print("-" * 50)
    
    # Test directory change
    print("\n🧪 Testing State Preservation (cd command)\n")
    
    original_dir = executor.get_current_directory()
    print(f"Original directory: {original_dir}")
    
    # Change to /tmp
    output, exit_code = executor.execute_command("cd /tmp")
    print(f"After 'cd /tmp': {executor.get_current_directory()}")
    
    # Execute command in new directory
    output, exit_code = executor.execute_command("pwd")
    print(f"pwd output: {output.strip()}")
    
    # Change back
    output, exit_code = executor.execute_command(f"cd {original_dir}")
    print(f"After changing back: {executor.get_current_directory()}")
    
    # Test command history
    print("\n🧪 Testing Command History\n")
    
    history = executor.get_recent_history(5)
    print(f"Recent {len(history)} commands:")
    for h in history:
        status = "✅" if h['exit_code'] == 0 else "❌"
        print(f"  {status} {h['command']} (in {h['directory']})")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("AI Shell Test Suite")
    print("=" * 60)
    
    # Test classification
    await test_classification()
    
    # Test execution
    test_execution()
    
    print("\n✨ All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
