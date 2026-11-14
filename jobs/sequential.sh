#!/bin/bash
# Sequential baseline as a batch job (one physical core).
#
# Submit with:
#   sbatch --export=ALL,SCENARIOS=10000 jobs/sequential.sh
#
#SBATCH --job-name=sequential
#SBATCH --partition=cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=03:00:00
#SBATCH --output=sequential-%j.out

set -euo pipefail

# Course Python environment (check the cluster instructions on Blackboard).
export PATH=/data/software/envs/ospc/bin:$PATH
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1

SCENARIOS=${SCENARIOS:-10000}
PROPERTIES=${PROPERTIES:-500}
REPS=${REPS:-5}

echo "node=$(hostname) job=$SLURM_JOB_ID"
echo "load before: $(cat /proc/loadavg)"

for rep in $(seq 1 "$REPS"); do
    /usr/bin/time -v python src/sequential.py --scenarios "$SCENARIOS" \
        --properties "$PROPERTIES" --rep "$rep" \
        --csv "results/sequential_${SLURM_JOB_ID}.csv"
done

echo "load after: $(cat /proc/loadavg)"
