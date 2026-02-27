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
import shutil
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
# Known services — loaded from YAML config (Etap 2), hardcoded fallback
# ---------------------------------------------------------------------------
_HARDCODED_SERVICES: dict[str, dict[str, Any]] = {
    "openrouter": {
        "base_url": "https://openrouter.ai",
        "keys_url": "https://openrouter.ai/settings/keys",
        "login_url": "https://openrouter.ai/auth/login",
        "key_pattern": r"sk-or-v1-[a-f0-9]{64}",
        "env_var": "OPENROUTER_API_KEY",
        "key_selectors": ["code", ".api-key-value", "[data-testid='api-key']"],
        "session_indicators": ["API Keys", "Manage your keys", "Create"],
        "login_indicators": ["Sign in", "Log in", "Continue with Google"],
        "create_key": {
            "button_selector": "button:has-text('Create')",
            "form_fields": {
                "name": {"selector": "input[placeholder*='Chatbot']", "default": "nlp2cmd"},
                "credit_limit": {"selector": "input[placeholder*='unlimited']", "default": ""},
            },
            "submit_selector": "button:has-text('Create')",
            "key_reveal_selector": "code, .api-key-value, [data-testid='api-key']",
        },
    },
    "anthropic": {
        "base_url": "https://console.anthropic.com",
        "keys_url": "https://console.anthropic.com/settings/keys",
        "login_url": "https://console.anthropic.com/login",
        "key_pattern": r"sk-ant-[a-zA-Z0-9-]{40,}",
        "env_var": "ANTHROPIC_API_KEY",
        "key_selectors": ["code", "pre"],
        "session_indicators": ["API keys", "Create Key", "Settings"],
        "login_indicators": ["Sign in", "Log in", "Email"],
        "create_key": {
            "button_selector": "button:has-text('Create Key')",
            "form_fields": {
                "name": {"selector": "input[name='name']", "default": "nlp2cmd"},
            },
            "submit_selector": "button[type='submit']:has-text('Create')",
            "key_reveal_selector": "code, pre, .key-value",
        },
    },
    "openai": {
        "base_url": "https://platform.openai.com",
        "keys_url": "https://platform.openai.com/api-keys",
        "login_url": "https://platform.openai.com/login",
        "key_pattern": r"sk-[a-zA-Z0-9]{48,}",
        "env_var": "OPENAI_API_KEY",
        "key_selectors": ["code", "pre", ".sensitive"],
        "session_indicators": ["API keys", "Create new secret key", "Dashboard"],
        "login_indicators": ["Log in", "Welcome back", "Email address"],
        "create_key": {
            "button_selector": "button:has-text('Create new secret key')",
            "form_fields": {
                "name": {"selector": "input[placeholder*='key']", "default": "nlp2cmd"},
            },
            "submit_selector": "button:has-text('Create secret key')",
            "key_reveal_selector": "code, .key-value, input[readonly]",
        },
    },
    "groq": {
        "base_url": "https://console.groq.com",
        "keys_url": "https://console.groq.com/keys",
        "login_url": "https://console.groq.com/login",
        "key_pattern": r"gsk_[a-zA-Z0-9]{52,}",
        "env_var": "GROQ_API_KEY",
        "key_selectors": ["code", "pre", ".api-key"],
        "session_indicators": ["API Keys", "Create API Key", "GroqCloud"],
        "login_indicators": ["Sign in", "Log in", "Continue with Google"],
        "create_key": {
            "button_selector": "button:has-text('Create API Key')",
            "form_fields": {
                "name": {"selector": "input[name='name']", "default": "nlp2cmd"},
            },
            "submit_selector": "button:has-text('Submit')",
            "key_reveal_selector": "code, pre, input[readonly]",
        },
    },
    "mistral": {
        "base_url": "https://console.mistral.ai",
        "keys_url": "https://console.mistral.ai/api-keys",
        "login_url": "https://console.mistral.ai/login",
        "key_pattern": r"[a-zA-Z0-9]{32}",
        "env_var": "MISTRAL_API_KEY",
        "key_selectors": ["code", "pre", ".api-key"],
        "session_indicators": ["API keys", "Create new key", "La Plateforme"],
        "login_indicators": ["Sign in", "Log in"],
        "create_key": {
            "button_selector": "button:has-text('Create new key')",
            "form_fields": {
                "name": {"selector": "input[name='name']", "default": "nlp2cmd"},
            },
            "submit_selector": "button:has-text('Create')",
            "key_reveal_selector": "code, pre, input[readonly]",
        },
    },
    "deepseek": {
        "base_url": "https://platform.deepseek.com",
        "keys_url": "https://platform.deepseek.com/api_keys",
        "login_url": "https://platform.deepseek.com/sign_in",
        "key_pattern": r"sk-[a-f0-9]{48,}",
        "env_var": "DEEPSEEK_API_KEY",
        "key_selectors": ["code", "pre", ".api-key"],
        "session_indicators": ["API keys", "Create new", "DeepSeek"],
        "login_indicators": ["Sign in", "Log in", "Email"],
        "create_key": {
            "button_selector": "button:has-text('Create')",
            "form_fields": {},
            "submit_selector": "button:has-text('Create')",
            "key_reveal_selector": "code, pre, input[readonly]",
        },
    },
    "together": {
        "base_url": "https://api.together.ai",
        "keys_url": "https://api.together.ai/settings/api-keys",
        "login_url": "https://api.together.ai/signin",
        "key_pattern": r"[a-f0-9]{64}",
        "env_var": "TOGETHER_API_KEY",
        "key_selectors": ["code", "pre", ".api-key"],
        "session_indicators": ["API Keys", "Create", "Together"],
        "login_indicators": ["Sign in", "Log in"],
        "create_key": {
            "button_selector": "button:has-text('Create')",
            "form_fields": {},
            "submit_selector": "button:has-text('Create')",
            "key_reveal_selector": "code, pre",
        },
    },
    "github": {
        "base_url": "https://github.com",
        "keys_url": "https://github.com/settings/tokens",
        "login_url": "https://github.com/login",
        "key_pattern": r"ghp_[a-zA-Z0-9]{36}",
        "env_var": "GITHUB_TOKEN",
        "key_selectors": ["code", "#new-oauth-token"],
        "session_indicators": ["Personal access tokens", "Generate new token"],
        "login_indicators": ["Sign in to GitHub", "Username or email"],
        "create_key": {
            "button_selector": "a:has-text('Generate new token')",
            "form_fields": {
                "note": {"selector": "#oauth_access_description", "default": "nlp2cmd"},
            },
            "submit_selector": "button:has-text('Generate token')",
            "key_reveal_selector": "code, #new-oauth-token",
        },
    },
    "huggingface": {
        "base_url": "https://huggingface.co",
        "keys_url": "https://huggingface.co/settings/tokens",
        "login_url": "https://huggingface.co/login",
        "key_pattern": r"hf_[a-zA-Z0-9]{34,}",
        "env_var": "HF_TOKEN",
        "key_selectors": ["code", "pre"],
        "session_indicators": ["Access Tokens", "New token", "User Access Tokens"],
        "login_indicators": ["Sign In", "Log In"],
        "create_key": {
            "button_selector": "button:has-text('New token')",
            "form_fields": {
                "name": {"selector": "input[name='name']", "default": "nlp2cmd"},
            },
            "submit_selector": "button:has-text('Generate')",
            "key_reveal_selector": "code, pre, input[readonly]",
        },
    },
    "replicate": {
        "base_url": "https://replicate.com",
        "keys_url": "https://replicate.com/account/api-tokens",
        "login_url": "https://replicate.com/signin",
        "key_pattern": r"r8_[a-zA-Z0-9]{37,}",
        "env_var": "REPLICATE_API_TOKEN",
        "key_selectors": ["code", "pre"],
        "session_indicators": ["API tokens", "Create token"],
        "login_indicators": ["Sign in", "Log in"],
        "create_key": {
            "button_selector": "button:has-text('Create token')",
            "form_fields": {},
            "submit_selector": "button:has-text('Create')",
            "key_reveal_selector": "code, pre",
        },
    },
}

