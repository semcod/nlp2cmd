#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from nlp2cmd import NLP2CMD
from nlp2cmd.adapters import ShellAdapter
from nlp2cmd.environment import EnvironmentAnalyzer
from nlp2cmd.feedback import FeedbackAnalyzer, FeedbackResult
from nlp2cmd.generation.pipeline import RuleBasedPipeline


@dataclass
class PromptCase:
    name: str
    text: str
    expected_sentences_min: int = 1
    expected_domain: Optional[str] = None
    expected_intent: Optional[str] = None
    tags: list[str] = field(default_factory=list)


def looks_like_log_input(text: str) -> bool:
    if not text or "\n" not in text:
        return False

    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 3:
        return False

    score = 0
    for ln in lines[:40]:
        ll = ln.lower()

        if "traceback (most recent call last)" in ll:
            score += 4
        if re.search(r"file \".+\", line \d+", ln):
            score += 3
        if re.search(r"\b(exception|error|fatal|stack trace)\b", ll):
            score += 1
        if re.search(r"^\d{4}-\d{2}-\d{2}[ t]\d{2}:\d{2}:\d{2}", ln):
            score += 1
        if re.search(r"^\[(info|warn|warning|error|debug|trace)\]", ll):
            score += 1
        if "command not found" in ll:
            score += 2

    return score >= 4


def default_answer_provider(question: str) -> str:
    q = (question or "").lower()

    if "tool/domain" in q or "domain" in q:
        return "shell"

    if "base command" in q:
        return "grep"

    if "package manager" in q or "distro" in q:
        return "apt"

    if "port" in q:
        return "8080"

    if "which file" in q:
        return "./app.log"

    if "what exactly" in q or "clarify" in q:
        return "Find the root error and propose a safe fix command"

    return "Provide a safe default"


def _shell_env_context() -> dict[str, Any]:
    env = EnvironmentAnalyzer().analyze()
    os_info = env.get("os") or {}
    shell_info = env.get("shell") or {}
    env_vars = env.get("env_vars") or {}

    os_name = os_info.get("system")
    if isinstance(os_name, str):
        os_name = os_name.lower()
    else:
        os_name = "linux"

    return {
        "os": os_name,
        "distro": os_info.get("release", ""),
        "shell": shell_info.get("name", "bash"),
        "available_tools": [],
        "environment_variables": env_vars,
    }


def analyze_with_feedback(
    text: str,
    *,
    adapter_factory: Callable[[], Any],
    context: dict[str, Any],
    answer_provider: Callable[[str], str],
) -> tuple[FeedbackResult, Optional[FeedbackResult]]:
    adapter = adapter_factory()
    nlp = NLP2CMD(adapter=adapter)
    analyzer = FeedbackAnalyzer()

    result = nlp.transform(text, context=context)
    context["last_plan"] = result.plan.model_dump() if hasattr(result.plan, "model_dump") else {}
    context["transform_status"] = result.status.value if hasattr(result.status, "value") else str(result.status)

    feedback = analyzer.analyze(
        original_input=text,
        generated_output=result.command,
        validation_errors=result.errors,
        validation_warnings=result.warnings,
        dsl_type=result.dsl_type,
        context=context,
    )

    if not feedback.requires_user_input:
        return feedback, None

    questions = list(feedback.clarification_questions or [])
    if not questions:
        return feedback, None

    answers: list[str] = []
    for q in questions[:5]:
        a = answer_provider(q)
        if a:
            answers.append(a)

    if not answers:
        return feedback, None

    followup_text = f"{text}. " + " ".join(answers)

    result2 = nlp.transform(followup_text, context=context)
    context["last_plan"] = result2.plan.model_dump() if hasattr(result2.plan, "model_dump") else {}
    context["transform_status"] = result2.status.value if hasattr(result2.status, "value") else str(result2.status)

    feedback2 = analyzer.analyze(
        original_input=followup_text,
        generated_output=result2.command,
        validation_errors=result2.errors,
        validation_warnings=result2.warnings,
        dsl_type=result2.dsl_type,
        context=context,
    )

    return feedback, feedback2


