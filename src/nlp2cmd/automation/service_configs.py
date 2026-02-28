"""
Service configuration data for ActionPlanner.

Extracted from action_planner.py for better maintainability.
Contains known API service definitions, email client configs, and NL aliases.
"""

from __future__ import annotations

import logging
import os
import shutil
from typing import Any

log = logging.getLogger("nlp2cmd.action_planner")


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
            # GitHub has a dropdown: "Generate new token" → choose "classic"
            "pre_clicks": [
                {"text": "Generate new token", "description": "Otwórz dropdown 'Generate new token'"},
            ],
            "button_selector": "a:has-text('Generate new token (classic)')",
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
        "key_selectors": [
            "input[readonly]",
            "input[type='text'][readonly]",
            ".token-value",
            "[data-testid*='token']",
            "code",
            "pre",
        ],
        "session_indicators": ["Access Tokens", "New token", "User Access Tokens"],
        "login_indicators": ["Sign In", "Log In"],
        "create_key": {
            "button_selector": "button:has-text('Create new token')",
            "form_fields": {
                # Step 1: Select token type (radio button) - default to "Read"
                "token_type": {
                    "selector": "input[type='radio'][value='read']",
                    "action": "click_radio",  # Special action for radio selection
                    "default": "read",
                },
                # Step 2: Token name field
                "name": {
                    "selector": "input[name='displayName']",
                    "alt_selectors": [
                        "input[placeholder*='Token name' i]",
                        "input[placeholder*='name' i]",
                        "input[type='text']:visible",
                    ],
                    "default": "nlp2cmd",
                },
            },
            "submit_selector": "button[type='submit']:has-text('Create token')",
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
