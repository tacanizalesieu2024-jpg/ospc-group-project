"""Benchmark sequential Python against Numba.

Measure compilation separately from steady-state execution.
Run the same Monte Carlo scenarios in both implementations.
"""

import argparse
import csv
import statistics
import time
from pathlib import Path

from src.model import generate_portfolio, simulate_scenario
from src.numba_version import simulate_scenario_numba


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios", type=int, default=200)
    parser.add_argument("--properties", type=int, default=500)
    parser.add_argument("--reps", type=int, default=5)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    # Generate one identical portfolio for both versions.
    portfolio = generate_portfolio(args.properties, args.seed)

    # First Numba call: includes JIT compilation.
    start = time.perf_counter()
    simulate_scenario_numba(portfolio, 0, args.seed)
    first_call = time.perf_counter() - start

    # Measure the sequential implementation.
    sequential_times = []

    for _ in range(args.reps):
        start = time.perf_counter()

        for s in range(args.scenarios):
            simulate_scenario(portfolio, s, args.seed)

        sequential_times.append(time.perf_counter() - start)

    # Measure Numba after compilation.
    numba_times = []

    for _ in range(args.reps):
        start = time.perf_counter()

        for s in range(args.scenarios):
            simulate_scenario_numba(portfolio, s, args.seed)

        numba_times.append(time.perf_counter() - start)

    # Use medians to reduce the influence of noisy measurements.
    sequential_median = statistics.median(sequential_times)
    numba_median = statistics.median(numba_times)
    speedup = sequential_median / numba_median

    print("\n--- NUMBA BENCHMARK ---")
    print(f"Scenarios: {args.scenarios}")
    print(f"Properties: {args.properties}")
    print(f"First Numba call: {first_call:.4f} s")
    print(f"Sequential median: {sequential_median:.4f} s")
    print(f"Numba median: {numba_median:.4f} s")
    print(f"Steady-state speedup: {speedup:.2f}x")

    # Save the measurements for the final project report.
    output = Path("results/numba_benchmark.csv")
    output.parent.mkdir(parents=True, exist_ok=True)

    with output.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "scenarios", "properties", "repetitions",
            "first_call_s", "sequential_median_s",
            "numba_median_s", "speedup"
        ])
        writer.writerow([
            args.scenarios, args.properties, args.reps,
            first_call, sequential_median, numba_median, speedup
        ])

    print(f"Results saved to {output}")


if __name__ == "__main__":
    main()
