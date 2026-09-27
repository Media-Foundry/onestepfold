#!/bin/bash
#SBATCH --partition=acd_u
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --gres=gpu:4
#SBATCH --mem=64G
#SBATCH --time=05:00:00
set -euo pipefail
ROOT=/data/user/shuang886/Folding/esmc_pretrained_gt_continuation_v1_20260927
export PROTENIX_ROOT_DIR=/data/user/shuang886/Folding/runtime_cache/protenix_v1_1
export LAYERNORM_TYPE=torch OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 CUBLAS_WORKSPACE_CONFIG=:4096:8
export PYTHONPATH="$ROOT/code_v1/src"
exec /data/user/shuang886/.conda/envs/fold/bin/python -m torch.distributed.run --standalone --nproc_per_node=4 "$ROOT/code_v1/scripts/train_pretrained_esmc_gt_continuation.py" --root "$ROOT" --size "$SIZE"
