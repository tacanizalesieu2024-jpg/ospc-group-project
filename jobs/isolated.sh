#!/bin/bash
# Open question 2: one benchmark configuration, run while NO other job of ours runs.
# Do not sbatch this file directly: jobs/submit_isolated.sh submits one per
# configuration with --dependency=singleton, so they run strictly one at a time.
#
# Writes to results/profiling/ so the original scaling plot (results/*.csv)
# is not changed.

#SBATCH --job-name=iso
#SBATCH --partition=cpu
#SBATCH --mem=8G
#SBATCH --time=01:00:00
#SBATCH --output=iso-%j.out

set -euo pipefail
export PATH=/data/software/envs/ospc/bin:$PATH
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1

VERSION=${VERSION:?set VERSION=sequential or VERSION=pool}
SCENARIOS=${SCENARIOS:-20000}
REPS=${REPS:-5}
WORKERS=${WORKERS:-$((SLURM_CPUS_PER_TASK / 2))}
OUT=results/profiling
CSV="$OUT/isolated_${SLURM_JOB_ID}.csv"
mkdir -p "$OUT"

echo "node=$(hostname) job=$SLURM_JOB_ID version=$VERSION workers=$WORKERS cpus=$SLURM_CPUS_PER_TASK"
echo "allowed CPUs: $(taskset -cp $$)"
echo "load before: $(cat /proc/loadavg)"

for rep in $(seq 1 "$REPS"); do
    if [ "$VERSION" = "sequential" ]; then
        python src/sequential.py --scenarios "$SCENARIOS" --rep "$rep" --csv "$CSV"
    else
        python src/pool.py --scenarios "$SCENARIOS" --workers "$WORKERS" --rep "$rep" --csv "$CSV"
    fi
done

echo "load after: $(cat /proc/loadavg)"
