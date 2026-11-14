"""Build the strong-scaling table and plot from the raw CSV files in results/.

Run from the repository root:  python analysis/plot_scaling.py --scenarios 10000
Writes results/scaling.png and prints the table.

Speedup(p) = T(1) / T(p), efficiency(p) = speedup(p) / p, with T = median elapsed
time. T(1) is the sequential baseline if it was measured at the same size,
otherwise the pool with 1 worker.
"""

import argparse
import csv
import glob
import statistics
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

parser = argparse.ArgumentParser()
parser.add_argument("--scenarios", type=int, required=True, help="problem size to plot")
parser.add_argument("--properties", type=int, default=500)
parser.add_argument("--out", default="results/scaling.png")
args = parser.parse_args()

times = defaultdict(list)  # (version, workers) -> elapsed times
for path in sorted(glob.glob("results/*.csv")):
    with open(path, newline="") as f:
        for row in csv.DictReader(f):
            if (int(row["n_scenarios"]) == args.scenarios
                    and int(row["n_properties"]) == args.properties):
                times[(row["version"], int(row["workers"]))].append(float(row["elapsed_s"]))

pool_workers = sorted(w for (v, w) in times if v == "pool")
if not pool_workers:
    raise SystemExit(f"No pool runs with {args.scenarios} scenarios found in results/")

if ("sequential", 1) in times:
    base_label, base_times = "sequential baseline", times[("sequential", 1)]
elif ("pool", 1) in times:
    base_label, base_times = "pool with 1 worker", times[("pool", 1)]
else:
    raise SystemExit("Need a sequential run or a pool run with 1 worker as reference")
t1 = statistics.median(base_times)

print(f"Reference T(1) = {t1:.2f} s ({base_label}, {len(base_times)} runs)")
print(f"{'workers':>7} {'runs':>4} {'median s':>9} {'min s':>8} {'max s':>8} {'speedup':>8} {'effic.':>7}")
speedup, low, high, efficiency = [], [], [], []
for w in pool_workers:
    t = times[("pool", w)]
    med = statistics.median(t)
    speedup.append(t1 / med)
    low.append(t1 / max(t))    # slowest run = lowest speedup
    high.append(t1 / min(t))
    efficiency.append(t1 / med / w)
    print(f"{w:>7} {len(t):>4} {med:>9.2f} {min(t):>8.2f} {max(t):>8.2f} "
          f"{speedup[-1]:>8.2f} {efficiency[-1]:>7.0%}")

INK, MUTED, BLUE = "#1f2328", "#6b7280", "#2563eb"
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))

ax1.plot(pool_workers, pool_workers, linestyle="--", color=MUTED, linewidth=1.5,
         label="Ideal (linear)")
err = [[s - l for s, l in zip(speedup, low)], [h - s for s, h in zip(speedup, high)]]
ax1.errorbar(pool_workers, speedup, yerr=err, color=BLUE, linewidth=2, marker="o",
             markersize=7, capsize=4, label="Process pool (median, min-max)")
ax1.set_xscale("log", base=2)
ax1.set_yscale("log", base=2)
ax1.set_ylabel("Speedup  T(1) / T(p)")
ax1.set_title("Strong scaling: speedup", loc="left", color=INK)
ax1.legend(frameon=False)

ax2.axhline(1.0, linestyle="--", color=MUTED, linewidth=1.5)
ax2.plot(pool_workers, efficiency, color=BLUE, linewidth=2, marker="o", markersize=7)
ax2.set_xscale("log", base=2)
ax2.set_ylim(0, 1.15)
ax2.set_ylabel("Efficiency  speedup / workers")
ax2.set_title("Strong scaling: efficiency", loc="left", color=INK)

for ax in (ax1, ax2):
    ax.set_xticks(pool_workers)
    ax.set_xticklabels([str(w) for w in pool_workers])
    ax.set_xlabel("Workers (processes)")
    ax.grid(True, color="#e5e7eb", linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
ax1.set_yticks(pool_workers)
ax1.set_yticklabels([str(w) for w in pool_workers])

fig.suptitle(f"{args.scenarios:,} scenarios x {args.properties} properties, "
             f"reference: {base_label}", x=0.01, ha="left", fontsize=10, color=MUTED)
fig.tight_layout()
fig.savefig(args.out, dpi=200)
print(f"Saved {args.out}")
