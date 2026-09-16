#!/usr/bin/env bash
set -euo pipefail

if command -v module >/dev/null 2>&1; then
  module load slurm >/dev/null 2>&1 || true
fi
command -v sbatch >/dev/null 2>&1 || {
  echo "sbatch is unavailable; load the Slurm module before submitting" >&2
  exit 127
}

CODE_ROOT="${CODE_ROOT:-/hpc2hdd/home/shuang886/Folding/catalog_pilot_code}"
PROTENIX_ROOT_DIR="${PROTENIX_ROOT_DIR:-/hpc2hdd/home/shuang886/Folding/protenix_stage0_pkg/v1_1/runtime}"
PROTENIX_SITE="${PROTENIX_SITE:-/hpc2hdd/home/shuang886/Folding/protenix_stage0_pkg/v1_1/site}"
TIMING_OVERLAY="${TIMING_OVERLAY:-/hpc2hdd/home/shuang886/Folding/protenix_stage0_pkg/v1_1/timing_overlay}"
PROTENIX_BIN="${PROTENIX_BIN:-$PROTENIX_SITE/bin/protenix}"
PROTENIX_PYTHON="${PROTENIX_PYTHON:-/hpc2ssd/softwares/anaconda3/envs/af3/bin/python}"
INPUT_JSON="${INPUT_JSON:?INPUT_JSON is required}"
OUTPUT_ROOT="${OUTPUT_ROOT:?OUTPUT_ROOT is required}"
PARTITION="${PARTITION:-i64m1tga800ue}"

mkdir -p "$OUTPUT_ROOT/logs"
for setting in c1_s1 c1_s5 c4_s1 c4_s5; do
  sbatch \
    --job-name="onefold-time-$setting" \
    --partition="$PARTITION" \
    --gres=gpu:a800:1 \
    --cpus-per-task=8 \
    --mem=64G \
    --time="${TIME_LIMIT:-02:00:00}" \
    --output="$OUTPUT_ROOT/logs/%j.out" \
    --error="$OUTPUT_ROOT/logs/%j.err" \
    --export="ALL,INPUT_JSON=$INPUT_JSON,OUTPUT_ROOT=$OUTPUT_ROOT,PROTENIX_BIN=$PROTENIX_BIN,PROTENIX_PYTHON=$PROTENIX_PYTHON,PROTENIX_PYTHONPATH=$TIMING_OVERLAY:$PROTENIX_SITE,PROTENIX_ROOT_DIR=$PROTENIX_ROOT_DIR,STAGE0_SETTING=$setting,KERNEL_BACKEND=torch,LAYERNORM_TYPE=torch" \
    "$CODE_ROOT/scripts/slurm_stage0_protenix.sh"
done
