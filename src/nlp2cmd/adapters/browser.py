from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass
from typing import Any, Optional

from nlp2cmd.adapters.base import AdapterConfig, BaseDSLAdapter, SafetyPolicy
from nlp2cmd.ir import ActionIR
from nlp2cmd.web_schema.form_data_loader import FormDataLoader
from nlp2cmd.web_schema.site_explorer import SiteExplorer

_DEBUG = os.environ.get("NLP2CMD_DEBUG", "").lower() in ("1", "true", "yes")


def _debug(msg: str) -> None:
    """Print debug message to stderr when NLP2CMD_DEBUG=1."""
    if _DEBUG:
        print(f"DEBUG [BrowserAdapter] {msg}", file=sys.stderr, flush=True)


@dataclass
class BrowserSafetyPolicy(SafetyPolicy):
    enabled: bool = True


class BrowserAdapter(BaseDSLAdapter):
    """Minimal adapter that turns NL into dom_dql.v1 navigation (Playwright)."""

    DSL_NAME = "browser"
    DSL_VERSION = "1.0"
    
    # Class-level singleton for FormDataLoader to avoid repeated file I/O
    _form_data_loader = None

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

    @classmethod
    def get_form_data_loader(cls):
        """Get or create the FormDataLoader singleton."""
        if cls._form_data_loader is None:
            cls._form_data_loader = FormDataLoader()
        return cls._form_data_loader
    
    def __init__(
        self,
        config: Optional[AdapterConfig] = None,
        safety_policy: Optional[SafetyPolicy] = None,
    ):
        super().__init__(config, safety_policy or BrowserSafetyPolicy())
        self.last_action_ir: Optional[ActionIR] = None
        self._site_explorer = None
        self._form_data_loader = None
        
    @property
    def site_explorer(self):
        """Lazy load SiteExplorer to avoid browser startup during tests."""
        if self._site_explorer is None:
            self._site_explorer = SiteExplorer(max_depth=2, max_pages=8, headless=True)
        return self._site_explorer
        
    @site_explorer.setter
    def site_explorer(self, value):
        """Allow setting site_explorer for testing."""
        self._site_explorer = value
        
    @property
    def form_data_loader(self):
        """Lazy load FormDataLoader to avoid file I/O during tests."""
        if self._form_data_loader is None:
            self._form_data_loader = FormDataLoader()
        return self._form_data_loader
        
    @form_data_loader.setter
    def form_data_loader(self, value):
        """Allow setting form_data_loader for testing."""
        self._form_data_loader = value

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
    
    def _extract_type_text(self, text: str) -> Optional[str]:
        """Extract text to type from patterns like 'wpisz w pole: nlp2cmd' or 'type: hello'."""
        patterns = self.form_data_loader.get_type_text_patterns()

        for pattern in patterns:
            m = re.search(pattern, text, flags=re.IGNORECASE)
            if m:
                extracted = m.group(1).strip()
                # Clean up common trailing phrases
                extracted = re.sub(r',?\s*(?:oraz|and|i)\s+(?:naciśnij|nacisnij|press|hit)\s+(?:enter|return).*$', '', extracted, flags=re.IGNORECASE)
                extracted = extracted.rstrip(',').strip()
                return extracted if extracted else None
        
        return None
    
    @classmethod
    def _has_type_action(cls, text: str) -> bool:
        """Check if text contains typing action."""
        type_keywords = cls.get_form_data_loader().get_nlp_keywords("typing")
        tl = text.lower()
        return any(kw in tl for kw in type_keywords)
    
    @staticmethod
    def _should_explore_for_content(text: str) -> tuple[bool, str]:
        """Check if we should explore the site for content and what type."""
        content_patterns = {
            "article": [
                "znajdź artykuł", "znajdz artykul", "find article", "szukaj artykułu",
                "przeszukaj artykuły", "znajdź post", "znajdz post", "blog", "news"
            ],
            "product": [
                "znajdź produkt", "znajdz produkt", "find product", "szukaj produktu",
                "przeszukaj ofertę", "katalog", "sklep", "cena", "buy"
            ],
            "docs": [
                "znajdź dokumentację", "znajdz dokumentacje", "find documentation",
                "szukaj pomocy", "przeszukaj manual", "faq", "guide", "tutorial",
                "readme", "wiki", "api docs", "documentation"
            ]
        }
        
        text_lower = text.lower()
        for content_type, patterns in content_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                return True, content_type
        return False, "unknown"
    
    @staticmethod
    def _should_explore_for_forms(text: str) -> bool:
        """Check if we should explore the site for forms instead of just checking current page."""
        explore_keywords = [
            "znajdź formularz", "znajdz formularz", "find form",
            "szukaj formularza", "szukaj kontaktu", "search contact",
            "przeszukaj stronę", "przeszukaj strone", "explore site",
            "odnajdź formularz", "odnajdz formularz", "locate form",
            "znajdź stronę kontaktu", "znajdz strone kontaktu", "szukaj kontaktu",
            "znajdź kontakt", "znajdz kontakt"
        ]
        text_lower = text.lower()
        
        # Also return True if we're asked to fill a form but no specific path is given in URL
        # handled in generate() logic too
        return any(kw in text_lower for kw in explore_keywords)
    
    @classmethod
    def _has_fill_form_action(cls, text: str) -> bool:
        t = (text or "").lower()
        phrases = cls.get_form_data_loader().get_nlp_keywords("fill_form_phrases")
        return any(p in t for p in phrases)

    @classmethod
    def _has_press_enter(cls, text: str) -> bool:
        t = (text or "").lower()
        keywords = cls.get_form_data_loader().get_nlp_keywords("press_enter")
        return any(k in t for k in keywords)
    
    @classmethod
    def _has_form_action(cls, text: str) -> bool:
        """Check if text contains form filling action."""
        form_keywords = cls.get_form_data_loader().get_nlp_keywords("form")
        tl = text.lower()
        return any(kw in tl for kw in form_keywords)
    
    @classmethod
    def _has_submit_action(cls, text: str) -> bool:
        """Check if text contains form submission intent."""
        submit_keywords = cls.get_form_data_loader().get_nlp_keywords("submit")
        tl = text.lower()
        return any(kw in tl for kw in submit_keywords)
    
    @classmethod
    def _has_extract_article_action(cls, text: str) -> bool:
        """Check if text contains article extraction intent."""
        extract_keywords = cls.get_form_data_loader().get_nlp_keywords("extract_article")
        plural_keywords = cls.get_form_data_loader().get_nlp_keywords("extract_articles_plural")
        tl = text.lower()
        return any(kw in tl for kw in extract_keywords) or any(kw in tl for kw in plural_keywords)
    
    @classmethod
    def _is_plural_article_request(cls, text: str) -> bool:
        """Check if request is for multiple articles (plural form)."""
        plural_keywords = cls.get_form_data_loader().get_nlp_keywords("extract_articles_plural")
        tl = text.lower()
        return any(kw in tl for kw in plural_keywords)
    
    @classmethod
    def _extract_article_topic(cls, text: str) -> Optional[str]:
        """Extract topic/subject from article request (e.g., 'artykuł o polityce' -> 'polityce')."""
        patterns = cls.get_form_data_loader().get_article_topic_patterns()
        for pattern in patterns:
            m = re.search(pattern, text, flags=re.IGNORECASE)
            if m:
                topic = m.group(1).strip()
                # Clean up trailing punctuation
                topic = re.sub(r'[,;.!?]+$', '', topic).strip()
                return topic if topic else None
        return None

    @classmethod
    def _has_extract_companies_action(cls, text: str) -> bool:
        """Check if text contains company extraction intent."""
        keywords = cls.get_form_data_loader().get_nlp_keywords("extract_companies")
        tl = text.lower()
        matched = [kw for kw in keywords if kw in tl]
        if matched:
            _debug(f"_has_extract_companies_action: matched keywords {matched}")
        return bool(matched)

    @classmethod
    def _has_save_to_file_action(cls, text: str) -> bool:
        """Check if text contains save-to-file intent."""
        keywords = cls.get_form_data_loader().get_nlp_keywords("save_to_file")
        tl = text.lower()
        matched = [kw for kw in keywords if kw in tl]
        if matched:
            _debug(f"_has_save_to_file_action: matched keywords {matched}")
        return bool(matched)

    @classmethod
    def _extract_save_filename(cls, text: str) -> Optional[str]:
        """Extract output filename from NL (e.g. 'zapisz do pliku firmy.txt' -> 'firmy.txt')."""
        patterns = cls.get_form_data_loader().get_save_filename_patterns()
        for pattern in patterns:
            m = re.search(pattern, text, flags=re.IGNORECASE)
            if m:
                fname = m.group(1).strip()
                _debug(f"_extract_save_filename: extracted '{fname}' via pattern")
                return fname if fname else None
        # Fallback: look for quoted filename anywhere
        m = re.search(r"['\"]([\\w._-]+\\.\\w{1,5})['\"]", text)
        if m:
            fname = m.group(1).strip()
            _debug(f"_extract_save_filename: extracted '{fname}' via quoted fallback")
            return fname
        return None

    @staticmethod
    def _has_deep_website_extraction(text: str) -> bool:
        """Check if text requests deep extraction of company websites."""
        deep_keywords = [
            "strona www", "strony www", "strona firmy", "strony firm",
            "witryna", "witryny", "website firmy", "websites firm",
            "adres www", "adresy www", "adres strony", "adresy stron",
            "www firmy", "www firm", "strona internetowa", "strony internetowe",
            "company website", "company websites", "firm website", "business website",
            "wejdź na profil", "wejdz na profil", "wejdź w profil", "wejdz w profil",
            "otwórz profil", "otworz profil",
            "pobierz strony www", "pobierz www", "extract websites", "pobierz adresy"
        ]
        tl = text.lower()
        matched = [kw for kw in deep_keywords if kw in tl]
        if matched:
            _debug(f"_has_deep_website_extraction: matched {matched}")
        return bool(matched)

    @staticmethod
    def _has_csv_format(text: str) -> bool:
        """Check if text requests CSV format."""
        csv_indicators = [".csv", "csv", "format csv", "do csv", "w csv"]
        tl = text.lower()
        return any(ind in tl for ind in csv_indicators)

    @staticmethod
    def _wants_clipboard(text: str) -> bool:
        tl = (text or "").lower()
        return any(
            k in tl
            for k in [
                "schowek",
                "clipboard",
                "skopiuj",
                "kopiuj",
                "do schowka",
                "to clipboard",
                "copy to clipboard",
            ]
        )

    @staticmethod
    def _wants_print_terminal(text: str) -> bool:
        tl = (text or "").lower()
        return any(
            k in tl
            for k in [
                "wypisz",
                "wydrukuj",
                "print",
                "pokaż",
                "pokaz",
                "w terminalu",
                "na terminal",
                "to terminal",
                "print to terminal",
                "stdout",
            ]
        )

    def generate(self, plan: dict[str, Any]) -> str:
        text = str(plan.get("text") or plan.get("query") or "")
        entities = plan.get("entities") if isinstance(plan.get("entities"), dict) else {}

        _debug(f"generate() text='{text[:120]}...'")

        url = None
        if isinstance(entities, dict):
            u = entities.get("url") or entities.get("target")
            if isinstance(u, str) and u.strip():
                url = u.strip()

        url = url or self._extract_url(text)
        if not url:
            _debug("generate(): no URL found, aborting")
            self.last_action_ir = None
            return "# Could not generate command"

        _debug(f"generate(): URL={url}")

        actions: list[dict[str, Any]] = [{"action": "goto", "url": url}]
        params: dict[str, Any] = {"url": url}
        action_id = "dom.goto"
        explanation = "browser adapter: goto"

        # --- Detect all intents upfront for debug visibility ---
        has_fill = self._has_fill_form_action(text)
        has_explore_forms = self._should_explore_for_forms(text)
        should_explore_content, explore_content_type = self._should_explore_for_content(text)
        has_type = self._has_type_action(text)
        has_enter = self._has_press_enter(text)
        has_submit = self._has_submit_action(text)
        has_extract_article = self._has_extract_article_action(text)
        has_extract_companies = self._has_extract_companies_action(text)
        has_deep_extraction = self._has_deep_website_extraction(text)
        has_save_keyword = self._has_save_to_file_action(text)
        has_csv = self._has_csv_format(text)
        save_filename = self._extract_save_filename(text)
        # Trigger save if keyword found OR filename explicitly mentioned
        has_save = has_save_keyword or bool(save_filename)

        _debug(
            f"generate(): intents: fill_form={has_fill}, explore_forms={has_explore_forms}, "
            f"explore_content={should_explore_content}({explore_content_type}), type={has_type}, "
            f"enter={has_enter}, submit={has_submit}, extract_article={has_extract_article}, "
            f"extract_companies={has_extract_companies}, deep_extraction={has_deep_extraction}, "
            f"save={has_save}, csv={has_csv}, filename={save_filename}"
        )

        if has_fill:
            is_root = False
            try:
                parsed = urlparse(url)
                is_root = parsed.path in ("", "/")
            except Exception:
                pass

            if has_explore_forms or is_root:
                actions.append({"action": "explore_for_form", "intent": "contact"})
                actions.append({"action": "fill_form"})
                action_id = "dom.explore_and_fill_form"
                explanation = f"browser adapter: explore {url} for contact form and fill"
                _debug("generate(): chose explore_and_fill_form path")
            else:
                actions.append({"action": "fill_form"})
                action_id = "dom.goto_and_fill_form"
                explanation = f"browser adapter: goto {url} and fill form"
                _debug("generate(): chose goto_and_fill_form path")
        elif has_explore_forms:
            actions.append({"action": "explore_for_form", "intent": "contact"})
            action_id = "dom.explore_for_form"
            explanation = f"browser adapter: explore {url} for contact form"
            _debug("generate(): chose explore_for_form path")

        # Check for content exploration (but don't duplicate with form exploration)
        if should_explore_content and not has_fill and not has_extract_companies:
            actions.append({"action": "explore_for_content", "content_type": explore_content_type})
            action_id = f"dom.explore_for_{explore_content_type}"
            explanation = f"browser adapter: explore {url} for {explore_content_type}"
            _debug(f"generate(): chose explore_for_content({explore_content_type}) path")

        # --- Company extraction (deep or shallow) ---
        if has_deep_extraction:
            # Deep extraction: navigate to each profile and get external website
            actions.append({"action": "extract_company_websites_deep", "max_companies": 20})
            params["deep_extraction"] = True
            action_id = f"{action_id}_and_extract_company_websites_deep"
            explanation = f"{explanation} and extract company websites from profiles"
            _debug("generate(): added extract_company_websites_deep action")
        elif has_extract_companies:
            actions.append({"action": "extract_companies"})
            params["extract_companies"] = True
            action_id = f"{action_id}_and_extract_companies"
            explanation = f"{explanation} and extract companies"
            _debug("generate(): added extract_companies action")

        type_text = self._extract_type_text(text)
        if type_text and has_type:
            actions.append({"action": "type", "selector": "__auto__", "text": type_text})
            params["type_text"] = type_text
            if action_id == "dom.goto":
                action_id = "dom.goto_and_type"
                explanation = f"browser adapter: goto {url} and type '{type_text}'"
            else:
                action_id = f"{action_id}_and_type"
                explanation = f"{explanation} and type '{type_text}'"

        if has_enter:
            actions.append({"action": "press", "key": "Enter"})
            params["press_key"] = "Enter"
            action_id = f"{action_id}_and_press_enter"
            explanation = f"{explanation} and press Enter"

        if has_submit:
            actions.append({"action": "submit"})
            params["submit"] = True
            action_id = f"{action_id}_and_submit"
            explanation = f"{explanation} and submit"

        if has_extract_article:
            is_plural = self._is_plural_article_request(text)
            topic = self._extract_article_topic(text)

            extract_action: dict[str, Any] = {"action": "extract_article"}
            if is_plural:
                extract_action["mode"] = "list"
                params["extract_mode"] = "list"
            if topic:
                extract_action["topic"] = topic
                params["article_topic"] = topic

            actions.append(extract_action)
            params["extract_article"] = True

            if is_plural:
                action_id = f"{action_id}_and_list_articles"
                explanation = f"{explanation} and list articles"
            else:
                action_id = f"{action_id}_and_extract_article"
                explanation = f"{explanation} and extract article"

            if topic:
                explanation = f"{explanation} about '{topic}'"

        # --- Save to file (CSV or text) ---
        if has_save:
            wants_clipboard = self._wants_clipboard(text)
            wants_print = self._wants_print_terminal(text)
            if has_csv:
                save_action: dict[str, Any] = {"action": "save_to_csv"}
                default_ext = ".csv"
            else:
                save_action = {"action": "save_to_file"}
                default_ext = ".txt"
            
            if save_filename:
                save_action["filename"] = save_filename
                params["save_filename"] = save_filename
            else:
                # Generate default filename from URL domain
                try:
                    from urllib.parse import urlparse as _urlparse
                    domain = _urlparse(url).netloc.replace(".", "_")
                    default_name = f"{domain}_data{default_ext}"
                except Exception:
                    default_name = f"extracted_data{default_ext}"
                save_action["filename"] = default_name
                params["save_filename"] = default_name

            if wants_clipboard:
                save_action["also_copy"] = True
            if wants_print:
                save_action["also_print"] = True
            actions.append(save_action)
            action_id = f"{action_id}_and_save"
            explanation = f"{explanation} and save to '{params.get('save_filename', 'file')}'"
            _debug(f"generate(): added {save_action['action']} action, filename={params.get('save_filename')}")

        _debug(f"generate(): final actions={[a.get('action') for a in actions]}, action_id={action_id}")

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

    # Supported parameterless actions (no selector/key/text needed)
    _PARAMETERLESS_ACTIONS = {
        "goto", "navigate",
        "fill_form", "submit", "extract_article",
        "explore_for_form", "explore_for_content",
        "extract_companies", "save_to_file",
        "extract_company_websites_deep", "save_to_csv",
    }

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
                if act in self._PARAMETERLESS_ACTIONS:
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
