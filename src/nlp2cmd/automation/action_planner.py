"""
Action Planner for NLP2CMD — Multi-Step Command Decomposition.

Decomposes complex natural language commands into ActionPlan sequences.
Uses a 2-tier approach:
  1. Rule-based decomposition for known services (0ms overhead)
  2. LLM decomposition via Ollama for unknown patterns (~200-400ms cold)

Position: Layer 0.7 — after ComplexQueryDetector, before PipelineRunner.

Example:
    planner = ActionPlanner()
    plan = await planner.decompose(
        "otwórz openrouter.ai i wyciągnij klucz API, zapisz do .env"
    )
    # plan.steps == [navigate, extract_api_key, save_env]
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Optional

log = logging.getLogger("nlp2cmd.action_planner")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class ActionStep:
    """Single step in an execution plan."""
    action: str                     # "navigate", "click", "extract_api_key", "save_env"
    params: dict[str, Any] = field(default_factory=dict)
    description: str = ""           # Human-readable description
    timeout_ms: int = 10000         # Max execution time
    retry_on_fail: bool = True
    depends_on: Optional[str] = None  # ID of prior step (if depends on its result)
    store_as: Optional[str] = None    # Variable name to store result

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"action": self.action, "params": self.params}
        if self.description:
            d["description"] = self.description
        if self.store_as:
            d["store_as"] = self.store_as
        return d


@dataclass
class ActionPlan:
    """Complete execution plan for a complex command."""
    query: str                      # Original query
    steps: list[ActionStep] = field(default_factory=list)
    confidence: float = 0.0
    source: str = ""                # "rule_decomposer" | "llm_planner" | "cache"
    estimated_time_ms: int = 0

    def to_cache_dict(self) -> dict:
        """Serialize for cache storage."""
        return {
            "query": self.query,
            "steps": [s.to_dict() for s in self.steps],
            "confidence": self.confidence,
            "source": self.source,
        }

    @classmethod
    def from_cache_dict(cls, data: dict) -> ActionPlan:
        """Deserialize from cache."""
        steps = []
        for s in data.get("steps", []):
            steps.append(ActionStep(
                action=s.get("action", "unknown"),
                params=s.get("params", {}),
                description=s.get("description", ""),
                store_as=s.get("store_as"),
            ))
        return cls(
            query=data.get("query", ""),
            steps=steps,
            confidence=data.get("confidence", 0.8),
            source="cache",
        )


# ---------------------------------------------------------------------------
# Known services — rule-based decomposition without LLM
# ---------------------------------------------------------------------------
KNOWN_SERVICES: dict[str, dict[str, Any]] = {
    "openrouter": {
        "base_url": "https://openrouter.ai",
        "keys_url": "https://openrouter.ai/settings/keys",
        "key_pattern": r"sk-or-v1-[a-f0-9]{64}",
        "env_var": "OPENROUTER_API_KEY",
        "key_selectors": ["code", ".api-key-value", "[data-testid='api-key']"],
    },
    "anthropic": {
        "base_url": "https://console.anthropic.com",
        "keys_url": "https://console.anthropic.com/settings/keys",
        "key_pattern": r"sk-ant-[a-zA-Z0-9-]{40,}",
        "env_var": "ANTHROPIC_API_KEY",
        "key_selectors": ["code", "pre"],
    },
    "openai": {
        "base_url": "https://platform.openai.com",
        "keys_url": "https://platform.openai.com/api-keys",
        "key_pattern": r"sk-[a-zA-Z0-9]{48,}",
        "env_var": "OPENAI_API_KEY",
        "key_selectors": ["code", "pre", ".sensitive"],
    },
    "github": {
        "base_url": "https://github.com",
        "keys_url": "https://github.com/settings/tokens",
        "key_pattern": r"ghp_[a-zA-Z0-9]{36}",
        "env_var": "GITHUB_TOKEN",
        "key_selectors": ["code", "#new-oauth-token"],
    },
    "huggingface": {
        "base_url": "https://huggingface.co",
        "keys_url": "https://huggingface.co/settings/tokens",
        "key_pattern": r"hf_[a-zA-Z0-9]{34,}",
        "env_var": "HF_TOKEN",
        "key_selectors": ["code", "pre"],
    },
    "replicate": {
        "base_url": "https://replicate.com",
        "keys_url": "https://replicate.com/account/api-tokens",
        "key_pattern": r"r8_[a-zA-Z0-9]{37,}",
        "env_var": "REPLICATE_API_TOKEN",
        "key_selectors": ["code", "pre"],
    },
}


# ---------------------------------------------------------------------------
# LLM System Prompt
# ---------------------------------------------------------------------------
_SYSTEM_PROMPT = """\
Jesteś planistą akcji browser automation.
Dekomponujesz złożone komendy na sekwencję kroków.

