import asyncio
import concurrent.futures
from src.brain.orchestrator import BrainOrchestrator
from src.utils.paths import get_absolute_path


class Command:
    """
    Brain Session command - creates autonomous AI pentester sessions
    """
    
    def execute(self, params: dict) -> str:
        target = params.get("target")
        if not target:
            return "Error: No target specified for brain session."
        
        goal = params.get("goal", "Complete penetration test")
        prompt_file = params.get("prompt_file")
        prompt_text = params.get("prompt")
        max_iterations = int(params.get("max_iterations", 50))
        
        # Load brain prompt
        if prompt_file:
            try:
                with open(get_absolute_path(prompt_file), 'r') as f:
                    brain_prompt = f.read()
            except Exception as e:
                return f"Error loading prompt file: {e}"
        elif prompt_text:
            brain_prompt = prompt_text
        else:
            # Use default senior pentester prompt
            brain_prompt = self._get_default_brain_prompt()
        
        try:
            # Check if we're already in an async context
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context - need to run in new thread with new event loop
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(
                        self._run_brain_session_sync,
                        target,
                        goal,
                        brain_prompt,
                        max_iterations
                    )
                    return future.result()
            except RuntimeError:
                # No running loop - we can use asyncio.run()
                return asyncio.run(self._run_brain_session(
                    target=target,
                    goal=goal, 
                    brain_prompt=brain_prompt,
                    max_iterations=max_iterations
                ))
        except KeyboardInterrupt:
            return "🧠 Brain session interrupted by user."
        except Exception as e:
            import traceback
            return f"Error running brain session: {e}\n{traceback.format_exc()}"
    
    def _run_brain_session_sync(self, target: str, goal: str, brain_prompt: str, max_iterations: int) -> str:
        """Run brain session in a new event loop (for when called from async context)"""
        return asyncio.run(self._run_brain_session(target, goal, brain_prompt, max_iterations))
    
    async def _run_brain_session(self, target: str, goal: str, brain_prompt: str, max_iterations: int) -> str:
        """Run the autonomous brain session"""
        orchestrator = BrainOrchestrator(
            target=target,
            goal=goal,
            brain_prompt=brain_prompt,
            max_iterations=max_iterations
        )
        
        result = await orchestrator.run()
        return result
    
    def _get_default_brain_prompt(self) -> str:
        return """You are a Senior Penetration Tester with 15+ years of experience. You guide junior pentesters through systematic penetration testing.

Your role:
- Maintain awareness of target IP, open ports, discovered services, and vulnerabilities
- Make strategic decisions about what to test next
- Assign specific tasks to your junior pentester (the Worker)
- Track progress through reconnaissance, enumeration, exploitation, and post-exploitation phases
- Keep detailed notes like a professional pentester's cheatsheet

You communicate by giving direct task assignments like:
"Run nmap scan on 10.0.0.1"
"Check HTTP service on port 80 for common vulnerabilities" 
"Try default credentials on the admin panel"

Always explain your reasoning briefly and track what phase you're in."""