# ---------------------------------------------------------------------------
# Email client configuration — for login fallback
# ---------------------------------------------------------------------------
EMAIL_CLIENTS: dict[str, dict[str, Any]] = {
    "roundcube": {
        "type": "webmail",
        "name": "Roundcube Webmail",
        "login_selectors": {
            "user": "input#rcmloginuser, input[name='_user']",
            "pass": "input#rcmloginpwd, input[name='_pass']",
            "submit": "button#rcmloginsubmit, input[type='submit']",
        },
        "inbox_indicators": ["Inbox", "Odebrane", "INBOX"],
        "search_selector": "input#quicksearchbox",
        "message_list_selector": "#messagelist tbody tr",
    },
    "thunderbird": {
        "type": "desktop",
        "name": "Mozilla Thunderbird",
        "launch_cmd": "thunderbird",
        "shortcuts": {
            "get_mail": "Ctrl+Shift+T",
            "new_message": "Ctrl+N",
            "search": "Ctrl+K",
            "reply": "Ctrl+R",
            "forward": "Ctrl+L",
        },
        "wmclass": "Thunderbird",
    },
    "gmail": {
        "type": "webmail",
        "name": "Gmail",
        "url": "https://mail.google.com",
        "inbox_indicators": ["Inbox", "Primary", "Compose"],
        "search_selector": "input[aria-label='Search mail']",
    },
    "outlook": {
        "type": "webmail",
        "name": "Outlook",
        "url": "https://outlook.live.com/mail",
        "inbox_indicators": ["Inbox", "Focused", "Other"],
        "search_selector": "input[aria-label='Search']",
    },
}

