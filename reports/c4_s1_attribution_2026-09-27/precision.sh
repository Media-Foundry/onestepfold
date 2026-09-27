#!/bin/bash
#SBATCH --partition=acd_u
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=64G
#SBATCH --gres=gpu:1
#SBATCH --time=01:30:00
set -euo pipefail
RUN_ROOT=/data/user/shuang886/Folding/c4_s1_attribution_v1_20260927
export PYTHONPATH="$RUN_ROOT/code_precision_v1/src"
export PROTENIX_ROOT_DIR=/data/user/shuang886/Folding/runtime_cache/protenix_v1_1
export LAYERNORM_TYPE=torch OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export CUBLAS_WORKSPACE_CONFIG=:4096:8
exec /data/user/shuang886/.conda/envs/fold/bin/python -u "$RUN_ROOT/code_precision_v1/scripts/run_c4_s1_precision.py" --root "$RUN_ROOT" --worker "$SLURM_ARRAY_TASK_ID"
