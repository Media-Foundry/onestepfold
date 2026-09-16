#!/usr/bin/env bash
set -euo pipefail

if command -v module >/dev/null 2>&1; then
  module load slurm >/dev/null 2>&1 || true
fi
command -v sbatch >/dev/null 2>&1 || { echo "sbatch unavailable" >&2; exit 127; }

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INPUT_ROOT="${INPUT_ROOT:?INPUT_ROOT is required}"
OUTPUT_ROOT="${OUTPUT_ROOT:?OUTPUT_ROOT is required}"
PROTENIX_BIN="${PROTENIX_BIN:-protenix}"
PROTENIX_PYTHONPATH="${PROTENIX_PYTHONPATH:-}"
PROTENIX_ROOT_DIR="${PROTENIX_ROOT_DIR:-}"
PARTITION="${PARTITION:-i64m1tga800ue}"
TIME_LIMIT="${TIME_LIMIT:-08:00:00}"
SHARD_COUNT="${SHARD_COUNT:-8}"
SEED="${SEED:-101}"

[[ -s "$INPUT_ROOT/manifest.json" ]] || { echo "missing teacher manifest" >&2; exit 2; }
mkdir -p "$OUTPUT_ROOT/logs"

for setting in c2_s2 c4_s2; do
  export_args="ALL,INPUT_ROOT=$INPUT_ROOT,OUTPUT_ROOT=$OUTPUT_ROOT,SETTING=$setting"
  export_args+=",PROTENIX_BIN=$PROTENIX_BIN,PROTENIX_PYTHONPATH=$PROTENIX_PYTHONPATH"
  export_args+=",PROTENIX_ROOT_DIR=$PROTENIX_ROOT_DIR,SEED=$SEED"
  sbatch \
    --job-name="onefold-teacher-${setting}" \
    --partition="$PARTITION" --array="0-$((SHARD_COUNT - 1))" \
    --gres=gpu:a800:1 --cpus-per-task=8 --mem=64G --time="$TIME_LIMIT" \
    --output="$OUTPUT_ROOT/logs/%A_%a_${setting}.out" \
    --error="$OUTPUT_ROOT/logs/%A_%a_${setting}.err" \
    --export="$export_args,SHARD_ID=\${SLURM_ARRAY_TASK_ID}" \
    "$REPO_ROOT/scripts/slurm_teacher_pair.sh"
done
