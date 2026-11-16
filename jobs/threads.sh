#!/bin/bash
# Threads version as a batch job. One job = one thread count, REPS repetitions.
#
# Submit with (threads = half the CPUs, i.e. one thread per physical core):
#   sbatch --cpus-per-task=8 --export=ALL,SCENARIOS=20000 jobs/threads.sh
#
#SBATCH --job-name=threads
#SBATCH --partition=cpu
#SBATCH --mem=4G
#SBATCH --time=02:00:00
#SBATCH --output=threads-%j.out

set -euo pipefail

# Course Python environment (check the cluster instructions on Blackboard).
export PATH=/data/software/envs/ospc/bin:$PATH

# No hidden threads inside numerical libraries: only our own threads run.
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1

SCENARIOS=${SCENARIOS:-20000}
PROPERTIES=${PROPERTIES:-500}
REPS=${REPS:-5}
# Slurm counts hardware threads as CPUs: 2 CPUs = 1 physical core.
WORKERS=${WORKERS:-$((SLURM_CPUS_PER_TASK / 2))}

echo "node=$(hostname) job=$SLURM_JOB_ID cpus=$SLURM_CPUS_PER_TASK threads=$WORKERS"
echo "load before: $(cat /proc/loadavg)"

for rep in $(seq 1 "$REPS"); do
    python src/threads.py --scenarios "$SCENARIOS" --properties "$PROPERTIES" \
        --workers "$WORKERS" --rep "$rep" \
        --csv "results/threads_${SLURM_JOB_ID}.csv"
done

echo "load after: $(cat /proc/loadavg)"
