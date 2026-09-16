#!/usr/bin/env bash
set -euo pipefail

module load slurm

PARTITION="${PARTITION:-i64m512r}"
CODE_ROOT="${CODE_ROOT:-/hpc2hdd/home/shuang886/Folding/catalog_pilot_code}"
MANIFEST="${MANIFEST:-/hpc2hdd/home/shuang886/Folding/stage0_v1/temporal_dev_v1.jsonl.gz}"
PREDICTION_ROOT="${PREDICTION_ROOT:-/hpc2hdd/home/shuang886/Folding/stage0_v1/protenix_runs}"
OUTPUT_ROOT="${OUTPUT_ROOT:-/hpc2hdd/home/shuang886/Folding/stage0_v1/eval_v1}"
EVAL_SCRIPT="${EVAL_SCRIPT:-$CODE_ROOT/scripts/slurm_evaluate_stage0.sh}"

mkdir -p "$OUTPUT_ROOT"
for setting in c1_s1 c1_s2 c1_s5 c2_s1 c2_s2 c2_s5 c4_s1 c4_s2 c4_s5; do
  sbatch \
    --job-name="onefold-eval-$setting" \
    --partition="$PARTITION" \
    --cpus-per-task="${CPUS_PER_TASK:-4}" \
    --mem="${MEMORY:-32G}" \
    --time="${TIME_LIMIT:-02:00:00}" \
    --output="$OUTPUT_ROOT/slurm-%x-%j.out" \
    --error="$OUTPUT_ROOT/slurm-%x-%j.err" \
    --export="ALL,STAGE0_SETTING=$setting,CODE_ROOT=$CODE_ROOT,MANIFEST=$MANIFEST,PREDICTION_ROOT=$PREDICTION_ROOT,OUTPUT_ROOT=$OUTPUT_ROOT" \
    "$EVAL_SCRIPT"
done
