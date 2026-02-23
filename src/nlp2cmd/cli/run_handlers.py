"""
Run mode handlers for NLP2CMD CLI.

Handles command generation and execution with error recovery.
"""

from __future__ import annotations

import json
import shlex
import sys
import time
from pathlib import Path
from typing import Any, Optional

try:
    from rich.console import Console
except Exception:  # pragma: no cover
    class Console:  # type: ignore
        def print(self, *args, **kwargs):
            print(*args, **kwargs)

        def input(self, *args, **kwargs):
            return ""

from nlp2cmd.cli.syntax_cache import get_cached_syntax
from nlp2cmd.cli.markdown_output import print_yaml_block
from nlp2cmd.generation.pipeline import RuleBasedPipeline


def handle_run_mode(
    query: str,
    dsl: str,
    appspec: Optional[Path],
    auto_confirm: bool,
    execute_web: bool,
    auto_install: bool,
    auto_repair: bool,
    only_output: bool = False,
):
    """
    Handle --run option: generate and execute command with error recovery.
    
    Features:
    - Generate command from natural language
    - Execute with real-time output
    - Detect errors and suggest recovery
    - Interactive retry loop with LLM assistance
    - Context-aware disambiguation from history
    """
    from nlp2cmd import NLP2CMD
    from nlp2cmd.adapters import (
        SQLAdapter,
        ShellAdapter,
        DockerAdapter,
        KubernetesAdapter,
        DQLAdapter,
        AppSpecAdapter,
        BrowserAdapter,
    )
    from nlp2cmd.web_schema.form_data_loader import FormDataLoader

    console = Console()
    history_selected_command: str | None = None

    if not only_output:
        print(f"```bash")
        # Use cached syntax highlighting for better performance
        syntax = get_cached_syntax(f"# 🚀 Run Mode: {query}", "bash", theme="monokai", line_numbers=False)
        console.print(syntax)
        print(f"```")
        print()
    
    # Step 0: Check for similar queries in history (disambiguation)
    # - interactive mode: ask user to pick an option
    # - auto-confirm mode: auto-select only if similarity is very high
    try:
        from nlp2cmd.context.disambiguator import CommandDisambiguator

        disambiguator = CommandDisambiguator(console=console)
        result = disambiguator.disambiguate(query, auto_select=auto_confirm)

        if result.from_history and result.selected_command:
            if not only_output:
                print_yaml_block(
                    {
                        "status": "using_previous_command_from_history",
                        "selected_query": result.selected_query,
                    },
                    console=console,
                )
            query = result.selected_query
            history_selected_command = result.selected_command
    except Exception:
        pass

    # If the user selected a previous command from history, execute it directly.
    # This avoids regenerating a simpler command (e.g., browser/navigate) and losing
    # multi-step dom_dql.v1 sequences (fill_form/submit/etc.).
    if history_selected_command:
        cmd = history_selected_command.strip()

        # If it's dom_dql.v1 JSON, prefer executing via Playwright PipelineRunner.
        try:
            import json

            payload = json.loads(cmd)
        except Exception:
            payload = None

        if isinstance(payload, dict) and payload.get("dsl") == "dom_dql.v1":
            requires_web_execution = True

            confirmed_for_web = bool(auto_confirm or execute_web)

            if requires_web_execution and not execute_web and not auto_confirm:
                console.print(
                    "\n[yellow]Selected history command is dom_dql.v1 and requires browser automation (Playwright).[/yellow]"
                )
                resp = console.input("[yellow]Execute via Playwright now? [Y/n]: [/yellow]").strip().lower()
                if resp in {"n", "no", "nie"}:
                    console.print("[yellow]Cancelled by user[/yellow]")
                    return
                confirmed_for_web = True

            if not only_output:
                print(f"```bash")
                syntax = get_cached_syntax("# Using command from history\n " + cmd, "bash", theme="monokai", line_numbers=False)
                console.print(syntax)
                print(f"```")
                print()

            try:
                from nlp2cmd.ir import ActionIR
                from nlp2cmd.pipeline_runner import PipelineRunner

                # Ensure Playwright (and browsers) are installed.
                from nlp2cmd.utils.playwright_installer import ensure_playwright_installed

                if not ensure_playwright_installed(console=console, auto_install=auto_install):
                    if not only_output:
                        print_yaml_block(
                            {
                                "status": "browser_automation_skipped",
                                "reason": "playwright_not_available",
                            },
                            console=console,
                        )
                    _fallback_open_url_from_query(query)
                    return

                ir = ActionIR(
                    action_id=str(payload.get("action") or payload.get("actions") or "history.dom"),
                    dsl=cmd,
                    dsl_kind="dom",  # type: ignore[arg-type]
                    params={},
                    output_format="raw",  # type: ignore[arg-type]
                    confidence=1.0,
                    explanation="history command: dom_dql.v1",
                    metadata={},
                )

                runner = PipelineRunner(headless=False)
                res = runner.run(ir, dry_run=False, confirm=confirmed_for_web)
                if res.success:
                    if not only_output:
                        console.print(f"\n✅ Executed history web action in {res.duration_ms:.1f}ms")
                    return

                # Retry with explicit confirmation if required.
                if (not res.success) and isinstance(res.data, dict) and res.data.get("requires_confirmation"):
                    res2 = runner.run(ir, dry_run=False, confirm=True)
                    if res2.success:
                        if not only_output:
                            console.print(f"\n✅ Executed history web action in {res2.duration_ms:.1f}ms")
                        return
                    res = res2

                if not only_output:
                    console.print(f"\n[red]✗ Failed to execute history command: {res.error}[/red]")
                return
            except Exception as e:
                if not only_output:
                    console.print(f"\n[red]✗ Failed to execute history command: {e}[/red]")
                return

        # Otherwise treat it as a shell command and execute via existing runner.
        if cmd:
            if not only_output:
                print(f"```bash")
                syntax = get_cached_syntax("# Using command from history\n " + cmd, "bash", theme="monokai", line_numbers=False)
                console.print(syntax)
                print(f"```")
                print()

            try:
                from nlp2cmd.execution import ExecutionRunner
                runner_cls = ExecutionRunner
            except Exception:
                from nlp2cmd.execution import ExecutionRunner as _ExecutionRunner
                runner_cls = _ExecutionRunner

            runner = runner_cls(
                console=console,
                auto_confirm=auto_confirm,
                max_retries=3,
                plain_output=only_output,
            )
            runner.run_with_recovery(cmd, query)
            return
    
    # Step 1: Generate command
    if not only_output:
        console.print("\n[dim]Generating command...[/dim]")
    
    adapter_map = {
        "sql": lambda: SQLAdapter(),
        "shell": lambda: ShellAdapter(),
        "docker": lambda: DockerAdapter(),
        "kubernetes": lambda: KubernetesAdapter(),
        "dql": lambda: DQLAdapter(),
        "appspec": lambda: AppSpecAdapter(appspec_path=str(appspec) if appspec else None),
        "browser": lambda: BrowserAdapter(),
    }

    # Step 2: Detect domain/intent and generate command
    command = None
    detected_domain = "unknown"
    detected_intent = "unknown"

    if dsl == "auto":
        pipeline = RuleBasedPipeline()
        result = pipeline.process(query)

        if (not _looks_like_log_input(query)) and (not result.success) and auto_repair:
            try:
                from nlp2cmd.generation.llm_simple import LiteLLMClient
                import asyncio

                llm = LiteLLMClient()
                result = pipeline.process_with_llm_repair(
                    query, llm_client=llm, persist=True, max_repairs=1,
                )
            except Exception:
                pass

        if result.success:
            command = result.command
            detected_domain = result.domain
            detected_intent = result.intent
        else:
            if only_output:
                sys.stderr.write("nlp2cmd: could not generate executable command\n")
                raise SystemExit(1)
            console.print(f"[red]✗ Could not generate command: {result.errors}[/red]")
            return
    else:
        adapter = adapter_map.get(dsl, lambda: ShellAdapter())()
        nlp = NLP2CMD(adapter=adapter)
        transform_result = nlp.transform(query)
        command = transform_result.command
        detected_domain = dsl
        detected_intent = getattr(getattr(transform_result, "plan", None), "intent", "unknown")

    if not only_output:
        print_yaml_block(
            {"status": "detected", "domain": detected_domain, "intent": detected_intent},
            console=console,
        )

    # Step 3: Handle SQL (no execution)
    if detected_domain == "sql":
        if only_output:
            sql_text = (command or "").rstrip() + "\n"
            if sql_text.strip():
                sys.stdout.write(sql_text)
            sys.stderr.write("Run Mode executes shell commands; SQL is not executed automatically.\n")
        else:
            print(f"```sql")
            syntax = get_cached_syntax(command, "sql", theme="monokai", line_numbers=False)
            console.print(syntax)
            print(f"```")
            console.print("[yellow]SQL is not executed automatically. Use your database client.[/yellow]")
        return

    # Step 4: Detect browser commands with typing/form actions
    is_browser_command = False
    detected_has_typing = False

    loader = FormDataLoader()
    typing_keywords = loader.get_nlp_keywords("typing")
    clicking_keywords = loader.get_nlp_keywords("clicking")
    form_keywords = FormDataLoader.dedupe_selectors([
        *loader.get_nlp_keywords("form"),
        *loader.get_nlp_keywords("submit"),
        *loader.get_nlp_keywords("fill_form_phrases"),
        *loader.get_nlp_keywords("press_enter"),
    ])

    query_lower = query.lower()
    has_typing = any(kw in query_lower for kw in typing_keywords)
    has_clicking = any(kw in query_lower for kw in clicking_keywords)
    has_form = any(kw in query_lower for kw in form_keywords)

    if dsl == "auto":
        if detected_domain == "shell" and detected_intent in ("open_url", "search_web"):
            is_browser_command = True
            detected_has_typing = has_typing or has_clicking or has_form
            if detected_has_typing and not execute_web:
                if not only_output:
                    print_yaml_block(
                        {"status": "browser_automation_auto_enabled", "reason": "detected_typing_clicking_or_form_action"},
                        console=console,
                    )
                execute_web = True
    elif dsl == "browser":
        is_browser_command = True
        detected_has_typing = True
        if not execute_web:
            execute_web = True

    # Step 5: Execute
    try:
        from nlp2cmd.execution import ExecutionRunner
        runner_cls = ExecutionRunner
    except Exception:
        from nlp2cmd.execution import ExecutionRunner as _ExecutionRunner
        runner_cls = ExecutionRunner

    runner = runner_cls(
        console=console,
        auto_confirm=auto_confirm,
        max_retries=3,
        plain_output=only_output,
    )

    if is_browser_command and execute_web and detected_has_typing:
        if not only_output:
            console.print("\n[cyan]Using Playwright for browser automation...[/cyan]")

        from nlp2cmd.utils.playwright_installer import ensure_playwright_installed

        if not ensure_playwright_installed(console=console, auto_install=auto_install):
            if not only_output:
                print_yaml_block({"status": "browser_automation_skipped", "reason": "playwright_not_available"}, console=console)
            _fallback_open_url_from_query(query)
            return

        try:
            browser_adapter = BrowserAdapter()
            nlp_browser = NLP2CMD(adapter=browser_adapter)
            ir = nlp_browser.transform_ir(query)

            if not only_output:
                payload_info: dict[str, Any] = {
                    "status": "actions",
                    "action_id": getattr(ir, "action_id", ""),
                    "dsl_kind": getattr(ir, "dsl_kind", ""),
                    "confidence": getattr(ir, "confidence", 0.0),
                    "explanation": getattr(ir, "explanation", ""),
                }
                try:
                    dsl_payload = json.loads(getattr(ir, "dsl", "") or "")
                    if isinstance(dsl_payload, dict):
                        if isinstance(dsl_payload.get("url"), str):
                            payload_info["url"] = dsl_payload["url"]
                        actions = dsl_payload.get("actions")
                        if isinstance(actions, list):
                            payload_info["actions_count"] = len(actions)
                            payload_info["actions"] = [a.get("action") for a in actions if isinstance(a, dict)]
                except Exception:
                    pass
                print_yaml_block(payload_info, console=console)

            from nlp2cmd.pipeline_runner import PipelineRunner
            pw_runner = PipelineRunner(headless=False)
            pw_result = pw_runner.run(ir, dry_run=False, confirm=auto_confirm)

            if (not pw_result.success) and isinstance(pw_result.data, dict) and pw_result.data.get("requires_confirmation"):
                reason = str(pw_result.data.get("confirmation_reason") or "unknown")
                url_for_confirm = str(pw_result.data.get("url") or "")
                data_loader_for_confirm = FormDataLoader(site=url_for_confirm) if url_for_confirm else FormDataLoader()

                approved = False
                if reason in {"submit", "press_enter"}:
                    approved = data_loader_for_confirm.get_site_approval(reason)

                if not approved and not auto_confirm:
                    if reason == "submit":
                        timed_prompt = "\n[yellow]This action will submit a form. Proceed? (auto-Y in 1s; Enter=choose):[/yellow] "
                        full_prompt = "\n[yellow]This action will submit a form. Proceed? [[y/N/a(always)]]:[/yellow] "
                    elif reason == "press_enter":
                        timed_prompt = "\n[yellow]Press Enter action. Proceed? (auto-Y in 1s; Enter=choose):[/yellow] "
                        full_prompt = "\n[yellow]Press Enter action. Proceed? [[y/N/a(always)]]:[/yellow] "
                    else:
                        timed_prompt = "\n[yellow]Confirm action? (auto-Y in 1s):[/yellow] "
                        full_prompt = "\n[yellow]Confirm action? [[y/N]]:[/yellow] "

                    resp = _timed_default_yes(timed_prompt=timed_prompt, full_prompt=full_prompt)
                    if resp in {"a", "always"} and reason in {"submit", "press_enter"}:
                        data_loader_for_confirm.set_site_approval(reason, True)
                        approved = True
                    elif resp in {"y", "yes", "tak"}:
                        approved = True

                if not approved and not auto_confirm:
                    if not only_output:
                        console.print("[yellow]Cancelled by user[/yellow]")
                    return

                pw_result = pw_runner.run(ir, dry_run=False, confirm=True)

            if pw_result.success:
                if not only_output:
                    print_yaml_block(
                        {
                            "status": "browser_automation_completed",
                            "success": True,
                            "duration_ms": float(pw_result.duration_ms),
                        },
                        console=console,
                    )
                return

            if not only_output:
                print_yaml_block({"status": "browser_automation_failed", "error": str(pw_result.error or "")}, console=console)
            _fallback_open_url_from_query(query)
            return
        except Exception as e:
            if not only_output:
                print_yaml_block({"status": "playwright_error", "error": str(e)}, console=console)
            _fallback_open_url_from_query(query)
            return
    else:
        # Execute shell command with recovery
        if not only_output:
            print(f"```bash")
            syntax = get_cached_syntax(command, "bash", theme="monokai", line_numbers=False)
            console.print(syntax)
            print(f"```")
            print()

        exec_result = runner.run_with_recovery(command, query)

        if not exec_result.success:
            if exec_result.error_context:
                _suggest_next_steps(query, command, exec_result, runner)


