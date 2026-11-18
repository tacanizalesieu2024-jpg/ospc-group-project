"""Figure for the open performance questions: original vs isolated runs.

Left:  parallel efficiency (median of 5 runs) when all jobs ran at once
       vs one job at a time.
Right: CPU-seconds used by the whole job (sacct TotalCPU) relative to the
       sequential job of the same batch. Same work everywhere, so anything
       above 0% means each core computed more slowly.

Run from the repository root:
    python analysis/plot_profiling.py
Writes results/profiling/efficiency_original_vs_isolated.png
"""

import csv
import glob
import statistics
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SCENARIOS = 20000
OUT = "results/profiling/efficiency_original_vs_isolated.png"


def efficiency(pattern):
    times = defaultdict(list)
    for path in glob.glob(pattern):
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            if "version" not in (reader.fieldnames or []):
                continue
            for r in reader:
                if int(r["n_scenarios"]) == SCENARIOS and r["version"] in ("sequential", "pool"):
                    times[(r["version"], int(r["workers"]))].append(float(r["elapsed_s"]))
    t1 = statistics.median(times[("sequential", 1)])
    workers = sorted(w for v, w in times if v == "pool")
    return workers, [t1 / statistics.median(times[("pool", w)]) / w for w in workers]


def seconds(text):
    parts = [float(p) for p in text.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    return parts[0] * 3600 + parts[1] * 60 + parts[2]


def cpu_inflation(path):
    """(workers, TotalCPU / TotalCPU of the sequential job - 1) per pool job."""
    with open(path) as f:
        rows = [r for r in csv.DictReader(f, delimiter="|") if "." not in r["JobID"]]
    base, points = None, {}
    for r in rows:
        cpu, workers = seconds(r["TotalCPU"]), int(r["AllocCPUS"]) // 2
        if r["NodeList"] != "haskell":
            continue                     # job 32308 ran on another node
        if base is None:
            base = cpu                   # first haskell job = sequential
            continue
        points[workers] = cpu / base - 1
    ws = sorted(points)
    return ws, [points[w] for w in ws]


fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))
for label, pattern, sacct, style in [
        ("All jobs at once (original)", "results/*.csv", "results/profiling/sacct_original.txt", "o-"),
        ("One job at a time (isolated)", "results/profiling/isolated_*.csv", "results/profiling/sacct_rerun.txt", "s-")]:
    w, e = efficiency(pattern)
    ax1.plot(w, [100 * x for x in e], style, label=label)
    w, c = cpu_inflation(sacct)
    ax2.plot(w, [100 * x for x in c], style, label=label)

for ax in (ax1, ax2):
    ax.set_xscale("log", base=2)
    ax.set_xticks([1, 2, 4, 8, 16, 32], ["1", "2", "4", "8", "16", "32"])
    ax.set_xlabel("Workers (processes)")
    ax.grid(alpha=0.3)
ax1.set_ylabel("Parallel efficiency (%)")
ax1.set_ylim(50, 105)
ax1.axhline(100, color="grey", lw=0.8, ls="--")
ax1.set_title("Efficiency, 20,000 scenarios")
ax1.legend(loc="lower left")
ax2.set_ylabel("Extra CPU-seconds vs sequential (%)")
ax2.set_title("Same work, more CPU time = slower cores")
ax2.axvspan(7, 9, color="orange", alpha=0.12)
ax2.annotate("8 workers = one full\n8-core L3 block", xy=(8, 2), ha="center", fontsize=8)
fig.tight_layout()
fig.savefig(OUT, dpi=150)
print(f"Written: {OUT}")
