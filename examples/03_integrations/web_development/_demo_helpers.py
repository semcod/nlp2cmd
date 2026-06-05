"""Shared helpers for web development demo scripts."""

from __future__ import annotations

import asyncio
import subprocess
from typing import Any

from _example_helpers import print_rule


def print_config(config: dict[str, Any]) -> None:
    print("\n⚙️ Konfiguracja:")
    for key, value in config.items():
        if key == "env_vars":
            print(f"   {key}:")
            for k, v in value.items():
                print(f"     {k}: {v}")
        else:
            print(f"   {key}: {value}")


def print_containers(containers: list[dict[str, Any]], container_count: int | None = None) -> None:
    count = container_count if container_count is not None else len(containers)
    print(f"\n📦 Kontenery ({count}):")
    for container in containers:
        status_emoji = "✅" if "Up" in container.get("status", "") else "❌"
        print(f"   {status_emoji} {container['name']}: {container['status']}")
        if container.get("ports"):
            print(f"      🌐 Porty: {container['ports']}")


def print_files_saved(files_saved: dict[str, str]) -> None:
    print("\n💾 Zapisane pliki:")
    for file_type, file_path in files_saved.items():
        print(f"   📄 {file_type}: {file_path}")


async def print_docker_result(result: dict[str, Any], controller: Any) -> None:
    docker_result = result.get("docker_execution")
    if not docker_result:
        return

    print(f"\n🐳 Docker: {docker_result.get('message', 'Unknown')}")
    if docker_result.get("status") != "success":
        print(f"   ❌ Błąd: {docker_result.get('message', 'Unknown error')}")
        return

    containers = result.get("containers", [])
    if containers:
        print_containers(containers, result.get("container_count"))
    print("\n📋 Ostatnie logi kontenerów:")
    await controller.show_container_logs(follow=False, lines=5)


def print_command_result(result: dict[str, Any], controller: Any | None = None) -> None:
    print(f"\n📊 Status: {result.get('status', 'unknown')}")
    if result.get("message"):
        print(f"💬 {result['message']}")

    if result.get("config"):
        print_config(result["config"])

    if result.get("files_saved"):
        print_files_saved(result["files_saved"])

    if result.get("note"):
        print(f"\n📝 {result['note']}")

    if result.get("services"):
        print("\n📦 Aktywne usługi:")
        for name, info in result["services"].items():
            print(f"   - {name}: port {info['port']} ({info['type']})")

    if result.get("examples"):
        print("\n💡 Przykłady:")
        for example in result["examples"]:
            print(f"   • {example}")


async def show_container_status(controller: Any) -> None:
    print("\n⚙️ Sprawdzanie statusu kontenerów...")
    print_rule()
    status_result = await controller.get_container_status()
    if status_result.get("status") != "success":
        print(f"❌ Błąd: {status_result.get('message')}")
        return

    containers = status_result.get("containers", [])
    if containers:
        print_containers(containers)
    else:
        print("📦 Brak działających kontenerów")


async def show_container_logs(controller: Any, *, follow: bool = False, lines: int = 20) -> None:
    label = "Śledzenie logów kontenerów (Ctrl+C aby przerwać)..." if follow else "Pobieranie logów kontenerów..."
    print(f"\n📋 {label}")
    print_rule()
    await controller.show_container_logs(follow=follow, lines=lines)


async def stop_all_containers(controller: Any) -> None:
    print("\n🛑 Zatrzymywanie kontenerów...")
    print_rule()
    stop_result = await controller.stop_containers()
    if stop_result.get("status") == "success":
        print("✅ Kontenery zatrzymane pomyślnie")
    else:
        print(f"❌ Błąd: {stop_result.get('message')}")


def _run_subprocess(cmd: list[str], timeout: int = 5) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


async def test_chat_service(container: dict[str, Any]) -> None:
    try:
        result = await asyncio.to_thread(
            _run_subprocess,
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://localhost:8080"],
        )
        if result.stdout.strip() == "200":
            print("      ✅ Serwis czatu odpowiada (HTTP 200)")
        else:
            print(f"      ⚠️ Serwis czatu zwrócił kod: {result.stdout.strip()}")
    except Exception as e:
        print(f"      ❌ Błąd testu serwisu czatu: {e}")


