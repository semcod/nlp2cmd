from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Optional

from nlp2cmd.adapters.base import AdapterConfig, BaseDSLAdapter, SafetyPolicy
from nlp2cmd.ir import ActionIR
from nlp2cmd.web_schema.form_data_loader import FormDataLoader


@dataclass
class BrowserSafetyPolicy(SafetyPolicy):
    enabled: bool = True


class BrowserAdapter(BaseDSLAdapter):
    """Minimal adapter that turns NL into dom_dql.v1 navigation (Playwright)."""

    DSL_NAME = "browser"
    DSL_VERSION = "1.0"

    INTENTS = {
        "browse": {
            "patterns": [
                "otwórz przeglądark",
                "otworz przegladark",
                "open browser",
                "wejdź na",
                "wejdz na",
                "go to",
                "navigate to",
                "open",
            ],
            "required_entities": [],
            "optional_entities": ["url"],
        }
    }

    def __init__(
        self,
        config: Optional[AdapterConfig] = None,
        safety_policy: Optional[SafetyPolicy] = None,
    ):
        super().__init__(config, safety_policy or BrowserSafetyPolicy())
        self.last_action_ir: Optional[ActionIR] = None

    @staticmethod
    def _extract_url(text: str) -> Optional[str]:
        t = (text or "").strip()
        if not t:
            return None

        # Prefer explicit scheme.
        m = re.search(r"(https?://\S+)", t, flags=re.IGNORECASE)
        if m:
            return m.group(1).rstrip(".,)")

        # Domain-like tokens (google.com, example.org/path)
        m = re.search(
            r"\b([a-z0-9][a-z0-9-]*(?:\.[a-z0-9][a-z0-9-]*)+)(/\S*)?\b",
            t,
            flags=re.IGNORECASE,
        )
        if m:
            host = m.group(1)
            path = m.group(2) or ""
            return f"https://{host}{path}"

        return None
    
    @staticmethod
    def _extract_type_text(text: str) -> Optional[str]:
        """Extract text to type from patterns like 'wpisz w pole: nlp2cmd' or 'type: hello'."""
        patterns = FormDataLoader().get_type_text_patterns()

        for pattern in patterns:
            m = re.search(pattern, text, flags=re.IGNORECASE)
            if m:
                extracted = m.group(1).strip()
                # Clean up common trailing phrases
                extracted = re.sub(r',?\s*(?:oraz|and|i)\s+(?:naciśnij|nacisnij|press|hit)\s+(?:enter|return).*$', '', extracted, flags=re.IGNORECASE)
                extracted = extracted.rstrip(',').strip()
                return extracted if extracted else None
        
        return None
    
    @staticmethod
    def _has_type_action(text: str) -> bool:
        """Check if text contains typing action."""
        type_keywords = FormDataLoader().get_nlp_keywords("typing")
        tl = text.lower()
        return any(kw in tl for kw in type_keywords)
    
    @staticmethod
    def _has_fill_form_action(text: str) -> bool:
        t = (text or "").lower()
        phrases = FormDataLoader().get_nlp_keywords("fill_form_phrases")
        return any(p in t for p in phrases)

    @staticmethod
    def _has_press_enter(text: str) -> bool:
        t = (text or "").lower()
        keywords = FormDataLoader().get_nlp_keywords("press_enter")
        return any(k in t for k in keywords)
    
    @staticmethod
    def _has_form_action(text: str) -> bool:
        """Check if text contains form filling action."""
        form_keywords = FormDataLoader().get_nlp_keywords("form")
        tl = text.lower()
        return any(kw in tl for kw in form_keywords)
    
    @staticmethod
    def _has_submit_action(text: str) -> bool:
        """Check if text contains form submission intent."""
        submit_keywords = FormDataLoader().get_nlp_keywords("submit")
        tl = text.lower()
        return any(kw in tl for kw in submit_keywords)
    
    @staticmethod
    def _has_extract_article_action(text: str) -> bool:
        """Check if text contains article extraction intent."""
        extract_keywords = FormDataLoader().get_nlp_keywords("extract_article")
        tl = text.lower()
        return any(kw in tl for kw in extract_keywords)
    
    def generate(self, plan: dict[str, Any]) -> str:
        text = str(plan.get("text") or plan.get("query") or "")
        entities = plan.get("entities") if isinstance(plan.get("entities"), dict) else {}

        url = None
        if isinstance(entities, dict):
            u = entities.get("url") or entities.get("target")
            if isinstance(u, str) and u.strip():
                url = u.strip()

        url = url or self._extract_url(text)
        if not url:
            self.last_action_ir = None
            return "# Could not generate command"

        actions: list[dict[str, Any]] = [{"action": "goto", "url": url}]
        params: dict[str, Any] = {"url": url}
        action_id = "dom.goto"
        explanation = "browser adapter: goto"

        if self._has_fill_form_action(text):
            actions.append({"action": "fill_form"})
            action_id = "dom.goto_and_fill_form"
            explanation = f"browser adapter: goto {url} and fill form"

        type_text = self._extract_type_text(text)
        if type_text and self._has_type_action(text):
            actions.append({"action": "type", "selector": "__auto__", "text": type_text})
            params["type_text"] = type_text
            if action_id == "dom.goto":
                action_id = "dom.goto_and_type"
                explanation = f"browser adapter: goto {url} and type '{type_text}'"
            else:
                action_id = f"{action_id}_and_type"
                explanation = f"{explanation} and type '{type_text}'"

        if self._has_press_enter(text):
            actions.append({"action": "press", "key": "Enter"})
            params["press_key"] = "Enter"
            action_id = f"{action_id}_and_press_enter"
            explanation = f"{explanation} and press Enter"
        
        if self._has_submit_action(text):
            actions.append({"action": "submit"})
            params["submit"] = True
            action_id = f"{action_id}_and_submit"
            explanation = f"{explanation} and submit"
        
        if self._has_extract_article_action(text):
            actions.append({"action": "extract_article"})
            params["extract_article"] = True
            action_id = f"{action_id}_and_extract_article"
            explanation = f"{explanation} and extract article"

        if len(actions) == 1:
            payload = {
                "dsl": "dom_dql.v1",
                "action": "goto",
                "url": url,
                "params": {},
            }
        else:
            payload = {
                "dsl": "dom_dql.v1",
                "actions": actions,
                "url": url,
            }

        self.last_action_ir = ActionIR(
            action_id=action_id,
            dsl=json.dumps(payload, ensure_ascii=False),
            dsl_kind="dom",  # type: ignore[arg-type]
            params=params,
            output_format="raw",  # type: ignore[arg-type]
            confidence=float(plan.get("confidence") or 0.8),
            explanation=explanation,
            metadata=params,
        )

        return self.last_action_ir.dsl

    def validate_syntax(self, command: str) -> dict[str, Any]:
        try:
            payload = json.loads(command)
        except Exception as e:
            return {"valid": False, "errors": [f"Invalid JSON: {e}"]}

        if not isinstance(payload, dict) or payload.get("dsl") != "dom_dql.v1":
            return {"valid": False, "errors": ["Not dom_dql.v1"]}

        if not isinstance(payload.get("url"), str) or not payload.get("url"):
            return {"valid": False, "errors": ["Missing url"]}

        actions = payload.get("actions")
        if isinstance(actions, list):
            errors: list[str] = []
            if not actions:
                errors.append("Empty actions")
            for i, a in enumerate(actions):
                if not isinstance(a, dict):
                    errors.append(f"Action {i}: not an object")
                    continue
                act = str(a.get("action") or "")
                if act in {"goto", "navigate"}:
                    continue
                if act in {"fill_form", "submit", "extract_article"}:
                    continue
                if act in {"type", "click", "press", "select"}:
                    if act in {"type", "click", "select"} and not str(a.get("selector") or ""):
                        errors.append(f"Action {i}: missing selector")
                    if act == "type" and not str(a.get("text") or ""):
                        errors.append(f"Action {i}: missing text")
                    if act == "press" and not str(a.get("key") or ""):
                        errors.append(f"Action {i}: missing key")
                    continue
                errors.append(f"Action {i}: unsupported action: {act}")

            if errors:
                return {"valid": False, "errors": errors}

            return {"valid": True, "errors": []}

        if str(payload.get("action") or "") not in {"goto", "navigate"}:
            return {"valid": False, "errors": ["Unsupported action"]}

        return {"valid": True, "errors": []}
