"""Strategy planning and recovery actions for evolutionary executions."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Optional

try:
    from rich.console import Console

    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    Console = None

from .store import EvolutionaryKnowledgeStore
from .types import ExecutionMetrics, RecoveryStrategy


class EvolutionaryRecoveryPlanner:
    """Chooses and executes recovery strategies."""

    def __init__(
        self,
        knowledge_store: EvolutionaryKnowledgeStore,
        console: Optional[Console] = None,
    ):
        self.console = console
        self.knowledge_store = knowledge_store
        self.knowledge_base = knowledge_store.knowledge_base
        self.current_metrics: Optional[ExecutionMetrics] = None

    def _print(self, message: str, style: str = "") -> None:
        if self.console and HAS_RICH:
            self.console.print(message, style=style)
        else:
            print(message)

    async def consult_llm_for_strategy(
        self,
        error_type: str,
        error_message: str,
        context: dict[str, Any],
        available_strategies: list[RecoveryStrategy],
    ) -> tuple[RecoveryStrategy, str]:
        """Konsultuje się z LLM jaką strategię wybrać."""
        self._print("🤖 Consulting LLM for recovery strategy...", "cyan")

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

                    for strategy in available_strategies:
                        if strategy.value == strategy_name or strategy.name.lower() == strategy_name.lower():
                            self._print(f"   LLM suggests: {strategy.value}", "green")
                            self._print(f"   Reasoning: {reasoning}", "dim")
                            return strategy, reasoning
                except Exception:
                    pass

            self._print("   LLM consultation failed, using learned patterns", "yellow")
        except Exception as exc:
            self._print(f"   LLM unavailable: {exc}", "yellow")

        return self._select_from_learned_patterns(error_type, available_strategies)

    def _select_from_learned_patterns(
        self,
        error_type: str,
        available_strategies: list[RecoveryStrategy],
    ) -> tuple[RecoveryStrategy, str]:
        """Wybiera strategię na podstawie historycznych wzorców."""
        if not available_strategies:
            return RecoveryStrategy.RETRY_WITH_DELAY, "No available strategies"

        patterns = self.knowledge_base.get("error_patterns", {})

        if error_type in patterns:
            history = patterns[error_type]
            best_strategy = None
            best_success_rate = 0.0

            for strategy in available_strategies:
                s_history = history.get(strategy.value, {"attempts": 0, "successes": 0})
                attempts = s_history.get("attempts", 0)
                if attempts > 0:
                    rate = s_history.get("successes", 0) / attempts
                    if rate > best_success_rate:
                        best_success_rate = rate
                        best_strategy = strategy

            if best_strategy and best_success_rate > 0.3:
                return best_strategy, f"Learned pattern: {best_success_rate:.0%} success rate"

        lowered = error_type.lower()
        if "hf_token" in lowered or "huggingface" in lowered:
            return RecoveryStrategy.SWITCH_FALLBACK, "HF auth issue - use fallback"
        if "playwright" in lowered or "browser" in lowered:
            return RecoveryStrategy.INSTALL_DEPENDENCY, "Browser automation issue"
        if "timeout" in lowered:
            return RecoveryStrategy.RETRY_WITH_DELAY, "Network timeout"

        return available_strategies[0], "Default first strategy"

    async def plan_strategy(
        self,
        error_type: str,
        error_message: str,
        context: dict[str, Any],
        attempt_index: int,
        current_metrics: Optional[ExecutionMetrics] = None,
    ) -> tuple[RecoveryStrategy, str, bool]:
        """Plan the best recovery strategy for the current attempt."""
        if current_metrics is not None:
            self.current_metrics = current_metrics

        available = self._get_available_strategies(error_type, context, current_metrics)
        if attempt_index < 2:
            strategy, reasoning = self._select_from_learned_patterns(error_type, available)
            return strategy, reasoning, False

        strategy, reasoning = await self.consult_llm_for_strategy(
            error_type,
            error_message,
            context,
            available,
        )
        return strategy, reasoning, True

    async def execute_recovery(
        self,
        strategy: RecoveryStrategy,
        context: dict[str, Any],
        current_metrics: Optional[ExecutionMetrics] = None,
    ) -> tuple[bool, dict[str, Any]]:
        """Wykonuje strategię naprawy."""
        if current_metrics is not None:
            self.current_metrics = current_metrics

        self._print(f"🔧 Executing recovery: {strategy.value}", "cyan")

        start = asyncio.get_event_loop().time()
        success = False
        new_context = context.copy()

        handler_map = {
            RecoveryStrategy.INSTALL_DEPENDENCY: self._recover_install_dependency,
            RecoveryStrategy.SWITCH_FALLBACK: self._recover_switch_fallback,
            RecoveryStrategy.CONFIGURE_ENV: self._recover_configure_env,
            RecoveryStrategy.RETRY_WITH_DELAY: self._recover_retry_with_delay,
            RecoveryStrategy.MODIFY_ARGS: self._recover_modify_args,
            RecoveryStrategy.CONSULT_LLM: self._recover_consult_llm,
            RecoveryStrategy.FALLBACK_LOCAL_MODEL: self._recover_fallback_local_model,
            RecoveryStrategy.USE_ALTERNATIVE_SITE: self._recover_alternative_site,
            RecoveryStrategy.ESCALATE_TO_CLOUD: self._recover_escalate_to_cloud,
        }

        try:
            handler = handler_map.get(strategy, self._recover_generic)
            success = await handler(new_context)
        except Exception as exc:
            self._print(f"   Recovery failed: {exc}", "red")
            new_context["recovery_error"] = str(exc)

        duration = (asyncio.get_event_loop().time() - start) * 1000
        new_context["recovery_duration_ms"] = duration

        if context.get("error_type"):
            self.knowledge_store.record_recovery(context["error_type"], strategy, success)

        return success, new_context

    async def _recover_install_dependency(self, context: dict[str, Any]) -> bool:
        """Naprawa: instalacja zależności."""
        self._print("   Installing missing dependencies...", "yellow")

        try:
            from nlp2cmd.utils.playwright_installer import ensure_playwright_installed

            result = ensure_playwright_installed(console=self.console, auto_install=True)
            if result:
                self._print("   ✓ Dependencies installed", "green")
                return True
        except Exception as exc:
            self._print(f"   ✗ Installation failed: {exc}", "red")

        return False

    async def _recover_switch_fallback(self, context: dict[str, Any]) -> bool:
        """Naprawa: przełączenie na fallback."""
        self._print("   Switching to fallback configuration...", "yellow")

        if "HF_TOKEN" in context.get("error_type", ""):
            self._print("   ⚠ Continuing without HF_TOKEN (rate limits apply)", "yellow")
            self._print("   💡 Tip: Set HF_TOKEN for better performance", "cyan")
            context["skip_hf_hub"] = True
            return True

        return False

    async def _recover_configure_env(self, context: dict[str, Any]) -> bool:
        """Naprawa: konfiguracja środowiska."""
        self._print("   Configuring environment...", "yellow")

        if not os.getenv("OLLAMA_BASE_URL"):
            os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"

        return True

    async def _recover_retry_with_delay(self, context: dict[str, Any]) -> bool:
        """Naprawa: ponowna próba z opóźnieniem."""
        delay = context.get("retry_delay", 5)
        self._print(f"   Retrying in {delay}s...", "yellow")
        await asyncio.sleep(delay)
        return True

    async def _recover_modify_args(self, context: dict[str, Any]) -> bool:
        """Naprawa: modyfikacja argumentów."""
        self._print("   Modifying execution arguments...", "yellow")

        args = context.get("args", [])
        if "--query" in args and context.get("error_message", "").startswith("No such option"):
            idx = args.index("--query")
            if idx + 1 < len(args):
                value = args[idx + 1]
                args = [a for a in args if a not in ["--query", value]]
                context["positional_arg"] = value

        context["args"] = args
        return True

    async def _recover_consult_llm(self, context: dict[str, Any]) -> bool:
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
        except Exception as exc:
            self._print(f"   LLM consultation failed: {exc}", "yellow")

        return False

    async def _recover_escalate_to_cloud(self, context: dict[str, Any]) -> bool:
        """Naprawa: eskalacja do cloud LLM."""
        self._print("   Escalating to cloud LLM for complex recovery...", "cyan")

        try:
            from nlp2cmd.llm.router import LLMRouter

            router = LLMRouter(adaptive_learning=True)
            attempted = []
            if self.current_metrics:
                attempted = [r.strategy.value for r in self.current_metrics.recovery_attempts]

            prompt = f"""
