"""Analysis for the two open performance questions.

Part A (needs a sacct export): for every job, how many CPUs of OUR jobs were
allocated at the same time, and how much of its allocated CPU it really used.
    sacct -j <ids> -P --format=JobID,JobName,NodeList,AllocCPUS,Start,End,Elapsed,TotalCPU,State \
        > results/profiling/sacct_original.txt

Part B: median times, speedup and efficiency of the original runs (results/*.csv)
next to the isolated reruns and the A/B pairs (results/profiling/*.csv).

Run from the repository root:
    python analysis/open_questions.py --sacct results/profiling/sacct_original.txt
"""

import argparse
import csv
import datetime as dt
import glob
import os
import statistics
from collections import defaultdict


def seconds(text):
    """Slurm duration ([D-]HH:MM:SS, MM:SS.mmm, ...) to seconds."""
    text = text.strip()
    if not text:
        return 0.0
    days = 0
    if "-" in text:
        d, text = text.split("-", 1)
        days = int(d)
    parts = [float(p) for p in text.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    h, m, s = parts
    return days * 86400 + h * 3600 + m * 60 + s


def read_sacct(path):
    jobs = {}
    with open(path) as f:
        rows = list(csv.DictReader(f, delimiter="|"))
    for r in rows:
        base = r["JobID"].split(".")[0]
        job = jobs.setdefault(base, {"id": base, "total_cpu": 0.0})
        if r["JobID"] == base:                        # allocation line
            job.update(name=r["JobName"], node=r["NodeList"], cpus=int(r["AllocCPUS"]),
                       start=dt.datetime.fromisoformat(r["Start"]),
                       end=dt.datetime.fromisoformat(r["End"]),
                       elapsed=seconds(r["Elapsed"]), state=r["State"])
        job["total_cpu"] = max(job["total_cpu"], seconds(r["TotalCPU"]))
    return [j for j in jobs.values() if "start" in j]


def part_a(path):
    jobs = sorted(read_sacct(path), key=lambda j: j["start"])
    t0 = min(j["start"] for j in jobs)
    print(f"Part A - placement and overlap ({path})")
    print(f"{'job':>8} {'name':<14} {'node':<10} {'cpus':>4} {'start':>7} {'end':>7} "
          f"{'cpu_use':>7} {'avg_our_cpus':>12}  overlapping jobs")
    for j in jobs:
        # time-weighted CPUs of our jobs allocated on the same node during this job
        events = sorted({j["start"], j["end"]} |
                        {t for o in jobs if o["node"] == j["node"]
                         for t in (o["start"], o["end"]) if j["start"] < t < j["end"]})
        busy = 0.0
        for a, b in zip(events, events[1:]):
            cpus = sum(o["cpus"] for o in jobs
                       if o["node"] == j["node"] and o["start"] < b and o["end"] > a)
            busy += cpus * (b - a).total_seconds()
        span = max((j["end"] - j["start"]).total_seconds(), 1e-9)
        others = [o["id"] for o in jobs if o is not j and o["node"] == j["node"]
                  and o["start"] < j["end"] and o["end"] > j["start"]]
        use = j["total_cpu"] / max(j["elapsed"] * j["cpus"], 1e-9)
        print(f"{j['id']:>8} {j['name'][:14]:<14} {j['node'][:10]:<10} {j['cpus']:>4} "
              f"{(j['start'] - t0).total_seconds():>6.0f}s {(j['end'] - t0).total_seconds():>6.0f}s "
              f"{use:>7.0%} {busy / span:>12.1f}  {','.join(others) or '-'}")
    print("cpu_use = TotalCPU / (Elapsed x AllocCPUS). Hyperthreads count as CPUs,")
    print("so one worker per physical core gives about 50% at best.\n")


def load_runs(pattern):
    times = defaultdict(list)
    nodes = defaultdict(set)
    for path in glob.glob(pattern):
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            if not {"version", "workers", "n_scenarios", "elapsed_s"} <= set(reader.fieldnames or []):
                continue                      # other formats, e.g. numba_benchmark.csv
            for r in reader:
                key = (r["version"], int(r["workers"]), int(r["n_scenarios"]))
                times[key].append(float(r["elapsed_s"]))
                nodes[key].add(r["node"])
    return times, nodes


def table(title, times, nodes, scenarios):
    keys = sorted(k for k in times if k[2] == scenarios and k[0] in ("sequential", "pool"))
    if not keys:
        print(f"{title}: no runs with {scenarios} scenarios yet\n")
        return
    base = times.get(("sequential", 1, scenarios))
    t1 = statistics.median(base) if base else None
    print(f"{title} ({scenarios} scenarios)")
    print(f"{'version':<11}{'workers':>7}{'runs':>5}{'median s':>10}{'min':>8}{'max':>8}"
          f"{'spread':>8}{'speedup':>8}{'effic.':>8}  node")
    for k in keys:
        t = times[k]
        med = statistics.median(t)
        spread = (max(t) - min(t)) / med
        sp = f"{t1 / med:8.2f}" if t1 else f"{'-':>8}"
        ef = f"{t1 / med / k[1]:8.0%}" if t1 else f"{'-':>8}"
        print(f"{k[0]:<11}{k[1]:>7}{len(t):>5}{med:>10.2f}{min(t):>8.2f}{max(t):>8.2f}"
              f"{spread:>8.0%}{sp}{ef}  {','.join(sorted(nodes[k]))}")
    print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sacct", nargs="*", default=[], help="sacct -P export(s)")
    parser.add_argument("--scenarios", type=int, default=20000)
    args = parser.parse_args()

    for path in args.sacct:
        part_a(path)

    print("Part B - original vs isolated runs")
    for title, pattern in [("Original runs, all jobs at once", "results/*.csv"),
                           ("Isolated reruns, one job at a time", "results/profiling/isolated_*.csv"),
                           ("Sequential vs pool(1), alternated in one job", "results/profiling/abab_*.csv")]:
        times, nodes = load_runs(pattern)
        table(title, times, nodes, args.scenarios)

    for path in sorted(glob.glob("results/profiling/abab_*.csv")):
        rows = list(csv.DictReader(open(path)))
        seq = [float(r["elapsed_s"]) for r in rows if r["version"] == "sequential"]
        pool = [float(r["elapsed_s"]) for r in rows if r["version"] == "pool"]
        diffs = [p - s for s, p in zip(seq, pool)]
        if diffs:
            print(f"{os.path.basename(path)}: pool(1) - sequential per pair = "
                  + ", ".join(f"{d:+.1f}s" for d in diffs)
                  + f"  (median {statistics.median(diffs):+.1f}s, "
                  f"{statistics.median(diffs) / statistics.median(seq):+.1%})")


if __name__ == "__main__":
    main()
