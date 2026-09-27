#!/bin/bash
#SBATCH --partition=debug
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=00:15:00
set -euo pipefail
ROOT=/data/user/shuang886/Folding/esmc_pretrained_gt_continuation_v1_20260927
export PROTENIX_ROOT_DIR=/data/user/shuang886/Folding/runtime_cache/protenix_v1_1
export LAYERNORM_TYPE=torch OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 CUBLAS_WORKSPACE_CONFIG=:4096:8
export PYTHONPATH="$ROOT/code_v1/src:$ROOT/code_v1/scripts:/data/user/shuang886/Folding/stage1b/coordinate_refiner/scaling_eval_deps_v1"
PY=/data/user/shuang886/.conda/envs/fold/bin/python
export CUDA_VISIBLE_DEVICES=
export PYTHONPATH="/data/user/shuang886/Folding/esmc_endpoint_objective_v1_20260926/plot_deps_v2:$ROOT/code_v1/src:$ROOT/code_v1/scripts"
$PY "$ROOT/code_v1/scripts/report_pretrained_gt_continuation.py" --root "$ROOT" --output "$ROOT/final_report" --through-step 16384
