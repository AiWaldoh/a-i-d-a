#!/usr/bin/env python3
"""
Demo script to test AI Shell functionality
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set project root for proper initialization
os.environ['AI_CODER_PROJECT_ROOT'] = os.path.dirname(os.path.abspath(__file__))

from src.ai_shell.classifier import CommandClassifier
from src.ai_shell.executor import CommandExecutor


async def test_classification():
    """Test the classification system"""
    print("🧪 Testing Classification\n")
    
    classifier = CommandClassifier()
    
    test_cases = [
        ("ls -la", "Should be command"),
        ("list the files in the current folder", "Should be natural language"),
        ("what files are here?", "Should be natural language"),
        ("pwd", "Should be command"),
        ("show me the current directory", "Should be natural language"),
        ("cd /tmp", "Should be command"),
        ("go to the temp directory", "Should be natural language"),
    ]
    
    for text, expected in test_cases:
        is_command, confidence = await classifier.classify(text)
        classification = "Command" if is_command else "Natural Language"
        print(f"Input: '{text}'")
        print(f"  → {classification} (confidence: {confidence:.2f})")
        print(f"  Expected: {expected}")
        print()


def test_execution():
    """Test command execution"""
    print("\n🧪 Testing Execution\n")
    
    executor = CommandExecutor()
    
    # Test a simple command
    print("Executing: echo 'Hello from AI Shell'")
    output, exit_code = executor.execute_command("echo 'Hello from AI Shell'")
    print(f"Output: {output.strip()}")
    print(f"Exit code: {exit_code}")
    print()
    
    # Test directory listing
    print("Executing: ls -la | head -5")
    output, exit_code = executor.execute_command("ls -la | head -5")
    print(f"Output:\n{output}")
    print(f"Exit code: {exit_code}")


async def main():
    print("=" * 60)
    print("AI Shell Demo")
    print("=" * 60)
    
    await test_classification()
    test_execution()
    
    print("\n✨ Demo completed!")


if __name__ == "__main__":
    asyncio.run(main())
