"""
Benchmark latency across different communication protocols.

This script measures the latency of:
- Chrome DevTools Protocol (CDP) over WebSocket
- Native Messaging protocol (simulated)
- Direct process communication
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, List

from surfboard.automation.browser import ChromeManager
from surfboard.protocols.cdp import CDPClient
from surfboard.protocols.native_messaging import NativeMessagingHost


class LatencyBenchmark:
    """Benchmark communication protocol latencies."""

    def __init__(self):
        self.results: Dict[str, List[float]] = {}

    async def benchmark_cdp(self, iterations: int = 100) -> float:
        """Benchmark CDP protocol latency."""
        latencies = []

        try:
            async with ChromeManager(debugging_port=9998, headless=True) as manager:
                async with CDPClient(port=9998) as client:
                    # Warm up
                    await client.send_command("Runtime.evaluate", {"expression": "1"})

                    # Benchmark iterations
                    for _ in range(iterations):
                        start_time = time.perf_counter()
                        await client.send_command(
                            "Runtime.evaluate", {"expression": "Date.now()"}
                        )
                        end_time = time.perf_counter()
                        latencies.append(
                            (end_time - start_time) * 1000
                        )  # Convert to ms

        except Exception as e:
            print(f"CDP benchmark failed: {e}")
            return 0.0

        avg_latency = sum(latencies) / len(latencies)
        self.results["CDP"] = latencies
        return avg_latency

    async def benchmark_native_messaging_simulation(
        self, iterations: int = 100
    ) -> float:
        """Simulate Native Messaging protocol latency."""
        latencies = []

        # Simulate the overhead of Native Messaging
        # (JSON serialization/deserialization + IPC overhead)
        host = NativeMessagingHost()

        for _ in range(iterations):
            start_time = time.perf_counter()

            # Simulate message creation and handling
            test_message = {
                "type": "test_command",
                "data": {"action": "evaluate", "expression": "Date.now()"},
                "timestamp": time.time(),
            }

            # Simulate JSON serialization (part of native messaging overhead)
            json_data = json.dumps(test_message)
            parsed_data = json.loads(json_data)

            # Simulate handler processing
            response = await host._handle_ping(parsed_data)

            end_time = time.perf_counter()
            latencies.append((end_time - start_time) * 1000)  # Convert to ms

        avg_latency = sum(latencies) / len(latencies)
        self.results["Native Messaging (Simulated)"] = latencies
        return avg_latency

    async def benchmark_direct_process(self, iterations: int = 100) -> float:
        """Benchmark direct process communication latency."""
        latencies = []

        # Direct function call simulation (minimal overhead)
        for _ in range(iterations):
            start_time = time.perf_counter()

            # Simulate direct function execution
            result = {"timestamp": time.time(), "value": 42}
            _ = json.dumps(result)  # Minimal serialization

            end_time = time.perf_counter()
            latencies.append((end_time - start_time) * 1000)  # Convert to ms

        avg_latency = sum(latencies) / len(latencies)
        self.results["Direct Process"] = latencies
        return avg_latency

    def print_results(self):
        """Print benchmark results."""
        print("\n" + "=" * 60)
        print("PROTOCOL LATENCY BENCHMARK RESULTS")
        print("=" * 60)

        for protocol, latencies in self.results.items():
            if latencies:
                avg = sum(latencies) / len(latencies)
                min_latency = min(latencies)
                max_latency = max(latencies)
                median = sorted(latencies)[len(latencies) // 2]

                print(f"\n{protocol}:")
                print(f"  Average: {avg:.2f}ms")
                print(f"  Median:  {median:.2f}ms")
                print(f"  Min:     {min_latency:.2f}ms")
                print(f"  Max:     {max_latency:.2f}ms")
                print(f"  Samples: {len(latencies)}")
            else:
                print(f"\n{protocol}: No data collected")

        print("\n" + "=" * 60)

    def save_results(self, filepath: Path):
        """Save results to JSON file."""
        data = {"timestamp": time.time(), "results": {}}

        for protocol, latencies in self.results.items():
            if latencies:
                data["results"][protocol] = {
                    "latencies": latencies,
                    "average": sum(latencies) / len(latencies),
                    "min": min(latencies),
                    "max": max(latencies),
                    "median": sorted(latencies)[len(latencies) // 2],
                    "count": len(latencies),
                }

        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        print(f"Results saved to: {filepath}")


async def main():
    """Run the benchmark suite."""
    print("Starting Protocol Latency Benchmark...")
    print("This may take a few minutes...\n")

    benchmark = LatencyBenchmark()

    # Run benchmarks
    print("1. Benchmarking Direct Process communication...")
    direct_latency = await benchmark.benchmark_direct_process()
    print(f"   Average latency: {direct_latency:.2f}ms")

    print("\n2. Benchmarking Native Messaging (simulated)...")
    native_latency = await benchmark.benchmark_native_messaging_simulation()
    print(f"   Average latency: {native_latency:.2f}ms")

    print("\n3. Benchmarking CDP over WebSocket...")
    cdp_latency = await benchmark.benchmark_cdp()
    print(f"   Average latency: {cdp_latency:.2f}ms")

    # Print comprehensive results
    benchmark.print_results()

    # Save results
    results_path = Path(__file__).parent / "latency_results.json"
    benchmark.save_results(results_path)


if __name__ == "__main__":
    asyncio.run(main())
