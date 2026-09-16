#!/usr/bin/env bash
set -euo pipefail

# Submit one independent c2_s2 Protenix run with the cycle-state hook enabled.
# The hook is provided through PROTENIX_PYTHONPATH/sitecustomize.py.

if command -v module >/dev/null 2>&1; then
  module load slurm >/dev/null 2>&1 || true
fi
command -v sbatch >/dev/null 2>&1 || {
  echo "sbatch is unavailable; load the Slurm module before submitting" >&2
  exit 127
}

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INPUT_JSON="${INPUT_JSON:?INPUT_JSON is required}"
OUTPUT_ROOT="${OUTPUT_ROOT:?OUTPUT_ROOT is required}"
PROTENIX_BIN="${PROTENIX_BIN:-protenix}"
PROTENIX_PYTHON="${PROTENIX_PYTHON:-python}"
PROTENIX_PYTHONPATH="${PROTENIX_PYTHONPATH:?PROTENIX_PYTHONPATH must include the router sitecustomize overlay}"
PROTENIX_ROOT_DIR="${PROTENIX_ROOT_DIR:-}"
PARTITION="${PARTITION:-i64m1tga800ue}"
TIME_LIMIT="${TIME_LIMIT:-04:00:00}"
KERNEL_BACKEND="${KERNEL_BACKEND:-torch}"
LAYERNORM_TYPE="${LAYERNORM_TYPE:-torch}"
SEED="${SEED:-101}"
MODEL_NAME="${MODEL_NAME:-protenix_mini_esm_v0.5.0}"

mkdir -p "$OUTPUT_ROOT/logs"
export_args="ALL,INPUT_JSON=$INPUT_JSON,OUTPUT_ROOT=$OUTPUT_ROOT"
export_args+=",PROTENIX_BIN=$PROTENIX_BIN,PROTENIX_PYTHON=$PROTENIX_PYTHON"
export_args+=",PROTENIX_PYTHONPATH=$PROTENIX_PYTHONPATH,PROTENIX_ROOT_DIR=$PROTENIX_ROOT_DIR"
export_args+=",KERNEL_BACKEND=$KERNEL_BACKEND,LAYERNORM_TYPE=$LAYERNORM_TYPE"
export_args+=",SEED=$SEED,MODEL_NAME=$MODEL_NAME,STAGE0_SETTING=c2_s2,RUN_VARIANCE=0"

sbatch \
  --job-name=onefold-0e-c2s2 \
  --partition="$PARTITION" \
  --gres=gpu:a800:1 \
  --cpus-per-task=8 \
  --mem=64G \
  --time="$TIME_LIMIT" \
  --output="$OUTPUT_ROOT/logs/%j.out" \
  --error="$OUTPUT_ROOT/logs/%j.err" \
  --export="$export_args" \
  "$REPO_ROOT/scripts/slurm_stage0_protenix.sh"
