"""Process-pool version: scenarios are split into chunks, one chunk per task.

Why processes: the monthly loop is pure Python and CPU-bound, so the GIL lets
only one thread run it at a time. Each process has its own interpreter and GIL.

Data movement: the portfolio is sent to each worker once (initializer), not
with every task. A task is just (start, stop); only small results come back.

Example:  python src/pool.py --scenarios 200 --workers 4 --csv results/pool_local.csv
"""

import multiprocessing
import time

from common import parse_args, run_and_log
from model import simulate_range

_portfolio = None
_seed = None


def _init_worker(portfolio, seed):
    global _portfolio, _seed
    _portfolio = portfolio
    _seed = seed


def _ready(_):
    return True


def _simulate_chunk(bounds):
    start, stop = bounds
    return simulate_range(_portfolio, start, stop, _seed)


def make_chunks(n_scenarios, chunksize):
    return [(start, min(start + chunksize, n_scenarios))
            for start in range(0, n_scenarios, chunksize)]


def run(portfolio, args):
    chunksize = args.chunksize or max(1, args.scenarios // (4 * args.workers))
    chunks = make_chunks(args.scenarios, chunksize)

    t0 = time.perf_counter()
    pool = multiprocessing.Pool(args.workers, initializer=_init_worker,
                                initargs=(portfolio, args.seed))
    pool.map(_ready, range(args.workers), chunksize=1)  # wait until workers answer
    startup = time.perf_counter() - t0                  # measured overhead

    with pool:
        # map returns the chunks in submission order, whatever order workers finish in.
        chunk_results = pool.map(_simulate_chunk, chunks, chunksize=1)
    results = [r for chunk in chunk_results for r in chunk]
    return results, startup


if __name__ == "__main__":
    run_and_log("pool", parse_args(__doc__, parallel=True), run)
