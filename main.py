import asyncio
import sys
import os
import argparse
from datetime import datetime

# Add the 'src' directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.trace.events import FileEventSink
from src.trace.orchestrator import TaskOrchestrator

async def main():
    """
    The main entry point for the agent application.
    """
    parser = argparse.ArgumentParser(description="City Code Agent - Your shitty code assistant")
    parser.add_argument("--context-mode", choices=["none", "ast", "rag"], default="none",
                        help="Context strategy to use (default: none)")
    parser.add_argument("--prompt", type=str, default=None,
                        help="Run a single prompt non-interactively")
    args = parser.parse_args()

    # --- Setup Event Logging ---
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    trace_file = f"tmp/trace_{timestamp}.jsonl"
    os.makedirs("tmp", exist_ok=True)
    
    print(f"📊 Logging trace to: {trace_file}")
    print(f"🔧 Context mode: {args.context_mode}")

    # Create the event sink and orchestrator
    event_sink = FileEventSink(trace_file)
    orchestrator = TaskOrchestrator(event_sink, context_mode=args.context_mode)

    if args.prompt:
        # Single prompt mode
        print(f"🚀 Executing single prompt: '{args.prompt}'")
        result = await orchestrator.execute_task(args.prompt)
        print(f"\n✅ Task completed. Result: {result}")
    else:
        # Interactive chat mode
        print("💬 Welcome to the City Code Agent! Type 'exit' or 'quit' to end the session.")
        while True:
            try:
                prompt = await asyncio.to_thread(input, "👨‍💻 Your request: ")
                if prompt.lower() in ["exit", "quit"]:
                    print("👋 Goodbye! Thanks for visiting City Code.")
                    break
                
                result = await orchestrator.execute_task(prompt)
                print(f"\n🤖 City Code Agent:\n{result}\n")

            except (KeyboardInterrupt, EOFError):
                print("\n👋 Goodbye! Thanks for visiting City Code.")
                break
    
    print(f"📊 Trace saved to: {trace_file}")


if __name__ == "__main__":
    asyncio.run(main())
