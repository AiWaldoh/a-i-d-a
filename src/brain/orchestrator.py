import asyncio
import uuid
import yaml
import sys
import threading
import time
from datetime import datetime
from typing import Dict, Any, List
from pydantic import BaseModel

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


class ExtractionStep(BaseModel):
    reasoning: str
    extracted_info: str
    
    class Config:
        title = "ExtractionStep"


class ServiceInfo(BaseModel):
    port: str
    service: str
    
    class Config:
        title = "ServiceInfo"


class TargetStateExtraction(BaseModel):
    steps: List[ExtractionStep]
    open_ports: List[int]
    services: List[ServiceInfo]
    vulnerabilities: List[str]
    key_findings: List[str]
    
    class Config:
        title = "TargetStateExtraction"


class Spinner:
    def __init__(self, message: str):
        self.message = message
        self.running = False
        self.thread = None
        self.spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    
    def _spin(self):
        idx = 0
        while self.running:
            sys.stdout.write(f'\r{self.spinner_chars[idx]} {self.message}')
            sys.stdout.flush()
            idx = (idx + 1) % len(self.spinner_chars)
            time.sleep(0.1)
        sys.stdout.write('\r' + ' ' * (len(self.message) + 3) + '\r')
        sys.stdout.flush()
    
    def start(self):
        self.running = True
        self.thread = threading.Thread(target=self._spin)
        self.thread.daemon = True
        self.thread.start()
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()


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
        
        self.target = target
        self.goal = goal
        
        self.target_state = {
            "target_ip": target,
            "goal": goal,
            "open_ports": [],
            "services": {},
            "vulnerabilities": [],
            "key_findings": []
        }
        
        # Initialize agents
        self._setup_agents()
    
    def _timestamp(self) -> str:
        return datetime.now().strftime("%H:%M:%S")
    
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
        self.command_executor = CommandExecutor()
        
        # Create LLM clients
        brain_llm = LLMClient(AppSettings.get_llm_config("brain_llm"))
        worker_llm = LLMClient(AppSettings.get_llm_config("worker_llm"))
        
        # Create tool executor for worker
        worker_tool_executor = AIShellToolExecutor(command_executor=self.command_executor)
        
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
        print(f"[{self._timestamp()}] 🧠 Starting Brain Session")
        print(f"[{self._timestamp()}] 🎯 Target: {self.target}")
        print(f"[{self._timestamp()}] 🎯 Goal: {self.goal}")
        print(f"[{self._timestamp()}] 📝 Max iterations: {self.max_iterations}")
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
                print(f"[{self._timestamp()}] 🔄 ITERATION {self.iteration_count}/{self.max_iterations}")
                print(f"{'='*80}")
                
                # 1. Brain decides next action
                print(f"\n[{self._timestamp()}] 🧠 BRAIN THINKING...")
                print(f"[{self._timestamp()}] 📊 Iteration: {self.iteration_count}/{self.max_iterations}")
                
                brain_context = self._build_brain_context()
                print(f"\n[{self._timestamp()}] 🧠 BRAIN CONTEXT:\n{brain_context}")
                
                spinner = Spinner("Brain analyzing target state and deciding next action...")
                spinner.start()
                brain_decision = await self._get_brain_decision()
                spinner.stop()
                
                if not brain_decision:
                    print(f"[{self._timestamp()}] ❌ Brain failed to make a decision. Stopping.")
                    break
                
                print(f"\n[{self._timestamp()}] 🧠 BRAIN DECISION:")
                print(f"{'─'*80}")
                print(f"{brain_decision}")
                print(f"{'─'*80}")
                
                # 2. Check if brain wants to stop
                if self._should_stop(brain_decision):
                    print(f"\n[{self._timestamp()}] 🏁 Brain has decided to complete the session!")
                    break
                
                # 3. Worker executes the task
                print(f"\n[{self._timestamp()}] 🔧 WORKER EXECUTING TASK...")
                
                spinner = Spinner(f"Worker executing: {brain_decision[:60]}...")
                spinner.start()
                worker_result = await self._execute_worker_task(brain_decision)
                spinner.stop()
                
                print(f"\n[{self._timestamp()}] 🔧 WORKER RESULT:")
                print(f"{'─'*80}")
                print(f"{worker_result}")
                print(f"{'─'*80}")
                
                # 4. Brain takes notes
                print(f"\n[{self._timestamp()}] 📝 BRAIN TAKING NOTES...")
                
                spinner = Spinner("Brain analyzing results and taking notes...")
                spinner.start()
                notes = await self._ask_brain_for_notes(brain_decision, worker_result)
                spinner.stop()
                
                print(f"[{self._timestamp()}] Notes:\n{notes}")
                
                # 5. Extract structured data from notes (LLM with temp 0.1)
                print(f"\n[{self._timestamp()}] 🔍 EXTRACTING STRUCTURED DATA...")
                
                spinner = Spinner("Extracting structured data with chain-of-thought reasoning...")
                spinner.start()
                extracted = await self._extract_state_from_notes(notes)
                spinner.stop()
                
                print(f"[{self._timestamp()}]   Extracted ports: {extracted['open_ports']}")
                print(f"[{self._timestamp()}]   Extracted services: {list(extracted['services'].keys()) if extracted['services'] else []}")
                print(f"[{self._timestamp()}]   Extracted vulnerabilities: {len(extracted['vulnerabilities'])} items")
                print(f"[{self._timestamp()}]   Extracted findings: {len(extracted['key_findings'])} items")
                
                # 6. Update target state
                self._update_target_state(extracted)
                
                # 7. Remove notes conversation from Brain's history (save context)
                self.brain_session.memory.remove_last_exchange(self.brain_thread_id)
                
                # 8. Show updated state
                print(f"\n[{self._timestamp()}] 📊 UPDATED STATE:")
                if self.target_state['open_ports']:
                    print(f"[{self._timestamp()}]   Open Ports: {self.target_state['open_ports']}")
                if self.target_state['services']:
                    print(f"[{self._timestamp()}]   Services: {self.target_state['services']}")
                if self.target_state['vulnerabilities']:
                    print(f"[{self._timestamp()}]   Vulnerabilities: {len(self.target_state['vulnerabilities'])} found")
                if self.target_state['key_findings']:
                    print(f"[{self._timestamp()}]   Key Findings: {len(self.target_state['key_findings'])} items")
                
                # 9. Brief pause to prevent overwhelming
                await asyncio.sleep(1)
            
            # Print session history
            self._print_session_history()
            
            # Generate final report
            print(f"\n[{self._timestamp()}] 🤖 Generating final report...")
            
            spinner = Spinner("Generating final penetration testing report...")
            spinner.start()
            final_report = await self._generate_final_report()
            spinner.stop()
            
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
            print(f"[{self._timestamp()}] ❌ Brain decision error: {e}")
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
    
    async def _ask_brain_for_notes(self, task: str, result: str) -> str:
        notes_prompt = f"""You asked Worker to: {task}
Worker reported: {result}

Update your notes with key findings. Extract:
- Open ports (if any)
- Services and versions (if any)  
- Vulnerabilities or issues found (if any)
- Important discoveries (credentials, endpoints, etc.)

Write concise technical notes about what was discovered."""

        try:
            notes, _ = await self.brain_session.ask(notes_prompt)
            return notes.strip()
        except Exception as e:
            print(f"[{self._timestamp()}] ❌ Brain notes error: {e}")
            return ""
    
    def _build_brain_context(self) -> str:
        current_dir = self.command_executor.get_current_directory()
        
        parts = [
            f"Target: {self.target_state['target_ip']}",
            f"Goal: {self.target_state['goal']}",
            f"Working Directory: {current_dir}",
            f"Iteration: {self.iteration_count}/{self.max_iterations}"
        ]
        
        if self.target_state['open_ports']:
            parts.append(f"Open Ports: {', '.join(map(str, self.target_state['open_ports']))}")
        
        if self.target_state['services']:
            services = ', '.join([f"{port}:{svc}" for port, svc in self.target_state['services'].items()])
            parts.append(f"Services: {services}")
        
        if self.target_state['vulnerabilities']:
            parts.append(f"Vulnerabilities: {', '.join(self.target_state['vulnerabilities'])}")
        
        if self.target_state['key_findings']:
            recent = self.target_state['key_findings'][-3:]
            parts.append(f"Key Findings: {'; '.join(recent)}")
        
        return '\n'.join(parts)
    
    async def _extract_state_from_notes(self, notes: str) -> dict:
        extraction_llm = LLMClient(AppSettings.get_llm_config("brain_llm"))
        
        extraction_prompt = f"""Extract structured data from these technical penetration testing notes. Think step by step.

Notes:
{notes}

Analyze the notes and extract:
1. **Open Ports**: Only actual network ports (22, 80, 443, etc.), NOT version numbers or iteration counts
2. **Services**: List of services with their port and name/version
3. **Vulnerabilities**: Security issues, CVEs, exploitable weaknesses
4. **Key Findings**: Credentials, endpoints, access points, important discoveries

For each piece of information you extract, explain your reasoning in the steps array.

Rules:
- Be precise: Don't confuse version numbers (8.2) with port numbers
- Only extract ports that are explicitly mentioned as network ports
- For services: port can be any string ("22", "22/tcp", "80/udp", etc.) - keep whatever format makes sense
- Services is an array of objects with "port" and "service" fields
- If nothing found for a field, use empty list
"""

        try:
            result = await extraction_llm.parse(
                messages=[{"role": "user", "content": extraction_prompt}],
                response_format=TargetStateExtraction,
                temperature=0.1
            )
            
            if result is None:
                raise Exception("Structured parsing returned None")
            
            print(f"\n[{self._timestamp()}] 🧠 EXTRACTION REASONING:")
            for i, step in enumerate(result.steps, 1):
                print(f"[{self._timestamp()}]   Step {i}: {step.reasoning}")
                print(f"[{self._timestamp()}]     → {step.extracted_info}")
            
            services_dict = {svc.port: svc.service for svc in result.services}
            
            return {
                "open_ports": result.open_ports,
                "services": services_dict,
                "vulnerabilities": result.vulnerabilities,
                "key_findings": result.key_findings
            }
        except Exception as e:
            print(f"[{self._timestamp()}] ⚠️  Extraction failed: {e}")
            import traceback
            traceback.print_exc()
            return {
                "open_ports": [],
                "services": {},
                "vulnerabilities": [],
                "key_findings": []
            }
    
    def _update_target_state(self, extracted: dict) -> None:
        for port in extracted["open_ports"]:
            if port not in self.target_state["open_ports"]:
                self.target_state["open_ports"].append(port)
        
        self.target_state["services"].update(extracted["services"])
        
        for vuln in extracted["vulnerabilities"]:
            if vuln not in self.target_state["vulnerabilities"]:
                self.target_state["vulnerabilities"].append(vuln)
        
        for finding in extracted["key_findings"]:
            if finding not in self.target_state["key_findings"]:
                self.target_state["key_findings"].append(finding)
    
    def _should_stop(self, brain_decision: str) -> bool:
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
        print(f"{'='*80}\n")
        
        # Get conversation history from both agents
        brain_history = self.brain_session.get_history()
        worker_history = self.worker_session.get_history()
        
        print("🧠 BRAIN CONVERSATION HISTORY:")
        print(f"{'─'*80}")
        for i, msg in enumerate(brain_history, 1):
            if msg.role == "user":
                print(f"\n[{i}] USER → BRAIN:")
                print(f"  {msg.content}")
            elif msg.role == "assistant":
                print(f"\n[{i}] BRAIN RESPONSE:")
                print(f"  {msg.content}")
        print(f"\n{'─'*80}\n")
        
        print("🔧 WORKER CONVERSATION HISTORY:")
        print(f"{'─'*80}")
        for i, msg in enumerate(worker_history, 1):
            if msg.role == "user":
                print(f"\n[{i}] BRAIN → WORKER:")
                print(f"  {msg.content}")
            elif msg.role == "assistant":
                print(f"\n[{i}] WORKER RESPONSE:")
                print(f"  {msg.content}")
        print(f"\n{'─'*80}\n")
        
        print("📊 FINAL TARGET STATE:")
        print(f"{'─'*80}")
        print(f"Target: {self.target_state['target_ip']}")
        print(f"Goal: {self.target_state['goal']}")
        if self.target_state['open_ports']:
            print(f"Open Ports: {self.target_state['open_ports']}")
        if self.target_state['services']:
            print(f"Services: {self.target_state['services']}")
        if self.target_state['vulnerabilities']:
            print(f"Vulnerabilities ({len(self.target_state['vulnerabilities'])} total):")
            for i, vuln in enumerate(self.target_state['vulnerabilities'][:5], 1):
                print(f"  {i}. {vuln}")
        if self.target_state['key_findings']:
            print(f"Key Findings ({len(self.target_state['key_findings'])} total):")
            for i, finding in enumerate(self.target_state['key_findings'][:5], 1):
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
