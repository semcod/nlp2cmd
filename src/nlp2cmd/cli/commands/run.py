"""
Run mode for NLP2CMD CLI.

Handles --run option: generate and execute command with error recovery.
Features:
- Generate command from natural language
- Execute with real-time output
- Detect errors and suggest recovery
- Interactive retry loop with LLM assistance
- Context-aware disambiguation from history
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Optional

from nlp2cmd.cli.helpers import (
    console,
    get_cached_syntax,
    print_yaml_block,
    _looks_like_log_input,
    _timed_default_yes,
    _timed_default_no,
    _fallback_open_url_from_query,
    ExecutionRunner,
)

try:
    from nlp2cmd.web_schema.form_data_loader import FormDataLoader
except Exception:  # pragma: no cover
    FormDataLoader = None  # type: ignore


def handle_run_mode(
    query: str,
    dsl: str,
    appspec: Optional[Path],
    auto_confirm: bool,
    no_submit: bool,
    execute_web: bool,
    auto_install: bool,
    auto_repair: bool,
    only_output: bool = False,
    verbose: bool = False,
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
    
    # Verbose logging setup
    def _verbose_log(msg: str, data: Any = None):
        if verbose:
            print_yaml_block({"verbose": msg, "data": data}, console=console)
    
    _verbose_log("handle_run_mode started", {"query": query, "dsl": dsl})
    
    from nlp2cmd.generation.pipeline import RuleBasedPipeline
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
    from nlp2cmd import NLP2CMD, AppSpecAdapter, BrowserAdapter
    from nlp2cmd.web_schema.form_data_loader import FormDataLoader

    history_selected_command: str | None = None

    if not only_output:
        print(f"```bash")
        # Use cached syntax highlighting for better performance
        syntax = get_cached_syntax(f"# 🚀 Run Mode: {query}", "bash", theme="monokai", line_numbers=False)
        console.print(syntax)
        print(f"```")
        print()
    
    # Step 0: Check for similar queries in history (disambiguation)
    _verbose_log("Step 0: Checking history for similar queries")
    try:
        from nlp2cmd.context.disambiguator import CommandDisambiguator

        disambiguator = CommandDisambiguator(console=console)
        result = disambiguator.disambiguate(query, auto_select=auto_confirm)
        
        _verbose_log("History check result", {
            "from_history": result.from_history,
            "selected_command": bool(result.selected_command),
        })

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
    except Exception as e:
        _verbose_log("History check failed", {"error": str(e)})

    # If the user selected a previous command from history, execute it directly.
    if history_selected_command:
        _verbose_log("Using history command", {"command": history_selected_command[:100]})
        cmd = history_selected_command.strip()

        # If it's dom_dql.v1 JSON, prefer executing via Playwright PipelineRunner.
        try:
            payload = json.loads(cmd)
        except Exception:
            payload = None

        if isinstance(payload, dict) and payload.get("dsl") == "dom_dql.v1":
            requires_web_execution = True
            _verbose_log("Detected dom_dql.v1 command from history")

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

            if ExecutionRunner is None:
                from nlp2cmd.execution import ExecutionRunner as _ExecutionRunner
                runner_cls = _ExecutionRunner
            else:
                runner_cls = ExecutionRunner

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
                from nlp2cmd.generation.auto_repair import CommandRepairer, should_attempt_repair
                import asyncio

                llm = LiteLLMClient()
                repairer = CommandRepairer(llm_client=llm)
                result = pipeline.process_with_llm_repair(
                    query, llm_client=llm, persist=True, max_repairs=1,
                )
                
                # If pipeline repair fails, try command-level repair
                if not result.success and result.command:
                    context = {
                        "domain": result.domain,
                        "intent": result.intent,
                        "confidence": getattr(result, "confidence", 0.0),
                    }
                    
                    # Simulate execution to get error
                    try:
                        import subprocess
                        proc = subprocess.run(
                            result.command,
                            shell=True,
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )
                        if proc.returncode != 0:
                            if should_attempt_repair(proc.stderr, context):
                                repair_result = repairer.repair_command(
                                    result.command,
                                    proc.stderr,
                                    context,
                                )
                                if repair_result["success"]:
                                    result.command = repair_result["command"]
                                    result.success = True
                    except subprocess.TimeoutExpired:
                        pass  # Command might be valid but long-running
                    except Exception:
                        pass  # Other errors, skip repair
                        
            except Exception:
                pass

        if result.success:
            command = result.command
            detected_domain = result.domain
            detected_intent = result.intent

            # Multi-step ActionPlan execution (browser + prompts + file updates)
            if detected_domain == "multi_step" and getattr(result, "action_plan", None):
                if not only_output:
                    print_yaml_block(
                        {
                            "status": "multistep_plan_detected",
                            "intent": detected_intent,
                            "steps": [
                                getattr(s, "action", "")
                                for s in (getattr(result.action_plan, "steps", None) or [])
                            ],
                        },
                        console=console,
                    )

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
                    return

                try:
                    from nlp2cmd.pipeline_runner import PipelineRunner
                    pw_runner = PipelineRunner(headless=False)
                    plan_res = pw_runner.execute_action_plan(
                        result.action_plan,
                        dry_run=False,
                        confirm=bool(auto_confirm),
                    )
                    if not only_output:
                        print_yaml_block(
                            {
                                "status": "multistep_plan_completed",
                                "success": bool(plan_res.success),
                                "error": str(plan_res.error or "") if not plan_res.success else "",
                            },
                            console=console,
                        )
                    return
                except Exception as e:
                    if not only_output:
                        print_yaml_block(
                            {
                                "status": "multistep_plan_failed",
                                "error": str(e),
                            },
                            console=console,
                        )
                    return
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
    _verbose_log("Step 4: Detecting browser command indicators")
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
    extract_article_keywords = loader.get_nlp_keywords("extract_article")
    extract_companies_keywords = loader.get_nlp_keywords("extract_companies")
    save_to_file_keywords = loader.get_nlp_keywords("save_to_file")
    save_filename_patterns = loader.get_save_filename_patterns()

    query_lower = query.lower()
    has_typing = any(kw in query_lower for kw in typing_keywords)
    has_clicking = any(kw in query_lower for kw in clicking_keywords)
    has_form = any(kw in query_lower for kw in form_keywords)
    has_extract_article = any(kw in query_lower for kw in extract_article_keywords)
    has_extract_companies = any(kw in query_lower for kw in extract_companies_keywords)
    has_save_keyword = any(kw in query_lower for kw in save_to_file_keywords)
    
    # Also detect save if a filename pattern is found
    has_save_filename = False
    for pattern in save_filename_patterns:
        if re.search(pattern, query, flags=re.IGNORECASE):
            has_save_filename = True
            break
    # Fallback: check for .csv, .txt, .json extensions
    if not has_save_filename:
        if re.search(r'[\w._-]+\.(csv|txt|json|md|yaml|yml)', query, flags=re.IGNORECASE):
            has_save_filename = True
    
    has_save_to_file = has_save_keyword or has_save_filename
    
    _verbose_log("Keyword detection results", {
        "has_typing": has_typing,
        "has_clicking": has_clicking,
        "has_form": has_form,
        "has_extract_article": has_extract_article,
        "has_extract_companies": has_extract_companies,
        "has_save_to_file": has_save_to_file,
        "detected_domain": detected_domain,
        "detected_intent": detected_intent,
    })

    if dsl == "auto":
        if detected_domain == "shell" and detected_intent in ("open_url", "search_web"):
            is_browser_command = True
            detected_has_typing = has_typing or has_clicking or has_form or has_extract_article or has_extract_companies
            _verbose_log("Detected as shell browser command", {"has_typing": detected_has_typing})
            if detected_has_typing and not execute_web:
                if not only_output:
                    print_yaml_block(
                        {"status": "browser_automation_auto_enabled", "reason": "detected_typing_clicking_or_form_action"},
                        console=console,
                    )
                execute_web = True
        elif detected_domain == "browser":
            is_browser_command = True
            detected_has_typing = has_typing or has_clicking or has_form or has_extract_article or has_extract_companies
            _verbose_log("Detected as browser domain command", {"has_typing": detected_has_typing})
            # Enable browser automation for ANY browser domain command when in run mode
            # This allows simple navigation (open URL) to use Playwright, not just xdg-open
            if not execute_web:
                if not only_output:
                    if detected_has_typing:
                        print_yaml_block(
                            {"status": "browser_automation_auto_enabled", "reason": "detected_browser_domain_and_form_or_typing_or_clicking"},
                            console=console,
                        )
                    else:
                        print_yaml_block(
                            {"status": "browser_automation_auto_enabled", "reason": "detected_browser_domain_in_run_mode"},
                            console=console,
                        )
                execute_web = True
    elif dsl == "browser":
        is_browser_command = True
        detected_has_typing = True
        _verbose_log("DSL explicitly set to browser")
        if not execute_web:
            execute_web = True
    
    _verbose_log("Browser detection complete", {
        "is_browser_command": is_browser_command,
        "execute_web": execute_web,
        "detected_has_typing": detected_has_typing,
    })

    # Step 5: Execute
    if ExecutionRunner is None:
        from nlp2cmd.execution import ExecutionRunner as _ExecutionRunner
        runner_cls = _ExecutionRunner
    else:
        runner_cls = ExecutionRunner

    runner = runner_cls(
        console=console,
        auto_confirm=auto_confirm,
        max_retries=3,
        plain_output=only_output,
    )

    if is_browser_command and execute_web:
        if not only_output:
            console.print("\n[cyan]Using Playwright for browser automation...[/cyan]")
            print_yaml_block(
                {
                    "status": "run_mode_flags",
                    "auto_confirm": bool(auto_confirm),
                    "no_submit": bool(no_submit),
                    "execute_web": bool(execute_web),
                },
                console=console,
            )

        from nlp2cmd.utils.playwright_installer import ensure_playwright_installed

        if not ensure_playwright_installed(console=console, auto_install=auto_install):
            if not only_output:
                print_yaml_block({"status": "browser_automation_skipped", "reason": "playwright_not_available"}, console=console)
            _fallback_open_url_from_query(query)
            return

        try:
            _verbose_log("Starting browser automation try block")
            print("DEBUG: Entering try block", file=sys.stderr, flush=True)
            browser_adapter = BrowserAdapter()
            _verbose_log("BrowserAdapter created successfully")
            nlp_browser = NLP2CMD(adapter=browser_adapter)
            _verbose_log("NLP2CMD created successfully")
            
            _verbose_log("Transforming query to IR via BrowserAdapter")
            ir = nlp_browser.transform_ir(query)
            
            _verbose_log("BrowserAdapter transformation result", {
                "action_id": getattr(ir, "action_id", None),
                "dsl_kind": getattr(ir, "dsl_kind", None),
                "dsl_preview": str(getattr(ir, "dsl", "")[:200]),
                "confidence": getattr(ir, "confidence", 0),
            })

            if no_submit:
                try:
                    dsl_payload = json.loads(getattr(ir, "dsl", "") or "")
                except Exception as e:
                    dsl_payload = None
                    if not only_output:
                        print_yaml_block(
                            {
                                "status": "no_submit_json_loads_error",
                                "error": str(e),
                                "error_type": str(type(e).__name__),
                            },
                            console=console,
                        )

                if dsl_payload is None and not only_output:
                    try:
                        raw_dsl = getattr(ir, "dsl", None)
                        raw_preview = str(raw_dsl)[:300] if raw_dsl is not None else ""
                    except Exception:
                        raw_preview = ""
                    print_yaml_block(
                        {
                            "status": "no_submit_parse_failed",
                            "dsl_type": str(type(getattr(ir, "dsl", None)).__name__),
                            "dsl_preview": raw_preview,
                        },
                        console=console,
                    )

                if isinstance(dsl_payload, dict):
                    actions = dsl_payload.get("actions")
                    is_dom_payload = (
                        dsl_payload.get("dsl") == "dom_dql.v1"
                        or isinstance(actions, list)
                    )

                    if not only_output:
                        try:
                            actions_len = len(actions) if isinstance(actions, list) else None
                        except Exception:
                            actions_len = None
                        print_yaml_block(
                            {
                                "status": "no_submit_payload_info",
                                "dsl": dsl_payload.get("dsl"),
                                "is_dom_payload": bool(is_dom_payload),
                                "actions_type": str(type(actions).__name__),
                                "actions_len": actions_len,
                            },
                            console=console,
                        )

                    if (not is_dom_payload) and (not only_output):
                        print_yaml_block(
                            {
                                "status": "no_submit_payload_not_dom",
                                "dsl": dsl_payload.get("dsl"),
                                "has_actions": bool(isinstance(actions, list)),
                            },
                            console=console,
                        )
                    if is_dom_payload and isinstance(actions, list):
                        filtered: list[dict[str, Any]] = []
                        for a in actions:
                            if not isinstance(a, dict):
                                continue

                            act = str(a.get("action") or "")
                            if act == "submit":
                                continue
                            if act == "press" and str(a.get("key") or "") in {"Enter", "Return"}:
                                continue

                            filtered.append(a)

                        dsl_payload["actions"] = filtered
                        ir.dsl = json.dumps(dsl_payload, ensure_ascii=False)

                        if not only_output:
                            try:
                                filtered_actions = [
                                    a.get("action")
                                    for a in dsl_payload.get("actions")
                                    if isinstance(a, dict)
                                ]
                            except Exception:
                                filtered_actions = []
                            print_yaml_block(
                                {
                                    "status": "no_submit_filtered_actions",
                                    "actions_count": int(len(filtered_actions)),
                                    "actions": filtered_actions,
                                },
                                console=console,
                            )

            if not only_output:
                import json as _json
                payload_info: dict[str, Any] = {
                    "status": "actions",
                    "action_id": getattr(ir, "action_id", ""),
                    "dsl_kind": getattr(ir, "dsl_kind", ""),
                    "confidence": getattr(ir, "confidence", 0.0),
                    "explanation": getattr(ir, "explanation", ""),
                }
                try:
                    dsl_payload = _json.loads(getattr(ir, "dsl", "") or "")
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
            pw_runner = PipelineRunner(headless=True)  # Force headless for testing
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
                        timed_prompt = "\n[yellow]This action will submit a form. Proceed? (auto-N in 1s; Enter=choose):[/yellow] "
                        full_prompt = "\n[yellow]This action will submit a form. Proceed? [[y/N/a(always)]]:[/yellow] "
                    elif reason == "press_enter":
                        timed_prompt = "\n[yellow]Press Enter action. Proceed? (auto-N in 1s; Enter=choose):[/yellow] "
                        full_prompt = "\n[yellow]Press Enter action. Proceed? [[y/N/a(always)]]:[/yellow] "
                    else:
                        timed_prompt = "\n[yellow]Confirm action? (auto-N in 1s):[/yellow] "
                        full_prompt = "\n[yellow]Confirm action? [[y/N]]:[/yellow] "

                    resp = _timed_default_no(timed_prompt=timed_prompt, full_prompt=full_prompt)
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
    no_submit: bool,
    execute_web: bool,
    auto_install: bool,
    auto_repair: bool,
    only_output: bool = False,
    verbose: bool = False,
) -> None:
    handle_run_mode(
        query,
        dsl=dsl,
        appspec=appspec,
        auto_confirm=auto_confirm,
        no_submit=no_submit,
        execute_web=execute_web,
        auto_install=auto_install,
        auto_repair=auto_repair,
        only_output=only_output,
        verbose=verbose,
    )
    return


def _suggest_next_steps(
    original_query: str,
    command: str,
    result,
    runner,
):
    """Suggest next steps based on error context."""
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
                    from nlp2cmd.generation.pipeline import RuleBasedPipeline
                    pipeline = RuleBasedPipeline()
                    new_result = pipeline.process(new_query)
                    if new_result.success:
                        runner.run_with_recovery(new_result.command, new_query)
                    else:
                        console.print(f"[red]Could not generate command from: {new_query}[/red]")
