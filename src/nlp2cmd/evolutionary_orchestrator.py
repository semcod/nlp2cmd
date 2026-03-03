"""
Evolutionary Autonomous Orchestrator - "Never Give Up" Engine

System autonomicznego uruchamiania z ewolucyjnym uczeniem się:
- Nigdy nie kończy się błędem bez próby naprawy
- Konsultuje się z LLM przy każdym problemie
- Ewolucyjnie uczy się najlepszych strategii
- Ciągłe doskonalenie na podstawie metryk
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

try:
    from rich.console import Console
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    Console = None


class RecoveryStrategy(Enum):
    """Strategie naprawy - rozszerzalne i ewolucyjne."""
    INSTALL_DEPENDENCY = "install_dependency"
    SWITCH_FALLBACK = "switch_fallback"
    CONFIGURE_ENV = "configure_env"
    CONSULT_LLM = "consult_llm"
    RETRY_WITH_DELAY = "retry_with_delay"
    MODIFY_ARGS = "modify_args"
    SKIP_AND_CONTINUE = "skip_and_continue"
    CREATE_WORKAROUND = "create_workaround"
    ESCALATE_TO_CLOUD = "escalate_to_cloud"
    USE_ALTERNATIVE_SITE = "use_alternative_site"
    FALLBACK_LOCAL_MODEL = "fallback_local_model"


@dataclass
class RecoveryAttempt:
    """Pojedyncza próba naprawy."""
    timestamp: float
    strategy: RecoveryStrategy
    context: dict[str, Any]
    llm_consulted: bool = False
    llm_advice: str = ""
    success: bool = False
    duration_ms: float = 0.0
    metrics_before: dict = field(default_factory=dict)
    metrics_after: dict = field(default_factory=dict)


@dataclass
class ExecutionMetrics:
    """Metryki wykonania - dla ciągłego doskonalenia."""
    start_time: float
    end_time: Optional[float] = None
    attempts: int = 0
    recovery_attempts: list[RecoveryAttempt] = field(default_factory=list)
    fallback_used: bool = False
    llm_calls: int = 0
    success: bool = False
    error_type: Optional[str] = None
    error_message: str = ""
    
    @property
    def duration_ms(self) -> float:
        end = self.end_time or time.time()
        return (end - self.start_time) * 1000
    
    @property
    def recovery_count(self) -> int:
        return len(self.recovery_attempts)


class EvolutionaryRecoveryEngine:
    """Silnik ewolucyjnych napraw - uczy się z każdej sytuacji."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console
        self.learning_db_path = Path.home() / ".nlp2cmd" / "evolutionary_learning.json"
        self.learning_db_path.parent.mkdir(parents=True, exist_ok=True)
        self.knowledge_base = self._load_knowledge()
        self.current_metrics: Optional[ExecutionMetrics] = None
    
    def _load_knowledge(self) -> dict:
        """Wczytuje bazę wiedzy o naprawach."""
        if self.learning_db_path.exists():
            try:
                return json.loads(self.learning_db_path.read_text())
            except:
                pass
        return {
            "error_patterns": {},
            "successful_strategies": {},
            "llm_insights": [],
            "version": 1,
        }
    
    def _save_knowledge(self):
        """Zapisuje bazę wiedzy."""
        self.learning_db_path.write_text(json.dumps(self.knowledge_base, indent=2, default=str))
    
    def _print(self, message: str, style: str = ""):
        if self.console and HAS_RICH:
            self.console.print(message, style=style)
        else:
            print(message)
    
    async def consult_llm_for_strategy(
        self,
        error_type: str,
        error_message: str,
        context: dict,
        available_strategies: list[RecoveryStrategy],
    ) -> tuple[RecoveryStrategy, str]:
        """Konsultuje się z LLM jaką strategię wybrać."""
        self._print(f"🤖 Consulting LLM for recovery strategy...", "cyan")
        
        try:
            from nlp2cmd.llm.router import LLMRouter
            
            router = LLMRouter(adaptive_learning=True)
            
            prompt = f"""
Error occurred during example execution:
- Type: {error_type}
- Message: {error_message}
- Context: {json.dumps(context, indent=2, default=str)}

Available recovery strategies:
{chr(10).join(f"- {s.value}: {s.name}" for s in available_strategies)}

Which strategy should I use? Reply with JSON:
{{"strategy": "strategy_name", "reasoning": "why", "confidence": 0.8}}
"""
            
            resp = await router.completion(
                prompt,
                task="planning",
                max_tokens=300,
                temperature=0.1,
                json_mode=True,
            )
            
            if resp.success and resp.content:
                try:
                    result = json.loads(resp.content)
                    strategy_name = result.get("strategy", "")
                    reasoning = result.get("reasoning", "")
                    
                    # Map to enum
                    for s in available_strategies:
                        if s.value == strategy_name or s.name.lower() == strategy_name.lower():
                            self._print(f"   LLM suggests: {s.value}", "green")
                            self._print(f"   Reasoning: {reasoning}", "dim")
                            return s, reasoning
                except:
                    pass
            
            self._print("   LLM consultation failed, using learned patterns", "yellow")
        except Exception as e:
            self._print(f"   LLM unavailable: {e}", "yellow")
        
        # Fallback to learned patterns
        return self._select_from_learned_patterns(error_type, available_strategies)
    
    def _select_from_learned_patterns(
        self,
        error_type: str,
        available_strategies: list[RecoveryStrategy],
    ) -> tuple[RecoveryStrategy, str]:
        """Wybiera strategię na podstawie historycznych wzorców."""
        patterns = self.knowledge_base.get("error_patterns", {})
        
        if error_type in patterns:
            history = patterns[error_type]
            # Find most successful strategy
            best_strategy = None
            best_success_rate = 0
            
            for s in available_strategies:
                s_history = history.get(s.value, {"attempts": 0, "successes": 0})
                if s_history["attempts"] > 0:
                    rate = s_history["successes"] / s_history["attempts"]
                    if rate > best_success_rate:
                        best_success_rate = rate
                        best_strategy = s
            
            if best_strategy and best_success_rate > 0.3:
                return best_strategy, f"Learned pattern: {best_success_rate:.0%} success rate"
        
        # Default strategies by error type
        if "HF_TOKEN" in error_type or "huggingface" in error_type.lower():
            return RecoveryStrategy.SWITCH_FALLBACK, "HF auth issue - use fallback"
        if "playwright" in error_type.lower() or "browser" in error_type.lower():
            return RecoveryStrategy.INSTALL_DEPENDENCY, "Browser automation issue"
        if "timeout" in error_type.lower():
            return RecoveryStrategy.RETRY_WITH_DELAY, "Network timeout"
        
        return available_strategies[0], "Default first strategy"
    
    async def execute_recovery(
        self,
        strategy: RecoveryStrategy,
        context: dict,
    ) -> tuple[bool, dict]:
        """Wykonuje strategię naprawy."""
        self._print(f"🔧 Executing recovery: {strategy.value}", "cyan")
        
        start = time.time()
        success = False
        new_context = context.copy()
        
        try:
            if strategy == RecoveryStrategy.INSTALL_DEPENDENCY:
                success = await self._recover_install_dependency(context)
            elif strategy == RecoveryStrategy.SWITCH_FALLBACK:
                success = await self._recover_switch_fallback(context)
            elif strategy == RecoveryStrategy.CONFIGURE_ENV:
                success = await self._recover_configure_env(context)
            elif strategy == RecoveryStrategy.RETRY_WITH_DELAY:
                success = await self._recover_retry_with_delay(context)
            elif strategy == RecoveryStrategy.MODIFY_ARGS:
                success = await self._recover_modify_args(context)
            elif strategy == RecoveryStrategy.CONSULT_LLM:
                success = await self._recover_consult_llm(context)
            elif strategy == RecoveryStrategy.FALLBACK_LOCAL_MODEL:
                success = await self._recover_fallback_local_model(context)
            elif strategy == RecoveryStrategy.USE_ALTERNATIVE_SITE:
                success = await self._recover_alternative_site(context)
            else:
                success = await self._recover_generic(context)
        except Exception as e:
            self._print(f"   Recovery failed: {e}", "red")
            new_context["recovery_error"] = str(e)
        
        duration = (time.time() - start) * 1000
        
        # Update learning
        if context.get("error_type"):
            self._update_learning(context["error_type"], strategy, success)
        
        return success, new_context
    
    async def _recover_install_dependency(self, context: dict) -> bool:
        """Naprawa: instalacja zależności."""
        self._print("   Installing missing dependencies...", "yellow")
        
        try:
            from nlp2cmd.utils.playwright_installer import ensure_playwright_installed
            result = ensure_playwright_installed(console=self.console, auto_install=True)
            if result:
                self._print("   ✓ Dependencies installed", "green")
                return True
        except Exception as e:
            self._print(f"   ✗ Installation failed: {e}", "red")
        
        return False
    
    async def _recover_switch_fallback(self, context: dict) -> bool:
        """Naprawa: przełączenie na fallback."""
        self._print("   Switching to fallback configuration...", "yellow")
        
        # For HF_TOKEN issues, continue without it
        if "HF_TOKEN" in context.get("error_type", ""):
            self._print("   ⚠ Continuing without HF_TOKEN (rate limits apply)", "yellow")
            self._print("   💡 Tip: Set HF_TOKEN for better performance", "cyan")
            # Modify context to skip HF-dependent operations
            context["skip_hf_hub"] = True
            return True
        
        return False
    
    async def _recover_configure_env(self, context: dict) -> bool:
        """Naprawa: konfiguracja środowiska."""
        self._print("   Configuring environment...", "yellow")
        
        # Set default env vars
        if not os.getenv("OLLAMA_BASE_URL"):
            os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
        
        return True
    
    async def _recover_retry_with_delay(self, context: dict) -> bool:
        """Naprawa: ponowna próba z opóźnieniem."""
        delay = context.get("retry_delay", 5)
        self._print(f"   Retrying in {delay}s...", "yellow")
        await asyncio.sleep(delay)
        return True
    
    async def _recover_modify_args(self, context: dict) -> bool:
        """Naprawa: modyfikacja argumentów."""
        self._print("   Modifying execution arguments...", "yellow")
        
        # Modify args to avoid the error
        args = context.get("args", [])
        
        # Remove problematic args
        if "--query" in args and context.get("error_message", "").startswith("No such option"):
            # Convert to positional arg if needed
            idx = args.index("--query")
            if idx + 1 < len(args):
                value = args[idx + 1]
                args = [a for a in args if a not in ["--query", value]]
                context["positional_arg"] = value
        
        context["args"] = args
        return True
    
    async def _recover_consult_llm(self, context: dict) -> bool:
        """Naprawa: głęboka konsultacja z LLM."""
        self._print("   Deep consultation with LLM for workaround...", "cyan")
        
        try:
            from nlp2cmd.llm.router import LLMRouter
            
            router = LLMRouter(adaptive_learning=True)
            
            error_msg = context.get("error_message", "")
            error_type = context.get("error_type", "")
            
            prompt = f"""
Execution failed with:
{error_type}: {error_msg}

How should I work around this to continue? Give specific actionable steps.
Context: Running drawing example with nlp2cmd
"""
            
            resp = await router.completion(
                prompt,
                task="repair",
                max_tokens=400,
                temperature=0.2,
            )
            
            if resp.success:
                self._print(f"   LLM advice: {resp.content[:200]}...", "green")
                context["llm_workaround"] = resp.content
                return True
        except Exception as e:
            self._print(f"   LLM consultation failed: {e}", "yellow")
        
        return False
    
    async def _recover_escalate_to_cloud(self, context: dict) -> bool:
        """Naprawa: eskalacja do cloud LLM."""
        self._print("   Escalating to cloud LLM for complex recovery...", "cyan")
        
        try:
            from nlp2cmd.llm.router import LLMRouter
            
            router = LLMRouter(adaptive_learning=True)
            
            prompt = f"""
Critical execution failure. Previous recovery strategies failed.
Error: {context.get('error_type')}: {context.get('error_message')}
Attempted: {[r.strategy.value for r in self.current_metrics.recovery_attempts]}

Design a creative workaround to complete the task.
"""
            
            resp = await router.completion(
                prompt,
                task="planning",  # Use cloud models
                max_tokens=500,
                temperature=0.3,
            )
            
            if resp.success:
                self._print(f"   Cloud LLM strategy: {resp.content[:150]}...", "green")
                context["cloud_strategy"] = resp.content
                return True
        except:
            pass
        
        return False
    
    async def _recover_fallback_local_model(self, context: dict) -> bool:
        """Naprawa: przejście na lokalny model."""
        self._print("   Switching to local Ollama model...", "yellow")
        
        os.environ["NLP2CMD_USE_LOCAL"] = "1"
        context["use_local_model"] = True
        
        return True
    
    async def _recover_alternative_site(self, context: dict) -> bool:
        """Naprawa: użycie alternatywnego site'u."""
        self._print("   Trying alternative drawing site...", "yellow")
        
        # Try jspaint as reliable fallback
        context["alternative_site"] = "jspaint"
        return True
    
    async def _recover_generic(self, context: dict) -> bool:
        """Generyczna naprawa: kontynuuj mimo błędu."""
        self._print("   Applying generic recovery (continue with warnings)...", "yellow")
        context["continue_with_warnings"] = True
        return True
    
    def _update_learning(self, error_type: str, strategy: RecoveryStrategy, success: bool):
        """Aktualizuje bazę wiedzy o wyniku naprawy."""
        patterns = self.knowledge_base.setdefault("error_patterns", {})
        
        if error_type not in patterns:
            patterns[error_type] = {}
        
        s_key = strategy.value
        if s_key not in patterns[error_type]:
            patterns[error_type][s_key] = {"attempts": 0, "successes": 0}
        
        patterns[error_type][s_key]["attempts"] += 1
        if success:
            patterns[error_type][s_key]["successes"] += 1
        
        self._save_knowledge()
    
    async def execute_with_evolutionary_recovery(
        self,
        func: callable,
        context: dict,
        max_attempts: int = 5,
    ) -> tuple[bool, Any, ExecutionMetrics]:
        """Główna metoda: wykonaj z ewolucyjnym recovery."""
        metrics = ExecutionMetrics(start_time=time.time())
        self.current_metrics = metrics
        
        result = None
        success = False
        
        for attempt in range(max_attempts):
            metrics.attempts = attempt + 1
            
            self._print(f"\n🚀 Attempt {attempt + 1}/{max_attempts}", "bold cyan")
            
            try:
                result = await func(context)
                success = True
                metrics.success = True
                break
            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)
                
                metrics.error_type = error_type
                metrics.error_message = error_msg
                
                self._print(f"   ✗ Error: {error_type}: {error_msg}", "red")
                
                # Determine available strategies
                available = self._get_available_strategies(error_type, context)
                
                # Consult LLM for strategy selection
                strategy, reasoning = await self.consult_llm_for_strategy(
                    error_type,
                    error_msg,
                    context,
                    available,
                )
                
                # Execute recovery
                recovery_success, new_context = await self.execute_recovery(
                    strategy,
                    context,
                )
                
                # Record attempt
                attempt_record = RecoveryAttempt(
                    timestamp=time.time(),
                    strategy=strategy,
                    context=context.copy(),
                    llm_consulted=True,
                    llm_advice=reasoning,
                    success=recovery_success,
                )
                metrics.recovery_attempts.append(attempt_record)
                
                if recovery_success:
                    self._print(f"   ✓ Recovery successful, retrying...", "green")
                    context.update(new_context)
                else:
                    self._print(f"   ⚠ Recovery failed, trying next strategy...", "yellow")
                    
                    # Try fallback strategies
                    for fallback in available[1:]:
                        self._print(f"   Trying fallback: {fallback.value}", "cyan")
                        recovery_success, new_context = await self.execute_recovery(
                            fallback,
                            context,
                        )
                        if recovery_success:
                            context.update(new_context)
                            break
                    
                    if not recovery_success:
                        # Last resort: ask LLM for creative workaround
                        self._print(f"   🆘 All strategies failed, consulting LLM for workaround...", "magenta")
                        await self._recover_consult_llm(context)
                        # Continue anyway with modified context
                        context["force_continue"] = True
                        break
        
        metrics.end_time = time.time()
        
        if not success and context.get("force_continue"):
            self._print(f"\n⚠ Continuing with best-effort (forced)", "yellow")
            try:
                result = await func(context)
                success = True
                metrics.success = True
            except Exception as e:
                self._print(f"   Final failure: {e}", "red")
        
        # Store execution in history
        self._store_execution_history(metrics)
        
        return success, result, metrics
    
    def _store_execution_history(self, metrics: ExecutionMetrics):
        """Przechowuje historię wykonań."""
        history = self.knowledge_base.setdefault("execution_history", [])
        history.append({
            "timestamp": datetime.now().isoformat(),
            "success": metrics.success,
            "attempts": metrics.attempts,
            "recovery_count": metrics.recovery_count,
            "duration_ms": metrics.duration_ms,
            "error_type": metrics.error_type,
        })
        # Keep last 100 executions
        self.knowledge_base["execution_history"] = history[-100:]
        self._save_knowledge()
    
    def get_learning_report(self) -> dict:
        """Generuje raport uczenia się."""
        history = self.knowledge_base.get("execution_history", [])
        if not history:
            return {"message": "No executions yet"}
        
        total = len(history)
        successful = sum(1 for h in history if h.get("success"))
        avg_duration = sum(h.get("duration_ms", 0) for h in history) / total if total > 0 else 0
        avg_recoveries = sum(h.get("recovery_count", 0) for h in history) / total if total > 0 else 0
        
        # Calculate improvement over time
        recent = history[-10:] if len(history) >= 10 else history
        recent_success_rate = sum(1 for h in recent if h.get("success")) / len(recent) if recent else 0
        
        return {
            "total_executions": total,
            "successful": successful,
            "success_rate": successful / total if total > 0 else 0,
            "recent_success_rate": recent_success_rate,
            "avg_duration_ms": avg_duration,
            "avg_recoveries": avg_recoveries,
            "patterns_learned": len(self.knowledge_base.get("error_patterns", {})),
            "llm_insights": len(self.knowledge_base.get("llm_insights", [])),
            "evolution": "System is learning and adapting",
        }
    
    def _get_available_strategies(
        self,
        error_type: str,
        context: dict,
    ) -> list[RecoveryStrategy]:
        """Określa dostępne strategie dla danego błędu."""
        strategies = [
            RecoveryStrategy.CONSULT_LLM,
            RecoveryStrategy.RETRY_WITH_DELAY,
        ]
        
        if "HF_TOKEN" in error_type or "huggingface" in error_type.lower():
            strategies.insert(0, RecoveryStrategy.SWITCH_FALLBACK)
            strategies.insert(1, RecoveryStrategy.FALLBACK_LOCAL_MODEL)
        
        if "playwright" in error_type.lower() or "browser" in error_type.lower():
            strategies.insert(0, RecoveryStrategy.INSTALL_DEPENDENCY)
        
        if "arg" in error_type.lower() or "option" in error_type.lower():
            strategies.insert(0, RecoveryStrategy.MODIFY_ARGS)
        
        if "timeout" in error_type.lower() or "network" in error_type.lower():
            strategies.insert(0, RecoveryStrategy.RETRY_WITH_DELAY)
            strategies.insert(1, RecoveryStrategy.USE_ALTERNATIVE_SITE)
        
        if "credit" in error_type.lower() or "402" in error_type or "rate_limit" in error_type.lower():
            strategies.insert(0, RecoveryStrategy.FALLBACK_LOCAL_MODEL)
        
        if len(self.current_metrics.recovery_attempts if self.current_metrics else []) > 2:
            # Escalate after multiple failures
            strategies.append(RecoveryStrategy.ESCALATE_TO_CLOUD)
        
        return strategies