def try_spacy_parse(text: str) -> dict[str, Any]:
    try:
        import spacy
    except Exception:
        return {"available": False, "reason": "spacy not installed"}

    model_name: Optional[str] = None
    nlp = None
    for name in ("pl_core_news_sm", "en_core_web_sm"):
        try:
            nlp = spacy.load(name)
            model_name = name
            break
        except Exception:
            continue

    if nlp is None:
        try:
            nlp = spacy.blank("pl")
        except Exception:
            nlp = spacy.blank("en")
        if "sentencizer" not in nlp.pipe_names:
            nlp.add_pipe("sentencizer")

    doc = nlp(text)

    sents = []
    for sent in doc.sents:
        sent_info: dict[str, Any] = {
            "text": sent.text,
            "tokens": [t.text for t in sent],
        }

        if "parser" in nlp.pipe_names:
            deps = []
            root = None
            for t in sent:
                if t.head == t:
                    root = t
                deps.append({"text": t.text, "dep": t.dep_, "head": t.head.text})
            sent_info["root"] = root.text if root is not None else None
            sent_info["deps"] = deps

        sents.append(sent_info)

    return {
        "available": True,
        "model": model_name,
        "has_parser": bool(nlp and "parser" in nlp.pipe_names),
        "sentence_count": len(sents),
        "sentences": sents,
        "suggested_install": [
            "python -m spacy download en_core_web_sm",
            "python -m spacy download pl_core_news_sm",
        ]
        if model_name is None
        else [],
    }


def split_sentences(text: str) -> list[str]:
    if not text:
        return []

    if looks_like_log_input(text):
        return [text]

    parse = try_spacy_parse(text)
    if isinstance(parse, dict) and parse.get("available") and isinstance(parse.get("sentences"), list):
        sents = []
        for s in parse.get("sentences") or []:
            if isinstance(s, dict) and isinstance(s.get("text"), str):
                st = s.get("text").strip()
                if st:
                    sents.append(st)
        if sents:
            return sents

    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def aggregate_detection(items: list[dict[str, Any]]) -> dict[str, Any]:
    domain_scores: dict[str, float] = {}
    intent_scores: dict[str, float] = {}

    for it in items:
        domain = it.get("domain")
        intent = it.get("intent")
        conf = it.get("confidence")
        try:
            c = float(conf)
        except (TypeError, ValueError):
            c = 0.0

        if isinstance(domain, str) and domain and domain != "unknown":
            domain_scores[domain] = domain_scores.get(domain, 0.0) + max(0.0, c)

        if isinstance(intent, str) and intent and intent != "unknown":
            intent_scores[intent] = intent_scores.get(intent, 0.0) + max(0.0, c)

    dominant_domain = max(domain_scores.items(), key=lambda x: x[1])[0] if domain_scores else "unknown"
    dominant_intent = max(intent_scores.items(), key=lambda x: x[1])[0] if intent_scores else "unknown"

    return {
        "dominant_domain": dominant_domain,
        "dominant_intent": dominant_intent,
        "domain_scores": domain_scores,
        "intent_scores": intent_scores,
    }


