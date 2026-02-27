"""
Form data loader from .env and data/*.json files.

Loads form field values from environment variables and JSON configuration files.
Configuration is loaded from data/form_schema.json.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse
from typing import Any, Optional

from nlp2cmd.utils.data_files import find_data_file


class FormDataLoader:
    """
    Loads form field data from multiple sources:
    1. .env file (for sensitive data like email, name, phone)
    2. data/form_schema.json (for field mappings configuration)
    3. data/form_data.json (for default values)
    """
    
    def __init__(
        self,
        data_dir: str = "./data",
        env_file: str = ".env",
        schema_file: str = "form_schema.json",
        site: Optional[str] = None,
        site_domain: Optional[str] = None,
    ):
        self.data_dir = Path(data_dir)
        self.env_file = Path(env_file)
        self.schema_file = self.data_dir / schema_file
        self._schema_file_name = schema_file

        # Backwards/forwards compatibility:
        # - `site` can be a full URL or domain
        # - `site_domain` can be provided directly
        self.site_domain = site_domain or self._parse_domain(site)
        
        self._env_data: dict[str, str] = {}
        self._json_data: dict[str, Any] = {}
        self._field_values: dict[str, str] = {}
        self._schema: dict[str, Any] = {}
        self._field_mappings: dict[str, str] = {}  # pattern -> env_var
        
        self._load_schema()
        self._load_env()
        self._load_json_files()
        self._build_field_values()

    @staticmethod
    def _dedupe_preserve_order(items: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for s in items:
            if not isinstance(s, str):
                continue
            key = s.strip()
            if not key:
                continue
            if key in seen:
                continue
            seen.add(key)
            out.append(key)
        return out

    @staticmethod
    def dedupe_selectors(items: list[str]) -> list[str]:
        return FormDataLoader._dedupe_preserve_order(items)

    @staticmethod
    def _parse_domain(site: Optional[str]) -> Optional[str]:
        if not isinstance(site, str) or not site.strip():
            return None
        s = site.strip()

        try:
            if "://" in s:
                parsed = urlparse(s)
                domain = parsed.netloc
                return domain or None
        except Exception:
            return None

        if "/" in s:
            s = s.split("/", 1)[0]
        return s or None

    @staticmethod
    def _safe_domain_filename(domain: str) -> str:
        return (
            domain.strip()
            .replace("/", "_")
            .replace("\\", "_")
            .replace(":", "_")
        )

    def _user_sites_dir(self) -> Path:
        return Path.home() / ".nlp2cmd" / "sites"

    def _project_sites_dir(self) -> Path:
        return self.data_dir / "sites"

    def _site_profile_paths(self, domain: str) -> list[Path]:
        fname = f"{self._safe_domain_filename(domain)}.json"
        return [self._user_sites_dir() / fname, self._project_sites_dir() / fname]

    def get_site_profile_write_path(self, domain: str) -> Path:
        candidates = self._site_profile_paths(domain)
        last_err: Optional[Exception] = None

        for path in candidates:
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                with open(path, "a", encoding="utf-8"):
                    pass
                return path
            except Exception as e:
                last_err = e
                continue

        if last_err is not None:
            raise last_err
        return candidates[-1]

    def _load_site_profile_payload(self, domain: Optional[str]) -> dict[str, Any]:
        if not isinstance(domain, str) or not domain.strip():
            return {}

        for path in self._site_profile_paths(domain.strip()):
            try:
                if not path.exists():
                    continue
                payload = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    return payload
            except Exception:
                continue

        return {}

    def _deep_merge(self, base: Any, override: Any) -> Any:
        if isinstance(base, dict) and isinstance(override, dict):
            out: dict[str, Any] = dict(base)
            for k, v in override.items():
                if k in out:
                    out[k] = self._deep_merge(out[k], v)
                else:
                    out[k] = v
            return out

        if isinstance(base, list) and isinstance(override, list):
            merged: list[Any] = [*override, *base]
            str_items: list[str] = [x for x in merged if isinstance(x, str)]
            if len(str_items) == len([x for x in merged if x is not None]):
                return self._dedupe_preserve_order(str_items)
            return merged

        return override
    
    def _load_schema(self) -> None:
        """Load form configuration from schema file."""
        base: dict[str, Any] = {}

        resolved = find_data_file(explicit_path=None, default_filename=self._schema_file_name)
        schema_path = resolved or self.schema_file

        if schema_path.exists():
            try:
                with open(schema_path) as f:
                    payload = json.load(f)
                    if isinstance(payload, dict):
                        base = payload
            except Exception:
                base = {}

        site_payload = self._load_site_profile_payload(self.site_domain)
        self._schema = self._deep_merge(base, site_payload) if site_payload else base

        self._field_mappings = {}
        field_mappings = self._schema.get("field_mappings", {})
        if isinstance(field_mappings, dict):
            for _, config in field_mappings.items():
                if not isinstance(config, dict):
                    continue
                env_var = config.get("env_var", "")
                patterns = config.get("patterns", [])
                if isinstance(env_var, str) and env_var and isinstance(patterns, list):
                    for pattern in patterns:
                        if isinstance(pattern, str) and pattern.strip():
                            self._field_mappings[pattern.lower()] = env_var

    def _ensure_domain(self, domain: Optional[str]) -> Optional[str]:
        if isinstance(domain, str) and domain.strip():
            return domain.strip()
        if isinstance(self.site_domain, str) and self.site_domain.strip():
            return self.site_domain.strip()
        return None

    def _load_site_profile_payload_anywhere(self, domain: str) -> tuple[dict[str, Any], Optional[Path]]:
        for path in self._site_profile_paths(domain):
            try:
                if not path.exists():
                    continue
                payload = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    return payload, path
            except Exception:
                continue
        return {}, None

    def _save_site_profile_payload(self, domain: str, payload: dict[str, Any]) -> Optional[Path]:
        if not isinstance(domain, str) or not domain.strip():
            return None
        if not isinstance(payload, dict):
            return None

        path = self.get_site_profile_write_path(domain.strip())
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        return path

    def _add_selector_to_list(self, domain: Optional[str], *, key: str, selector: str, max_items: int = 50) -> bool:
        d = self._ensure_domain(domain)
        if not d:
            return False
        if not isinstance(selector, str) or not selector.strip():
            return False

        existing, _ = self._load_site_profile_payload_anywhere(d)
        if not isinstance(existing, dict):
            existing = {}

        current = existing.get(key)
        if not isinstance(current, list):
            current = []

        cleaned = [x for x in current if isinstance(x, str) and x.strip()]
        sel = selector.strip()

        if cleaned and cleaned[0] == sel:
            return False

        cleaned = [sel] + [x for x in cleaned if x != sel]
        if max_items > 0:
            cleaned = cleaned[:max_items]

        existing[key] = cleaned
        existing.setdefault("$schema", "form_schema.site.v1")
        existing.setdefault("domain", d)

        try:
            self._save_site_profile_payload(d, existing)
            return True
        except Exception:
            return False

    def _add_selector_to_type_selectors(self, domain: Optional[str], *, selector_type: str, selector: str, max_items: int = 50) -> bool:
        d = self._ensure_domain(domain)
        if not d:
            return False
        if not isinstance(selector_type, str) or not selector_type.strip():
            return False
        if not isinstance(selector, str) or not selector.strip():
            return False

        existing, _ = self._load_site_profile_payload_anywhere(d)
        if not isinstance(existing, dict):
            existing = {}

        ts = existing.get("type_selectors")
        if not isinstance(ts, dict):
            ts = {}

        st = selector_type.strip()
        current = ts.get(st)
        if not isinstance(current, list):
            current = []

        cleaned = [x for x in current if isinstance(x, str) and x.strip()]
        sel = selector.strip()

        if cleaned and cleaned[0] == sel:
            return False

        cleaned = [sel] + [x for x in cleaned if x != sel]
        if max_items > 0:
            cleaned = cleaned[:max_items]

        ts[st] = cleaned
        existing["type_selectors"] = ts
        existing.setdefault("$schema", "form_schema.site.v1")
        existing.setdefault("domain", d)

        try:
            self._save_site_profile_payload(d, existing)
            return True
        except Exception:
            return False

    def add_dismiss_selector(self, selector: str, *, domain: Optional[str] = None) -> bool:
        return self._add_selector_to_list(domain, key="dismiss_selectors", selector=selector)

    def add_submit_selector(self, selector: str, *, domain: Optional[str] = None) -> bool:
        return self._add_selector_to_list(domain, key="submit_selectors", selector=selector)

    def add_type_selector(self, selector: str, *, selector_type: str = "generic", domain: Optional[str] = None) -> bool:
        return self._add_selector_to_type_selectors(domain, selector_type=selector_type, selector=selector)

    def add_article_link_selector(self, selector: str, *, domain: Optional[str] = None) -> bool:
        return self._add_selector_to_list(domain, key="article_link_selectors", selector=selector)

    def add_article_content_selector(self, selector: str, *, domain: Optional[str] = None) -> bool:
        return self._add_selector_to_list(domain, key="article_content_selectors", selector=selector)

    def get_site_approval(self, action: str, *, domain: Optional[str] = None) -> bool:
        d = self._ensure_domain(domain)
        if not d:
            return False
        if not isinstance(action, str) or not action.strip():
            return False

        payload = self._load_site_profile_payload(d)
        if not isinstance(payload, dict):
            return False

        approvals = payload.get("approvals")
        if not isinstance(approvals, dict):
            return False

        return bool(approvals.get(action.strip()))

    def set_site_approval(self, action: str, value: bool, *, domain: Optional[str] = None) -> bool:
        d = self._ensure_domain(domain)
        if not d:
            return False
        if not isinstance(action, str) or not action.strip():
            return False

        existing, _ = self._load_site_profile_payload_anywhere(d)
        if not isinstance(existing, dict):
            existing = {}

        approvals = existing.get("approvals")
        if not isinstance(approvals, dict):
            approvals = {}

        approvals[action.strip()] = bool(value)
        existing["approvals"] = approvals
        existing.setdefault("$schema", "form_schema.site.v1")
        existing.setdefault("domain", d)

        try:
            self._save_site_profile_payload(d, existing)
            return True
        except Exception:
            return False
    
    def _load_env(self) -> None:
        """Load environment variables from .env file."""
        # First, load from .env file if it exists
        if self.env_file.exists():
            with open(self.env_file) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        key, _, value = line.partition('=')
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        self._env_data[key] = value
        
        # Also check current environment variables
        for key in os.environ:
            if key.startswith('FORM_'):
                self._env_data[key] = os.environ[key]
    
    def _load_json_files(self) -> None:
        """Load all JSON files from data directory."""
        if not self.data_dir.exists():
            return
        
        # Load form_data.json specifically if it exists
        form_data_file = self.data_dir / "form_data.json"
        if form_data_file.exists():
            try:
                with open(form_data_file) as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self._json_data.update(data)
            except Exception:
                pass
        
        # Load any other JSON files that might contain form data
        for json_file in self.data_dir.glob("*.json"):
            if json_file.name == "form_data.json":
                continue  # Already loaded
            try:
                with open(json_file) as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        # Check if it has form-related keys
                        if any(k.lower() in ['forms', 'form_fields', 'fields', 'defaults'] for k in data.keys()):
                            self._json_data[json_file.stem] = data
            except Exception:
                continue
    
    def _build_field_values(self) -> None:
        """Build field values dictionary from all sources."""
        # Priority: .env > site-specific > form_data.json > other json files
        
        # Load from JSON defaults first (lowest priority)
        if 'defaults' in self._json_data:
            for key, value in self._json_data['defaults'].items():
                self._field_values[key.lower()] = str(value)
        
        if 'fields' in self._json_data:
            for key, value in self._json_data['fields'].items():
                self._field_values[key.lower()] = str(value)
        
        # Load site-specific data (higher priority)
        if 'sites' in self._json_data and self.site_domain:
            # Try exact domain match first
            if self.site_domain in self._json_data['sites']:
                site_data = self._json_data['sites'][self.site_domain]
                if isinstance(site_data, dict):
                    for key, value in site_data.items():
                        self._field_values[key.lower()] = str(value)
            
            # Try variations of domain
            domain_variations = [
                f"www.{self.site_domain}",
                self.site_domain.replace("www.", ""),
            ]
            for variation in domain_variations:
                if variation in self._json_data['sites']:
                    site_data = self._json_data['sites'][variation]
                    if isinstance(site_data, dict):
                        for key, value in site_data.items():
                            self._field_values[key.lower()] = str(value)
                        break
        
        # Load from env using schema-based field mappings (highest priority)
        for field_pattern, env_key in self._field_mappings.items():
            if env_key in self._env_data:
                self._field_values[field_pattern.lower()] = self._env_data[env_key]
    
    def get_value_for_field(
        self,
        field_name: Optional[str] = None,
        field_id: Optional[str] = None,
        field_label: Optional[str] = None,
        field_placeholder: Optional[str] = None,
        field_type: Optional[str] = None,
    ) -> Optional[str]:
        """
        Get value for a form field based on its attributes.
        
        Tries to match field by:
        1. Exact field name/id/label match
        2. Partial match in mappings
        3. Field type defaults
        """
        # Try exact matches first
        candidates = [
            field_name,
            field_id,
            field_label,
            field_placeholder,
        ]
        
        for candidate in candidates:
            if not candidate:
                continue
            candidate_lower = candidate.lower().strip()
            # Normalize by removing asterisks and extra whitespace (for required field indicators)
            candidate_lower = re.sub(r'\s*\*\s*', '', candidate_lower).strip()
            
            # Direct match in field values
            if candidate_lower in self._field_values:
                return self._field_values[candidate_lower]
            
            # Check env mappings from schema
            if candidate_lower in self._field_mappings:
                env_key = self._field_mappings[candidate_lower]
                if env_key in self._env_data:
                    return self._env_data[env_key]
        
        # Try partial matching using schema mappings
        for candidate in candidates:
            if not candidate:
                continue
            candidate_lower = candidate.lower().strip()
            
            for mapping_key, env_key in self._field_mappings.items():
                if mapping_key in candidate_lower or candidate_lower in mapping_key:
                    if env_key in self._env_data:
                        return self._env_data[env_key]
        
        # Type-based defaults
        if field_type == 'email':
            return self._env_data.get('FORM_EMAIL')
        elif field_type == 'tel':
            return self._env_data.get('FORM_PHONE')
        
        return None
    
    def get_all_values(self) -> dict[str, str]:
        """Get all loaded form values."""
        return self._field_values.copy()
    
    def get_env_value(self, key: str) -> Optional[str]:
        """Get specific env value."""
        return self._env_data.get(key)
    
    def has_data(self) -> bool:
        """Check if any form data is available."""
        return bool(self._env_data) or bool(self._field_values)
    
    def get_skip_fields(self) -> set[str]:
        """Get set of field names to skip during form filling."""
        configured = self._schema.get("skip_fields")
        defaults = {
            "sl",
            "tl",
            "query",
            "gtrans",
            "vote",
            "honeypot",
            "bot",
            "captcha",
            "hidden",
        }

        out = set(defaults)
        if isinstance(configured, list):
            for s in configured:
                if isinstance(s, str) and s.strip():
                    out.add(s.strip().lower())
        return out
    
    def get_submit_selectors(self) -> list[str]:
        """Get list of submit button selectors from schema."""
        configured = self._schema.get("submit_selectors")
        defaults = [
            'button[type="submit"]',
            'input[type="submit"]',
            '[type="submit"]',
            'button:has-text("Wyślij")',
            'button:has-text("Wyslij")',
            'button:has-text("Submit")',
            'button:has-text("Send")',
            'button:has-text("Prześlij")',
            'button:has-text("Przeslij")',
            'button:has-text("OK")',
            '.submit-button',
        ]

        if isinstance(configured, list):
            return self._dedupe_preserve_order([*configured, *defaults])
        return defaults

    def get_article_link_selectors(self) -> list[str]:
        configured = self._schema.get("article_link_selectors")
        defaults = [
            "article a[href]",
            "main a[href]",
            "h1 a[href]",
            "h2 a[href]",
            "h3 a[href]",
            "a[href*='artykul']",
            "a[href*='article']",
            "a[class*='title']",
            "a[class*='headline']",
        ]
        if isinstance(configured, list):
            cleaned: list[str] = []
            for s in configured:
                if isinstance(s, str) and s.strip():
                    cleaned.append(s.strip())
            return self._dedupe_preserve_order([*cleaned, *defaults])
        return defaults

    def get_article_content_selectors(self) -> list[str]:
        configured = self._schema.get("article_content_selectors")
        defaults = [
            "article",
            "[role='article']",
            "main article",
            ".article-content",
            ".article-body",
            ".entry-content",
            ".post-content",
        ]
        if isinstance(configured, list):
            cleaned: list[str] = []
            for s in configured:
                if isinstance(s, str) and s.strip():
                    cleaned.append(s.strip())
            return self._dedupe_preserve_order([*cleaned, *defaults])
        return defaults

    def get_company_listing_selectors(self) -> list[str]:
        """Get CSS selectors for company listing items."""
        configured = self._schema.get("company_listing_selectors")
        defaults = [
            ".company-item", ".business-listing", ".listing-item",
            ".company-card", ".search-result", ".result-item",
        ]
        if isinstance(configured, list):
            cleaned: list[str] = [s.strip() for s in configured if isinstance(s, str) and s.strip()]
            return self._dedupe_preserve_order([*cleaned, *defaults])
        return defaults

    def get_company_link_selectors(self) -> list[str]:
        """Get CSS selectors for company name links."""
        configured = self._schema.get("company_link_selectors")
        defaults = [
            "a[href*='firma']", "a[href*='company']",
            "h2 a", "h3 a", ".listing-title a",
        ]
        if isinstance(configured, list):
            cleaned: list[str] = [s.strip() for s in configured if isinstance(s, str) and s.strip()]
            return self._dedupe_preserve_order([*cleaned, *defaults])
        return defaults

    def get_company_website_selectors(self) -> list[str]:
        """Get CSS selectors for company external website links."""
        configured = self._schema.get("company_website_selectors")
        defaults = [
            ".website a", ".www a", ".company-website a",
            "a[rel='nofollow'][href*='http']", "a.external-link",
        ]
        if isinstance(configured, list):
            cleaned: list[str] = [s.strip() for s in configured if isinstance(s, str) and s.strip()]
            return self._dedupe_preserve_order([*cleaned, *defaults])
        return defaults

    def get_save_filename_patterns(self) -> list[str]:
        """Get regex patterns to extract output filename from NL."""
        patterns = self._schema.get("save_filename_patterns")
        if isinstance(patterns, list):
            return [p for p in patterns if isinstance(p, str) and p.strip()]
        return []

    def get_nlp_keywords(self, group: str) -> list[str]:
        """Get schema-driven NLP keyword list (e.g. typing/clicking/form/submit/press_enter)."""
        nlp_cfg = self._schema.get("nlp_keywords")
        if not isinstance(nlp_cfg, dict):
            return []

        values = nlp_cfg.get(group)
        if isinstance(values, list):
            out: list[str] = []
            for v in values:
                if isinstance(v, str) and v.strip():
                    out.append(v.strip())
            return out
        return []

    def get_type_text_patterns(self) -> list[str]:
        """Get regex patterns used to extract text-to-type from NL (schema-driven)."""
        patterns = self._schema.get("type_text_patterns")
        if isinstance(patterns, list):
            out: list[str] = []
            for p in patterns:
                if isinstance(p, str) and p.strip():
                    out.append(p)
            return out
        return []
    
    def get_article_topic_patterns(self) -> list[str]:
        """Get regex patterns used to extract article topic from NL (schema-driven)."""
        patterns = self._schema.get("article_topic_patterns")
        if isinstance(patterns, list):
            out: list[str] = []
            for p in patterns:
                if isinstance(p, str) and p.strip():
                    out.append(p)
            return out
        return []
    
    def get_dismiss_selectors(self) -> list[str]:
        """Get list of popup dismiss selectors from schema."""
        configured = self._schema.get("dismiss_selectors")
        defaults = [
            "button:has-text('Accept all')",
            "button:has-text('Akceptuj wszystko')",
            "button:has-text('Zaakceptuj')",
            "button:has-text('Accept')",
            "button:has-text('Zgadzam się')",
            "button:has-text('Zgadzam sie')",
            "button:has-text('I agree')",
            "button:has-text('OK')",
            "button[aria-label*='Accept']",
            "button[aria-label*='Akceptuj']",
            "button[id*='accept']",
            "button[id*='consent']",
            "#L2AGLb",
        ]

        if isinstance(configured, list):
            cleaned: list[str] = []
            for s in configured:
                if isinstance(s, str) and s.strip():
                    cleaned.append(s.strip())
            return self._dedupe_preserve_order([*cleaned, *defaults])

        return defaults

    def get_type_selectors(self, selector_type: str = "search") -> list[str]:
        """Get list of input selectors for typing from schema."""
        type_selectors = self._schema.get("type_selectors")
        if isinstance(type_selectors, dict):
            configured = type_selectors.get(selector_type)
            if isinstance(configured, list):
                cleaned: list[str] = []
                for s in configured:
                    if isinstance(s, str) and s.strip():
                        cleaned.append(s.strip())
                if cleaned:
                    return cleaned

        # Minimal fallback (should be overridden by schema)
        return ["textarea", "input[type='text']", "input"]

    def get_browser_context_options(self) -> dict[str, Any]:
        ctx = self._schema.get("browser_context")

        viewport: dict[str, Any] = {"width": 1280, "height": 720}
        locale: str = "pl-PL"

        if isinstance(ctx, dict):
            v = ctx.get("viewport")
            if isinstance(v, dict):
                w = v.get("width")
                h = v.get("height")
                if isinstance(w, int) and w > 0:
                    viewport["width"] = w
                if isinstance(h, int) and h > 0:
                    viewport["height"] = h

            loc = ctx.get("locale")
            if isinstance(loc, str) and loc.strip():
                locale = loc.strip()

        return {"viewport": viewport, "locale": locale}


def create_example_env_file(path: str = ".env.example") -> None:
    """Create example .env file with form field templates."""
    content = """# Form Data Configuration
# Uncomment and fill in values for automatic form filling

# Personal Information
FORM_NAME=YOUR_NAME
FORM_LASTNAME=YOUR_LASTNAME
FORM_EMAIL=your.email@example.com
FORM_PHONE=+00 000 000 000

# Message Content
FORM_MESSAGE=YOUR_MESSAGE
FORM_SUBJECT=YOUR_SUBJECT

# Business Information
# FORM_COMPANY=Moja Firma Sp. z o.o.
# FORM_ADDRESS=ul. Przykładowa 1
# FORM_CITY=Warszawa
# FORM_WEBSITE=https://example.com
"""
    with open(path, 'w') as f:
        f.write(content)


def create_example_form_data_json(path: str = "./data/form_data.json") -> None:
    """Create example form_data.json file."""
    data = {
        "defaults": {
            "imię": "YOUR_NAME",
            "email": "your.email@example.com",
            "telefon": "+00 000 000 000",
            "wiadomość": "YOUR_MESSAGE"
        },
        "sites": {
            "example.com": {
                "Imię": "YOUR_NAME",
                "Adres e-mail": "your.email@example.com",
                "Wiadomość": "YOUR_MESSAGE"
            }
        }
    }
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
