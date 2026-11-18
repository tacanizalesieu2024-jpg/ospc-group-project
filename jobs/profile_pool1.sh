#!/bin/bash
# Open question 1: is pool(1) slower than sequential, or did it just get a worse core?
#
# Both versions run INSIDE THE SAME JOB (same node, same 2 CPUs), alternating
# A B A B ..., so any difference left is caused by the pool, not by placement.
# Then cProfile compares where each version spends its time.
#
# Submit from the repository root:
#   sbatch jobs/profile_pool1.sh
#
#SBATCH --job-name=profile-pool1
#SBATCH --partition=cpu
#SBATCH --cpus-per-task=2
#SBATCH --mem=4G
#SBATCH --time=01:00:00
#SBATCH --output=profile-pool1-%j.out

set -euo pipefail
export PATH=/data/software/envs/ospc/bin:$PATH
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1

SCENARIOS=${SCENARIOS:-20000}      # same size as the original runs
PAIRS=${PAIRS:-5}
PROFILE_SCENARIOS=${PROFILE_SCENARIOS:-2000}
OUT=results/profiling
CSV="$OUT/abab_${SLURM_JOB_ID}.csv"
mkdir -p "$OUT"

echo "node=$(hostname) job=$SLURM_JOB_ID cpus=$SLURM_CPUS_PER_TASK"
echo "allowed CPUs: $(taskset -cp $$)"
lscpu | grep -E "^(Model name|CPU\(s\)|Thread\(s\) per core|Core\(s\) per socket|Socket\(s\)|CPU max MHz)" || true
echo "load before: $(cat /proc/loadavg)"

for rep in $(seq 1 "$PAIRS"); do
    python src/sequential.py --scenarios "$SCENARIOS" --rep "$rep" --csv "$CSV"
    python src/pool.py --scenarios "$SCENARIOS" --workers 1 --rep "$rep" --csv "$CSV"
done

python analysis/profile_versions.py --scenarios "$PROFILE_SCENARIOS" --out "$OUT"

echo "load after: $(cat /proc/loadavg)"
