import asyncio
import sys
import os
import argparse
import uuid
from datetime import datetime

# Add the 'src' directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.trace.events import FileEventSink
from src.trace.orchestrator import TaskOrchestrator
from src.agent.session import ChatSession
from src.trace.proxies import LLMProxy, ToolProxy
from src.rag.strategy import ContextStrategy, NullContextStrategy, ASTContextStrategy, RAGContextStrategy

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
        # Interactive chat mode with persistent session
        print("💬 Welcome to the City Code Agent! Type 'exit' or 'quit' to end the session.")
        
        # Create context strategy based on mode
        if args.context_mode == "ast":
            strategy = ASTContextStrategy()
        elif args.context_mode == "rag":
            strategy = RAGContextStrategy()
        else:
            strategy = NullContextStrategy()
        
        # Create proxies for logging
        from src.llm.client import LLMClient
        from src.agent.tool_executor import ToolExecutor
        from src.trace.events import TraceContext
        
        trace_context = TraceContext(
            trace_id=str(uuid.uuid4()),
            user_request="Interactive Session",
            start_time=datetime.now()
        )
        
        real_llm_client = LLMClient()
        real_tool_executor = ToolExecutor()
        
        llm_proxy = LLMProxy(real_llm_client, trace_context, event_sink)
        tool_proxy = ToolProxy(real_tool_executor, trace_context, event_sink)
        
        # Create the chat session
        session = ChatSession(
            llm_client=llm_proxy,
            tool_executor=tool_proxy,
            context_mode=args.context_mode
        )
        
        print(f"📝 Session ID: {session.thread_id}")
        
        while True:
            try:
                prompt = await asyncio.to_thread(input, "👨‍💻 Your request: ")
                if prompt.lower() in ["exit", "quit"]:
                    print(f"\n📊 Total tokens used in session: {session.total_tokens}")
                    print("👋 Goodbye! Thanks for visiting City Code.")
                    break
                
                # Build context if needed
                context = ""
                if args.context_mode != "none":
                    context = await strategy.build(prompt)
                
                # Get response from session
                result, tokens_used = await session.ask(prompt, context)
                
                print(f"\n🤖 City Code Agent:\n{result}\n")
                print(f"📊 Tokens this turn: {tokens_used} | Total session tokens: {session.total_tokens}")

            except (KeyboardInterrupt, EOFError):
                print(f"\n📊 Total tokens used in session: {session.total_tokens}")
                print("\n👋 Goodbye! Thanks for visiting City Code.")
                break
    
    print(f"📊 Trace saved to: {trace_file}")


if __name__ == "__main__":
    asyncio.run(main())
