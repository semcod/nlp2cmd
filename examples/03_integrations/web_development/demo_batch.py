#!/usr/bin/env python3
"""
Batch demo - execute all commands from prompt.txt automatically.
"""

import asyncio
import shutil
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
sys.path.append(str(Path(__file__).resolve().parents[2]))

from _demo_helpers import (
    handle_docker_execution,
    print_batch_banner,
    print_config,
    print_containers,
    print_execution_summary,
    print_files_saved,
)
from _example_helpers import print_rule, print_separator

from nlp2cmd_web_controller import NLP2CMDWebController


def _print_batch_result(result: dict) -> None:
    print(f"\n📊 Status: {result.get('status')}")
    print(f"💬 {result.get('message')}")
    if result.get("config"):
        print_config(result["config"])
    if result.get("files_saved"):
        print_files_saved(result["files_saved"])


def _load_commands(prompt_file: Path) -> list[str] | None:
    if not prompt_file.exists():
        print(f"❌ Plik {prompt_file} nie istnieje!")
        return None
    with open(prompt_file, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


async def _execute_command(controller, command: str, index: int, total: int) -> dict:
    print(f"\n📝 Komenda {index}/{total}: {command}")
    print("⚙️ Przetwarzanie...")
    print_rule()
    try:
        result = await controller.execute(command)
        _print_batch_result(result)
        await handle_docker_execution(result, controller)
        return {
            "command": command,
            "status": result.get("status"),
            "message": result.get("message"),
            "success": result.get("status") == "success",
        }
    except Exception as e:
        print(f"❌ Błąd wykonania: {e}")
        return {"command": command, "status": "error", "message": str(e), "success": False}


async def _print_final_status(controller) -> None:
    files_info = controller.get_generated_files_info()
    if files_info["files"]:
        print(f"\n📁 Wszystkie wygenerowane pliki ({files_info['total_files']}):")
        for file_info in files_info["files"]:
            print(f"   📄 {file_info['name']} ({file_info['size']} bytes)")

    if not controller.docker_manager:
        return
    print("\n📦 Finalny status kontenerów:")
    status_result = await controller.get_container_status()
    if status_result.get("status") == "success":
        print_containers(status_result.get("containers", []))


async def _cleanup(controller) -> None:
    print("\n🧹 Sprzątanie...")
    if controller.docker_manager:
        await controller.stop_containers()
    if Path("./generated").exists():
        shutil.rmtree("./generated")
        print("✅ Pliki usunięte")


async def run_batch_demo():
    """Run all commands from prompt.txt automatically."""
    print_batch_banner()
    print_separator(
        "🤖 NLP2CMD - Tryb Batch (wszystkie komendy z prompt.txt)",
        leading_newline=True,
        width=70,
    )

    commands = _load_commands(Path("prompt.txt"))
    if not commands:
        return

    print(f"\n📋 Znaleziono {len(commands)} komend do wykonania:")
    for i, cmd in enumerate(commands, 1):
        print(f"   {i}. {cmd}")

    if Path("./generated").exists():
        shutil.rmtree("./generated")

    controller = NLP2CMDWebController(output_dir="./generated")
    print("\n🚀 Rozpoczynam wykonywanie komend...")
    print_rule(width=70, char="=")

    results = []
    for i, command in enumerate(commands, 1):
        results.append(await _execute_command(controller, command, i, len(commands)))
        await asyncio.sleep(1)

    print_separator("📊 Podsumowanie wykonania", leading_newline=True, width=70)
    await _print_final_status(controller)
    print_execution_summary(results)
    await _cleanup(controller)


if __name__ == "__main__":
    if "MAKELEVEL" in os.environ or "MAKEFLAGS" in os.environ:
        print("Invoked under make; skipping web_development demo_batch.")
        print("Run directly with: python3 demo_batch.py")
        raise SystemExit(0)
    asyncio.run(run_batch_demo())
