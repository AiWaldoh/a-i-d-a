#!/usr/bin/env python3

import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.trace.events import FileEventSink
from src.trace.orchestrator import TaskOrchestrator

async def test_ripgrep():
    os.makedirs("tmp", exist_ok=True)
    trace_file = "tmp/test_ripgrep.jsonl"
    
    print("Testing ripgrep command...")
    
    event_sink = FileEventSink(trace_file)
    orchestrator = TaskOrchestrator(event_sink, context_mode="none")
    
    # Test 1: Basic search
    print("\n1. Basic pattern search")
    result = await orchestrator.execute_task("Search for 'def execute' in Python files")
    print(f"   Found: {len(result.splitlines())} matches")
    
    # Test 2: Search with specific extension
    print("\n2. Search in YAML files")
    result = await orchestrator.execute_task("Find all occurrences of 'name:' in YAML files")
    print(f"   Found: {result.count('tools.yaml')} matches in tools.yaml")
    
    print("\n✅ Tests completed")
    
    # Cleanup
    if os.path.exists(trace_file):
        os.remove(trace_file)

if __name__ == "__main__":
    asyncio.run(test_ripgrep())