Critical execution failure. Previous recovery strategies failed.
Error: {context.get('error_type')}: {context.get('error_message')}
Attempted: {attempted}

Design a creative workaround to complete the task.
"""

            resp = await router.completion(
                prompt,
                task="planning",
                max_tokens=500,
                temperature=0.3,
            )

            if resp.success:
                self._print(f"   Cloud LLM strategy: {resp.content[:150]}...", "green")
                context["cloud_strategy"] = resp.content
                return True
        except Exception:
            pass

        return False

    async def _recover_fallback_local_model(self, context: dict[str, Any]) -> bool:
        """Naprawa: przejście na lokalny model."""
        self._print("   Switching to local Ollama model...", "yellow")

        os.environ["NLP2CMD_USE_LOCAL"] = "1"
        context["use_local_model"] = True
        return True

    async def _recover_alternative_site(self, context: dict[str, Any]) -> bool:
        """Naprawa: użycie alternatywnego site'u."""
        self._print("   Trying alternative drawing site...", "yellow")

        context["alternative_site"] = "jspaint"
        return True

    async def _recover_generic(self, context: dict[str, Any]) -> bool:
        """Generyczna naprawa: kontynuuj mimo błędu."""
        self._print("   Applying generic recovery (continue with warnings)...", "yellow")
        context["continue_with_warnings"] = True
        return True

    def _get_available_strategies(
        self,
        error_type: str,
        context: dict[str, Any],
        current_metrics: Optional[ExecutionMetrics] = None,
    ) -> list[RecoveryStrategy]:
        """Określa dostępne strategie dla danego błędu."""
        metrics = current_metrics or self.current_metrics
        strategies: list[RecoveryStrategy] = []

        def add(strategy: RecoveryStrategy) -> None:
            if strategy not in strategies:
                strategies.append(strategy)

        lowered = error_type.lower()

        if "hf_token" in error_type or "huggingface" in lowered:
            add(RecoveryStrategy.SWITCH_FALLBACK)
            add(RecoveryStrategy.FALLBACK_LOCAL_MODEL)

        if "playwright" in lowered or "browser" in lowered:
            add(RecoveryStrategy.INSTALL_DEPENDENCY)

        if "dependency" in lowered or "modulenotfounderror" in lowered:
            add(RecoveryStrategy.INSTALL_DEPENDENCY)

        if "arg" in lowered or "option" in lowered:
            add(RecoveryStrategy.MODIFY_ARGS)

        if "timeout" in lowered or "network" in lowered:
            add(RecoveryStrategy.RETRY_WITH_DELAY)
            add(RecoveryStrategy.USE_ALTERNATIVE_SITE)

        if "credit" in lowered or "402" in error_type or "rate_limit" in lowered:
            add(RecoveryStrategy.FALLBACK_LOCAL_MODEL)

        add(RecoveryStrategy.CONSULT_LLM)
        add(RecoveryStrategy.RETRY_WITH_DELAY)

        if metrics and len(metrics.recovery_attempts) > 2:
            add(RecoveryStrategy.ESCALATE_TO_CLOUD)

        return strategies or [RecoveryStrategy.CONSULT_LLM, RecoveryStrategy.RETRY_WITH_DELAY]
