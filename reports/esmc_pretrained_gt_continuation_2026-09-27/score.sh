#!/bin/bash
#SBATCH --partition=debug
#SBATCH --cpus-per-task=2
#SBATCH --mem=16G
#SBATCH --time=00:25:00
set -euo pipefail
ROOT=/data/user/shuang886/Folding/esmc_pretrained_gt_continuation_v1_20260927
export PROTENIX_ROOT_DIR=/data/user/shuang886/Folding/runtime_cache/protenix_v1_1
export LAYERNORM_TYPE=torch OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 CUBLAS_WORKSPACE_CONFIG=:4096:8
export PYTHONPATH="$ROOT/code_v1/src:$ROOT/code_v1/scripts:/data/user/shuang886/Folding/stage1b/coordinate_refiner/scaling_eval_deps_v1"
PY=/data/user/shuang886/.conda/envs/fold/bin/python
export ROOT CUDA_VISIBLE_DEVICES=
$PY -c 'import json,os;from pathlib import Path;r=Path(os.environ["ROOT"]);a=json.loads((r/ ("train_"+os.environ["SIZE"])/"checkpoint_audit_16384.json").read_text());assert a["complete"] and len(a["predictions"])==32 and all(x["exact"] for x in a["predictions"])'
for STEP in 4096 8192 16384; do
 $PY "$ROOT/code_v1/scripts/score_pretrained_esmc_gt.py" --root "$ROOT" --size "$SIZE" --step "$STEP"
done
