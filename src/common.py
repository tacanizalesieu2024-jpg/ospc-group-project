"""Command line, timing and CSV logging shared by every version."""

import argparse
import csv
import datetime
import os
import socket
import time

from model import generate_portfolio, summarize

CSV_COLUMNS = [
    "version", "workers", "n_scenarios", "n_properties", "repetition",
    "elapsed_s", "startup_s", "compute_s", "load_s", "write_s",
    "node", "slurm_job_id", "node_load_1min", "date",
    "irr_p5", "breach_count",
]


def parse_args(description, parallel):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--scenarios", type=int, default=200, help="problem size: number of scenarios")
    parser.add_argument("--properties", type=int, default=500, help="number of properties")
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--rep", type=int, default=1, help="repetition number, written to the CSV")
    parser.add_argument("--csv", default=None, help="append one timing row to this CSV file")
    if parallel:
        parser.add_argument("--workers", type=int, default=2)
        parser.add_argument("--chunksize", type=int, default=0,
                            help="scenarios per task (0 = scenarios / (4 x workers))")
    return parser.parse_args()


def run_and_log(version, args, run):
    """Time the three phases separately and log one CSV row.

    `run(portfolio, args)` must return (results, startup_seconds).
    """
    t0 = time.perf_counter()
    portfolio = generate_portfolio(args.properties, args.seed)   # "load" phase
    t1 = time.perf_counter()
    results, startup = run(portfolio, args)                      # startup + compute
    t2 = time.perf_counter()
    summary = summarize(results)                                 # "write" phase
    print(f"[{version}] scenarios={summary['n_scenarios']} properties={args.properties}")
    print(f"[{version}] 5th-percentile IRR = {summary['irr_p5']:.4%}  "
          f"median IRR = {summary['irr_median']:.4%}")
    print(f"[{version}] covenant breached in {summary['breach_count']} scenarios "
          f"({summary['breach_probability']:.2%})")
    t3 = time.perf_counter()

    elapsed = t2 - t1
    row = {
        "version": version,
        "workers": getattr(args, "workers", 1),
        "n_scenarios": args.scenarios,
        "n_properties": args.properties,
        "repetition": args.rep,
        "elapsed_s": f"{elapsed:.4f}",
        "startup_s": f"{startup:.4f}",
        "compute_s": f"{elapsed - startup:.4f}",
        "load_s": f"{t1 - t0:.4f}",
        "write_s": f"{t3 - t2:.4f}",
        "node": socket.gethostname(),
        "slurm_job_id": os.environ.get("SLURM_JOB_ID", "local"),
        "node_load_1min": f"{os.getloadavg()[0]:.2f}",
        "date": datetime.datetime.now().isoformat(timespec="seconds"),
        "irr_p5": repr(summary["irr_p5"]),
        "breach_count": summary["breach_count"],
    }
    print(f"[{version}] workers={row['workers']} load={row['load_s']}s "
          f"startup={row['startup_s']}s compute={row['compute_s']}s elapsed={row['elapsed_s']}s")
    if args.csv:
        os.makedirs(os.path.dirname(args.csv) or ".", exist_ok=True)
        new_file = not os.path.exists(args.csv)
        with open(args.csv, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            if new_file:
                writer.writeheader()
            writer.writerow(row)
    return results
