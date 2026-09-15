#!/usr/bin/env bash
set -euo pipefail

CODE_ROOT="${CODE_ROOT:-/hpc2hdd/home/shuang886/Folding/catalog_pilot_code}"
GROUPS="${GROUPS:-/hpc2hdd/home/shuang886/Folding/quality_v1/exact_sequence_groups_quality_v1.jsonl.gz}"
OUTPUT_ROOT="${OUTPUT_ROOT:-/hpc2hdd/home/shuang886/Folding/low_homology_v1}"
BLOCK_SIZE="${BLOCK_SIZE:-128}"
WORKERS="${WORKERS:-1}"
MIN_ALIGNED_RESIDUES="${MIN_ALIGNED_RESIDUES:-50}"

: "${SLURM_ARRAY_TASK_ID:?SLURM_ARRAY_TASK_ID is required}"
START=$((SLURM_ARRAY_TASK_ID * BLOCK_SIZE))
END=$((START + BLOCK_SIZE))
mkdir -p "$OUTPUT_ROOT"
export PYTHONPATH="$CODE_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
exec python -u "$CODE_ROOT/scripts/audit_low_homology.py" \
  --groups "$GROUPS" \
  --output "$OUTPUT_ROOT/block-$(printf '%05d' "$SLURM_ARRAY_TASK_ID").jsonl" \
  --query-start "$START" \
  --query-end "$END" \
  --min-aligned-residues "$MIN_ALIGNED_RESIDUES" \
  --workers "$WORKERS"
