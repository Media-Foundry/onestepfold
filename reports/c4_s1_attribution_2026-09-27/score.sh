#!/bin/bash
#SBATCH --partition=debug
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=00:30:00
set -euo pipefail
RUN_ROOT=/data/user/shuang886/Folding/c4_s1_attribution_v1_20260927
export PYTHONPATH="$RUN_ROOT/code_precision_v1/src"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
exec /data/user/shuang886/.conda/envs/fold/bin/python -u "$RUN_ROOT/code_precision_v1/scripts/score_c4_s1_attribution.py" --root "$RUN_ROOT" ${PRECISION_FLAG:-}
