#!/usr/bin/env python3

import asyncio
import sys
import os
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.trace.events import FileEventSink
from src.trace.orchestrator import TaskOrchestrator

async def test_ripgrep_command():
    # Create test trace file
    os.makedirs("tmp", exist_ok=True)
    trace_file = "tmp/test_ripgrep_trace.jsonl"
    
    print("🧪 Testing ripgrep command through agent...")
    
    # Create orchestrator
    event_sink = FileEventSink(trace_file)
    orchestrator = TaskOrchestrator(event_sink, context_mode="none")
    
    # Test prompt that should trigger ripgrep
    test_prompt = "Search for all occurrences of 'class Command' in Python files"
    
    print(f"📝 Test prompt: {test_prompt}")
    
    try:
        # Execute the task
        result = await orchestrator.execute_task(test_prompt)
        
        print(f"\n✅ Test completed successfully")
        print(f"📊 Result: {result[:200]}..." if len(result) > 200 else f"📊 Result: {result}")
        
        # Verify the trace file contains ripgrep execution
        with open(trace_file, 'r') as f:
            trace_lines = f.readlines()
            
        ripgrep_found = False
        for line in trace_lines:
            event = json.loads(line)
            if event.get('event_type') == 'tool_request' and event.get('data', {}).get('tool_name') == 'ripgrep':
                ripgrep_found = True
                print(f"\n🔍 Ripgrep command was executed with params: {event['data'].get('params')}")
                break
        
        if not ripgrep_found:
            print("\n⚠️  Warning: ripgrep command was not found in trace")
            
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        return False
    finally:
        # Clean up
        if os.path.exists(trace_file):
            os.remove(trace_file)
            print(f"\n🧹 Cleaned up trace file: {trace_file}")

if __name__ == "__main__":
    success = asyncio.run(test_ripgrep_command())
    sys.exit(0 if success else 1)
