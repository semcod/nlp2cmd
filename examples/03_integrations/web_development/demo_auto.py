#!/usr/bin/env python3
"""
Demo with automatic deployment and testing.
"""

import asyncio
import sys
import argparse
import os
from pathlib import Path

if "MAKELEVEL" in os.environ or "MAKEFLAGS" in os.environ:
    print("Invoked under make; skipping web_development demo_auto.")
    print("Run directly with: python3 demo_auto.py [--interactive]")
    raise SystemExit(0)

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
 
sys.path.append(str(Path(__file__).resolve().parents[2]))
 
from _demo_helpers import (
    dispatch_management_command,
    handle_docker_execution,
    print_config,
    print_containers,
    print_files_saved,
    test_services,
)
from _example_helpers import print_rule, print_separator

from nlp2cmd_web_controller import NLP2CMDWebController


async def run_demo_with_test(interactive=False):
    """Run demo with automatic deployment and testing."""
    print("╔══════════════════════════════════════════════════════════════════════╗")
    print("║                                                                      ║")
    print("║     🚀 NLP2CMD Web Examples - Auto Demo & Test                      ║")
    print("║                                                                      ║")
    print("║     Natural Language → DevOps Configuration + Testing               ║")
    print("║                                                                      ║")
    print("╚══════════════════════════════════════════════════════════════════════╝")
    
    mode = "Interaktywny" if interactive else "Automatyczny"
    print_separator(f"🤖 NLP2CMD - Tryb {mode}", leading_newline=True, width=70)
    
    # Clean up any existing files
    import shutil
    if Path("./generated").exists():
        shutil.rmtree("./generated")
    
    # Initialize controller
    controller = NLP2CMDWebController(output_dir="./generated")
    
    # Default command
    command = "Uruchom serwis czatu na porcie 8080"
    
    print(f"\n📝 Domyślne polecenie: '{command}'")
    print("⚙️ Przetwarzanie...")
    print_rule()
    
    # Execute command
    result = await controller.execute(command)
    
    print(f"\n📊 Status: {result.get('status')}")
    print(f"💬 {result.get('message')}")
    
    if result.get("config"):
        print_config(result["config"])
    if result.get("files_saved"):
        print_files_saved(result["files_saved"])
    
    if result.get("docker_execution"):
        docker_result = result["docker_execution"]
        if docker_result.get("status") == "success":
            await handle_docker_execution(result, controller)
        else:
            print(f"\n🐳 Docker: {docker_result.get('message', 'Unknown')}")
            print(f"   ❌ Błąd: {docker_result.get('message', 'Unknown error')}")
            print("\n🔧 Próba naprawy...")
            await troubleshoot_and_fix(controller, command)
    
    # Show generated files
    files_info = controller.get_generated_files_info()
    if files_info['files']:
        print(f"\n📁 Wygenerowane pliki w: {files_info['output_directory']}")
        print(f"   Łącznie {files_info['total_files']} plików:")
        for file_info in files_info['files']:
            print(f"   📄 {file_info['name']} ({file_info['size']} bytes)")
    
    # Interactive mode (only if requested)
    if interactive:
        await interactive_mode(controller)
    else:
        # Auto-stop services in non-interactive mode
        if controller.docker_manager:
            print("\n🛑 Automatyczne zatrzymywanie kontenerów...")
            await controller.stop_containers()
    
    # Final cleanup
    print("\n🧹 Final cleanup...")
    if Path("./generated").exists():
        shutil.rmtree("./generated")
        print("✅ Wygenerowane pliki usunięte")
    
    print("\n🎉 Demo zakończone!")


async def troubleshoot_and_fix(controller, original_command):
    """Troubleshoot and fix deployment issues."""
    print("🔧 Diagnozowanie problemów...")
    
    # Check if Docker is running
    try:
        import subprocess
        result = subprocess.run(["docker", "ps"], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            print("❌ Docker nie działa. Uruchom Dockera.")
            return
    except Exception as e:
        print(f"❌ Błąd sprawdzania Dockera: {e}")
        return
    
    # Check generated files
    files_info = controller.get_generated_files_info()
    if not files_info['files']:
        print("❌ Brak wygenerowanych plików")
        return
    
    # Show Docker Compose file
    compose_file = None
    for file_info in files_info['files']:
        if 'docker-compose.yml' in file_info['name']:
            compose_file = Path(file_info['path'])
            break
    
    if compose_file and compose_file.exists():
        print(f"\n📄 Plik Docker Compose: {compose_file}")
        print("Zawartość:")
        with open(compose_file, 'r') as f:
            for i, line in enumerate(f.readlines()[:10], 1):
                print(f"   {i:2d}: {line.rstrip()}")
        
        # Try manual start
        print(f"\n🔧 Próba ręcznego uruchomienia...")
        try:
            result = subprocess.run(
                ["docker-compose", "-f", str(compose_file), "up", "-d"],
                cwd=compose_file.parent,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                print("✅ Usługi uruchomione ręcznie")
                # Test again
                await asyncio.sleep(3)
                await test_services(controller)
            else:
                print(f"❌ Ręczne uruchomienie nie powiodło się: {result.stderr}")
        except Exception as e:
            print(f"❌ Błąd ręcznego uruchomienia: {e}")


async def interactive_mode(controller):
    """Interactive mode for additional commands."""
    print_separator("🎮 Tryb Interaktywny", leading_newline=True, width=70)
    print("Dostępne komendy:")
    print("  status - pokaż status kontenerów")
    print("  logs - pokaż logi kontenerów")
    print("  logs follow - śledź logi na żywo")
    print("  stop - zatrzymaj kontenery")
    print("  test - ponownie przetestuj usługi")
    print("  quit - wyjdź")

    if not sys.stdin.isatty():
        print("\n🤖 Tryb nieinteraktywny - kończę działanie")
        if controller.docker_manager:
            print("🛑 Automatyczne zatrzymywanie kontenerów...")
            await controller.stop_containers()
        return

    while True:
        try:
            command = input("\n📝 Twoje polecenie: ").strip()
            if not command:
                continue

            lowered = command.lower()
            if lowered == "quit":
                print("\n👋 Zatrzymywanie usług i wyjście...")
                if controller.docker_manager:
                    await controller.stop_containers()
                break
            if lowered == "test":
                print("\n🧪 Testowanie usług...")
                await test_services(controller)
                continue
            if await dispatch_management_command(controller, command):
                continue

            print(f"🤖 Wykonuję: {command}")
            result = await controller.execute(command)
            print(f"Status: {result.get('status')}")
            print(f"Message: {result.get('message')}")

        except KeyboardInterrupt:
            print("\n\n👋 Przerwano.")
            break
        except Exception as e:
            print(f"\n❌ Błąd: {e}")

    if controller.docker_manager:
        print("🛑 Zatrzymywanie kontenerów przed wyjściem...")
        await controller.stop_containers()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NLP2CMD Auto Demo & Test")
    parser.add_argument("--interactive", "-i", action="store_true", 
                       help="Run in interactive mode")
    args = parser.parse_args()
    
    asyncio.run(run_demo_with_test(interactive=args.interactive))
