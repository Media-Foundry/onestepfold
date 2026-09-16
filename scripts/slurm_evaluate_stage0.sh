#!/usr/bin/env bash
set -euo pipefail

CODE_ROOT="${CODE_ROOT:-/hpc2hdd/home/shuang886/Folding/catalog_pilot_code}"
PYTHON="${PYTHON:-/hpc2ssd/softwares/anaconda3/bin/python}"
MANIFEST="${MANIFEST:-/hpc2hdd/home/shuang886/Folding/stage0_v1/temporal_dev_v1.jsonl.gz}"
PREDICTION_ROOT="${PREDICTION_ROOT:-/hpc2hdd/home/shuang886/Folding/stage0_v1/protenix_runs}"
OUTPUT_ROOT="${OUTPUT_ROOT:-/hpc2hdd/home/shuang886/Folding/stage0_v1/eval_v1}"

: "${STAGE0_SETTING:?STAGE0_SETTING is required (for example c4_s5)}"

mkdir -p "$OUTPUT_ROOT"
export PYTHONPATH="$CODE_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"

exec "$PYTHON" -u "$CODE_ROOT/scripts/evaluate_stage0.py" \
  --manifest "$MANIFEST" \
  --prediction-root "$PREDICTION_ROOT" \
  --setting "$STAGE0_SETTING" \
  --output "$OUTPUT_ROOT/$STAGE0_SETTING.json"
