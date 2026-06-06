"""Form field filtering helpers for junk/contact detection."""

from __future__ import annotations

from typing import Any, Optional
from nlp2cmd.utils.yaml_compat import yaml


def _field_attrs(f: object) -> tuple[str, str, str, str, str, str]:
    """Extract common field attributes as lowered strings.

    Returns (field_type, name, fid, label, placeholder, selector).
    """
    try:
        field_type = str(getattr(f, "field_type", "") or "").strip().lower()
        name = str(getattr(f, "name", "") or "").strip().lower()
        fid = str(getattr(f, "id", "") or "").strip().lower()
        label = str(getattr(f, "label", "") or "").strip().lower()
        placeholder = str(getattr(f, "placeholder", "") or "").strip().lower()
        selector = str(getattr(f, "selector", "") or "").strip().lower()
    except Exception:
        return ("", "", "", "", "", "")
    return (field_type, name, fid, label, placeholder, selector)


def _is_junk_field(f: object) -> bool:
    """Return True if a detected field is search/cookie/captcha/comment junk."""
    field_type, name, fid, label, placeholder, _ = _field_attrs(f)
    hay = " ".join([name, fid, label, placeholder])

    if field_type == "search":
        return True
    if name in {"s", "q", "search", "query"}:
        return True
    if "search" in hay or "szukaj" in hay or "wyszuki" in hay:
        return True
    if "cookie" in hay or "consent" in hay:
        return True
    if fid.startswith("cky") or "cky" in hay:
        return True
    if fid.startswith("cmplz") or "cmplz" in hay:
        return True
    if "captcha" in hay or "recaptcha" in hay or "g-recaptcha" in hay or "hcaptcha" in hay:
        return True
    if name in {"comment", "author", "url", "wp-comment-cookies-consent"}:
        return True
    if "comment" in hay:
        return True
    if name.startswith("apbct__") or "cleantalk" in hay:
        return True
    return False


def _is_contact_relevant_field(f: object) -> bool:
    """Return True if a field looks like part of a contact form."""
    if _is_junk_field(f):
        return False

    field_type, name, fid, label, placeholder, _ = _field_attrs(f)
    if field_type in {"email", "tel"}:
        return True
    if field_type not in {"text", "textarea", "email", "tel"}:
        return False

    hay = " ".join([name, fid, label, placeholder])
    contact_tokens = [
        "email", "e-mail", "mail", "telefon", "phone",
        "wiadomo", "message", "imi", "name", "temat", "subject",
    ]
    return any(t in hay for t in contact_tokens)


def _looks_like_comment_form(fields: list) -> bool:
    """Return True if *fields* look like a WordPress comment form."""
    try:
        for f in fields:
            _, name, fid, _, label, selector = _field_attrs(f)
            placeholder = str(getattr(f, "placeholder", "") or "").strip().lower()
            hay = " ".join([name, fid, selector, label, placeholder])
            if "comment" in hay or name in {"author", "email", "url"}:
                return True
    except Exception:
        pass
    return False


def _filter_form_fields(
    fields: list,
    console_wrapper: Optional[Any] = None,
) -> list:
    """Filter out junk / comment / non-contact fields, log via *console_wrapper*.

    Returns the (possibly empty) filtered list.
    """
    if not fields:
        return fields

    if _looks_like_comment_form(fields):
        if console_wrapper is not None:
            try:
                console_wrapper.print(
                    yaml.safe_dump(
                        {"status": "form_fields_ignored_as_comment_form", "detected_count": len(fields)},
                        sort_keys=False, allow_unicode=True,
                    ).rstrip(),
                    language="yaml",
                )
            except Exception:
                pass
        return []

    contact_like = [f for f in fields if _is_contact_relevant_field(f)]
    if not contact_like:
        # Fallback: some contact forms have poor metadata (no name/id/placeholder),
        # so token-based heuristics may fail. If we see strong form signals (textarea/email/tel/checkbox),
        # keep non-junk typical fields instead of returning empty.
        try:
            strong_types = {"textarea", "email", "tel", "checkbox"}
            has_strong = any((_field_attrs(f)[0] in strong_types) and (not _is_junk_field(f)) for f in fields)
        except Exception:
            has_strong = False

        if has_strong:
            relaxed = []
            for f in fields:
                if _is_junk_field(f):
                    continue
                field_type, *_ = _field_attrs(f)
                if field_type in {"text", "textarea", "email", "tel", "checkbox"}:
                    relaxed.append(f)
            if relaxed:
                return relaxed

        if console_wrapper is not None:
            try:
                console_wrapper.print(
                    yaml.safe_dump(
                        {"status": "form_fields_ignored_as_non_contact", "detected_count": len(fields)},
                        sort_keys=False, allow_unicode=True,
                    ).rstrip(),
                    language="yaml",
                )
            except Exception:
                pass
        return []

    return fields
