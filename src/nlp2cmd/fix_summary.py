import re

file_path = "/home/tom/github/wronai/nlp2cmd/src/nlp2cmd/pipeline_runner.py"
with open(file_path, "r") as f:
    content = f.read()

summary_code = """
            # Final summary
            ok_count = sum(1 for r in results_log if r["status"] in ("ok", "ok_retry", "ok_fallback", "fallback_injected"))
            fail_count = sum(1 for r in results_log if r["status"] == "failed")
            err_count = sum(1 for r in results_log if r["status"] == "error")
            total_ms = sum(r.get("elapsed_ms", 0) for r in results_log)

            console.print(f"\\n[bold]📊 Podsumowanie planu:[/bold]")
            console.print(
                f"  Kroki: {ok_count}✓ {err_count}⚠ {fail_count}✗ "
                f"z {len(plan.steps)} | Czas: {total_ms/1000:.1f}s"
            )

            if video_recorder and video_recorder.is_recording:
"""

content = content.replace(
    "            if video_recorder and video_recorder.is_recording:\n                try:\n                    # To ensure the video file is completely written",
    summary_code + "                try:\n                    # To ensure the video file is completely written"
)

with open(file_path, "w") as f:
    f.write(content)
