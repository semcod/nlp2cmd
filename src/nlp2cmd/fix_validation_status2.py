import re

file_path = "/home/tom/github/wronai/nlp2cmd/src/nlp2cmd/pipeline_runner.py"
with open(file_path, "r") as f:
    content = f.read()

# Replace the block added previously
old_block = """
                    # Default status unless overridden by validation/fallback
                    current_status = "ok"
                    if validator and not post_result.passed:
                        # Check if fallback fixed it
                        if step.action in ("check_session", "extract_key") and fallback_engine and fb_result and fb_result.success:
                            if fb_result.extracted_value:
                                current_status = "ok_fallback"
                            elif fb_result.replacement_steps:
                                current_status = "fallback_injected"
                        else:
                            current_status = "failed"

                    results_log.append({
                        "step": step_idx + 1, "action": step.action,
                        "status": current_status, "stored": step.store_as,
                        "elapsed_ms": round(elapsed_ms),
                    })
"""

new_block = """
                    current_status = "ok"
                    if 'validator' in locals() and validator and 'post_result' in locals() and not post_result.passed:
                        current_status = "failed"
                        if step.action in ("check_session", "extract_key") and 'fallback_engine' in locals() and fallback_engine:
                            if 'fb_result' in locals() and fb_result.success:
                                if fb_result.extracted_value:
                                    current_status = "ok_fallback"
                                elif fb_result.replacement_steps:
                                    current_status = "fallback_injected"

                    results_log.append({
                        "step": step_idx + 1, "action": step.action,
                        "status": current_status, "stored": step.store_as,
                        "elapsed_ms": round(elapsed_ms),
                    })
"""

if old_block in content:
    content = content.replace(old_block, new_block)
    with open(file_path, "w") as f:
        f.write(content)
    print("Fixed status append logic")
else:
    print("Could not find the block to fix")
