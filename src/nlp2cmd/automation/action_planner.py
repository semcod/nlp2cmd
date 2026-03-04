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

# Optional vector store for semantic drawing pattern search
try:
    from nlp2cmd.automation.vector_store import get_vector_store
    _VECTOR_STORE_AVAILABLE = True
except ImportError:
    _VECTOR_STORE_AVAILABLE = False

    def get_vector_store(*a, **kw):  # type: ignore[misc]
        return None

# Import new canvas planning orchestrator
try:
    from nlp2cmd.canvas_planner import CanvasPlanningOrchestrator
    _CANVAS_PLANNER_AVAILABLE = True
except ImportError:
    _CANVAS_PLANNER_AVAILABLE = False


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
                "name": {"selector": "#name", "default": "nlp2cmd"},
            },
            "submit_selector": "div.mt-4 button:has-text('Create'), button:has-text('Create'):not([disabled])",
            "key_reveal_selector": "code, .api-key-value, [data-testid='api-key'], pre",
            "copy_button_text": "Copy",
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
    """Load KNOWN_SERVICES: hardcoded base merged with YAML overrides.

    The hardcoded dict contains the full config (login_url, session_indicators,
    create_key, etc.). The YAML registry may override base_url/keys_url/key_pattern
    but should NOT strip fields it doesn't know about.
    """
    result = {k: dict(v) for k, v in _HARDCODED_SERVICES.items()}
    try:
        from nlp2cmd.nlp.config import get_service_registry
        registry = get_service_registry()
        if len(registry) > 0:
            yaml_dict = registry.as_planner_dict()
            for svc_name, yaml_svc in yaml_dict.items():
                if svc_name in result:
                    # Merge: YAML values override hardcoded, but don't drop new fields
                    result[svc_name].update(yaml_svc)
                else:
                    result[svc_name] = yaml_svc
    except Exception as e:
        log.debug("YAML service config unavailable, using hardcoded only: %s", e)
    return result


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
Jesteś planistą akcji browser automation oraz rysowania na canvas (jspaint).
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
- screenshot: Zrób screenshot {suffix?}
- wait: Czekaj {ms} milisekund
- new_tab: Otwórz nowy tab
- switch_tab: Przełącz na tab {filter}
- login: Zaloguj się {email} {password}