Dostępne akcje:
- browser_open: Otwórz przeglądarkę
- navigate: Przejdź na URL {url}
- click: Kliknij element {selector} lub {text}
- type_text: Wpisz tekst {text} w pole {selector}
- extract_text: Wyciągnij tekst z {selector} pasujący do {pattern}
- extract_api_key: Wyciągnij API key z serwisu {service}
- save_env: Zapisz wartość do .env {var_name}={value}
- fill_form: Wypełnij formularz {fields}
- submit_form: Wyślij formularz
- screenshot: Zrób screenshot
- wait: Czekaj {ms} milisekund
- new_tab: Otwórz nowy tab
- switch_tab: Przełącz na tab {filter}
- login: Zaloguj się {email} {password}

Znane serwisy (użyj ich URL-ów):
- openrouter: keys=https://openrouter.ai/settings/keys pattern=sk-or-v1-*
- anthropic: keys=https://console.anthropic.com/settings/keys pattern=sk-ant-*
- openai: keys=https://platform.openai.com/api-keys pattern=sk-*
- github: keys=https://github.com/settings/tokens pattern=ghp_*

Odpowiedz TYLKO JSON (bez markdown):
[
  {"action": "...", "params": {...}, "description": "..."},
  ...
]"""


# ---------------------------------------------------------------------------
# ActionPlanner
# ---------------------------------------------------------------------------
class ActionPlanner:
    """Decomposes complex NL commands into ActionPlan via rules or LLM.

    Costs:
    - Rule match (known service): ~0ms
    - LLM (Ollama cold): ~200-400ms
    - Cache hit: ~0.01ms (handled by EvolutionaryCache)
    """

    def __init__(
        self,
        ollama_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.ollama_url = ollama_url or os.getenv(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        )
        self.model = model or os.getenv("NLP2CMD_PLANNER_MODEL", "qwen2.5:3b")

    async def decompose(
        self,
        query: str,
        detected_intents: Optional[list[str]] = None,
    ) -> ActionPlan:
        """Decompose query into ActionPlan.

        Tries rule-based first, falls back to LLM.
        """
        # Tier 0: Rule-based for known patterns (no LLM needed)
        rule_plan = self._try_rule_decomposition(query)
        if rule_plan:
            log.debug("Rule decomposition hit for: %s", query[:60])
            return rule_plan

        # Tier 1: LLM decomposition
        try:
            plan = await self._call_llm(query)
            if plan:
                return plan
        except Exception as e:
            log.warning("LLM planner failed: %s", e)

        # Tier 2: Heuristic fallback
        return self._heuristic_decomposition(query)

    def decompose_sync(
        self,
        query: str,
        detected_intents: Optional[list[str]] = None,
    ) -> ActionPlan:
        """Synchronous wrapper for decompose()."""
        # Try rule-based first (no async needed)
        rule_plan = self._try_rule_decomposition(query)
        if rule_plan:
            return rule_plan

        # Try LLM via sync requests
        try:
            plan = self._call_llm_sync(query)
            if plan:
                return plan
        except Exception as e:
            log.warning("LLM planner (sync) failed: %s", e)

        return self._heuristic_decomposition(query)

    # ------------------------------------------------------------------
    # Rule-based decomposition
    # ------------------------------------------------------------------
    def _try_rule_decomposition(self, query: str) -> Optional[ActionPlan]:
        """Rule-based decomposition for known service patterns (no LLM)."""
        text = query.lower()

        # Pattern: "extract API key from <service> and save to .env"
        for svc_name, svc in KNOWN_SERVICES.items():
            if svc_name not in text:
                continue
            if not any(w in text for w in ["klucz", "key", "api", "token"]):
                continue

            steps = [
                ActionStep(
                    action="navigate",
                    params={"url": svc["keys_url"]},
                    description=f"Przejdź na stronę kluczy {svc_name}",
                ),
                ActionStep(
                    action="echo",
                    params={
                        "message": (
                            f"🔐 Otworzyłem stronę generowania kluczy {svc_name}. "
                            "Utwórz nowy klucz w przeglądarce, skopiuj go do schowka, "
                            "a następnie wklej tutaj."
                        )
                    },
                    description="Instrukcja ręcznego skopiowania klucza",
                ),
                ActionStep(
                    action="prompt_secret",
                    params={
                        "prompt": f"Wklej klucz API dla {svc_name} (nie będzie wyświetlany): ",
                        "env_var": svc["env_var"],
                    },
                    description=f"Wprowadź klucz API {svc_name}",
                    store_as="api_key",
                ),
            ]

            if ".env" in text or "zapisz" in text or "save" in text:
                steps.append(ActionStep(
                    action="save_env",
                    params={
                        "var_name": svc["env_var"],
                        "file": ".env",
                        "value": "$api_key",
                    },
                    description=f"Zapisz {svc['env_var']} do .env",
                ))

            return ActionPlan(
                query=query,
                steps=steps,
                confidence=0.95,
                source="rule_decomposer",
                estimated_time_ms=len(steps) * 2000,
            )

        # Pattern: "open N tabs: X, Y, Z"
        multi_tab = re.search(
            r"(?:otw[oó]rz|open)\s+(\d+)\s+(?:tab|kart)", text
        )
        if multi_tab:
            # Try to extract URLs/domains from text
            domains = re.findall(
                r'\b([a-zA-Z0-9][\w\-]*\.(?:com|org|net|io|ai|dev|pl|app|co))\b',
                text,
            )
            steps = []
            for i, domain in enumerate(domains):
                if i > 0:
                    steps.append(ActionStep(
                        action="new_tab", params={},
                        description="Nowy tab",
                    ))
                steps.append(ActionStep(
                    action="navigate",
                    params={"url": f"https://{domain}"},
                    description=f"Otwórz {domain}",
                ))
            if steps:
                return ActionPlan(
                    query=query, steps=steps,
                    confidence=0.9, source="rule_decomposer",
                    estimated_time_ms=len(steps) * 1500,
                )

        return None

    # ------------------------------------------------------------------
    # LLM decomposition
    # ------------------------------------------------------------------
    async def _call_llm(self, query: str) -> Optional[ActionPlan]:
        """Async LLM call via Ollama."""
        try:
            import httpx
        except ImportError:
            log.debug("httpx not available for async LLM call")
            return self._call_llm_sync(query)

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": query,
                    "system": _SYSTEM_PROMPT,
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 500},
                },
                timeout=30,
            )
            if resp.status_code != 200:
                log.warning("Ollama returned %d", resp.status_code)
                return None
            return self._parse_llm_response(query, resp.json().get("response", ""))

    def _call_llm_sync(self, query: str) -> Optional[ActionPlan]:
        """Synchronous LLM call via requests."""
        try:
            import requests
        except ImportError:
            log.debug("requests not available for sync LLM call")
            return None

        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": query,
                    "system": _SYSTEM_PROMPT,
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 500},
                },
                timeout=30,
            )
            if resp.status_code != 200:
                return None
            return self._parse_llm_response(query, resp.json().get("response", ""))
        except Exception as e:
            log.warning("Sync LLM call failed: %s", e)
            return None

    def _parse_llm_response(self, query: str, raw: str) -> Optional[ActionPlan]:
        """Parse LLM JSON response into ActionPlan."""
        # Strip markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
        raw = re.sub(r"\s*```$", "", raw)

        try:
            steps_data = json.loads(raw)
        except json.JSONDecodeError:
            log.warning("Failed to parse LLM response as JSON")
            return None

        if not isinstance(steps_data, list):
            return None

        steps = []
        for s in steps_data:
            if not isinstance(s, dict):
                continue

            # Enrich with known service data
            if s.get("action") == "extract_api_key":
                service = s.get("params", {}).get("service", "")
                if service in KNOWN_SERVICES:
                    svc = KNOWN_SERVICES[service]
                    s.setdefault("params", {})
                    s["params"].setdefault("pattern", svc["key_pattern"])
                    s["params"].setdefault("selectors", svc.get("key_selectors", []))

            if s.get("action") == "save_env" and "var_name" not in s.get("params", {}):
                for svc_name, svc in KNOWN_SERVICES.items():
                    if svc_name in query.lower():
                        s.setdefault("params", {})
                        s["params"]["var_name"] = svc["env_var"]
                        break

            steps.append(ActionStep(
                action=s.get("action", "unknown"),
                params=s.get("params", {}),
                description=s.get("description", ""),
                store_as=s.get("store_as"),
            ))

        if not steps:
            return None

        return ActionPlan(
            query=query,
            steps=steps,
            confidence=0.85,
            source="llm_planner",
            estimated_time_ms=len(steps) * 2000,
        )

    # ------------------------------------------------------------------
    # Heuristic fallback
    # ------------------------------------------------------------------
    def _heuristic_decomposition(self, query: str) -> ActionPlan:
        """Last-resort heuristic decomposition when rule + LLM fail."""
        text = query.lower()
        steps: list[ActionStep] = []

        # Try to extract a URL/domain
        url_match = re.search(r"(https?://\S+)", text)
        domain_match = re.search(
            r'\b([a-zA-Z0-9][\w\-]*\.(?:com|org|net|io|ai|dev|pl|app|co))\b',
            text,
        )
        url = None
        if url_match:
            url = url_match.group(1).rstrip(".,)")
        elif domain_match:
            url = f"https://{domain_match.group(1)}"

        if url:
            steps.append(ActionStep(
                action="navigate", params={"url": url},
                description=f"Otwórz {url}",
            ))

        # Check for extract/copy operations
        if any(w in text for w in ["wyciągnij", "wyciagnij", "skopiuj", "extract", "copy"]):
            steps.append(ActionStep(
                action="extract_text",
                params={"selectors": ["code", "pre", ".api-key"]},
                description="Wyciągnij dane ze strony",
                store_as="extracted",
            ))

        # Check for save operations
        if any(w in text for w in ["zapisz", "save", ".env"]):
            steps.append(ActionStep(
                action="save_env",
                params={"file": ".env", "value": "$extracted"},
                description="Zapisz do .env",
            ))

        # Check for screenshot
        if any(w in text for w in ["screenshot", "zrzut"]):
            steps.append(ActionStep(
                action="screenshot", params={},
                description="Zrób screenshot",
            ))

        if not steps:
            steps.append(ActionStep(
                action="echo",
                params={"message": f"Nie udało się zaplanować: {query}"},
                description="Brak planu",
            ))

        return ActionPlan(
            query=query,
            steps=steps,
            confidence=0.5,
            source="heuristic",
            estimated_time_ms=len(steps) * 2000,
        )
