#!/usr/bin/env bash
set -euo pipefail

# Submit one independent Slurm job per Stage 0 factorial point.  Keeping each
# point as a separate one-GPU job makes retries and scheduler placement simple.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INPUT_JSON="${INPUT_JSON:?INPUT_JSON is required}"
OUTPUT_ROOT="${OUTPUT_ROOT:?OUTPUT_ROOT is required}"
PROTENIX_BIN="${PROTENIX_BIN:-protenix}"
PROTENIX_PYTHON="${PROTENIX_PYTHON:-python}"
PROTENIX_PYTHONPATH="${PROTENIX_PYTHONPATH:-}"
PROTENIX_ROOT_DIR="${PROTENIX_ROOT_DIR:-}"
KERNEL_BACKEND="${KERNEL_BACKEND:-torch}"
LAYERNORM_TYPE="${LAYERNORM_TYPE:-torch}"
PARTITION="${PARTITION:-i64m1tga800ue}"
TIME_LIMIT="${TIME_LIMIT:-12:00:00}"
RUN_VARIANCE="${RUN_VARIANCE:-0}"
VARIANCE_INPUT_JSON="${VARIANCE_INPUT_JSON:-$INPUT_JSON}"

mkdir -p "$OUTPUT_ROOT/logs"

settings=(c1_s1 c1_s2 c1_s5 c2_s1 c2_s2 c2_s5 c4_s1 c4_s2 c4_s5)
for setting in "${settings[@]}"; do
  export_args="ALL,INPUT_JSON=$INPUT_JSON,OUTPUT_ROOT=$OUTPUT_ROOT,PROTENIX_BIN=$PROTENIX_BIN"
  export_args+=",PROTENIX_PYTHON=$PROTENIX_PYTHON,KERNEL_BACKEND=$KERNEL_BACKEND,LAYERNORM_TYPE=$LAYERNORM_TYPE,STAGE0_SETTING=$setting"
  export_args+=",RUN_VARIANCE=$RUN_VARIANCE,VARIANCE_INPUT_JSON=$VARIANCE_INPUT_JSON"
  if [[ -n "$PROTENIX_PYTHONPATH" ]]; then
    export_args+=",PROTENIX_PYTHONPATH=$PROTENIX_PYTHONPATH"
  fi
  if [[ -n "$PROTENIX_ROOT_DIR" ]]; then
    export_args+=",PROTENIX_ROOT_DIR=$PROTENIX_ROOT_DIR"
  fi

  sbatch \
    --job-name="onefold-$setting" \
    --partition="$PARTITION" \
    --gres=gpu:a800:1 \
    --cpus-per-task=8 \
    --mem=64G \
    --time="$TIME_LIMIT" \
    --output="$OUTPUT_ROOT/logs/%j.out" \
    --error="$OUTPUT_ROOT/logs/%j.err" \
    --export="$export_args" \
    "$REPO_ROOT/scripts/slurm_stage0_protenix.sh"
done
