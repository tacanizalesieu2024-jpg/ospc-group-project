"""Open question 1: why is the pool with 1 worker slower than the sequential version?

Profiles the SAME scenarios two ways and writes text reports to --out:
  * sequential: cProfile around simulate_range in the main process
  * pool(1):    cProfile INSIDE the worker process (profiling the main process
                would only show it waiting), plus wall-clock time of every pool
                phase: create, first answer, compute, shut down.
It also records which CPUs each process may use and the CPU it last ran on,
to check whether both versions really used the same core.

Run from the repository root:
    python analysis/profile_versions.py --scenarios 2000 --out results/profiling
"""

import argparse
import cProfile
import io
import multiprocessing
import os
import pstats
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from model import generate_portfolio, simulate_range  # noqa: E402

TOP = 15


def cpu_info():
    """Allowed CPUs and the CPU this process last ran on (/proc/self/stat field 39)."""
    allowed = sorted(os.sched_getaffinity(0))
    try:
        with open("/proc/self/stat") as f:
            last_cpu = int(f.read().rsplit(")", 1)[1].split()[36])
    except (OSError, IndexError, ValueError):
        last_cpu = -1
    return f"pid={os.getpid()} allowed_cpus={allowed} last_cpu={last_cpu}"


def stats_text(profile, title):
    buf = io.StringIO()
    stats = pstats.Stats(profile, stream=buf).strip_dirs().sort_stats("tottime")
    stats.print_stats(TOP)
    return f"===== {title} =====\n{buf.getvalue()}"


# ---- worker side -----------------------------------------------------------
_portfolio = None
_seed = None


def _init_worker(portfolio, seed):
    global _portfolio, _seed
    _portfolio, _seed = portfolio, seed


def _profiled_chunk(bounds):
    start, stop = bounds
    prof = cProfile.Profile()
    t0 = time.perf_counter()
    prof.enable()
    results = simulate_range(_portfolio, start, stop, _seed)
    prof.disable()
    compute = time.perf_counter() - t0
    return results, compute, stats_text(prof, f"pool worker, scenarios {start}-{stop}"), cpu_info()


# ---- main ------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios", type=int, default=2000)
    parser.add_argument("--properties", type=int, default=500)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--out", default="results/profiling")
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    tag = os.environ.get("SLURM_JOB_ID", "local")
    portfolio = generate_portfolio(args.properties, args.seed)
    lines = [f"node={os.uname().nodename} job={tag} scenarios={args.scenarios} "
             f"properties={args.properties} start_method={multiprocessing.get_start_method()}"]

    # 1) Sequential, profiled in this process.
    prof = cProfile.Profile()
    t0 = time.perf_counter()
    prof.enable()
    seq_results = simulate_range(portfolio, 0, args.scenarios, args.seed)
    prof.disable()
    seq_time = time.perf_counter() - t0
    seq_cpu = cpu_info()
    seq_report = stats_text(prof, "sequential (main process)")

    # 2) Pool with 1 worker, one chunk = same work, every phase timed.
    t0 = time.perf_counter()
    pool = multiprocessing.Pool(1, initializer=_init_worker, initargs=(portfolio, args.seed))
    t1 = time.perf_counter()
    pool.map(abs, [0])                       # first answer: worker is alive
    t2 = time.perf_counter()
    [(pool_results, worker_compute, worker_report, worker_cpu)] = pool.map(
        _profiled_chunk, [(0, args.scenarios)])
    t3 = time.perf_counter()
    pool.close()
    pool.join()
    t4 = time.perf_counter()

    same = [r[0] for r in seq_results] == [r[0] for r in pool_results]
    phases = {
        "pool_create_s": t1 - t0,
        "first_answer_s": t2 - t1,
        "map_total_s": t3 - t2,
        "worker_compute_s": worker_compute,
        "map_overhead_s": (t3 - t2) - worker_compute,   # send task + return results
        "shutdown_s": t4 - t3,
    }
    pool_total = t4 - t0

    lines += [
        "",
        f"sequential compute (profiled)  : {seq_time:9.3f} s   {seq_cpu}",
        f"pool(1) total, create->join    : {pool_total:9.3f} s   main {cpu_info()}",
        f"pool(1) worker compute         : {worker_compute:9.3f} s   worker {worker_cpu}",
        "",
        "pool(1) phases:",
        *[f"  {k:<18}{v:9.4f} s" for k, v in phases.items()],
        "",
        f"pool overhead outside compute  : {pool_total - worker_compute:9.4f} s "
        f"({(pool_total - worker_compute) / pool_total:.2%} of pool total)",
        f"worker compute vs sequential   : {worker_compute / seq_time - 1:+.2%}",
        f"identical IRRs                 : {same}",
        "",
        "Note: cProfile adds the same overhead to both versions, so compare the",
        "two profiles with each other, not with the unprofiled CSV timings.",
        "",
        seq_report,
        worker_report,
    ]
    text = "\n".join(lines)
    path = os.path.join(args.out, f"profile_{tag}.txt")
    with open(path, "w") as f:
        f.write(text + "\n")
    print(text)
    print(f"\nWritten: {path}")


if __name__ == "__main__":
    main()
