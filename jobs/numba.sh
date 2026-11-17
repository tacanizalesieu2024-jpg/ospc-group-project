#!/bin/bash

# Numba JIT-compiled Monte Carlo simulation.
# Submit with:
# sbatch --export=ALL,SCENARIOS=10000 jobs/numba.sh

#SBATCH --job-name=numba
#SBATCH --partition=cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=03:00:00
#SBATCH --output=numba-%j.out

set -euo pipefail

# Use the same Python environment as the sequential version.
export PATH=/data/software/envs/ospc/bin:$PATH

# Avoid extra threads from numerical libraries.
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1

SCENARIOS=${SCENARIOS:-10000}
PROPERTIES=${PROPERTIES:-500}
REPS=${REPS:-5}

echo "node=$(hostname) job=$SLURM_JOB_ID"
echo "load before: $(cat /proc/loadavg)"

# Run the reproducible benchmark.
# It measures compilation, sequential runtime,
# Numba runtime and steady-state speedup.
#
# Run as a module so imports from src work correctly.
# Repetitions are handled by the Python benchmark.
 /usr/bin/time -v python -m analysis.benchmark_numba \
    --scenarios "$SCENARIOS" \
    --properties "$PROPERTIES" \
    --reps "$REPS"

echo "load after: $(cat /proc/loadavg)"
