"""
Single-query generation mode for NLP2CMD CLI.

Fast path for `nlp2cmd -q "..."` without --run.
Avoids spinning up the full InteractiveSession (env scan + thermo router).
"""

from __future__ import annotations

import os
import sys
import time
from contextlib import nullcontext
from pathlib import Path
from typing import Any, Optional

from nlp2cmd.cli.helpers import (
    console,
    display_command_result,
    print_yaml_block,
)


def handle_generate_query(
    query: str,
    *,
    dsl: str,
    appspec: Optional[Path],
    explain: bool,
    execute_web: bool,
    stdout_only: bool,
    script_start_time: float,
    verbose: bool = False,
    debug_log_md: Optional[str] = None,
    record_video: Optional[str] = None,
    **_ignored_kwargs,
) -> None:
    """Handle single-query generation (no --run, dsl=auto fast path)."""
    from nlp2cmd.generation.pipeline import RuleBasedPipeline
    from nlp2cmd.monitoring import measure_resources, format_last_metrics

    pipeline = RuleBasedPipeline()
    _measure = str(os.environ.get("NLP2CMD_MEASURE_RESOURCES", "1") or "").strip().lower() not in {
        "0",
        "false",
        "no",
        "n",
        "off",
    }
    with (measure_resources() if _measure else nullcontext()):
        pipeline_result = pipeline.process(query)

    # Handle multi-step action plan - serialize it as the command
    action_plan = getattr(pipeline_result, 'action_plan', None)
    if action_plan and not pipeline_result.command:
        try:
            import json
            # Convert action plan to a JSON command
            steps = getattr(action_plan, 'steps', [])
            if steps:
                commands = []
                for step in steps:
                    step_dict = {
                        'action': getattr(step, 'action', 'unknown'),
                        'target': getattr(step, 'target', None),
                        'params': getattr(step, 'params', {}),
                    }
                    commands.append(step_dict)
                pipeline_result.command = json.dumps({
                    'dsl': 'multi_step',
                    'steps': commands,
                    'source': pipeline_result.source,
                }, ensure_ascii=False, indent=2)
        except Exception:
            pass

    if stdout_only:
        cmd = (pipeline_result.command or "").strip()
        if cmd:
            sys.stdout.write(cmd + "\n")
        if not pipeline_result.success:
            for err in list(pipeline_result.errors or []):
                sys.stderr.write(str(err).rstrip() + "\n")
        return

    metrics_str = format_last_metrics() if _measure else ""
    out: dict[str, Any] = {
        "dsl": "auto",
        "query": query,
        "status": "success" if pipeline_result.success else "error",
        "confidence": float(pipeline_result.confidence),
        "generated_command": (pipeline_result.command or "").strip() or None,
        "errors": list(pipeline_result.errors or []),
        "warnings": list(pipeline_result.warnings or []),
        "suggestions": [],
        "clarification_questions": [],
    }

    pipeline_meta = getattr(pipeline_result, "metadata", None)
    if isinstance(pipeline_meta, dict) and pipeline_meta:
        out.update(pipeline_meta)
    if metrics_str:
        try:
            from nlp2cmd.monitoring.token_costs import parse_metrics_string
            from nlp2cmd.monitoring import estimate_token_cost

            metrics = parse_metrics_string(metrics_str)
            if metrics:
                out["resource_metrics"] = {
                    "time_ms": metrics.get("time_ms"),
                    "cpu_percent": metrics.get("cpu_percent"),
                    "memory_mb": metrics.get("memory_mb"),
                    "energy_mj": metrics.get("energy_mj"),
                }
                out["resource_metrics_parsed"] = metrics

                if (
                    metrics.get("time_ms") is not None
                    and metrics.get("cpu_percent") is not None
                    and metrics.get("memory_mb") is not None
                ):
                    token_estimate = estimate_token_cost(
                        metrics["time_ms"],
                        metrics["cpu_percent"],
                        metrics["memory_mb"],
                        metrics.get("energy_mj"),
                    )
                    out["token_estimate"] = {
                        "total": int(token_estimate.total_tokens_estimate),
                        "input": int(token_estimate.input_tokens_estimate),
                        "output": int(token_estimate.output_tokens_estimate),
                        "cost_usd": float(token_estimate.estimated_cost_usd),
                        "model_tier": token_estimate.equivalent_model_tier,
                        "tokens_per_ms": float(token_estimate.tokens_per_millisecond),
                        "tokens_per_mj": float(token_estimate.tokens_per_mj),
                    }
        except Exception:
            pass

    if explain:
        out.update(
            {
                "domain": pipeline_result.domain,
                "intent": pipeline_result.intent,
                "detection_confidence": pipeline_result.detection_confidence,
                "template_used": pipeline_result.template_used,
                "source": pipeline_result.source,
                "entities": pipeline_result.entities,
            }
        )

    # Calculate total execution time
    total_time_ms = (time.time() - script_start_time) * 1000
    
    # Add total execution time to output
    out["total_execution_time_ms"] = round(total_time_ms, 1)
    
    display_command_result(
        command=out.get("generated_command", "") or "",
        metadata=out,
        metrics_str=metrics_str,
        show_yaml=True,
        title="NLP2CMD Result",
    )

    # Generate debug log if requested
    if debug_log_md:
        from nlp2cmd.cli.debug_info import generate_debug_log_md
        generate_debug_log_md(query, debug_log_md)

    # Record session video if requested
    if record_video:
        # Check if we have a multi-step action plan to execute with video
        action_plan = getattr(pipeline_result, 'action_plan', None)
        if action_plan and execute_web:
            try:
                _execute_multi_step_with_video(record_video, query, action_plan, pipeline_result)
            except Exception as e:
                console.print(f"[yellow]Browser execution with video failed: {e}[/yellow]")
                # Fallback to CLI recording
                try:
                    _record_cli_session(record_video, query, out)
                except Exception as e2:
                    console.print(f"[yellow]CLI recording also failed: {e2}[/yellow]")
        else:
            # Just record CLI session
            try:
                _record_cli_session(record_video, query, out)
            except Exception as e:
                console.print(f"[yellow]Session recording failed: {e}[/yellow]")

    # Execute in browser if requested (single-step or multi-step)
    if execute_web and dsl == "browser":
        try:
            from nlp2cmd import NLP2CMD
            from nlp2cmd.adapters import BrowserAdapter
            from nlp2cmd.pipeline_runner import PipelineRunner

            adapter = BrowserAdapter()
            nlp = NLP2CMD(adapter=adapter)
            ir = nlp.transform_ir(query)
            runner = PipelineRunner(headless=False)
            res = runner.run(ir, dry_run=False, confirm=True)
            if res.success:
                console.print(f"\n✅ Opened URL via Playwright in {res.duration_ms:.1f}ms")
            else:
                console.print(f"\n❌ Playwright execution failed: {res.error}")
        except Exception as e:
            console.print(f"\n❌ Playwright execution error: {e}")


