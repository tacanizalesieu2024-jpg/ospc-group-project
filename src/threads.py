"""Threads version: same chunks as the pool version, run by threads.

Expected result: no speedup. The monthly loop is pure Python and CPU-bound,
and the GIL lets only one thread run Python code at a time, so the threads
take turns instead of running in parallel. This is the control experiment
that shows why the main version uses processes.

Threads share memory, so the portfolio is NOT copied: every thread reads the
same object. Results come back in submission order (executor.map).

Example:  python src/threads.py --scenarios 200 --workers 4 --csv results/threads_local.csv
"""

import time
from concurrent.futures import ThreadPoolExecutor

from common import parse_args, run_and_log
from model import simulate_range


def make_chunks(n_scenarios, chunksize):
    return [(start, min(start + chunksize, n_scenarios))
            for start in range(0, n_scenarios, chunksize)]


def run(portfolio, args):
    chunksize = args.chunksize or max(1, args.scenarios // (4 * args.workers))
    chunks = make_chunks(args.scenarios, chunksize)

    t0 = time.perf_counter()
    executor = ThreadPoolExecutor(max_workers=args.workers)
    list(executor.map(lambda _: None, range(args.workers)))  # start the threads
    startup = time.perf_counter() - t0

    with executor:
        chunk_results = executor.map(
            lambda bounds: simulate_range(portfolio, bounds[0], bounds[1], args.seed),
            chunks)
        results = [r for chunk in chunk_results for r in chunk]
    return results, startup


if __name__ == "__main__":
    run_and_log("threads", parse_args(__doc__, parallel=True), run)
