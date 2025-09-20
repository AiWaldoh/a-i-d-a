import asyncio
import sys
import os
import argparse
import uuid
import time
from datetime import datetime

# Add the 'src' directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from src.trace.events import FileEventSink, TaskEvent
from src.trace.orchestrator import TaskOrchestrator
from src.agent.session import ChatSession
from src.trace.proxies import LLMProxy, ToolProxy
from src.rag.strategy import ContextStrategy, NullContextStrategy, ASTContextStrategy, RAGContextStrategy
from src.utils.paths import get_absolute_path

async def main():
    """
    The main entry point for the agent application.
    """
    parser = argparse.ArgumentParser(description="A.I.D.A - AI Intelligent Development Assistant")
    parser.add_argument("--context-mode", choices=["none", "ast", "rag"], default="none",
                        help="Context strategy to use (default: none)")
    parser.add_argument("--prompt", type=str, default=None,
                        help="Run a single prompt non-interactively")
    args = parser.parse_args()

    # --- Setup Event Logging ---
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tmp_dir = get_absolute_path("tmp")
    trace_file = str(tmp_dir / f"trace_{timestamp}.jsonl")
    os.makedirs(tmp_dir, exist_ok=True)
    
    # Removed verbose logging messages for cleaner output

    # Create the event sink and orchestrator
    event_sink = FileEventSink(trace_file)
    orchestrator = TaskOrchestrator(event_sink, context_mode=args.context_mode)

    if args.prompt:
        # Single prompt mode
        result = await orchestrator.execute_task(args.prompt)
        print(result)
    else:
        # Interactive chat mode with persistent session
        print("Welcome to A.I.D.A. Type 'exit' or 'quit' to end the session.")
        
        # Create context strategy based on mode
        if args.context_mode == "ast":
            strategy = ASTContextStrategy()
        elif args.context_mode == "rag":
            strategy = RAGContextStrategy()
        else:
            strategy = NullContextStrategy()
        
        # Create proxies for logging at session level
        from src.llm.client import LLMClient
        from src.agent.tool_executor import ToolExecutor
        from src.trace.events import TraceContext
        
        # Create a session-level trace context
        session_trace_id = str(uuid.uuid4())
        trace_context = TraceContext(
            trace_id=session_trace_id,
            user_request="Interactive Session",
            start_time=datetime.now()
        )
        
        real_llm_client = LLMClient()
        real_tool_executor = ToolExecutor()
        
        llm_proxy = LLMProxy(real_llm_client, trace_context, event_sink)
        tool_proxy = ToolProxy(real_tool_executor, trace_context, event_sink)
        
        # Create the chat session with proxies
        session = ChatSession(
            llm_client=llm_proxy,
            tool_executor=tool_proxy,
            context_mode=args.context_mode
        )
        
        # Removed session ID display for cleaner output
        
        # Emit session started event
        event_sink.emit(TaskEvent(
            event_type="session_started",
            trace_id=session_trace_id,
            timestamp=datetime.now(),
            data={
                "session_id": session.thread_id,
                "context_mode": args.context_mode
            }
        ))
        
        while True:
            try:
                prompt = await asyncio.to_thread(input, "> ")
                if prompt.lower() in ["exit", "quit"]:
                    print(f"\nTotal tokens: {session.total_tokens}")
                    print("\nGoodbye.")
                    break
                
                # Create a new trace_id for this request
                task_trace_id = str(uuid.uuid4())
                task_start_time = datetime.now()
                
                # Emit task_started event for consistency
                event_sink.emit(TaskEvent(
                    event_type="task_started",
                    trace_id=task_trace_id,
                    timestamp=task_start_time,
                    data={
                        "user_request": prompt,
                        "context_mode": args.context_mode,
                        "session_id": session.thread_id
                    }
                ))
                
                try:
                    # Build context if needed
                    context = ""
                    if args.context_mode != "none":
                        context_start = time.time()
                        context = await strategy.build(prompt)
                        context_duration = time.time() - context_start
                        
                        event_sink.emit(TaskEvent(
                            event_type="context_build_completed",
                            trace_id=task_trace_id,
                            timestamp=datetime.now(),
                            data={
                                "strategy": args.context_mode,
                                "duration_seconds": context_duration,
                                "context_length": len(context),
                                "context": context
                            }
                        ))
                    
                    # Get response from session
                    result, tokens_used = await session.ask(prompt, context)
                    
                    # Emit task_completed event
                    event_sink.emit(TaskEvent(
                        event_type="task_completed",
                        trace_id=task_trace_id,
                        timestamp=datetime.now(),
                        data={
                            "result": result,
                            "tokens_used": tokens_used,
                            "duration_seconds": (datetime.now() - task_start_time).total_seconds()
                        }
                    ))
                    
                    print(f"\nA.I.D.A:\n{result}")
                    print(f"\nTokens: {tokens_used} (Total: {session.total_tokens})")
                
                except Exception as e:
                    # Emit task_failed event
                    event_sink.emit(TaskEvent(
                        event_type="task_failed",
                        trace_id=task_trace_id,
                        timestamp=datetime.now(),
                        data={
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "duration_seconds": (datetime.now() - task_start_time).total_seconds()
                        }
                    ))
                    print(f"\n❌ Error: {str(e)}")

            except (KeyboardInterrupt, EOFError):
                print(f"\nTotal tokens: {session.total_tokens}")
                print("\nGoodbye.")
                break
    
    # Trace file saved


if __name__ == "__main__":
    asyncio.run(main())