def build_cases() -> list[PromptCase]:
    log_traceback = """Traceback (most recent call last):
  File \"app.py\", line 10, in <module>
    import requests
ModuleNotFoundError: No module named 'requests'
"""

    docker_log = """2026-01-23 18:00:00 [ERROR] docker: command not found
2026-01-23 18:00:01 [INFO] retrying...
2026-01-23 18:00:02 [ERROR] exit code 127
"""

    return [
        PromptCase(
            name="shell_find_big_logs",
            text="Znajdź wszystkie pliki .log w /var/log, posortuj po rozmiarze i pokaż 5 największych. Następnie wyświetl ostatnie 20 linii największego pliku.",
            expected_sentences_min=2,
            expected_domain="shell",
            expected_intent="find",
            tags=["multisentence", "shell"],
        ),
        PromptCase(
            name="shell_cleanup_old_files",
            text="W katalogu projektu wypisz pliki *.tmp i *.bak starsze niż 7 dni. Jeśli lista wygląda ok, usuń je. Na koniec pokaż ile miejsca odzyskałem.",
            expected_sentences_min=3,
            expected_domain="shell",
            expected_intent="file_operation",
            tags=["multisentence", "shell"],
        ),
        PromptCase(
            name="shell_grep_errors_then_count",
            text="Przejrzyj ./app.log. Najpierw wyszukaj linie z ERROR, potem policz ile ich jest. Jeśli jest ich więcej niż 10, pokaż ostatnie 5.",
            expected_sentences_min=3,
            expected_domain="shell",
            expected_intent="grep",
            tags=["multisentence", "shell"],
        ),
        PromptCase(
            name="shell_git_branch_and_status",
            text="Sprawdź aktualną gałąź gita. Następnie pokaż status. Jeżeli są niezacommitowane zmiany, wypisz tylko pliki zmodyfikowane.",
            expected_sentences_min=3,
            expected_domain="shell",
            expected_intent="git",
            tags=["multisentence", "shell"],
        ),
        PromptCase(
            name="docker_run_nginx_with_mount",
            text="Uruchom nginx w dockerze na porcie 8080. Zamontuj ./html do /usr/share/nginx/html i ustaw zmienną FOO=bar. Potem sprawdź czy kontener działa.",
            expected_sentences_min=3,
            expected_domain="docker",
            expected_intent="run",
            tags=["multisentence", "docker"],
        ),
        PromptCase(
            name="docker_logs_then_exec",
            text="Pokaż ostatnie 50 linii logów kontenera web. Następnie wejdź do niego i sprawdź zmienne środowiskowe. Jeśli kontener nie działa, uruchom go ponownie.",
            expected_sentences_min=3,
            expected_domain="docker",
            expected_intent="logs",
            tags=["multisentence", "docker"],
        ),
        PromptCase(
            name="k8s_scale_and_status",
            text="W namespace prod przeskaluj deployment api do 3 replik. Potem sprawdź rollout status. Jeśli rollout się nie uda, pokaż eventy.",
            expected_sentences_min=3,
            expected_domain="kubernetes",
            expected_intent="scale",
            tags=["multisentence", "kubernetes"],
        ),
        PromptCase(
            name="k8s_logs_and_fallback",
            text="Pokaż logi poda web w namespace prod z ostatnich 10 minut i przefiltruj ERROR. Jeżeli pod nie istnieje, wypisz pody w tym namespace.",
            expected_sentences_min=2,
            expected_domain="kubernetes",
            expected_intent="logs",
            tags=["multisentence", "kubernetes"],
        ),
        PromptCase(
            name="log_traceback_missing_dependency",
            text=log_traceback + "\nNapraw to: zainstaluj brakujący pakiet i pokaż komendę jak uruchomić aplikację ponownie.",
            expected_sentences_min=1,
            expected_domain="shell",
            tags=["logs"],
        ),
        PromptCase(
            name="log_command_not_found",
            text=docker_log + "\nCo mam zrobić, żeby to zadziałało?",
            expected_sentences_min=1,
            expected_domain="shell",
            tags=["logs"],
        ),
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="multisentence_log_test_results.json")
    args = parser.parse_args()

    cases = build_cases()

    pipeline = RuleBasedPipeline()
    base_context: dict[str, Any] = {"environment": _shell_env_context()}

    results: list[dict[str, Any]] = []

    for case in cases:
        started = time.time()
        entry: dict[str, Any] = {
            "name": case.name,
            "tags": case.tags,
            "text": case.text,
        }

        pr = pipeline.process(case.text)
        entry["rule_pipeline"] = {
            "success": pr.success,
            "domain": pr.domain,
            "intent": pr.intent,
            "confidence": pr.detection_confidence,
            "command": pr.command,
            "warnings": pr.warnings,
            "errors": pr.errors,
        }

        steps_payload: list[dict[str, Any]] = []
        if not looks_like_log_input(case.text):
            steps = pipeline.process_steps(case.text)
            for st in steps:
                steps_payload.append(
                    {
                        "text": st.input_text,
                        "success": st.success,
                        "domain": st.domain,
                        "intent": st.intent,
                        "confidence": st.detection_confidence,
                        "command": st.command,
                        "warnings": st.warnings,
                        "errors": st.errors,
                    }
                )
        entry["pipeline_steps"] = steps_payload

        entry["expected"] = {
            "domain": case.expected_domain,
            "intent": case.expected_intent,
            "sentences_min": case.expected_sentences_min,
        }

        parse_info = None
        if not looks_like_log_input(case.text):
            parse_info = try_spacy_parse(case.text)
        entry["parse"] = parse_info

        if isinstance(parse_info, dict) and parse_info.get("available"):
            entry["parse"]["meets_sentence_expectation"] = bool(
                int(parse_info.get("sentence_count") or 0) >= case.expected_sentences_min
            )

        sentences = split_sentences(case.text)
        entry["sentences"] = sentences

        per_sentence: list[dict[str, Any]] = []
        if not looks_like_log_input(case.text):
            for s in sentences:
                spr = pipeline.process(s)
                per_sentence.append(
                    {
                        "text": s,
                        "success": spr.success,
                        "domain": spr.domain,
                        "intent": spr.intent,
                        "confidence": spr.detection_confidence,
                        "command": spr.command,
                        "warnings": spr.warnings,
                        "errors": spr.errors,
                    }
                )

        entry["per_sentence"] = per_sentence
        entry["per_sentence_aggregate"] = aggregate_detection(per_sentence) if per_sentence else None

        fallback: dict[str, Any] = {"attempted": False}
        if looks_like_log_input(case.text):
            fallback["attempted"] = True
            ctx = dict(base_context)

            fb1, fb2 = analyze_with_feedback(
                case.text,
                adapter_factory=lambda: ShellAdapter(environment_context=_shell_env_context()),
                context=ctx,
                answer_provider=default_answer_provider,
            )

            fallback["first_feedback"] = fb1.to_dict()
            if fb2 is not None:
                fallback["followup_feedback"] = fb2.to_dict()

        entry["log_fallback"] = fallback
        entry["duration_ms"] = (time.time() - started) * 1000
        results.append(entry)

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = Path.cwd() / out_path

    out_path.write_text(json.dumps({"results": results}, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote: {out_path}")

    correct_domain = 0
    correct_intent = 0
    correct_domain_per_sentence = 0
    correct_intent_per_sentence = 0
    correct_domain_any_step = 0
    correct_intent_any_step = 0
    parse_sentence_ok = 0
    parse_checked = 0

    for r in results:
        name = r["name"]
        pr = r["rule_pipeline"]
        exp = r.get("expected") or {}
        exp_domain = exp.get("domain")
        exp_intent = exp.get("intent")

        if isinstance(exp_domain, str) and exp_domain:
            if pr.get("domain") == exp_domain:
                correct_domain += 1

            agg = r.get("per_sentence_aggregate")
            if isinstance(agg, dict) and agg.get("dominant_domain") == exp_domain:
                correct_domain_per_sentence += 1

            steps = r.get("pipeline_steps")
            if isinstance(steps, list) and any(isinstance(s, dict) and s.get("domain") == exp_domain for s in steps):
                correct_domain_any_step += 1

        if isinstance(exp_intent, str) and exp_intent:
            if pr.get("intent") == exp_intent:
                correct_intent += 1

            agg = r.get("per_sentence_aggregate")
            if isinstance(agg, dict) and agg.get("dominant_intent") == exp_intent:
                correct_intent_per_sentence += 1

            steps = r.get("pipeline_steps")
            if isinstance(steps, list) and any(isinstance(s, dict) and s.get("intent") == exp_intent for s in steps):
                correct_intent_any_step += 1

        parse = r.get("parse")
        if isinstance(parse, dict) and parse.get("available"):
            parse_checked += 1
            if parse.get("meets_sentence_expectation"):
                parse_sentence_ok += 1

        print(f"\n== {name} ==")
        print(f"pipeline: success={pr['success']} domain={pr['domain']} intent={pr['intent']} conf={pr['confidence']:.2f}")
        print(f"command: {pr['command']}")

        if exp_domain or exp_intent:
            print(f"expected: domain={exp_domain} intent={exp_intent}")

        agg = r.get("per_sentence_aggregate")
        if isinstance(agg, dict):
            print(f"per-sentence dominant: domain={agg.get('dominant_domain')} intent={agg.get('dominant_intent')}")

        ps = r.get("per_sentence")
        if isinstance(ps, list) and ps:
            for i, row in enumerate(ps, 1):
                if not isinstance(row, dict):
                    continue
                d = row.get("domain")
                it = row.get("intent")
                cmd = row.get("command")
                try:
                    c = float(row.get("confidence") or 0.0)
                except (TypeError, ValueError):
                    c = 0.0
                cmd_str = cmd if isinstance(cmd, str) else ""
                print(f"  sent {i}: {d}/{it} conf={c:.2f} cmd={cmd_str}")

        stp = r.get("pipeline_steps")
        if isinstance(stp, list) and stp:
            print("  steps:")
            for i, row in enumerate(stp, 1):
                if not isinstance(row, dict):
                    continue
                d = row.get("domain")
                it = row.get("intent")
                cmd = row.get("command")
                try:
                    c = float(row.get("confidence") or 0.0)
                except (TypeError, ValueError):
                    c = 0.0
                cmd_str = cmd if isinstance(cmd, str) else ""
                print(f"    {i}. {d}/{it} conf={c:.2f} cmd={cmd_str}")
        if r.get("log_fallback", {}).get("attempted"):
            fb2 = r["log_fallback"].get("followup_feedback")
            fb1 = r["log_fallback"].get("first_feedback")
            if fb1:
                print(f"fallback feedback type: {fb1.get('type')}")
            if fb2:
                print(f"fallback followup type: {fb2.get('type')}")
                print(f"fallback command: {fb2.get('generated_output')}")

        if isinstance(parse, dict) and parse.get("available"):
            print(f"parse: sentences={parse.get('sentence_count')} parser={parse.get('has_parser')} model={parse.get('model')}")
            if parse.get("model") is None:
                for cmd in parse.get("suggested_install") or []:
                    print(f"  install: {cmd}")

    total_expected_domain = sum(1 for c in cases if isinstance(c.expected_domain, str) and c.expected_domain)
    total_expected_intent = sum(1 for c in cases if isinstance(c.expected_intent, str) and c.expected_intent)

    print("\n==== SUMMARY ====")
    if total_expected_domain:
        print(f"domain accuracy: {correct_domain}/{total_expected_domain}")
        print(f"domain accuracy (per-sentence dominant): {correct_domain_per_sentence}/{total_expected_domain}")
        print(f"domain present in any step: {correct_domain_any_step}/{total_expected_domain}")
    if total_expected_intent:
        print(f"intent accuracy: {correct_intent}/{total_expected_intent}")
        print(f"intent accuracy (per-sentence dominant): {correct_intent_per_sentence}/{total_expected_intent}")
        print(f"intent present in any step: {correct_intent_any_step}/{total_expected_intent}")
    if parse_checked:
        print(f"sentence splitting ok: {parse_sentence_ok}/{parse_checked}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
