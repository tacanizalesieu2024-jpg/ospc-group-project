#!/bin/bash
#SBATCH --job-name=numpy
#SBATCH --partition=cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=03:00:00
#SBATCH --output=numpy-%j.out

set -euo pipefail

cd "$SLURM_SUBMIT_DIR"

export PATH=/data/software/envs/ospc/bin:$PATH
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1

SCENARIOS=${SCENARIOS:-10000}
PROPERTIES=${PROPERTIES:-500}
REPS=${REPS:-5}

echo "node=$(hostname) job=$SLURM_JOB_ID"
echo "load before: $(cat /proc/loadavg)"

for batch in 16 64 128; do
    for rep in $(seq 1 "$REPS"); do
        echo "batch_size=$batch repetition=$rep"
        /usr/bin/time -v python src/vectorized.py \
            --scenarios "$SCENARIOS" \
            --properties "$PROPERTIES" \
            --batch-size "$batch" \
            --rep "$rep" \
            --csv "results/numpy_batch_${batch}_${SLURM_JOB_ID}.csv"
    done
done

echo "load after: $(cat /proc/loadavg)"