# NL aliases for email clients (Polish + English)
EMAIL_ALIASES: dict[str, str] = {
    "roundcube": "roundcube",
    "round cube": "roundcube",
    "webmail": "roundcube",
    "thunderbird": "thunderbird",
    "poczta": "thunderbird",
    "gmail": "gmail",
    "outlook": "outlook",
    "hotmail": "outlook",
}


def _load_known_services() -> dict[str, dict[str, Any]]:
    """Load KNOWN_SERVICES from YAML config, falling back to hardcoded dict."""
    try:
        from nlp2cmd.nlp.config import get_service_registry
        registry = get_service_registry()
        if len(registry) > 0:
            return registry.as_planner_dict()
    except Exception as e:
        log.debug("YAML service config unavailable, using hardcoded: %s", e)
    return dict(_HARDCODED_SERVICES)


KNOWN_SERVICES: dict[str, dict[str, Any]] = _load_known_services()

# NL aliases for service names (Polish + English)
SERVICE_ALIASES: dict[str, str] = {
    "openrouter": "openrouter", "open router": "openrouter",
    "anthropic": "anthropic", "claude": "anthropic",
    "openai": "openai", "gpt": "openai", "chatgpt": "openai",
    "groq": "groq",
    "mistral": "mistral",
    "deepseek": "deepseek", "deep seek": "deepseek",
    "together": "together", "together.ai": "together", "togetherai": "together",
    "github": "github",
    "huggingface": "huggingface", "hugging face": "huggingface", "hf": "huggingface",
    "replicate": "replicate",
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
def _can_use_desktop_automation() -> bool:
    """Check if desktop automation (xdotool/wmctrl/ydotool) is usable.

    Returns False on Wayland sessions without a working tool.
    """
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    is_wayland = session_type == "wayland" or bool(os.environ.get("WAYLAND_DISPLAY"))

    if is_wayland:
        # On Wayland: ydotool works, xdotool/wmctrl do NOT
        if shutil.which("ydotool"):
            return True
        log.debug(
            "Wayland session detected but ydotool not installed. "
            "Desktop automation unavailable — falling back to Playwright. "
            "Install ydotool for native desktop control: sudo apt install ydotool"
        )
        return False

    # X11 session: xdotool or wmctrl suffice
    return bool(shutil.which("xdotool") or shutil.which("wmctrl"))


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
        self._desktop_available: Optional[bool] = None

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

        # Tier 0b: Multi-tab pattern
        multi_plan = self._try_multi_tab_decomposition(query)
        if multi_plan:
            return multi_plan

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
        rule_plan = self._try_rule_decomposition(query)
        if rule_plan:
            return rule_plan

        multi_plan = self._try_multi_tab_decomposition(query)
        if multi_plan:
            return multi_plan

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
        """Rule-based decomposition for known service patterns (no LLM).

        Enhanced with:
        - Verbose logging at every decision point
        - Session/login detection steps
        - Create-new-key form filling flow
        - Email client fallback when not logged in
        """
        text = query.lower()

        # --- Resolve service name via aliases ---
        svc_name, svc = self._resolve_service(text)
        if not svc_name:
            return None

        if not any(w in text for w in ["klucz", "key", "api", "token"]):
            return None

        log.info(
            "[ActionPlanner] Service matched: %s (keys_url=%s, env_var=%s)",
            svc_name, svc.get("keys_url"), svc.get("env_var"),
        )

        # --- Detect user intent flags ---
        wants_new_tab = self._wants_new_tab(text)
        wants_existing_firefox = self._wants_existing_firefox(text)
        wants_create = self._wants_create_key(text)
        wants_save = any(w in text for w in [".env", "zapisz", "save"])

        log.info(
            "[ActionPlanner] Flags: new_tab=%s, existing_firefox=%s, "
            "create_key=%s, save_to_env=%s",
            wants_new_tab, wants_existing_firefox, wants_create, wants_save,
        )

        steps: list[ActionStep] = []

        # --- Step 0: Screenshot before (audit) ---
        steps.append(ActionStep(
            action="echo",
            params={"text": (
                f"📋 Plan: {'Utwórz nowy' if wants_create else 'Pobierz'} klucz API "
                f"z serwisu {svc_name.upper()}\n"
                f"   URL: {svc.get('keys_url', 'N/A')}\n"
                f"   Env: {svc.get('env_var', 'N/A')}\n"
                f"   Pattern: {svc.get('key_pattern', 'N/A')}"
            )},
            description=f"Podsumowanie planu dla {svc_name}",
        ))

        # --- Step 1: Open browser / navigate ---
        steps.extend(self._build_navigation_steps(
            svc_name, svc, wants_existing_firefox, wants_new_tab,
        ))

        # --- Step 2: Session detection ---
        steps.extend(self._build_session_check_steps(svc_name, svc))

        # --- Step 3: Create key or manual prompt ---
        if wants_create:
            steps.extend(self._build_create_key_steps(svc_name, svc))
        else:
            steps.extend(self._build_manual_key_steps(svc_name, svc, wants_existing_firefox))

        # --- Step 4: Save to .env ---
        if wants_save:
            steps.append(ActionStep(
                action="save_env",
                params={
                    "var_name": svc["env_var"],
                    "file": ".env",
                    "value": "$api_key",
                },
                description=f"Zapisz {svc['env_var']} do .env",
            ))
            steps.append(ActionStep(
                action="echo",
                params={"text": (
                    f"✅ Klucz {svc['env_var']} zapisany do .env\n"
                    f"   Aby załadować: source .env"
                )},
                description="Potwierdzenie zapisu",
            ))

        log.info(
            "[ActionPlanner] Plan built: %d steps for %s (source=rule_decomposer)",
            len(steps), svc_name,
        )

        return ActionPlan(
            query=query,
            steps=steps,
            confidence=0.95,
            source="rule_decomposer",
            estimated_time_ms=len(steps) * 2000,
        )

    # ------------------------------------------------------------------
    # Service resolution
    # ------------------------------------------------------------------
    @staticmethod
    def _resolve_service(text: str) -> tuple[Optional[str], dict[str, Any]]:
        """Resolve service name from text using aliases."""
        for alias, canonical in SERVICE_ALIASES.items():
            if alias in text and canonical in KNOWN_SERVICES:
                return canonical, KNOWN_SERVICES[canonical]
        for svc_name, svc in KNOWN_SERVICES.items():
            if svc_name in text:
                return svc_name, svc
        return None, {}

    # ------------------------------------------------------------------
    # Intent detection helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _wants_new_tab(text: str) -> bool:
        return any(p in text for p in [
            "tab", "kart", "zakład", "zaklad", "nowa karta",
            "new tab", "otworz tab", "otwórz tab", "owtorz tab",
        ])

    @staticmethod
    def _wants_existing_firefox(text: str) -> bool:
        return (
            "firefox" in text
            and any(p in text for p in [
                "już", "juz", "otwart", "otwarty", "otwarte",
                "existing", "already open",
            ])
        )

    @staticmethod
    def _wants_create_key(text: str) -> bool:
        return any(p in text for p in [
            "stwórz", "stworz", "utwórz", "utworz", "wygeneruj",
            "nowy klucz", "nowy key", "nowy token",
            "create", "generate", "new key", "new token",
        ])

    # ------------------------------------------------------------------
    # Step builders
    # ------------------------------------------------------------------
    def _build_navigation_steps(
        self,
        svc_name: str,
        svc: dict[str, Any],
        wants_existing_firefox: bool,
        wants_new_tab: bool,
    ) -> list[ActionStep]:
        """Build steps for opening the keys page."""
        steps: list[ActionStep] = []

        if wants_existing_firefox:
            log.info("[ActionPlanner] Using existing Firefox window (desktop path)")
            steps.append(ActionStep(
                action="open_firefox_tab",
                params={"url": svc["keys_url"]},
                description=f"Otwórz {svc['keys_url']} w istniejącym Firefox",
                retry_on_fail=True,
            ))
            steps.append(ActionStep(
                action="desktop_wait",
                params={"ms": 2000},
                description="Poczekaj na załadowanie strony",
            ))
        else:
            if wants_new_tab:
                steps.append(ActionStep(
                    action="new_tab", params={},
                    description="Otwórz nową kartę w przeglądarce",
                ))
            steps.append(ActionStep(
                action="navigate",
                params={"url": svc["keys_url"]},
                description=f"Przejdź na stronę kluczy {svc_name}",
            ))
            steps.append(ActionStep(
                action="echo",
                params={"text": f"🌐 Otwieram stronę: {svc['keys_url']}"},
                description="Log: nawigacja",
            ))

        return steps

    def _build_session_check_steps(
        self,
        svc_name: str,
        svc: dict[str, Any],
    ) -> list[ActionStep]:
        """Build steps for session/login detection.

        Adds a check_session step that inspects the page for session
        indicators (logged in) vs login indicators (not logged in).
        If not logged in, prompts user about email client.
        """
        steps: list[ActionStep] = []

        session_indicators = svc.get("session_indicators", [])
        login_indicators = svc.get("login_indicators", [])
        login_url = svc.get("login_url", "")

        if session_indicators or login_indicators:
            steps.append(ActionStep(
                action="check_session",
                params={
                    "service": svc_name,
                    "session_indicators": session_indicators,
                    "login_indicators": login_indicators,
                    "login_url": login_url,
                    "keys_url": svc["keys_url"],
                },
                description=f"Sprawdź sesję na {svc_name} (zalogowany?)",
                store_as="session_status",
            ))
            steps.append(ActionStep(
                action="echo",
                params={"text": (
                    f"� Sprawdzam sesję na {svc_name}...\n"
                    f"   Szukam: {', '.join(session_indicators[:3])}\n"
                    f"   Login URL: {login_url}"
                )},
                description="Log: sprawdzanie sesji",
            ))

        return steps

    def _build_create_key_steps(
        self,
        svc_name: str,
        svc: dict[str, Any],
    ) -> list[ActionStep]:
        """Build steps for creating a NEW API key via the provider's form."""
        steps: list[ActionStep] = []
        create_cfg = svc.get("create_key", {})

        if not create_cfg:
            log.info("[ActionPlanner] No create_key config for %s, falling back to manual", svc_name)
            return self._build_manual_key_steps(svc_name, svc, False)

        log.info(
            "[ActionPlanner] Building create-key flow for %s (button=%s, fields=%d)",
            svc_name,
            create_cfg.get("button_selector", "?"),
            len(create_cfg.get("form_fields", {})),
        )

        # Explain what we're doing
        steps.append(ActionStep(
            action="echo",
            params={"text": (
                f"🔑 Tworzę nowy klucz API na {svc_name}...\n"
                f"   Kliknę przycisk: {create_cfg.get('button_selector', '?')}\n"
                f"   Wypełnię formularz: {list(create_cfg.get('form_fields', {}).keys())}"
            )},
            description=f"Log: tworzenie klucza {svc_name}",
        ))

        # Click "Create" button
        steps.append(ActionStep(
            action="click",
            params={"selector": create_cfg["button_selector"]},
            description=f"Kliknij przycisk tworzenia klucza na {svc_name}",
            timeout_ms=5000,
        ))

        steps.append(ActionStep(
            action="wait",
            params={"ms": 1500},
            description="Poczekaj na otwarcie formularza",
        ))

        # Fill form fields
        for field_name, field_cfg in create_cfg.get("form_fields", {}).items():
            default_value = field_cfg.get("default", "")
            if default_value:
                steps.append(ActionStep(
                    action="type_text",
                    params={
                        "selector": field_cfg["selector"],
                        "text": default_value,
                    },
                    description=f"Wypełnij pole '{field_name}': {default_value}",
                ))

        # Submit
        if create_cfg.get("submit_selector"):
            steps.append(ActionStep(
                action="click",
                params={"selector": create_cfg["submit_selector"]},
                description="Zatwierdź formularz tworzenia klucza",
            ))

        steps.append(ActionStep(
            action="wait",
            params={"ms": 3000},
            description="Poczekaj na wygenerowanie klucza",
        ))

        # Screenshot after creation
        steps.append(ActionStep(
            action="screenshot",
            params={"path": f"/tmp/nlp2cmd_{svc_name}_key_created.png"},
            description=f"Zrzut ekranu po utworzeniu klucza {svc_name}",
        ))

        # Try to extract the key automatically
        steps.append(ActionStep(
            action="echo",
            params={"text": (
                f"📋 Klucz powinien być widoczny na stronie.\n"
                f"   Skopiuj go i wklej poniżej.\n"
                f"   Pattern: {svc.get('key_pattern', 'N/A')}"
            )},
            description="Instrukcja skopiowania nowego klucza",
        ))

        steps.append(ActionStep(
            action="prompt_secret",
            params={
                "prompt": f"Wklej nowo utworzony klucz API {svc_name} (nie będzie wyświetlany): ",
                "env_var": svc["env_var"],
            },
            description=f"Wprowadź nowy klucz API {svc_name}",
            store_as="api_key",
        ))

        return steps

    def _build_manual_key_steps(
        self,
        svc_name: str,
        svc: dict[str, Any],
        is_firefox_desktop: bool,
    ) -> list[ActionStep]:
        """Build steps for manual key retrieval (user copies key themselves)."""
        steps: list[ActionStep] = []

        if is_firefox_desktop:
            msg = (
                f"🔐 Otworzyłem stronę kluczy {svc_name} w Firefox.\n"
                f"   1. Znajdź swój klucz API na stronie\n"
                f"   2. Jeśli nie masz klucza, kliknij 'Create' aby utworzyć nowy\n"
                f"   3. Skopiuj klucz do schowka\n"
                f"   4. Wróć do terminala i wklej"
            )
        else:
            msg = (
                f"🔐 Otworzyłem stronę generowania kluczy {svc_name}.\n"
                f"   URL: {svc.get('keys_url', 'N/A')}\n"
                f"   1. Zaloguj się jeśli trzeba\n"
                f"   2. Znajdź lub utwórz klucz API\n"
                f"   3. Skopiuj klucz do schowka\n"
                f"   4. Wklej poniżej"
            )

        steps.append(ActionStep(
            action="echo",
            params={"text": msg},
            description="Instrukcja ręcznego skopiowania klucza",
        ))

        steps.append(ActionStep(
            action="prompt_secret",
            params={
                "prompt": f"Wklej klucz API dla {svc_name} (nie będzie wyświetlany): ",
                "env_var": svc["env_var"],
            },
            description=f"Wprowadź klucz API {svc_name}",
            store_as="api_key",
        ))

        return steps

    def _try_multi_tab_decomposition(self, query: str) -> Optional[ActionPlan]:
        """Rule-based decomposition for 'open N tabs' pattern."""
        text = query.lower()
        multi_tab = re.search(
            r"(?:otw[oó]rz|open)\s+(\d+)\s+(?:tab|kart)", text
        )
        if not multi_tab:
            return None

        domains = re.findall(
            r'\b([a-zA-Z0-9][\w\-]*\.(?:com|org|net|io|ai|dev|pl|app|co))\b',
            text,
        )
        steps: list[ActionStep] = []
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