def _handle_run_query(
    query: str,
    *,
    dsl: str,
    appspec: Optional[Path],
    auto_confirm: bool,
    execute_web: bool,
    auto_install: bool,
    auto_repair: bool,
    only_output: bool = False,
) -> None:
    handle_run_mode(
        query,
        dsl=dsl,
        appspec=appspec,
        auto_confirm=auto_confirm,
        execute_web=execute_web,
        auto_install=auto_install,
        auto_repair=auto_repair,
        only_output=only_output,
    )
    return


def _looks_like_log_input(text: str) -> bool:
    import re
    
    if not text:
        return False

    if "\n" not in text:
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


def _timed_default_yes(
    *,
    timed_prompt: str,
    full_prompt: str,
    timeout_s: float = 1.0,
) -> str:
    import select
    import sys
    
    console = Console()
    
    if not sys.stdin.isatty():
        return "y"

    console.print(timed_prompt, end="")
    _system_beep()
    try:
        ready, _, _ = select.select([sys.stdin], [], [], timeout_s)
    except Exception:
        ready = []

    if not ready:
        console.print("y")
        return "y"

    try:
        line = sys.stdin.readline()
    except Exception:
        line = ""

    resp = (line or "").strip().lower()
    if resp:
        return resp

    resp = console.input(full_prompt).strip().lower()
    return resp or "y"