async def test_redis_service(container: dict[str, Any]) -> None:
    try:
        result = await asyncio.to_thread(
            _run_subprocess,
            ["docker", "exec", container["name"], "redis-cli", "ping"],
        )
        if "PONG" in result.stdout:
            print("      ✅ Redis odpowiada (PONG)")
        else:
            print(f"      ❌ Redis nie odpowiada: {result.stdout}")
    except Exception as e:
        print(f"      ❌ Błąd testu Redis: {e}")


async def test_postgres_service(container: dict[str, Any]) -> None:
    try:
        result = await asyncio.to_thread(
            _run_subprocess,
            ["docker", "exec", container["name"], "pg_isready", "-U", "nlp2cmd"],
        )
        if result.returncode == 0:
            print("      ✅ PostgreSQL gotowy")
        else:
            print(f"      ⚠️ PostgreSQL nie jest gotowy: {result.stderr}")
    except Exception as e:
        print(f"      ❌ Błąd testu PostgreSQL: {e}")


async def test_container_service(container: dict[str, Any]) -> None:
    name = container["name"].lower()
    if "chat-service" in name:
        await test_chat_service(container)
    elif "redis" in name:
        await test_redis_service(container)
    elif "postgres" in name:
        await test_postgres_service(container)


async def test_services(controller: Any, *, verbose: bool = True) -> bool:
    if verbose:
        print("🔍 Sprawdzanie działania usług...")
    status_result = await controller.get_container_status()
    if status_result.get("status") != "success":
        print("❌ Nie można sprawdzić statusu kontenerów")
        return False

    all_healthy = True
    for container in status_result.get("containers", []):
        status = container["status"]
        if "Up" in status:
            prefix = "   ✅" if verbose else "      ✅"
            print(f"{prefix} {container['name']}: działa")
            await test_container_service(container)
        else:
            all_healthy = False
            prefix = "   ❌" if verbose else "      ❌"
            print(f"{prefix} {container['name']}: nie działa ({status})")
    return all_healthy


async def handle_docker_execution(result: dict[str, Any], controller: Any) -> None:
    docker_result = result.get("docker_execution")
    if not docker_result:
        return
    print(f"\n🐳 Docker: {docker_result.get('message', 'Unknown')}")
    if docker_result.get("status") != "success":
        print(f"   ❌ Błąd: {docker_result.get('message', 'Unknown error')}")
        return
    containers = result.get("containers", [])
    if containers:
        print_containers(containers, result.get("container_count"))
    print("\n🧪 Testowanie usług...")
    await test_services(controller)


def print_batch_banner() -> None:
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║                                                                      ║")
    print("║     🚀 NLP2CMD Batch Demo - All Commands from prompt.txt            ║")
    print("║                                                                      ║")
    print("║     Natural Language → DevOps Configuration + Testing               ║")
    print("║                                                                      ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")


def print_execution_summary(results: list[dict[str, Any]]) -> None:
    successful = sum(1 for r in results if r["success"])
    total = len(results)
    print(f"\n✅ Pomyślne: {successful}/{total}")
    print(f"❌ Błędy: {total - successful}/{total}")
    print("\n📋 Szczegóły:")
    for i, result in enumerate(results, 1):
        status_emoji = "✅" if result["success"] else "❌"
        print(f"   {status_emoji} {i}. {result['command']}")
        print(f"      {result['message']}")
    print(f"\n🎉 Batch demo zakończone!")
    print(f"Wynik: {successful}/{total} komend wykonanych pomyślnie")


async def dispatch_management_command(controller: Any, command: str) -> bool:
    """Handle built-in container management commands. Returns True if handled."""
    normalized = command.lower()
    handlers = {
        "status": lambda: show_container_status(controller),
        "logs": lambda: show_container_logs(controller, follow=False, lines=20),
        "logs follow": lambda: show_container_logs(controller, follow=True),
        "stop": lambda: stop_all_containers(controller),
    }
    handler = handlers.get(normalized)
    if handler is None:
        return False
    await handler()
    return True
