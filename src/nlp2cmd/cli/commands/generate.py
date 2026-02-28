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
            current_color = "#000000"  # Track foreground color for canvas API fallbacks

            # ── JS helpers for jspaint.app interaction ──

            def _js_set_color(color_hex: str) -> str:
                """Click matching palette swatch in jspaint. Left-click = foreground."""
                return f"""
                () => {{
                    const target = '{color_hex}'.toUpperCase();
                    const tr = parseInt(target.slice(1,3), 16);
                    const tg = parseInt(target.slice(3,5), 16);
                    const tb = parseInt(target.slice(5,7), 16);

                    // Method 1: click matching swatch in palette
                    const swatches = document.querySelectorAll('.color-button');
                    for (const s of swatches) {{
                        const bg = getComputedStyle(s).backgroundColor;
                        const m = bg.match(/rgb\\((\\d+),\\s*(\\d+),\\s*(\\d+)\\)/);
                        if (m) {{
                            const r = +m[1], g = +m[2], b = +m[3];
                            if (Math.abs(r - tr) < 10 && Math.abs(g - tg) < 10 && Math.abs(b - tb) < 10) {{
                                s.click();
                                return 'palette: rgb(' + r + ',' + g + ',' + b + ')';
                            }}
                        }}
                    }}

                    // Method 2: jspaint internal API
                    if (typeof selected_colors !== 'undefined') {{
                        selected_colors.foreground = target;
                        return 'api: ' + target;
                    }}

                    // Method 3: Edit Colors dialog — open, set, close
                    // (too complex, skip for now)

                    return 'not_found';
                }}
                """

            def _js_select_tool(tool_name: str) -> str:
                """Select a tool in jspaint by matching its title attribute."""
                tool_title_map = {
                    'ellipse': 'Ellipse', 'circle': 'Ellipse', 'oval': 'Ellipse',
                    'rectangle': 'Rectangle', 'rect': 'Rectangle',
                    'rounded_rectangle': 'Rounded Rectangle',
                    'line': 'Line', 'curve': 'Curve',
                    'brush': 'Brush', 'pencil': 'Pencil',
                    'fill': 'Fill', 'eraser': 'Eraser',
                    'text': 'Text', 'select': 'Select',
                    'airbrush': 'Airbrush', 'polygon': 'Polygon',
                    'pick_color': 'Pick Color', 'magnifier': 'Magnifier',
                    'free_select': 'Free-Form Select',
                }
                title_part = tool_title_map.get(tool_name.lower(), tool_name)
                return f"""
                () => {{
                    const tools = document.querySelectorAll('.tool');
                    for (const t of tools) {{
                        if (t.title && t.title.includes('{title_part}')) {{
                            t.click();
                            return 'selected: ' + t.title;
                        }}
                    }}
                    return 'not_found: {tool_name}';
                }}
                """

            def _js_draw_filled_circle(cx: float, cy: float, radius: float, color: str) -> str:
                """Draw a filled circle directly on the jspaint canvas via Canvas 2D API."""
                return f"""
                () => {{
                    const canvas = document.querySelector('canvas');
                    if (!canvas) return 'no_canvas';
                    const rect = canvas.getBoundingClientRect();
                    const scaleX = canvas.width / rect.width;
                    const scaleY = canvas.height / rect.height;
                    const ctx = canvas.getContext('2d');
                    const pcx = ({cx} - rect.left) * scaleX;
                    const pcy = ({cy} - rect.top) * scaleY;
                    const pr = {radius} * Math.min(scaleX, scaleY);
                    ctx.save();
                    ctx.fillStyle = '{color}';
                    ctx.beginPath();
                    ctx.arc(pcx, pcy, pr, 0, Math.PI * 2);
                    ctx.fill();
                    ctx.restore();
                    return 'filled_circle_at(' + Math.round(pcx) + ',' + Math.round(pcy) + ')';
                }}
                """

            def _js_draw_filled_ellipse(cx: float, cy: float, rx: float, ry: float, color: str) -> str:
                """Draw a filled ellipse directly on the jspaint canvas via Canvas 2D API."""
                return f"""
                () => {{
                    const canvas = document.querySelector('canvas');
                    if (!canvas) return 'no_canvas';
                    const rect = canvas.getBoundingClientRect();
                    const scaleX = canvas.width / rect.width;
                    const scaleY = canvas.height / rect.height;
                    const ctx = canvas.getContext('2d');
                    const pcx = ({cx} - rect.left) * scaleX;
                    const pcy = ({cy} - rect.top) * scaleY;
                    const prx = {rx} * scaleX;
                    const pry = {ry} * scaleY;
                    ctx.save();
                    ctx.fillStyle = '{color}';
                    ctx.beginPath();
                    ctx.ellipse(pcx, pcy, prx, pry, 0, 0, Math.PI * 2);
                    ctx.fill();
                    ctx.restore();
                    return 'filled_ellipse';
                }}
                """

            def _js_draw_line(x1: float, y1: float, x2: float, y2: float, color: str, width: int = 2) -> str:
                """Draw a line directly on the jspaint canvas via Canvas 2D API."""
                return f"""
                () => {{
                    const canvas = document.querySelector('canvas');
                    if (!canvas) return 'no_canvas';
                    const rect = canvas.getBoundingClientRect();
                    const scaleX = canvas.width / rect.width;
                    const scaleY = canvas.height / rect.height;
                    const ctx = canvas.getContext('2d');
                    ctx.save();
                    ctx.strokeStyle = '{color}';
                    ctx.lineWidth = {width};
                    ctx.beginPath();
                    ctx.moveTo(({x1} - rect.left) * scaleX, ({y1} - rect.top) * scaleY);
                    ctx.lineTo(({x2} - rect.left) * scaleX, ({y2} - rect.top) * scaleY);
                    ctx.stroke();
                    ctx.restore();
                    return 'line_drawn';
                }}
                """

            # ── Step execution loop ──

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

                    elif action == 'wait':
                        ms = params.get('ms', 1000)
                        try:
                            ms = int(ms)
                        except Exception:
                            ms = 1000
                        page.wait_for_timeout(ms)

                    elif action == 'echo':
                        msg = str(params.get('text', '') or params.get('message', '') or '')
                        if msg:
                            console.print(f"    [dim]{msg}[/dim]")

                    elif action == 'wait_for_canvas':
                        try:
                            page.wait_for_selector('canvas', timeout=5000)
                        except Exception:
                            pass
                        page.wait_for_timeout(1000)

                    elif action == 'get_canvas_center':
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
                        try:
                            result = page.evaluate(_js_select_tool(tool))
                            console.print(f"      {result}")
                        except Exception as e:
                            console.print(f"      [yellow]Tool selection warning: {e}[/yellow]")
                        page.wait_for_timeout(300)

                    elif action == 'set_color':
                        color = params.get('color', '#000000')
                        current_color = color
                        console.print(f"    Setting color: {color}")
                        try:
                            result = page.evaluate(_js_set_color(color))
                            console.print(f"      {result}")
                        except Exception as e:
                            console.print(f"      [yellow]Color setting warning: {e}[/yellow]")
                        page.wait_for_timeout(200)

                    elif action == 'draw_filled_ellipse':
                        rx = params.get('rx', 50)
                        ry = params.get('ry', 50)
                        x = canvas_center['x']
                        y = canvas_center['y']
                        console.print(f"    Drawing filled ellipse at ({x}, {y}) rx={rx}, ry={ry}")

                        # 1) Select ellipse tool
                        page.evaluate(_js_select_tool('ellipse'))
                        page.wait_for_timeout(200)

                        # 2) Draw outline via mouse drag
                        page.mouse.move(x - rx, y - ry)
                        page.mouse.down()
                        page.wait_for_timeout(50)
                        page.mouse.move(x + rx, y + ry, steps=5)
                        page.mouse.up()
                        page.wait_for_timeout(300)

                        # 3) Fill interior via canvas API (reliable for any color)
                        result = page.evaluate(_js_draw_filled_ellipse(x, y, rx, ry, current_color))
                        console.print(f"      fill: {result}")

                        # 4) Re-draw outline on top so border is visible
                        page.evaluate(_js_select_tool('ellipse'))
                        page.wait_for_timeout(200)
                        page.mouse.move(x - rx, y - ry)
                        page.mouse.down()
                        page.wait_for_timeout(50)
                        page.mouse.move(x + rx, y + ry, steps=5)
                        page.mouse.up()
                        page.wait_for_timeout(300)

                    elif action in ('draw_circle', 'draw_filled_circle'):
                        radius = params.get('radius', 10)
                        offset = params.get('offset', [0, 0])
                        x = canvas_center['x'] + offset[0]
                        y = canvas_center['y'] + offset[1]
                        console.print(f"    Drawing {'filled ' if 'filled' in action else ''}circle at ({x}, {y}) radius={radius}")

                        # Draw filled circle via canvas API — precise and works with any color
                        result = page.evaluate(_js_draw_filled_circle(x, y, radius, current_color))
                        console.print(f"      {result}")
                        page.wait_for_timeout(150)

                    elif action == 'draw_ellipse':
                        rx = params.get('rx', 50)
                        ry = params.get('ry', 50)
                        offset = params.get('offset', [0, 0])
                        x = canvas_center['x'] + offset[0]
                        y = canvas_center['y'] + offset[1]
                        console.print(f"    Drawing ellipse at ({x}, {y}) rx={rx}, ry={ry}")

                        # We don't have _js_draw_ellipse but we can reuse _js_draw_filled_ellipse with transparent fill or just use the mouse
                        page.evaluate(_js_select_tool('ellipse'))
                        page.wait_for_timeout(200)
                        page.mouse.move(x - rx, y - ry)
                        page.mouse.down()
                        page.wait_for_timeout(50)
                        page.mouse.move(x + rx, y + ry, steps=5)
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

                        # Draw line via canvas API for precision
                        result = page.evaluate(_js_draw_line(x1, y1, x2, y2, current_color, 2))
                        console.print(f"      {result}")

                        # Also do mouse drag for visual effect in video recording
                        page.evaluate(_js_select_tool('line'))
                        page.wait_for_timeout(200)
                        page.mouse.move(x1, y1)
                        page.mouse.down()
                        page.mouse.move(x2, y2, steps=10)
                        page.mouse.up()
                        page.wait_for_timeout(300)

                    elif action == 'fill_at':
                        offset = params.get('offset', [0, 0])
                        x = canvas_center['x'] + offset[0]
                        y = canvas_center['y'] + offset[1]
                        console.print(f"    Fill at ({x}, {y}) with {current_color}")

                        # Select fill tool and click at position
                        page.evaluate(_js_select_tool('fill'))
                        page.wait_for_timeout(200)
                        page.mouse.click(x, y)
                        page.wait_for_timeout(300)

                    elif action == 'click_canvas':
                        offset = params.get('offset', [0, 0])
                        x = canvas_center['x'] + offset[0]
                        y = canvas_center['y'] + offset[1]
                        page.mouse.click(x, y)
                        page.wait_for_timeout(200)

                    elif action == 'type_text':
                        text = params.get('text', '')
                        if text:
                            page.keyboard.type(text, delay=30)
                        page.wait_for_timeout(200)

                    elif action == 'echo':
                        text = params.get('text', params.get('message', ''))
                        if text:
                            console.print(f"    [cyan]{text}[/cyan]")

                    elif action in ('draw_ellipse', 'draw_rectangle'):
                        rx = params.get('rx', params.get('width', 100) // 2)
                        ry = params.get('ry', params.get('height', 80) // 2)
                        offset = params.get('offset', [0, 0])
                        x = canvas_center['x'] + offset[0]
                        y = canvas_center['y'] + offset[1]
                        console.print(f"    Drawing {action} at ({x}, {y}) rx={rx}, ry={ry}")
                        page.mouse.move(x - rx, y - ry)
                        page.mouse.down()
                        page.wait_for_timeout(50)
                        page.mouse.move(x + rx, y + ry, steps=5)
                        page.mouse.up()
                        page.wait_for_timeout(300)

                    elif action == 'wait':
                        ms = params.get('ms', 1000)
                        page.wait_for_timeout(ms)

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
            console.print(f"[green]✅ Screenshot saved: {screenshot_path}[/green]")

    except ImportError:
        console.print("[red]Playwright not installed. Install with: pip install playwright[/red]")
        raise
    except Exception as e:
        console.print(f"[red]Browser execution error: {e}[/red]")
        raise