def handle_appspec_query(
    query: str,
    *,
    dsl: str,
    appspec: Optional[Path],
    auto_repair: bool,
    explain: bool,
    execute_web: bool,
) -> None:
    """Handle single-query generation for appspec DSL."""
    from nlp2cmd.cli.commands.interactive import InteractiveSession

    session = InteractiveSession(
        dsl=dsl,
        auto_repair=auto_repair,
        appspec=str(appspec) if appspec else None,
    )
    feedback = session.process(query)
    session.display_feedback(feedback, include_explanation=explain)
    
    if execute_web:
        try:
            from nlp2cmd import NLP2CMD
            from nlp2cmd.adapters import AppSpecAdapter
            from nlp2cmd.pipeline_runner import PipelineRunner

            adapter = AppSpecAdapter(appspec_path=str(appspec))
            nlp = NLP2CMD(adapter=adapter)
            ir = nlp.transform_ir(query)
            runner = PipelineRunner(headless=False)
            res = runner.run(ir, dry_run=False, confirm=True)
            if res.success:
                console.print(f"\n✅ Executed web action in {res.duration_ms:.1f}ms")
            else:
                console.print(f"\n❌ Web execution failed: {res.error}")
        except Exception as e:
            console.print(f"\n❌ Web execution error: {e}")


