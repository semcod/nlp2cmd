from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Optional

from nlp2cmd.appspec_runtime import AppAction, AppSpec
from nlp2cmd.ir import ActionIR


@dataclass
class MatchResult:
    action: AppAction
    score: float


class SchemaDrivenNLP2CMD:
    def __init__(self, spec: AppSpec):
        self.spec = spec

    _STOP_WORDS = {
        "a", "an", "and", "check", "dla", "for", "in", "into", "na",
        "of", "on", "please", "pokaż", "show", "the", "to", "usage",
    }

    def _extract_text_tokens(self, text_lower: str) -> set[str]:
        """Extract meaningful tokens from text, filtering stop words."""
        return {w for w in re.split(r"\W+", text_lower) if w and w not in self._STOP_WORDS}

    def _score_patterns(self, patterns: list, text_lower: str) -> float:
        """Score based on pattern matching."""
        for p in patterns:
            if isinstance(p, str) and p and p.lower() in text_lower:
                return 0.6
        return 0.0

    def _score_examples(self, examples: list, text_lower: str) -> float:
        """Score based on example matching."""
        for ex in examples:
            if isinstance(ex, str) and ex:
                ex_words = [w for w in re.split(r"\W+", ex.lower()) if w]
                if ex_words and any(w in text_lower for w in ex_words[:3]):
                    return 0.2
        return 0.0

    def _score_token_overlap(self, action: AppAction, text_tokens: set[str]) -> float:
        """Fallback scoring based on token overlap with action id and description."""
        aid = str(action.id or "").lower()
        desc = str(action.description or "").lower()
        a_tokens = {w for w in re.split(r"\W+", aid + " " + desc) if w}
        overlap = len(text_tokens & a_tokens)
        if overlap:
            return min(overlap, 4) * 0.12
        return 0.0

    def _score_command_boosts(self, action: AppAction, text_tokens: set[str]) -> float:
        """Apply command-specific scoring boosts."""
        schema = action.schema or {}
        cmd = str(schema.get("command") or "")
        boost = 0.0
        
        if cmd == "git" and "git" in text_tokens:
            boost += 0.2
        if cmd in {"df", "du"} and any(k in text_tokens for k in {"disk", "space", "dysk", "miejsce"}):
            boost += 0.35
        if cmd == "du" and any(k in text_tokens for k in {"directory", "dir", "katalog"}):
            boost += 0.2
            
        return boost

    def _apply_pattern_bonus(self, patterns: list, score: float) -> float:
        """Apply bonus for having patterns."""
        if score > 0:
            return score + min(len(patterns), 5) * 0.02
        return score

    def transform(self, text: str) -> ActionIR:
        match = self._select_action(text)
        params = self._extract_params(match.action, text)
        dsl = self._render_dsl(match.action, params, text)

        output_format = str(match.action.dsl.get("output_format") or "raw")

        return ActionIR(
            action_id=match.action.id,
            dsl=dsl,
            dsl_kind=match.action.dsl_kind,  # type: ignore[arg-type]
            params=params,
            output_format=output_format,  # type: ignore[arg-type]
            confidence=min(max(match.score, 0.0), 1.0),
            explanation=f"schema-driven match score={match.score:.2f}",
            metadata={"action_type": match.action.type},
        )

    def _select_action(self, text: str) -> MatchResult:
        text_lower = text.lower()
        text_tokens = self._extract_text_tokens(text_lower)
        best: Optional[MatchResult] = None

        for action in self.spec.actions:
            patterns = list((action.match or {}).get("patterns", []) or [])
            examples = list((action.match or {}).get("examples", []) or [])

            score = self._score_patterns(patterns, text_lower)
            score += self._score_examples(examples, text_lower)

            if score == 0.0:
                score += self._score_token_overlap(action, text_tokens)

            score += self._score_command_boosts(action, text_tokens)
            score = self._apply_pattern_bonus(patterns, score)

            if best is None or score > best.score:
                best = MatchResult(action=action, score=score)

        if best is None:
            raise ValueError("AppSpec has no actions")

        return best

    def _convert_param_value(self, value: str, param_type: str) -> Any:
        """Convert parameter value based on type specification."""
        if param_type == "integer":
            try:
                return int(value)
            except ValueError:
                return value
        elif param_type == "number":
            try:
                return float(value)
            except ValueError:
                return value
        elif param_type == "boolean":
            return value.lower() in {"1", "true", "yes", "y", "on"}
        else:
            return value

    def _extract_quoted_value(self, text: str) -> str | None:
        """Extract quoted value from text."""
        m = re.search(r"\"([^\"]+)\"|'([^']+)'", text)
        if m:
            return m.group(1) or m.group(2)
        return None

    def _extract_params(self, action: AppAction, text: str) -> dict[str, Any]:
        params: dict[str, Any] = {}

        tokens = re.split(r"\s+", text.strip())
        for tok in tokens:
            if "=" not in tok:
                continue
            key, value = tok.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key or key not in action.params:
                continue

            spec = action.params.get(key) or {}
            param_type = str(spec.get("type") or "string")
            params[key] = self._convert_param_value(value, param_type)

        if "value" in (action.params or {}) and "value" not in params:
            quoted_value = self._extract_quoted_value(text)
            if quoted_value:
                params["value"] = quoted_value

        return params

    def _render_dsl(self, action: AppAction, params: dict[str, Any], text: str) -> str:
        template = action.dsl.get("template")
        if isinstance(template, str) and template.strip():
            try:
                return template.format(**params, text=text)
            except Exception:
                pass

        if action.dsl_kind == "http":
            return self._render_http(action, params)

        if action.dsl_kind == "shell":
            return self._render_shell(action, params, text)

        if action.dsl_kind == "dom":
            return self._render_dom(action, params)

        return f"# action={action.id} (provide dsl.template to render), params={params}"

    def _render_dom(self, action: AppAction, params: dict[str, Any]) -> str:
        schema = action.schema or {}
        dom_action = str(schema.get("action") or "")
        selector = str(schema.get("selector") or "")
        base_url = schema.get("base_url")

        payload: dict[str, Any] = {
            "dsl": "dom_dql.v1",
            "action": dom_action,
            "target": {"by": "css", "value": selector},
            "params": {},
        }

        if isinstance(base_url, str) and base_url.strip():
            payload["url"] = base_url

        if dom_action in {"type", "select"}:
            if "value" in params and params.get("value") is not None:
                payload["params"]["value"] = params["value"]

        return json.dumps(payload, ensure_ascii=False)

    def _render_http(self, action: AppAction, params: dict[str, Any]) -> str:
        schema = action.schema or {}
        method = str(schema.get("method") or "GET").upper()
        path = str(schema.get("path") or "/")
        base_url = str(schema.get("base_url") or "")

        for name, p in (action.params or {}).items():
            if str((p or {}).get("location") or "") == "path" and name in params:
                path = path.replace("{" + name + "}", str(params[name]))

        url = path
        if base_url and not url.startswith(("http://", "https://")):
            if url.startswith("/"):
                url = base_url.rstrip("/") + url
            else:
                url = base_url.rstrip("/") + "/" + url

        query_parts: list[str] = []
        for name, p in (action.params or {}).items():
            if str((p or {}).get("location") or "") == "query" and name in params:
                query_parts.append(f"{name}={params[name]}")
        if query_parts:
            url += "?" + "&".join(query_parts)

        parts = ["curl", "-X", method, url, "-H", "Content-Type: application/json"]

        body: dict[str, Any] = {}
        for name, p in (action.params or {}).items():
            if str((p or {}).get("location") or "") == "body" and name in params:
                body[name] = params[name]

        if body and method in {"POST", "PUT", "PATCH"}:
            import json

            parts.extend(["-d", json.dumps(body)])

        return " ".join(parts)

    def _render_shell(self, action: AppAction, params: dict[str, Any], text: str) -> str:
        schema = action.schema or {}
        cmd = str(schema.get("command") or "")

        if not cmd:
            m = re.match(r"^shell\.(.+)$", action.id)
            if m:
                cmd = m.group(1)
            else:
                cmd = action.id

        parts = [cmd]

        if not params:
            text_lower = (text or "").lower()

            if cmd == "git":
                for sub in ["status", "log", "diff", "branch"]:
                    if sub in text_lower:
                        parts.append(sub)
                        break

            if cmd == "df":
                if any(k in text_lower for k in ["disk", "space", "usage", "miejsce", "dysk"]):
                    parts.append("-h")

            if cmd == "du":
                if any(k in text_lower for k in ["current directory", "this directory", "bieżąc", "aktualny", "katalog"]):
                    parts.extend(["-sh", "."])
                elif any(k in text_lower for k in ["disk", "space", "usage", "miejsce", "dysk"]):
                    parts.append("-sh")

        for name, value in params.items():
            spec = action.params.get(name) or {}
            loc = str(spec.get("location") or "option")
            t = str(spec.get("type") or "string")

            if loc not in {"option", "arg", "unknown"}:
                continue

            flag = "--" + name.replace("_", "-")
            if t == "boolean":
                if value:
                    parts.append(flag)
            else:
                parts.extend([flag, str(value)])

        return " ".join(parts)