class AutonomousExampleRunner:
    """Autonomiczny runner z evolutionary recovery."""
    
    def __init__(self, console: Optional[Console] = None):
        self.console = console
        self.recovery_engine = EvolutionaryRecoveryEngine(console)
        self.execution_history: list[ExecutionMetrics] = []
    
    def _print(self, message: str, style: str = ""):
        if self.console and HAS_RICH:
            self.console.print(message, style=style)
        else:
            print(message)
    
    async def run_example(
        self,
        scenario_id: str,
        script_path: Path,
        args: list[str],
        env_setup: dict,
    ) -> tuple[bool, ExecutionMetrics]:
        """Uruchamia przykład z pełnym autonomicznym recovery."""
        
        async def _execute(context: dict) -> dict:
            """Funkcja wykonywana z retry."""
            cmd = [sys.executable, str(context["script_path"])]
            
            # Apply arg modifications from recovery
            args = context.get("modified_args", context["args"])
            
            # Add positional arg if needed
            if context.get("positional_arg"):
                cmd.append(context["positional_arg"])
            
            cmd.extend(args)
            
            # Setup env
            for key, value in context.get("env_setup", {}).items():
                os.environ[key] = value
            
            # Skip HF if needed
            if context.get("skip_hf_hub"):
                os.environ["HF_HUB_OFFLINE"] = "1"
            
            self._print(f"   Executing: {' '.join(cmd)}", "dim")
            
            import subprocess
            result = subprocess.run(
                cmd,
                cwd=str(context["script_path"].parent),
                capture_output=True,
                text=True,
            )
            
            if result.returncode != 0:
                # Analyze error
                stderr = result.stderr
                stdout = result.stdout
                
                error_msg = stderr or stdout
                
                if "No such option" in error_msg:
                    raise ValueError(f"ARG_ERROR: {error_msg}")
                elif "HF_TOKEN" in error_msg or "huggingface" in error_msg.lower():
                    raise RuntimeError(f"HF_TOKEN_ERROR: {error_msg}")
                elif "playwright" in error_msg.lower():
                    raise RuntimeError(f"PLAYWRIGHT_ERROR: {error_msg}")
                else:
                    raise RuntimeError(f"EXECUTION_ERROR: {error_msg}")
            
            return {"stdout": result.stdout, "stderr": result.stderr}
        
        context = {
            "scenario_id": scenario_id,
            "script_path": script_path,
            "args": args,
            "env_setup": env_setup,
        }
        
        success, result, metrics = await self.recovery_engine.execute_with_evolutionary_recovery(
            _execute,
            context,
            max_attempts=5,
        )
        
        self.execution_history.append(metrics)
        
        # Print summary
        self._print(f"\n{'='*60}", "dim")
        self._print(f"Execution Summary:", "bold")
        self._print(f"  Attempts: {metrics.attempts}", "cyan")
        self._print(f"  Recovery operations: {metrics.recovery_count}", "cyan")
        self._print(f"  Duration: {metrics.duration_ms:.0f}ms", "cyan")
        self._print(f"  Success: {'✓' if success else '✗'}", "green" if success else "red")
        
        if metrics.recovery_attempts:
            self._print(f"\nRecovery strategies used:", "yellow")
            for r in metrics.recovery_attempts:
                status = "✓" if r.success else "✗"
                self._print(f"  {status} {r.strategy.value} ({r.duration_ms:.0f}ms)", "dim")
        
        self._print(f"{'='*60}\n", "dim")
        
        return success, metrics
    
    def get_learning_report(self) -> dict:
        """Generuje raport uczenia się."""
        if not self.execution_history:
            return {"message": "No executions yet"}
        
        total = len(self.execution_history)
        successful = sum(1 for m in self.execution_history if m.success)
        avg_duration = sum(m.duration_ms for m in self.execution_history) / total
        avg_recoveries = sum(m.recovery_count for m in self.execution_history) / total
        
        return {
            "total_executions": total,
            "successful": successful,
            "success_rate": successful / total,
            "avg_duration_ms": avg_duration,
            "avg_recoveries": avg_recoveries,
            "evolution": "System is learning and adapting",
        }
