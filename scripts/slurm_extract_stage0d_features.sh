#!/usr/bin/env bash
set -euo pipefail

CODE_ROOT="${CODE_ROOT:-/hpc2hdd/home/shuang886/Folding/catalog_pilot_code}"
PYTHON="${PYTHON:-/hpc2ssd/softwares/anaconda3/bin/python}"
EVAL_ROOT="${EVAL_ROOT:-/hpc2hdd/home/shuang886/Folding/stage0_v1/eval_v1}"
MANIFEST="${MANIFEST:-/hpc2hdd/home/shuang886/Folding/stage0_v1/temporal_dev_v1.jsonl.gz}"
GROUPS_PATH="${GROUPS_PATH:-/hpc2hdd/home/shuang886/Folding/stage0_v1/temporal_dev_groups_v1.jsonl.gz}"
OUTPUT="${OUTPUT:-/hpc2hdd/home/shuang886/Folding/stage0_v1/stage0d/features_v1.json}"

mkdir -p "$(dirname "$OUTPUT")"
export PYTHONPATH="$CODE_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"

exec "$PYTHON" -u "$CODE_ROOT/scripts/extract_stage0d_features.py" \
  --eval-root "$EVAL_ROOT" \
  --manifest "$MANIFEST" \
  --groups "$GROUPS_PATH" \
  --output "$OUTPUT" \
  --workers "${SLURM_CPUS_PER_TASK:-8}"
