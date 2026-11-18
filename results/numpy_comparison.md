# NumPy vectorization benchmark

Configuration: 10,000 scenarios, 500 properties, seed 2026.
Each configuration was run five times on the cluster.

| Version | Median runtime (s) | Speedup | Median peak memory (MiB) | Maximum peak memory (MiB) |
|---|---:|---:|---:|---:|
| Sequential | 61.4358 | 1.00x | 36.17 | 40.15 |
| NumPy batch 16 | 11.1515 | 5.51x | 48.25 | 50.08 |
| NumPy batch 64 | 10.6284 | 5.78x | 90.97 | 94.83 |
| NumPy batch 128 | 10.5196 | 5.84x | 154.88 | 156.47 |

Runtime uses elapsed_s from the shared CSV logger.
Peak memory uses Maximum resident set size from /usr/bin/time -v,
converted to MiB by dividing by 1024.

The NumPy version updates scenarios and properties together using arrays,
while retaining the dependent monthly loop and the baseline IRR solver.
Each scenario preserves the baseline random stream and draw order.

Correctness checks passed for 200 scenarios and 500 properties.
Annual IRRs match the sequential baseline within an absolute tolerance of
1e-10, and breach flags match exactly. Results are identical across batch
sizes 1, 7 and 64. Risk summaries also match across all benchmark runs.

Batch 128 had the lowest median runtime in this experiment.
Compared with batch 64, it reduced runtime by about 1% while increasing
median peak memory from 90.97 to 154.88 MiB. Larger batches therefore
provided a small additional runtime improvement at a higher memory cost.

The sequential and NumPy jobs overlapped on the same node for part of
the experiment, so shared-node activity may have influenced the timings.

Timing CSVs are stored in results/. Source job logs are numpy-32324.out
and sequential-32325.out.