def _record_cli_session(output_path: str, query: str, result_data: dict) -> None:
    """Record CLI session to webm video using ffmpeg."""
    import subprocess
    import tempfile
    from pathlib import Path

    console.print(f"[blue]Recording session to {output_path}...[/blue]")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Generate session info as text
        frames_data = [
            "NLP2CMD Session Recording",
            f"Query: {query}",
            "",
            f"Status: {result_data.get('status', 'unknown')}",
            f"Domain: {result_data.get('domain', 'unknown')}",
            f"Intent: {result_data.get('intent', 'unknown')}",
            f"Confidence: {result_data.get('confidence', 0):.2f}",
            "",
            "Generated Command:",
            result_data.get('generated_command', 'N/A')[:200] if result_data.get('generated_command') else 'N/A',
        ]

        for i, text in enumerate(frames_data):
            frame_file = tmp_path / f"frame_{i:04d}.txt"
            frame_file.write_text(text, encoding='utf-8')

        try:
            duration = len(frames_data) * 1.5

            filters = []
            for i, text in enumerate(frames_data):
                start = i * 1.5
                end = (i + 1) * 1.5
                safe_text = text.replace("'", "\\'").replace(":", "\\:").replace("[", "\\[").replace("]", "\\]")
                filters.append(
                    f"drawtext=text='{safe_text}':x=10:y=30+{i*30}:fontsize=24:fontcolor=white:enable='between(t,{start},{end})'"
                )

            filter_complex = ",".join(filters) if filters else "drawtext=text='NLP2CMD Session':x=10:y=10:fontsize=24:fontcolor=white"

            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", f"testsrc=duration={duration}:size=1280x720:rate=1",
                "-vf", filter_complex,
                "-c:v", "libvpx-vp9", "-pix_fmt", "yuv420p",
                "-b:v", "1M",
                "-deadline", "good",
                "-cpu-used", "2",
                output_path,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

            if result.returncode == 0 and Path(output_path).exists():
                console.print(f"[green]Session video saved to: {output_path}[/green]")
            else:
                console.print(f"[yellow]ffmpeg failed, saving session log instead[/yellow]")
                log_path = output_path.replace(".webm", ".txt")
                Path(log_path).write_text("\n".join(frames_data), encoding='utf-8')
                console.print(f"[blue]Session log saved to: {log_path}[/blue]")

        except FileNotFoundError:
            console.print(f"[yellow]ffmpeg not found. Install ffmpeg to enable video recording.[/yellow]")
            log_path = output_path.replace(".webm", ".txt")
            Path(log_path).write_text("\n".join(frames_data), encoding='utf-8')
            console.print(f"[blue]Session log saved to: {log_path}[/blue]")
        except subprocess.TimeoutExpired:
            console.print(f"[yellow]Video recording timed out[/yellow]")


