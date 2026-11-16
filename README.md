# Monte Carlo risk of a Madrid rental property portfolio

Operating Systems and Parallel Computing, group project.

**Question:** for a fund holding 500 Madrid rental properties financed with
floating-rate debt, what is the 5th-percentile 10-year IRR, and what is the
probability that the loan-to-value (LTV) covenant is breached at least once?

**Team:** 

## Layout

| Path | Content |
|---|---|
| `src/model.py` | Shared model: portfolio, random streams, one-scenario simulation |
| `src/common.py` | Command line, timing and CSV logging shared by all versions |
| `src/sequential.py` | Sequential baseline |
| `src/pool.py` | Process-pool version (`multiprocessing.Pool`) |
| `tests/check_equivalence.py` | Automated check: parallel results = sequential results |
| `jobs/` | Slurm job scripts |
| `results/` | Raw timings, one CSV row per run |
| `analysis/plot_scaling.py` | Builds the scaling table and plot from the CSVs |

## Run on the cluster

Open a terminal in JupyterLab (https://jupyter.iesci.tech:8085), then:

```bash
git clone <URL of this repository>
cd <repository folder>
export PATH=/data/software/envs/ospc/bin:$PATH
```

### Small configuration (under five minutes)

```bash
python tests/check_equivalence.py
python src/sequential.py --scenarios 200
python src/pool.py --scenarios 200 --workers 2
```

Both versions must print the same 5th-percentile IRR and the same breach count.

### Measurements (batch jobs)

Problem size = number of scenarios (`SCENARIOS`). Each job runs 5 repetitions.

```bash
# Sequential baseline
sbatch --export=ALL,SCENARIOS=10000 jobs/sequential.sh

# Strong scaling of the pool: 1, 2, 4, 8, 16, 32 workers (2 CPUs = 1 physical core)
for cpus in 2 4 8 16 32 64; do
    sbatch --cpus-per-task=$cpus --export=ALL,SCENARIOS=10000 jobs/pool.sh
done

squeue -u $USER          # R = running, PD = waiting
```

The 64-CPU job only starts when the JupyterLab session is stopped, because the
session uses 2 of the 64 CPUs of the account.

### Table and plot

```bash
python analysis/plot_scaling.py --scenarios 10000
```

Writes `results/scaling.png` and prints run time, speedup and efficiency.

## Reproducibility

- Every scenario has its own random stream, derived from `(seed, scenario index)`
  with NumPy's `SeedSequence`. Results do not depend on the number of workers,
  the chunk size, or the order in which workers finish.
- Each run records node, Slurm job ID, node load and date in its CSV row.

## Use of generative AI


