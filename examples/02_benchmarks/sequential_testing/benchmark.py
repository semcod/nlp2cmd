#!/usr/bin/env python3
"""
Sequential Commands Benchmark Example

This example demonstrates running multiple NLP2CMD commands sequentially
and measures their processing time. It shows how the system handles
batch processing of commands.

Usage:
    python3 examples/02_benchmarks/sequential_testing/benchmark.py
"""

import sys
import time
from pathlib import Path
from typing import List, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT / "examples"))

from _example_helpers import print_separator

from nlp2cmd import NLP2CMD
from nlp2cmd.adapters.shell import ShellAdapter


def print_section(title: str) -> None:
    """Print section header."""
    print_separator(f"  {title}", leading_newline=True, width=60)
    print()


def run_command_with_timing(nlp: NLP2CMD, command: str) -> Tuple[str, float]:
    """Run a single command and return the result with timing."""
    start_time = time.perf_counter()
    result = nlp.transform(command)
    end_time = time.perf_counter()
    
    latency_ms = (end_time - start_time) * 1000
    return result.command, latency_ms


def main():
    """Demonstrate sequential command processing."""
    print_section("NLP2CMD Sequential Commands Benchmark")
    
    # Initialize NLP2CMD with Shell adapter
    adapter = ShellAdapter()
    nlp = NLP2CMD(adapter=adapter)
    
    # Define test commands
    single_command = "Find all Python files in the current directory"
    
    sequential_commands = [
        "Find all Python files in the current directory",
        "Show running processes sorted by memory usage",
        "Count lines of code in all .py files",
        "Find files larger than 10MB",
        "List all open network connections",
        "Show disk usage for all mounted filesystems",
        "Find all TODO comments in source files",
        "Compress the logs directory",
        "Show system load average",
        "Kill all processes matching pattern"
    ]
    
    # Test 1: Single command processing
    print_section("Test 1: Single Command Processing")
    print(f"Command: {single_command}")
    
    single_latencies = []
    for i in range(5):
        cmd, latency = run_command_with_timing(nlp, single_command)
        single_latencies.append(latency)
        print(f"  Run {i+1}: {latency:.1f}ms -> {cmd}")
    
    avg_single_latency = sum(single_latencies) / len(single_latencies)
    print(f"\nAverage single command latency: {avg_single_latency:.1f}ms")
    
    # Test 2: Sequential command processing
    print_section(f"Test 2: Sequential Command Processing ({len(sequential_commands)} commands)")
    
    sequential_latencies = []
    total_start = time.perf_counter()
    
    for i, command in enumerate(sequential_commands, 1):
        print(f"\nCommand {i}/{len(sequential_commands)}: {command}")
        cmd, latency = run_command_with_timing(nlp, command)
        sequential_latencies.append(latency)
        print(f"  Generated: {cmd}")
        print(f"  Latency: {latency:.1f}ms")
    
    total_end = time.perf_counter()
    total_time_ms = (total_end - total_start) * 1000
    
    # Calculate statistics
    avg_sequential_latency = sum(sequential_latencies) / len(sequential_latencies)
    min_latency = min(sequential_latencies)
    max_latency = max(sequential_latencies)
    
    # Test 3: Batch processing simulation
    print_section("Test 3: Batch Processing Simulation")
    print("Simulating real-world batch processing scenario...")
    
    batch_commands = [
        "Check system status",
        "Find error logs",
        "Check disk space",
        "List running services",
        "Show network connections"
    ]
    
    batch_start = time.perf_counter()
    batch_results = []
    
    for cmd in batch_commands:
        result, latency = run_command_with_timing(nlp, cmd)
        batch_results.append((cmd, result, latency))
    
    batch_end = time.perf_counter()
    batch_total_ms = (batch_end - batch_start) * 1000
    
    # Summary
    print_section("Performance Summary")
    print(f"Single Command Test:")
    print(f"  Average latency: {avg_single_latency:.1f}ms")
    print(f"  Runs: 5")
    
    print(f"\nSequential Commands Test:")
    print(f"  Total commands: {len(sequential_commands)}")
    print(f"  Total time: {total_time_ms:.1f}ms")
    print(f"  Average latency: {avg_sequential_latency:.1f}ms")
    print(f"  Min latency: {min_latency:.1f}ms")
    print(f"  Max latency: {max_latency:.1f}ms")
    print(f"  Throughput: {len(sequential_commands) / (total_time_ms / 1000):.2f} commands/sec")
    
    print(f"\nBatch Processing Test:")
    print(f"  Batch size: {len(batch_commands)}")
    print(f"  Total time: {batch_total_ms:.1f}ms")
    print(f"  Average per command: {batch_total_ms / len(batch_commands):.1f}ms")
    
    # Performance comparison
    print(f"\nPerformance Analysis:")
    if avg_sequential_latency > avg_single_latency:
        overhead = ((avg_sequential_latency - avg_single_latency) / avg_single_latency) * 100
        print(f"  Sequential processing overhead: {overhead:.1f}%")
    else:
        print(f"  No significant overhead detected")
    
    print(f"\nGenerated Commands Preview:")
    for i, (input_cmd, output_cmd, latency) in enumerate(batch_results[:3], 1):
        print(f"  {i}. {input_cmd[:40]}...")
        print(f"     -> {output_cmd}")
    
    # Save results to file
    results_file = "sequential_benchmark_results.json"
    import json
    
    results = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "single_command": {
            "command": single_command,
            "average_latency_ms": avg_single_latency,
            "all_latencies": single_latencies
        },
        "sequential": {
            "total_commands": len(sequential_commands),
            "total_time_ms": total_time_ms,
            "average_latency_ms": avg_sequential_latency,
            "min_latency_ms": min_latency,
            "max_latency_ms": max_latency,
            "throughput_commands_per_second": len(sequential_commands) / (total_time_ms / 1000)
        },
        "batch": {
            "batch_size": len(batch_commands),
            "total_time_ms": batch_total_ms,
            "average_per_command_ms": batch_total_ms / len(batch_commands)
        }
    }
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✅ Results saved to {results_file}")


if __name__ == "__main__":
    main()