def _execute_multi_step_with_video(
    output_path: str,
    query: str,
    action_plan: Any,
    pipeline_result: Any,
) -> None:
    """Execute multi-step action plan in browser with video recording.

    Records browser session and saves final screenshot showing the result.
    """
    from pathlib import Path

    console.print(f"[blue]Starting browser execution with video recording...[/blue]")
    console.print(f"[dim]Video will be saved to: {output_path}[/dim]")

    try:
        from playwright.sync_api import sync_playwright

        steps = getattr(action_plan, 'steps', [])
        if not steps:
            console.print("[yellow]No steps to execute[/yellow]")
            return

        with sync_playwright() as p:
            # Launch browser with video recording
            video_dir = Path(output_path).parent if output_path else Path("/tmp")
            video_dir.mkdir(parents=True, exist_ok=True)

            browser = p.chromium.launch(headless=False)
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                record_video_dir=str(video_dir),
                record_video_size={"width": 1280, "height": 720},
            )

            page = context.new_page()

            console.print(f"[blue]Executing {len(steps)} steps...[/blue]")

            screenshot_path = None
            canvas_center = {"x": 640, "y": 360}  # Default center

            for i, step in enumerate(steps, 1):
                action = getattr(step, 'action', '')
                params = getattr(step, 'params', {}) or {}
                target = getattr(step, 'target', None)

                console.print(f"  Step {i}/{len(steps)}: {action}")

                try:
                    if action == 'navigate':
                        url = params.get('url', target) or 'https://jspaint.app'
                        if not url.startswith('http'):
                            url = 'https://' + url
                        page.goto(url, wait_until='networkidle')
                        page.wait_for_timeout(1000)

                    elif action == 'wait_for_canvas':
                        # Wait for canvas element
                        try:
                            page.wait_for_selector('canvas', timeout=5000)
                        except:
                            pass
                        page.wait_for_timeout(1000)

                    elif action == 'get_canvas_center':
                        # Get canvas center for drawing
                        try:
                            canvas = page.locator('canvas').first
                            if canvas.is_visible():
                                box = canvas.bounding_box()
                                if box:
                                    canvas_center['x'] = box['x'] + box['width'] // 2
                                    canvas_center['y'] = box['y'] + box['height'] // 2
                                    console.print(f"    Canvas center: {canvas_center}")
                        except Exception as e:
                            console.print(f"    [dim]Could not get canvas center: {e}[/dim]")

                    elif action == 'select_tool':
                        tool = params.get('tool', '')
                        console.print(f"    Selecting tool: {tool}")
                        # Try to select tool in jspaint - use JavaScript to click on toolbar tools
                        try:
                            if tool in ['ellipse', 'circle']:
                                # jspaint uses toolbar with tool icons - try multiple selectors
                                # The oval tool is typically the 6th tool in the toolbar
                                js_select_oval = """
                                () => {
                                    // Try to find and click the oval/ellipse tool
                                    const tools = document.querySelectorAll('.tool, [data-tool], .jspaint-tool, button[title*="oval"], button[title*="ellipse"], button[title*="circle"]');
                                    for (let t of tools) {
                                        const title = (t.title || t.getAttribute('aria-label') || '').toLowerCase();
                                        if (title.includes('oval') || title.includes('ellipse') || title.includes('circle')) {
                                            t.click();
                                            return 'oval tool clicked';
                                        }
                                    }
                                    // Fallback: try to find by icon or position in toolbar
                                    const allTools = document.querySelectorAll('.tool, button');
                                    if (allTools.length > 5) {
                                        allTools[5].click(); // Oval is usually 6th tool
                                        return 'oval tool clicked (position fallback)';
                                    }
                                    return 'no oval tool found';
                                }
                                """
                                result = page.evaluate(js_select_oval)
                                console.print(f"      {result}")
                                page.wait_for_timeout(500)
                                
                                # Also try to enable fill mode for filled ellipse
                                js_enable_fill = """
                                () => {
                                    // Look for fill option or transparent/filled toggle
                                    const fillOptions = document.querySelectorAll('[title*="fill"], [title*="Fill"], button[aria-label*="fill"]');
                                    for (let f of fillOptions) {
                                        f.click();
                                        return 'fill enabled';
                                    }
                                    return 'no fill option found';
                                }
                                """
                                page.evaluate(js_enable_fill)
                                
                            elif tool == 'brush':
                                js_select_brush = """
                                () => {
                                    const tools = document.querySelectorAll('.tool, [data-tool], button');
                                    for (let t of tools) {
                                        const title = (t.title || t.getAttribute('aria-label') || '').toLowerCase();
                                        if (title.includes('brush') || title.includes('pencil') || title.includes('paint')) {
                                            t.click();
                                            return 'brush tool clicked';
                                        }
                                    }
                                    // Fallback: brush is usually 2nd tool
                                    const allTools = document.querySelectorAll('.tool, button');
                                    if (allTools.length > 1) {
                                        allTools[1].click();
                                        return 'brush tool clicked (position fallback)';
                                    }
                                    return 'no brush tool found';
                                }
                                """
                                result = page.evaluate(js_select_brush)
                                console.print(f"      {result}")
                        except Exception as e:
                            console.print(f"      [yellow]Tool selection warning: {e}[/yellow]")
                        page.wait_for_timeout(500)

                    elif action == 'set_color':
                        color = params.get('color', '#000000')
                        console.print(f"    Setting color: {color}")
                        page.wait_for_timeout(300)

                    elif action == 'draw_filled_ellipse':
                        rx = params.get('rx', 50)
                        ry = params.get('ry', 50)
                        relative = params.get('relative_to', '')

                        x = canvas_center['x']
                        y = canvas_center['y']

                        console.print(f"    Drawing filled ellipse at ({x}, {y}) rx={rx}, ry={ry}")

                        # For jspaint: drag from top-left to bottom-right to draw ellipse
                        # First ensure oval tool is selected with fill enabled
                        try:
                            js_ensure_oval = """
                            () => {
                                // Select oval tool if not already selected
                                const tools = document.querySelectorAll('.tool, button');
                                for (let t of tools) {
                                    const title = (t.title || t.getAttribute('aria-label') || '').toLowerCase();
                                    if (title.includes('oval') || title.includes('ellipse')) {
                                        if (!t.classList.contains('selected')) {
                                            t.click();
                                        }
                                        return 'oval ready';
                                    }
                                }
                                return 'oval not found';
                            }
                            """
                            page.evaluate(js_ensure_oval)
                        except:
                            pass
                        
                        page.wait_for_timeout(200)
                        
                        # Draw ellipse by dragging from corner to corner
                        start_x = x - rx
                        start_y = y - ry
                        end_x = x + rx
                        end_y = y + ry
                        
                        # Move to start, drag to end
                        page.mouse.move(start_x, start_y)
                        page.mouse.down()
                        page.wait_for_timeout(100)  # Small delay for jspaint to register
                        page.mouse.move(end_x, end_y)
                        page.mouse.up()
                        page.wait_for_timeout(500)

                    elif action == 'draw_circle':
                        radius = params.get('radius', 10)
                        offset = params.get('offset', [0, 0])

                        x = canvas_center['x'] + offset[0]
                        y = canvas_center['y'] + offset[1]

                        console.print(f"    Drawing circle at ({x}, {y}) radius={radius}")

                        # For jspaint circles: use brush tool with single click or small drag
                        # First ensure brush tool is selected
                        try:
                            js_ensure_brush = """
                            () => {
                                const tools = document.querySelectorAll('.tool, button');
                                for (let t of tools) {
                                    const title = (t.title || t.getAttribute('aria-label') || '').toLowerCase();
                                    if (title.includes('brush') || title.includes('pencil')) {
                                        if (!t.classList.contains('selected')) {
                                            t.click();
                                        }
                                        return 'brush ready';
                                    }
                                }
                                return 'brush not found';
                            }
                            """
                            page.evaluate(js_ensure_brush)
                        except:
                            pass
                        
                        page.wait_for_timeout(200)
                        
                        # For jspaint: use filled circle tool if available, or draw small filled ellipse
                        # Try to select circle tool temporarily
                        try:
                            js_select_circle = """
                            () => {
                                const tools = document.querySelectorAll('.tool, button');
                                for (let t of tools) {
                                    const title = (t.title || t.getAttribute('aria-label') || '').toLowerCase();
                                    if (title.includes('circle') && !title.includes('ellipse')) {
                                        t.click();
                                        return 'circle tool selected';
                                    }
                                }
                                // Fallback: use oval tool
                                for (let t of tools) {
                                    const title = (t.title || t.getAttribute('aria-label') || '').toLowerCase();
                                    if (title.includes('oval') || title.includes('ellipse')) {
                                        t.click();
                                        return 'oval tool for circle';
                                    }
                                }
                                return 'using brush';
                            }
                            """
                            page.evaluate(js_select_circle)
                        except:
                            pass
                        
                        page.wait_for_timeout(200)
                        
                        # Draw circle by dragging (for filled circle) or single click for brush dot
                        page.mouse.move(x - radius, y - radius)
                        page.mouse.down()
                        page.wait_for_timeout(100)
                        page.mouse.move(x + radius, y + radius)
                        page.mouse.up()
                        page.wait_for_timeout(300)

                    elif action == 'draw_line':
                        from_offset = params.get('from_offset', [0, 0])
                        to_offset = params.get('to_offset', [0, 0])

                        x1 = canvas_center['x'] + from_offset[0]
                        y1 = canvas_center['y'] + from_offset[1]
                        x2 = canvas_center['x'] + to_offset[0]
                        y2 = canvas_center['y'] + to_offset[1]

                        console.print(f"    Drawing line from ({x1}, {y1}) to ({x2}, {y2})")

                        page.mouse.move(x1, y1)
                        page.mouse.down()
                        page.mouse.move(x2, y2, steps=10)
                        page.mouse.up()
                        page.wait_for_timeout(300)

                    elif action == 'screenshot':
                        suffix = params.get('suffix', 'final')
                        screenshot_path = str(video_dir / f"screenshot_{suffix}.png")
                        page.screenshot(path=screenshot_path, full_page=False)
                        console.print(f"[green]  Screenshot saved: {screenshot_path}[/green]")

                    else:
                        console.print(f"    [dim]Unknown action: {action}[/dim]")

                except Exception as e:
                    console.print(f"    [yellow]Step {i} error: {e}[/yellow]")
                    continue

            # Close context and browser
            context.close()
            browser.close()

        # Find the video file created by Playwright
        video_files = list(video_dir.glob('*.webm')) + list(video_dir.glob('*.mp4'))
        if video_files:
            # Rename the most recent video to the desired output path
            latest_video = max(video_files, key=lambda p: p.stat().st_mtime)
            import shutil
            shutil.move(str(latest_video), output_path)
            console.print(f"[green]✅ Browser video saved to: {output_path}[/green]")
        else:
            console.print(f"[yellow]No video file found in {video_dir}[/yellow]")

        if screenshot_path and Path(screenshot_path).exists():
            console.print(f"[green]✅ Screenshot showing ladybug: {screenshot_path}[/green]")

    except ImportError:
        console.print("[red]Playwright not installed. Install with: pip install playwright[/red]")
        raise
    except Exception as e:
        console.print(f"[red]Browser execution error: {e}[/red]")
        raise
