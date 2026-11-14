"""Sequential baseline: one process, one scenario after another.

Example:  python src/sequential.py --scenarios 200 --csv results/sequential_local.csv
"""

from common import parse_args, run_and_log
from model import simulate_range


def run(portfolio, args):
    results = simulate_range(portfolio, 0, args.scenarios, args.seed)
    return results, 0.0  # no worker startup in the sequential version


if __name__ == "__main__":
    run_and_log("sequential", parse_args(__doc__, parallel=False), run)
