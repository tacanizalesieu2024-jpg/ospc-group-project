#!/bin/bash
# Submit sequential + pool 1, 2, 4, 8, 16 workers as a chain of jobs that run
# ONE AT A TIME (same job name + --dependency=singleton).
# Run it from the repository root in the JupyterLab terminal (not with sbatch):
#
#   bash jobs/submit_isolated.sh            # any node
#   bash jobs/submit_isolated.sh haskell    # force the node of the original runs
#
# 32 workers is left out: it needs 64 CPUs, i.e. the JupyterLab session stopped,
# and it already ran alone in the original runs.

set -euo pipefail
NODE_OPT=()
if [ $# -ge 1 ]; then NODE_OPT=(--nodelist="$1"); fi

sbatch "${NODE_OPT[@]}" --dependency=singleton --cpus-per-task=2 \
    --export=ALL,VERSION=sequential jobs/isolated.sh
for workers in 1 2 4 8 16; do
    sbatch "${NODE_OPT[@]}" --dependency=singleton --cpus-per-task=$((2 * workers)) \
        --export=ALL,VERSION=pool,WORKERS=$workers jobs/isolated.sh
done
squeue -u "$USER"