def _system_beep() -> None:
    try:
        sys.stdout.write("\a")
        sys.stdout.flush()
    except Exception:
        return


def _suggest_next_steps(
    original_query: str,
    command: str,
    result,
    runner,
):
    """Suggest next steps based on error context."""
    console = Console()
    error = (result.stderr or result.stdout or "").lower()
    
    suggestions = []
    
    if "command not found" in error:
        cmd_parts = command.split()
        if cmd_parts:
            tool = cmd_parts[0]
            suggestions.append(f"Install missing tool: {tool}")
            suggestions.append("Check if the tool is in your PATH")
    
    if "permission denied" in error:
        suggestions.append(f"Try with sudo: sudo {command}")
    
    if "connection refused" in error or "could not connect" in error:
        suggestions.append("Check if the target service is running")
        suggestions.append("Verify the hostname/port is correct")
    
    if "no such file" in error:
        suggestions.append("Verify the file/directory path exists")
    
    if "playwright" in error:
        suggestions.append("Install Playwright: pip install playwright && playwright install")
    
    if suggestions:
        console.print("\n[yellow]💡 Suggestions:[/yellow]")
        for i, s in enumerate(suggestions, 1):
            console.print(f"  {i}. {s}")
        
        console.print("\n[cyan]Would you like to try another command? [y/N]:[/cyan] ", end="")
        response = console.input().strip().lower()
        
        if response in ("y", "yes", "tak"):
            new_query = console.input("[bold green]Enter new query or command: [/bold green]").strip()
            if new_query:
                if new_query.startswith("!"):
                    # Direct command execution
                    runner.run_with_recovery(new_query[1:].strip(), original_query)
                else:
                    # Generate new command from query
                    pipeline = RuleBasedPipeline()
                    new_result = pipeline.process(new_query)
                    if new_result.success:
                        runner.run_with_recovery(new_result.command, new_query)
                    else:
                        console.print(f"[red]Could not generate command from: {new_query}[/red]")


def _fallback_open_url_from_query(query: str) -> None:
    from nlp2cmd.adapters import BrowserAdapter
    from nlp2cmd.execution import open_url

    console = Console()

    try:
        url = BrowserAdapter._extract_url(query)
    except Exception:
        url = None
    if isinstance(url, str) and url:
        res = open_url(url, use_webbrowser=False)
        if res.success:
            console.print(f"\n[yellow]Opened URL without Playwright: {url}[/yellow]")
