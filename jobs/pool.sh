#!/bin/bash
# Process-pool version as a batch job. One job = one worker count, REPS repetitions.
#
# Submit with (workers = half the CPUs, i.e. one worker per physical core):
#   sbatch --cpus-per-task=8 --export=ALL,SCENARIOS=10000 jobs/pool.sh
#
#SBATCH --job-name=pool
#SBATCH --partition=cpu
#SBATCH --mem=8G
#SBATCH --time=02:00:00
#SBATCH --output=pool-%j.out

set -euo pipefail

# Course Python environment (check the cluster instructions on Blackboard).
export PATH=/data/software/envs/ospc/bin:$PATH

# One thread per worker inside numerical libraries: no oversubscription.
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1

SCENARIOS=${SCENARIOS:-10000}
PROPERTIES=${PROPERTIES:-500}
REPS=${REPS:-5}
# Slurm counts hardware threads as CPUs: 2 CPUs = 1 physical core.
WORKERS=${WORKERS:-$((SLURM_CPUS_PER_TASK / 2))}

echo "node=$(hostname) job=$SLURM_JOB_ID cpus=$SLURM_CPUS_PER_TASK workers=$WORKERS"
echo "load before: $(cat /proc/loadavg)"

for rep in $(seq 1 "$REPS"); do
    python src/pool.py --scenarios "$SCENARIOS" --properties "$PROPERTIES" \
        --workers "$WORKERS" --rep "$rep" \
        --csv "results/pool_${SLURM_JOB_ID}.csv"
done

echo "load after: $(cat /proc/loadavg)"