Akcje rysowania (na jspaint.app):
- wait_for_canvas: Poczekaj na załadowanie canvas
- get_canvas_center: Pobierz środek canvas
- select_tool: Wybierz narzędzie {tool} (dostępne: pencil, brush, fill, ellipse, rectangle, line, text, eraser, select)
- set_color: Ustaw kolor {color} (#RRGGBB)
- draw_circle: Narysuj okrąg {radius, offset: [x, y]}
- draw_filled_circle: Narysuj wypełnione koło {radius, offset: [x, y]}
- draw_ellipse: Narysuj elipsę {rx, ry, offset: [x, y]}
- draw_filled_ellipse: Narysuj wypełnioną elipsę {rx, ry, relative_to: "center"}
- draw_rectangle: Narysuj prostokąt {width, height, offset: [x, y]}
- draw_line: Narysuj linię {from_offset: [x, y], to_offset: [x, y]}
- fill_at: Wypełnij w punkcie {offset: [x, y]}
- click_canvas: Kliknij canvas w punkcie {offset: [x, y]}

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

        # Tier 0c: Canvas/drawing pattern (from ComplexCommandPlanner templates)
        canvas_plan = self._try_canvas_decomposition(query)
        if canvas_plan:
            return canvas_plan

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

        canvas_plan = self._try_canvas_decomposition(query)
        if canvas_plan:
            return canvas_plan

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
        dynamic_schema_only = os.environ.get(
            "NLP2CMD_DYNAMIC_SCHEMA_ONLY", "",
        ).strip().lower() in {"1", "true", "yes", "on"}

        log.info(
            "[ActionPlanner] Flags: new_tab=%s, existing_firefox=%s, "
            "create_key=%s, save_to_env=%s, dynamic_schema_only=%s",
            wants_new_tab, wants_existing_firefox, wants_create, wants_save,
            dynamic_schema_only,
        )

        # ALL API-key workflows need DOM access for proper validation:
        # - check_session needs to inspect page DOM for login indicators
        # - extract_key needs to read key from page elements
        # - clipboard validation needs browser context
        # The desktop path (firefox --new-tab) can only open a URL.
        if wants_existing_firefox:
            log.info(
                "[ActionPlanner] API-key workflow requires DOM access — "
                "switching from Firefox desktop to Playwright browser"
            )
            wants_existing_firefox = False
            wants_new_tab = False  # Playwright opens its own browser

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

        if dynamic_schema_only:
            steps.append(ActionStep(
                action="echo",
                params={"text": (
                    "🧠 Dynamic schema mode: bez twardych template create-flow.\n"
                    "   Używam generycznych kroków + auto-naprawy LLM."
                )},
                description="Log: dynamic schema mode",
            ))

        # --- Step 1: Open browser / navigate ---
        steps.extend(self._build_navigation_steps(
            svc_name, svc, wants_existing_firefox, wants_new_tab,
        ))

        # --- Step 2: Session detection ---
        steps.extend(self._build_session_check_steps(svc_name, svc))

        # --- Step 3: Create key or manual prompt ---
        if wants_create and not dynamic_schema_only:
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
            # --- Step 5: Verify the save ---
            steps.append(ActionStep(
                action="verify_env",
                params={
                    "var_name": svc["env_var"],
                    "file": ".env",
                },
                description=f"Weryfikacja zapisu {svc['env_var']}",
                store_as="verify_status",
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
        """Detect intent to CREATE a new key (not extract/copy existing one)."""
        create_keywords = [
            "stwórz", "stworz", "utwórz", "utworz", "wygeneruj",
            "nowy klucz", "nowy key", "nowy token",
            "create key", "create token", "create new",
            "generate key", "generate token", "generate api",
            "new key", "new token",
        ]
        # Exclude: "wyciągnij", "pobierz", "zapisz", "extract", "get key"
        # — these mean "get existing key", not "create new key"
        return any(p in text for p in create_keywords)

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
                action="discover_service_section",
                params={
                    "service": svc_name,
                    "section": "keys",
                    "base_url": svc.get("base_url", ""),
                    "keys_url": svc.get("keys_url", ""),
                    "hints": svc.get("section_hints", svc.get("session_indicators", [])),
                },
                description=f"Znajdź sekcję kluczy API na {svc_name}",
                store_as="resolved_keys_url",
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
                "key_pattern": svc.get("key_pattern", ""),
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
        """Build steps for key retrieval with automatic extraction + manual fallback.

        Order:
        1. Try automatic DOM extraction (extract_key)
        2. Check clipboard for key (check_clipboard)
        3. Fall back to manual prompt (prompt_secret)
        """
        steps: list[ActionStep] = []

        # Step 1: Try automatic extraction from page DOM
        steps.append(ActionStep(
            action="extract_key",
            params={
                "service": svc_name,
                "key_pattern": svc.get("key_pattern", ""),
                "selectors": svc.get("key_selectors", [
                    "code", "pre", "input[readonly]",
                    ".api-key", "[data-testid*='key']",
                ]),
                "keys_url": svc.get("keys_url", ""),
            },
            description=f"Szukaj klucza API na stronie {svc_name}",
            store_as="extracted_key",
        ))

        # Step 2: Check clipboard (user may have copied key)
        steps.append(ActionStep(
            action="check_clipboard",
            params={
                "key_pattern": svc.get("key_pattern", ""),
                "env_var": svc["env_var"],
            },
            description=f"Sprawdź schowek — klucz {svc_name}",
            store_as="clipboard_key",
        ))

        # Step 3: Manual prompt as last resort
        # (StepValidator pre-check will skip this if key already extracted)
        steps.append(ActionStep(
            action="prompt_secret",
            params={
                "prompt": f"Wklej klucz API dla {svc_name} (nie będzie wyświetlany): ",
                "env_var": svc["env_var"],
                "key_pattern": svc.get("key_pattern", ""),
            },
            description=f"Wprowadź klucz API {svc_name}",
            store_as="api_key",
        ))

        return steps

    def _try_canvas_decomposition(self, query: str) -> Optional[ActionPlan]:
        """Bridge drawing blueprints and templates into ActionPlanner.

        Handles queries like 'wejdź na jspaint.app i narysuj biedronkę'.
        Priority: 
            1) Rich blueprints (SVG paths, polygons, beziers) — hand-crafted, highest quality
            2) Vector DB semantic search (arbitrary objects) — fallback for novel objects
            3) Legacy templates (hardcoded patterns)
            4) LLM fallback (generate via Ollama)
            5) Rule-based generic (last resort)
        """
        text = query.lower()

        # Check if this is a drawing/canvas query
        has_draw = any(
            w in text for w in [
                "narysuj", "rysuj", "namaluj", "maluj", "naszkicuj",
                "draw", "paint", "sketch",
            ]
        )
        if not has_draw:
            return None

        # Extract target URL from query
        url_match = re.search(
            r'\b([a-zA-Z0-9][\w\-]*\.(?:app|com|io))\b', text,
        )
        canvas_url = f"https://{url_match.group(1)}" if url_match else "https://jspaint.app"

        # --- Tier 1: Rich drawing blueprints (SVG paths, polygons, beziers) ---
        try:
            from nlp2cmd.automation.drawing_blueprints import (
                get_blueprint_steps,
                lookup_blueprint,
            )
            bp = lookup_blueprint(text)
            if bp:
                log.info(
                    "[ActionPlanner] Blueprint match: %s", bp["description"],
                )
                draw_steps = bp["steps_fn"]()

                # Build full plan: navigate + canvas setup + drawing steps
                steps: list[ActionStep] = [
                    ActionStep("navigate", {"url": canvas_url}, f"Open {canvas_url}"),
                    ActionStep("wait_for_canvas", {}, "Wait for canvas"),
                    ActionStep("get_canvas_center", {}, "Get canvas center"),
                ]
                for ds in draw_steps:
                    steps.append(ActionStep(
                        action=ds.action,
                        params=dict(ds.params) if ds.params else {},
                        description=ds.description,
                    ))

                return ActionPlan(
                    query=query,
                    steps=steps,
                    confidence=0.95,
                    source="canvas_blueprint",
                    estimated_time_ms=len(steps) * 400,
                )
        except ImportError:
            pass

        # --- Tier 2: Vector database semantic search (novel objects) ---
        vector_plan = self._search_vector_db_for_pattern(query, text, canvas_url)
        if vector_plan:
            # Quality check: vector plan must be detailed enough (minimum 12 drawing steps)
            drawing_steps = [s for s in vector_plan.steps if s.action.startswith('draw_')]
            if len(drawing_steps) >= 8:  # Require at least 8 drawing steps
                log.info("[ActionPlanner] Using vector DB plan with %d drawing steps", len(drawing_steps))
                return vector_plan
            else:
                log.info("[ActionPlanner] Vector DB plan too simple (%d steps), trying LLM", len(drawing_steps))
                # Fall through to LLM generation

        # --- Tier 3: LLM-generated drawing plan ---
        try:
            from nlp2cmd.automation.complex_planner import (
                DRAWING_PATTERNS,
            )
            for template in DRAWING_PATTERNS:
                if re.search(template["pattern"], text):
                    log.info(
                        "[ActionPlanner] Canvas template match: %s",
                        template["description"],
                    )
                    steps = []
                    for cstep in template["steps"]:
                        steps.append(ActionStep(
                            action=cstep.action,
                            params=dict(cstep.params) if cstep.params else {},
                            description=cstep.description,
                        ))
                    return ActionPlan(
                        query=query,
                        steps=steps,
                        confidence=0.92,
                        source="canvas_template",
                        estimated_time_ms=sum(
                            s.wait_after_ms for s in template["steps"]
                        ) + len(steps) * 500,
                    )
        except ImportError:
            pass

        # --- Tier 3: LLM-generated drawing plan ---
        llm_plan = self._generate_canvas_plan_with_llm(query, text)
        if llm_plan:
            return llm_plan
        
        # --- Tier 4: Rule-based generic drawing plan (fallback when LLM unavailable) ---
        return self._generate_rule_based_canvas_plan(query, text, canvas_url)

    def _try_canvas_decomposition_dispatch(self, query: str) -> Optional[ActionPlan]:
        """New canvas decomposition using modular CanvasPlanningOrchestrator.
        
        This is the refactored version that delegates to canvas_planner package.
        Falls back to legacy _try_canvas_decomposition if orchestrator fails.
        """
        if not _CANVAS_PLANNER_AVAILABLE:
            # Fall back to legacy implementation
            return self._try_canvas_decomposition(query)
        
        text = query.lower()
        
        # Check if this is a drawing/canvas query
        has_draw = any(
            w in text for w in [
                "narysuj", "rysuj", "namaluj", "maluj", "naszkicuj",
                "draw", "paint", "sketch",
            ]
        )
        if not has_draw:
            return None
        
        # Use the orchestrator
        orchestrator = CanvasPlanningOrchestrator(
            ollama_url=self.ollama_url,
            model=self.model,
        )
        
        result = orchestrator.plan(query, text)
        if not result:
            # Fall back to legacy implementation
            return self._try_canvas_decomposition(query)
        
        # Convert CanvasPlanResult to ActionPlan
        action_steps = result.to_action_steps()
        if not action_steps:
            # If conversion failed, fall back to legacy
            return self._try_canvas_decomposition(query)
        
        return ActionPlan(
            query=query,
            steps=action_steps,
            confidence=result.confidence,
            source=result.source,
            estimated_time_ms=result.estimated_time_ms,
        )

    def _generate_canvas_plan_with_llm(
        self, query: str, text: str,
    ) -> Optional[ActionPlan]:
        """Generate a drawing plan for an arbitrary object via LLM.

        Extracts the object name from the query and asks the LLM to produce
        a sequence of canvas drawing actions (filled ellipses, circles, lines)
        that approximate the requested shape.
        """
        # Extract object name: "narysuj <object>" / "draw <object>"
        obj_match = re.search(
            r"(?:narysuj|rysuj|namaluj|maluj|naszkicuj|draw|paint|sketch)"
            r"\s+(.+?)(?:\s+na\s+|\s+w\s+|\s*$)",
            text,
        )
        object_name = obj_match.group(1).strip() if obj_match else "obiekt"
        # Remove trailing URL fragments
        object_name = re.sub(r"\s*https?://\S+", "", object_name).strip()
        if not object_name:
            object_name = "obiekt"

        canvas_prompt = (
            f'Wygeneruj SZCZEGÓŁOWY plan rysowania obiektu "{object_name}" na canvas.\n'
            "Obiekt powinien być rozpoznawalny i realistyczny — użyj wielu warstw.\n"
            "\n"
            "DOSTĘPNE AKCJE (JSON array):\n"
            "Kształty wypełnione:\n"
            '- set_color: {{"color": "#RRGGBB"}}\n'
            '- draw_filled_ellipse: {{"rx": N, "ry": N, "offset": [x,y], "rotation": rad}}\n'
            '- draw_filled_circle: {{"radius": N, "offset": [x,y]}}\n'
            '- draw_filled_rectangle: {{"width": N, "height": N, "offset": [x,y]}}\n'
            "Kontury:\n"
            '- draw_line: {{"from_offset": [x,y], "to_offset": [x,y]}}\n'
            '- draw_circle: {{"radius": N, "offset": [x,y]}}\n'
            '- draw_arc: {{"radius": N, "start_angle": rad, "end_angle": rad, "offset": [x,y], "fill": bool}}\n'
            "Zaawansowane:\n"
            '- draw_polygon: {{"points": [[x,y],...], "offset": [x,y], "fill": bool}}\n'
            '- draw_bezier: {{"curves": [{{"type":"M","x":N,"y":N}},{{"type":"Q","cpx":N,"cpy":N,"x":N,"y":N}},{{"type":"C","cp1x":N,"cp1y":N,"cp2x":N,"cp2y":N,"x":N,"y":N}}], "fill": bool, "close": bool}}\n'
            '- draw_svg_path: {{"d": "M0 0 L10 10...", "fill": bool, "scale": N}}\n'
            '- set_line_width: {{"width": N}}\n'
            '- screenshot: {{"suffix": "name"}}\n'
            "\n"
            "ZASADY:\n"
            "- offset [x,y] relatywny do środka canvas (0,0 = środek)\n"
            "- Ujemne y = góra, dodatnie y = dół\n"
            "- Rysuj od tyłu do przodu (tło → ciało → detale → oczy)\n"
            "- Każda część ciała = osobny kształt z set_color\n"
            "- Użyj realistycznych kolorów, proporcji i detali\n"
            "- Minimum 12 kroków dla rozpoznawalnego obiektu\n"
            "- Odpowiedz TYLKO tablicą JSON, BEZ markdown, BEZ komentarzy\n"
            "\n"
            "Przykład (kot — 18 kroków):\n"
            "[\n"
            '  {"action":"set_color","params":{"color":"#808080"}},\n'
            '  {"action":"draw_filled_ellipse","params":{"rx":80,"ry":60,"offset":[0,40]}},\n'
            '  {"action":"draw_filled_circle","params":{"radius":45,"offset":[0,-35]}},\n'
            '  {"action":"draw_polygon","params":{"points":[[-30,-10],[-45,-55],[-10,-30]],"offset":[0,-35],"fill":true}},\n'
            '  {"action":"draw_polygon","params":{"points":[[30,-10],[45,-55],[10,-30]],"offset":[0,-35],"fill":true}},\n'
            '  {"action":"set_color","params":{"color":"#FFB6C1"}},\n'
            '  {"action":"draw_polygon","params":{"points":[[-28,-12],[-40,-48],[-14,-28]],"offset":[0,-35],"fill":true}},\n'
            '  {"action":"draw_polygon","params":{"points":[[28,-12],[40,-48],[14,-28]],"offset":[0,-35],"fill":true}},\n'
            '  {"action":"set_color","params":{"color":"#32CD32"}},\n'
            '  {"action":"draw_filled_ellipse","params":{"rx":10,"ry":8,"offset":[-16,-40]}},\n'
            '  {"action":"draw_filled_ellipse","params":{"rx":10,"ry":8,"offset":[16,-40]}},\n'
            '  {"action":"set_color","params":{"color":"#000000"}},\n'
            '  {"action":"draw_filled_ellipse","params":{"rx":4,"ry":7,"offset":[-16,-40]}},\n'
            '  {"action":"draw_filled_ellipse","params":{"rx":4,"ry":7,"offset":[16,-40]}},\n'
            '  {"action":"set_color","params":{"color":"#FF69B4"}},\n'
            '  {"action":"draw_polygon","params":{"points":[[0,-4],[-5,4],[5,4]],"offset":[0,-25],"fill":true}},\n'
            '  {"action":"set_color","params":{"color":"#000000"}},\n'
            '  {"action":"draw_line","params":{"from_offset":[-15,-22],"to_offset":[-50,-30]}},\n'
            '  {"action":"draw_line","params":{"from_offset":[-15,-20],"to_offset":[-50,-20]}},\n'
            '  {"action":"draw_line","params":{"from_offset":[15,-22],"to_offset":[50,-30]}},\n'
            '  {"action":"draw_line","params":{"from_offset":[15,-20],"to_offset":[50,-20]}},\n'
            '  {"action":"set_line_width","params":{"width":8}},\n'
            '  {"action":"set_color","params":{"color":"#808080"}},\n'
            '  {"action":"draw_bezier","params":{"curves":[{"type":"M","x":75,"y":40},{"type":"C","cp1x":110,"cp1y":20,"cp2x":120,"cp2y":-30,"x":90,"y":-50}],"fill":false,"line_width":8}},\n'
            '  {"action":"screenshot","params":{"suffix":"cat"}}\n'
            "]\n"
        )

        log.info(
            "[ActionPlanner] Canvas LLM plan for object: %s", object_name,
        )

        try:
            import requests
            
            # Configurable timeout with fallback (default 60s for LLM generation)
            timeout = float(os.getenv("CANVAS_LLM_TIMEOUT", "60"))
            max_retries = int(os.getenv("CANVAS_LLM_RETRIES", "2"))
            
            resp = None
            last_error = None
            
            for attempt in range(max_retries + 1):
                try:
                    resp = requests.post(
                        f"{self.ollama_url}/api/generate",
                        json={
                            "model": self.model,
                            "prompt": canvas_prompt,
                            "stream": False,
                            "options": {"temperature": 0.3, "num_predict": 3000},
                        },
                        timeout=timeout,
                    )
                    if resp.status_code == 200:
                        break
                    # If we get a non-200, retry
                    if attempt < max_retries:
                        log.warning("Canvas LLM returned %d, retrying...", resp.status_code)
                        import time
                        time.sleep(1.0 * (attempt + 1))
                except requests.exceptions.Timeout as e:
                    last_error = e
                    if attempt < max_retries:
                        log.warning("Canvas LLM timeout (attempt %d/%d), retrying...", attempt + 1, max_retries + 1)
                        import time
                        time.sleep(1.0 * (attempt + 1))
                    else:
                        raise
                except Exception as e:
                    last_error = e
                    if attempt < max_retries:
                        log.warning("Canvas LLM error (attempt %d/%d): %s", attempt + 1, max_retries + 1, e)
                        import time
                        time.sleep(1.0 * (attempt + 1))
                    else:
                        raise
            
            if resp is None or resp.status_code != 200:
                log.warning("Canvas LLM failed after %d attempts", max_retries + 1)
                return None

            raw = resp.json().get("response", "").strip()
            # Strip markdown fences
            raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
            raw = re.sub(r"\s*```$", "", raw, flags=re.MULTILINE)
            
            # Basic cleanup for common LLM JSON mistakes
            raw = raw.strip()
            # If it didn't strip properly because of newlines
            if raw.startswith("```json"): raw = raw[7:]
            if raw.startswith("```"): raw = raw[3:]
            if raw.endswith("```"): raw = raw[:-3]
            raw = raw.strip()
            
            # Simple heuristic for fixing trailing commas in lists/dicts
            raw = re.sub(r",(\s*[\}\]])", r"\1", raw)

            steps_data = json.loads(raw)
            if not isinstance(steps_data, list) or len(steps_data) < 2:
                log.warning("Canvas LLM returned invalid plan")
                return None

        except Exception as e:
            log.warning("Canvas LLM call failed: %s", e)
            return None

        # Build ActionPlan: navigate + canvas setup + LLM steps
        url_match = re.search(
            r'\b([a-zA-Z0-9][\w\-]*\.(?:app|com|io))\b', text,
        )
        url = f"https://{url_match.group(1)}" if url_match else "https://jspaint.app"

        steps: list[ActionStep] = [
            ActionStep("navigate", {"url": url}, f"Otwórz {url}"),
            ActionStep("wait_for_canvas", {}, "Poczekaj na canvas"),
            ActionStep("get_canvas_center", {}, "Pobierz środek canvas"),
        ]

        for s in steps_data:
            if not isinstance(s, dict):
                continue
            action = s.get("action", "")
            params = s.get("params", {})
            desc = s.get("description", f"{action}")
            if action and isinstance(params, dict):
                steps.append(ActionStep(
                    action=action, params=params, description=desc,
                ))

        # Ensure screenshot at end
        if not any(s.action == "screenshot" for s in steps):
            steps.append(ActionStep(
                "screenshot", {"suffix": object_name.replace(" ", "_")},
                "Zrób screenshot",
            ))

        return ActionPlan(
            query=query,
            steps=steps,
            confidence=0.80,
            source="canvas_llm",
            estimated_time_ms=len(steps) * 600,
        )

    def _generate_rule_based_canvas_plan(self, query: str, text: str, canvas_url: str) -> ActionPlan:
        """Generate a drawing plan for an arbitrary object using rules.
        
        This is a fallback when LLM is not available. Uses object name to determine
        shape composition (ellipses, circles, lines) based on object characteristics.
        """
        # Extract object name
        obj_match = re.search(
            r"(?:narysuj|rysuj|namaluj|maluj|naszkicuj|draw|paint|sketch)"
            r"\s+(.+?)(?:\s+na\s+|\s+w\s+|\s*$)",
            text,
        )
        object_name = obj_match.group(1).strip() if obj_match else "obiekt"
        object_name = re.sub(r"\s*https?://\S+", "", object_name).strip()
        if not object_name:
            object_name = "obiekt"
        
        obj_lower = object_name.lower()
        
        # Define shape composition rules for different object categories
        steps: list[ActionStep] = [
            ActionStep("navigate", {"url": canvas_url}, f"Otwórz {canvas_url}"),
            ActionStep("wait_for_canvas", {}, "Poczekaj na canvas"),
            ActionStep("get_canvas_center", {}, "Pobierz środek canvas"),
        ]
        
        # Object category detection and shape rules
        if any(w in obj_lower for w in ["zając", "zajac", "królik", "krolik", "rabbit", "bunny"]):
            # Rabbit: tall body, long ears, small head
            steps.extend([
                ActionStep("select_tool", {"tool": "ellipse"}, "Wybierz elipsę"),
                ActionStep("set_color", {"color": "#D2B48C"}, "Kolor: beżowy"),
                ActionStep("draw_filled_ellipse", {"rx": 50, "ry": 80, "relative_to": "center"}, "Ciało zająca"),
                ActionStep("set_color", {"color": "#FFE4B5"}, "Kolor: jasny beż"),
                ActionStep("draw_filled_circle", {"radius": 35, "offset": [0, -90]}, "Głowa"),
                ActionStep("set_color", {"color": "#D2B48C"}, "Kolor: beżowy"),
                ActionStep("draw_polygon", {"points": [[-15, 0], [-35, -50], [0, -15]], "offset": [-20, -120], "fill": True}, "Lewe ucho"),
                ActionStep("draw_polygon", {"points": [[15, 0], [35, -50], [0, -15]], "offset": [20, -120], "fill": True}, "Prawe ucho"),
                ActionStep("set_color", {"color": "#000000"}, "Kolor: czarny"),
                ActionStep("draw_circle", {"radius": 5, "offset": [-12, -95]}, "Lewe oko"),
                ActionStep("draw_circle", {"radius": 5, "offset": [12, -95]}, "Prawe oko"),
                ActionStep("draw_circle", {"radius": 3, "offset": [0, -85]}, "Nos"),
                ActionStep("draw_line", {"from_offset": [-15, -105], "to_offset": [15, -105]}, "Wąsy"),
                ActionStep("screenshot", {"suffix": "rabbit"}, "Zrzut ekranu"),
            ])
            
        elif any(w in obj_lower for w in ["samochód", "samochod", "auto", "car", "pojazd", "vehicle"]):
            # Car: rectangle body, circles for wheels
            steps.extend([
                ActionStep("select_tool", {"tool": "ellipse"}, "Wybierz elipsę"),
                ActionStep("set_color", {"color": "#FF0000"}, "Kolor: czerwony"),
                ActionStep("draw_filled_ellipse", {"rx": 90, "ry": 40, "relative_to": "center"}, "Karoseria"),
                ActionStep("set_color", {"color": "#87CEEB"}, "Kolor: niebieski"),
                ActionStep("draw_filled_ellipse", {"rx": 50, "ry": 25, "offset": [20, -30]}, "Szyby"),
                ActionStep("set_color", {"color": "#333333"}, "Kolor: czarny"),
                ActionStep("draw_filled_circle", {"radius": 25, "offset": [-50, 30]}, "Lewe koło"),
                ActionStep("draw_filled_circle", {"radius": 25, "offset": [50, 30]}, "Prawe koło"),
                ActionStep("set_color", {"color": "#888888"}, "Kolor: szary"),
                ActionStep("draw_circle", {"radius": 12, "offset": [-50, 30]}, "Felga lewa"),
                ActionStep("draw_circle", {"radius": 12, "offset": [50, 30]}, "Felga prawa"),
                ActionStep("screenshot", {"suffix": "car"}, "Zrzut ekranu"),
            ])
            
        elif any(w in obj_lower for w in ["dom", "house", "budynek", "building", "chatka", "cottage"]):
            # House: rectangle body, triangle roof
            steps.extend([
                ActionStep("select_tool", {"tool": "ellipse"}, "Wybierz elipsę"),
                ActionStep("set_color", {"color": "#F4A460"}, "Kolor: brązowy"),
                ActionStep("draw_filled_ellipse", {"rx": 70, "ry": 60, "relative_to": "center"}, "Ściany domu"),
                ActionStep("set_color", {"color": "#8B4513"}, "Kolor: ciemny brąz"),
                ActionStep("draw_polygon", {"points": [[-70, -60], [0, -120], [70, -60]], "offset": [0, 0], "fill": True}, "Dach trójkątny"),
                ActionStep("set_color", {"color": "#8B4513"}, "Kolor: ciemny brąz"),
                ActionStep("draw_filled_ellipse", {"rx": 20, "ry": 30, "offset": [0, 15]}, "Drzwi"),
                ActionStep("set_color", {"color": "#87CEEB"}, "Kolor: niebieski"),
                ActionStep("draw_filled_circle", {"radius": 15, "offset": [-35, -30]}, "Okno lewe"),
                ActionStep("draw_filled_circle", {"radius": 15, "offset": [35, -30]}, "Okno prawe"),
                ActionStep("screenshot", {"suffix": "house"}, "Zrzut ekranu"),
            ])
            
        elif any(w in obj_lower for w in ["słońce", "slonce", "sun", "gwiazda", "star"]):
            # Sun: circle center with radiating lines
            steps.extend([
                ActionStep("select_tool", {"tool": "ellipse"}, "Wybierz elipsę"),
                ActionStep("set_color", {"color": "#FFD700"}, "Kolor: złoty"),
                ActionStep("draw_filled_circle", {"radius": 60, "offset": [0, 0], "relative_to": "center"}, "Słońce"),
                ActionStep("set_color", {"color": "#FFA500"}, "Kolor: pomarańczowy"),
                # Sun rays
                ActionStep("draw_line", {"from_offset": [0, -70], "to_offset": [0, -100]}, "Promień górny"),
                ActionStep("draw_line", {"from_offset": [50, -50], "to_offset": [70, -70]}, "Promień górny-prawy"),
                ActionStep("draw_line", {"from_offset": [70, 0], "to_offset": [100, 0]}, "Promień prawy"),
                ActionStep("draw_line", {"from_offset": [50, 50], "to_offset": [70, 70]}, "Promień dolny-prawy"),
                ActionStep("draw_line", {"from_offset": [0, 70], "to_offset": [0, 100]}, "Promień dolny"),
                ActionStep("draw_line", {"from_offset": [-50, 50], "to_offset": [-70, 70]}, "Promień dolny-lewy"),
                ActionStep("draw_line", {"from_offset": [-70, 0], "to_offset": [-100, 0]}, "Promień lewy"),
                ActionStep("draw_line", {"from_offset": [-50, -50], "to_offset": [-70, -70]}, "Promień górny-lewy"),
                ActionStep("screenshot", {"suffix": "sun"}, "Zrzut ekranu"),
            ])
            
        elif any(w in obj_lower for w in ["drzewo", "tree", "las", "forest", "sosna", "pine"]):
            # Tree: brown rectangle trunk, green triangle/ellipse for foliage
            steps.extend([
                ActionStep("select_tool", {"tool": "ellipse"}, "Wybierz elipsę"),
                ActionStep("set_color", {"color": "#8B4513"}, "Kolor: brązowy"),
                ActionStep("draw_filled_ellipse", {"rx": 20, "ry": 50, "offset": [0, 40]}, "Pień"),
                ActionStep("set_color", {"color": "#228B22"}, "Kolor: zielony"),
                ActionStep("draw_filled_ellipse", {"rx": 70, "ry": 60, "offset": [0, -40]}, "Korona dolna"),
                ActionStep("draw_filled_ellipse", {"rx": 50, "ry": 50, "offset": [0, -80]}, "Korona górna"),
                ActionStep("screenshot", {"suffix": "tree"}, "Zrzut ekranu"),
            ])
            
        else:
            # Generic object: simple ellipse/circle composition
            # Use object name length to determine size
            size_factor = min(40 + len(object_name) * 5, 100)
            steps.extend([
                ActionStep("select_tool", {"tool": "ellipse"}, "Wybierz elipsę"),
                ActionStep("set_color", {"color": "#4169E1"}, "Kolor: niebieski"),
                ActionStep("draw_filled_ellipse", {"rx": size_factor, "ry": size_factor * 0.8, "relative_to": "center"}, f"Ciało: {object_name}"),
                ActionStep("set_color", {"color": "#FFD700"}, "Kolor: złoty"),
                ActionStep("draw_filled_circle", {"radius": size_factor * 0.4, "offset": [0, -size_factor * 0.9]}, "Głowa"),
                ActionStep("set_color", {"color": "#000000"}, "Kolor: czarny"),
                ActionStep("draw_circle", {"radius": 5, "offset": [-size_factor*0.15, -size_factor*0.9]}, "Oko lewe"),
                ActionStep("draw_circle", {"radius": 5, "offset": [size_factor*0.15, -size_factor*0.9]}, "Oko prawe"),
                ActionStep("screenshot", {"suffix": object_name.replace(" ", "_")}, "Zrzut ekranu"),
            ])
        
        return ActionPlan(
            query=query,
            steps=steps,
            confidence=0.75,
            source="canvas_rule_based",
            estimated_time_ms=len(steps) * 400,
        )

    
    def _search_vector_db_for_pattern(self, query: str, text: str, canvas_url: str) -> Optional[ActionPlan]:
        """Search vector database for semantically similar drawing patterns.
        
        Tier 0: Semantic search through vector database of drawing patterns.
        Falls back to subsequent tiers if no match found.
        """
        if not _VECTOR_STORE_AVAILABLE:
            log.debug("Vector store not available, skipping semantic search")
            return None
            
        try:
            store = get_vector_store()
            if not store.is_available():
                log.debug("Vector store client not initialized")
                return None
            
            # Extract object description from query
            obj_match = re.search(
                r"(?:narysuj|rysuj|namaluj|maluj|naszkicuj|draw|paint|sketch)\s+(.+?)(?:\s+na\s+|\s+w\s+|\s*\$)",
                text,
            )
            search_query = obj_match.group(1).strip() if obj_match else text
            search_query = re.sub(r"\s*https?://\S+", "", search_query).strip()
            
            # Search vector database
            log.info("[ActionPlanner] Searching vector DB for: %s", search_query)
            
            best_pattern = None
            confidence = 0.0
            
            # 1. First try exact/fuzzy match on tags (helps with non-English queries)
            query_lower = search_query.lower()
            # Simple stemming: lisa -> lis
            if query_lower.endswith("a") or query_lower.endswith("ek") or query_lower.endswith("kiem") or query_lower.endswith("ka"):
                base_query = re.sub(r'(a|ek|kiem|ka)$', '', query_lower)
            else:
                base_query = query_lower
                
            all_patterns = store.list_patterns()
            for p_name in all_patterns:
                p = store.get_pattern(p_name)
                if p:
                    # Check tags and name
                    if base_query in p.tags or query_lower in p.tags or base_query == p.name:
                        best_pattern = p
                        confidence = 0.95
                        log.info("[ActionPlanner] Vector DB exact tag match: %s", p.name)
                        break
            
            # 2. Fallback to semantic search
            if not best_pattern:
                results = store.search(search_query, n_results=3, min_confidence=0.0)
                if results:
                    best_pattern, confidence = results[0]
                    log.info("[ActionPlanner] Vector DB semantic match: %s (confidence: %.2f)", 
                             best_pattern.name, confidence)
            
            if not best_pattern:
                log.debug("No matching patterns in vector DB")
                return None
            
            # Build ActionPlan from pattern steps
            steps: list[ActionStep] = [
                ActionStep("navigate", {"url": canvas_url}, f"Open {canvas_url}"),
                ActionStep("wait_for_canvas", {}, "Wait for canvas"),
                ActionStep("get_canvas_center", {}, "Get canvas center"),
            ]
            
            for step_data in best_pattern.steps:
                action = step_data.get("action", "")
                params = step_data.get("params", {})
                desc = step_data.get("description", action)
                if action:
                    steps.append(ActionStep(action=action, params=params, description=desc))
            
            return ActionPlan(
                query=query,
                steps=steps,
                confidence=confidence,
                source="vector_db",
                estimated_time_ms=len(steps) * 400,
            )
            
        except Exception as e:
            log.warning("Vector DB search failed: %s", e)
            return None

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
