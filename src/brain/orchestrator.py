import asyncio
import uuid
import yaml
from datetime import datetime
from typing import Dict, Any, List

from src.agent.session import ChatSession
from src.agent.memory import InMemoryMemory, Message
from src.agent.prompt_builder import PromptBuilder
from src.llm.client import LLMClient
from src.ai_shell.ai_tool_executor import AIShellToolExecutor
from src.ai_shell.executor import CommandExecutor
from src.config.settings import AppSettings
from src.trace.proxies import LLMProxy, ToolProxy
from src.trace.events import TraceContext, FileEventSink, TaskEvent
from src.utils.paths import get_absolute_path


class BrainOrchestrator:
    """
    Orchestrates the Brain-Worker agent interaction for autonomous penetration testing
    """
    
    def __init__(self, target: str, goal: str, brain_prompt: str, max_iterations: int = 50):
        self.target = target
        self.goal = goal
        self.brain_prompt = brain_prompt
        self.max_iterations = max_iterations
        self.iteration_count = 0
        
        self.prompts = self._load_prompts()
        
        # Create session IDs
        self.session_id = str(uuid.uuid4())
        self.brain_thread_id = str(uuid.uuid4())
        self.worker_thread_id = str(uuid.uuid4())
        
        # Create trace file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        tmp_dir = get_absolute_path("tmp")
        trace_file = str(tmp_dir / f"brain_trace_{timestamp}.jsonl")
        self.event_sink = FileEventSink(trace_file)
        
        # Initialize target state tracking
        self.target_state = {
            "target_ip": target,
            "goal": goal,
            "phase": "RECONNAISSANCE",
            "open_ports": [],
            "services": {},
            "vulnerabilities": [],
            "findings": [],
            "next_actions": []
        }
        
        # Initialize agents
        self._setup_agents()
    
    def _load_prompts(self) -> dict:
        try:
            with open(get_absolute_path("prompts.yaml"), 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Warning: Failed to load prompts.yaml: {e}")
            return {}
    
    def _setup_agents(self):
        """Initialize Brain and Worker agents"""
        # Create command executor for worker
        command_executor = CommandExecutor()
        
        # Create LLM clients
        brain_llm = LLMClient(AppSettings.get_llm_config("brain_llm"))
        worker_llm = LLMClient(AppSettings.get_llm_config("worker_llm"))
        
        # Create tool executor for worker
        worker_tool_executor = AIShellToolExecutor(command_executor=command_executor)
        
        # Create trace contexts
        brain_trace_context = TraceContext(
            trace_id=self.session_id,
            user_request=f"Brain Session: {self.goal}",
            start_time=datetime.now()
        )
        
        worker_trace_context = TraceContext(
            trace_id=self.session_id,
            user_request=f"Worker for Brain Session: {self.goal}",
            start_time=datetime.now()
        )
        
        # Create proxied clients
        brain_llm_proxy = LLMProxy(brain_llm, brain_trace_context, self.event_sink)
        worker_llm_proxy = LLMProxy(worker_llm, worker_trace_context, self.event_sink)
        worker_tool_proxy = ToolProxy(worker_tool_executor, worker_trace_context, self.event_sink)
        
        # Create Brain Agent (strategy only, no tools)
        brain_memory = InMemoryMemory()
        brain_prompt_builder = PromptBuilder(context_mode="none")
        
        self.brain_session = ChatSession(
            memory=brain_memory,
            llm_client=brain_llm_proxy,
            tool_executor=None,  # Brain doesn't execute tools directly
            prompt_builder=brain_prompt_builder,
            thread_id=self.brain_thread_id,
            context_mode="none"
        )
        
        # Create Worker Agent (execution)
        worker_memory = InMemoryMemory()
        worker_prompt_builder = PromptBuilder(context_mode="none")
        
        self.worker_session = ChatSession(
            memory=worker_memory,
            llm_client=worker_llm_proxy,
            tool_executor=worker_tool_proxy,
            prompt_builder=worker_prompt_builder,
            thread_id=self.worker_thread_id,
            context_mode="none"
        )
        
        # Initialize brain with custom prompt and target info
        self._initialize_brain()
    
    def _initialize_brain(self):
        """Initialize the brain agent with target information and custom prompt"""
        init_template = self.prompts.get("brain_agent_init", "{brain_prompt}\n\nTARGET INFORMATION:\n- Target IP: {target}\n- Goal: {goal}\n- Current Phase: RECONNAISSANCE\n\nYour first task is to begin reconnaissance of the target. Start with basic port scanning.")
        
        initialization_message = init_template.format(
            brain_prompt=self.brain_prompt,
            target=self.target,
            goal=self.goal
        )
        
        self.brain_session.memory.append(
            self.brain_thread_id,
            Message(role="system", content=initialization_message)
        )
    
    async def run(self) -> str:
        """Run the autonomous brain session"""
        print(f"🧠 Starting Brain Session")
        print(f"🎯 Target: {self.target}")
        print(f"🎯 Goal: {self.goal}")
        print(f"📝 Max iterations: {self.max_iterations}")
        print("=" * 60)
        
        # Emit session start event
        self.event_sink.emit(TaskEvent(
            event_type="brain_session_started",
            trace_id=self.session_id,
            timestamp=datetime.now(),
            data={
                "target": self.target,
                "goal": self.goal,
                "max_iterations": self.max_iterations
            }
        ))
        
        try:
            # Main brain-worker loop
            while self.iteration_count < self.max_iterations:
                self.iteration_count += 1
                
                print(f"\n{'='*80}")
                print(f"🔄 ITERATION {self.iteration_count}/{self.max_iterations}")
                print(f"{'='*80}")
                
                # 1. Brain decides next action
                print("\n🧠 BRAIN THINKING...")
                print(f"📊 Current State: Phase={self.target_state['phase']}, "
                      f"Ports={len(self.target_state['open_ports'])}, "
                      f"Findings={len(self.target_state['findings'])}")
                
                brain_decision = await self._get_brain_decision()
                if not brain_decision:
                    print("❌ Brain failed to make a decision. Stopping.")
                    break
                
                print(f"\n🧠 BRAIN DECISION:")
                print(f"{'─'*80}")
                print(f"{brain_decision}")
                print(f"{'─'*80}")
                
                # 2. Check if brain wants to stop
                if self._should_stop(brain_decision):
                    print("\n🏁 Brain has decided to complete the session!")
                    break
                
                # 3. Worker executes the task
                print(f"\n🔧 WORKER EXECUTING TASK...")
                worker_result = await self._execute_worker_task(brain_decision)
                
                print(f"\n🔧 WORKER RESULT:")
                print(f"{'─'*80}")
                # Show full result, not truncated
                if len(worker_result) > 1000:
                    print(f"{worker_result[:1000]}")
                    print(f"\n... [truncated, showing first 1000 chars of {len(worker_result)} total] ...")
                else:
                    print(f"{worker_result}")
                print(f"{'─'*80}")
                
                # 4. Update target state based on results
                self._update_target_state(brain_decision, worker_result)
                
                # 5. Show updated state
                print(f"\n📊 UPDATED STATE:")
                print(f"  Phase: {self.target_state['phase']}")
                if self.target_state['open_ports']:
                    print(f"  Open Ports: {self.target_state['open_ports']}")
                if self.target_state['services']:
                    print(f"  Services: {self.target_state['services']}")
                if self.target_state['vulnerabilities']:
                    print(f"  Vulnerabilities: {self.target_state['vulnerabilities']}")
                
                # 6. Brief pause to prevent overwhelming
                await asyncio.sleep(1)
            
            # Print session history
            self._print_session_history()
            
            # Generate final report
            print("\n🤖 Generating final report...")
            final_report = await self._generate_final_report()
            
            # Emit session end event
            self.event_sink.emit(TaskEvent(
                event_type="brain_session_completed",
                trace_id=self.session_id,
                timestamp=datetime.now(),
                data={
                    "iterations": self.iteration_count,
                    "target_state": self.target_state,
                    "final_report": final_report
                }
            ))
            
            return final_report
            
        except Exception as e:
            error_msg = f"Brain session failed: {str(e)}"
            self.event_sink.emit(TaskEvent(
                event_type="brain_session_failed",
                trace_id=self.session_id,
                timestamp=datetime.now(),
                data={"error": error_msg}
            ))
            return error_msg
    
    async def _get_brain_decision(self) -> str:
        """Get the next decision from the brain agent"""
        context = self._build_brain_context()
        
        decision_template = self.prompts.get("brain_agent_decision", "Based on the current target state, decide the next action.\n\nCURRENT STATE:\n{context}\n\nProvide a specific task for the worker to execute. Be direct and actionable.\nExamples:\n- \"Run nmap scan on {target}\"\n- \"Check HTTP service on port 80 for vulnerabilities\"\n- \"Try default credentials on admin panel\"\n- \"COMPLETE: Successfully gained access to target\"\n\nYour decision:")
        
        brain_prompt = decision_template.format(
            context=context,
            target=self.target
        )
        
        try:
            response, _ = await self.brain_session.ask(brain_prompt)
            return response.strip()
        except Exception as e:
            print(f"❌ Brain decision error: {e}")
            return ""
    
    async def _execute_worker_task(self, task: str) -> str:
        """Have the worker execute the given task"""
        worker_template = self.prompts.get("worker_agent_task", "Execute this specific task: {task}\n\nUse the appropriate tools to complete this task. Be thorough and report back with detailed results.")
        
        worker_prompt = worker_template.format(task=task)
        
        try:
            response, _ = await self.worker_session.ask(worker_prompt)
            return response
        except Exception as e:
            return f"Worker execution error: {str(e)}"
    
    def _build_brain_context(self) -> str:
        """Build context string for brain decision making"""
        context_parts = []
        context_parts.append(f"Target: {self.target_state['target_ip']}")
        context_parts.append(f"Goal: {self.target_state['goal']}")
        context_parts.append(f"Phase: {self.target_state['phase']}")
        context_parts.append(f"Iteration: {self.iteration_count}/{self.max_iterations}")
        
        if self.target_state['open_ports']:
            context_parts.append(f"Open Ports: {', '.join(map(str, self.target_state['open_ports']))}")
        
        if self.target_state['services']:
            services_str = ', '.join([f"{port}:{service}" for port, service in self.target_state['services'].items()])
            context_parts.append(f"Services: {services_str}")
        
        if self.target_state['vulnerabilities']:
            context_parts.append(f"Vulnerabilities: {', '.join(self.target_state['vulnerabilities'])}")
        
        if self.target_state['findings']:
            recent_findings = self.target_state['findings'][-3:]  # Last 3 findings
            context_parts.append(f"Recent Findings: {'; '.join(recent_findings)}")
        
        return '\n'.join(context_parts)
    
    def _update_target_state(self, task: str, result: str):
        """Update target state based on task results"""
        # Simple pattern matching to extract information
        # This could be enhanced with more sophisticated parsing
        
        # Extract ports from nmap results
        if "nmap" in task.lower() and "open" in result.lower():
            import re
            port_pattern = r'(\d+)\/tcp\s+open'
            ports = re.findall(port_pattern, result)
            for port in ports:
                if int(port) not in self.target_state['open_ports']:
                    self.target_state['open_ports'].append(int(port))
        
        # Track findings
        self.target_state['findings'].append(f"Task: {task[:50]}... Result: {result[:100]}...")
        
        # Update phase based on progress
        if len(self.target_state['open_ports']) > 0 and self.target_state['phase'] == 'RECONNAISSANCE':
            self.target_state['phase'] = 'ENUMERATION'
        elif self.target_state['vulnerabilities'] and self.target_state['phase'] == 'ENUMERATION':
            self.target_state['phase'] = 'EXPLOITATION'
    
    def _should_stop(self, brain_decision: str) -> bool:
        """Check if brain wants to stop the session"""
        stop_keywords = ['complete', 'finished', 'done', 'success', 'accomplished']
        return any(keyword in brain_decision.lower() for keyword in stop_keywords)
    
    def _print_session_history(self):
        """Print complete session history with all Brain decisions and Worker results"""
        print(f"\n\n{'='*80}")
        print(f"📜 SESSION HISTORY")
        print(f"{'='*80}")
        print(f"Target: {self.target}")
        print(f"Goal: {self.goal}")
        print(f"Total Iterations: {self.iteration_count}")
        print(f"Final Phase: {self.target_state['phase']}")
        print(f"{'='*80}\n")
        
        # Get conversation history from both agents
        brain_history = self.brain_session.get_history()
        worker_history = self.worker_session.get_history()
        
        print("🧠 BRAIN CONVERSATION HISTORY:")
        print(f"{'─'*80}")
        for i, msg in enumerate(brain_history, 1):
            if msg.role == "user":
                print(f"\n[{i}] USER → BRAIN:")
                print(f"  {msg.content[:200]}...")
            elif msg.role == "assistant":
                print(f"\n[{i}] BRAIN RESPONSE:")
                print(f"  {msg.content}")
        print(f"\n{'─'*80}\n")
        
        print("🔧 WORKER CONVERSATION HISTORY:")
        print(f"{'─'*80}")
        for i, msg in enumerate(worker_history, 1):
            if msg.role == "user":
                print(f"\n[{i}] BRAIN → WORKER:")
                print(f"  {msg.content[:200]}...")
            elif msg.role == "assistant":
                print(f"\n[{i}] WORKER RESPONSE:")
                # Truncate long worker responses
                if len(msg.content) > 300:
                    print(f"  {msg.content[:300]}...")
                    print(f"  ... [truncated {len(msg.content)} total chars]")
                else:
                    print(f"  {msg.content}")
        print(f"\n{'─'*80}\n")
        
        print("📊 FINAL TARGET STATE:")
        print(f"{'─'*80}")
        print(f"Phase: {self.target_state['phase']}")
        print(f"Open Ports: {self.target_state['open_ports']}")
        print(f"Services: {self.target_state['services']}")
        print(f"Vulnerabilities: {self.target_state['vulnerabilities']}")
        print(f"Total Findings: {len(self.target_state['findings'])}")
        
        if self.target_state['findings']:
            print(f"\nRecent Findings:")
            for i, finding in enumerate(self.target_state['findings'][-5:], 1):
                print(f"  {i}. {finding}")
        print(f"{'─'*80}\n")
    
    async def _generate_final_report(self) -> str:
        """Generate final penetration testing report"""
        report_prompt = f"""Generate a penetration testing report based on this session:

TARGET: {self.target}
GOAL: {self.goal}
ITERATIONS: {self.iteration_count}
FINAL STATE: {self._build_brain_context()}

Create a professional penetration testing report with:
1. Executive Summary
2. Target Information
3. Methodology
4. Findings and Vulnerabilities
5. Recommendations

Report:"""
        
        try:
            report, _ = await self.brain_session.ask(report_prompt)
            return f"""
🧠 BRAIN SESSION REPORT
{'=' * 60}
Target: {self.target}
Goal: {self.goal}
Iterations: {self.iteration_count}/{self.max_iterations}
Duration: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{report}

{'=' * 60}
Session completed successfully!
            """.strip()
        except Exception as e:
            return f"Error generating report: {str(e)}"
