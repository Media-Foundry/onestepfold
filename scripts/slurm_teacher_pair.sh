#!/usr/bin/env bash
set -euo pipefail

INPUT_ROOT="${INPUT_ROOT:?INPUT_ROOT is required}"
OUTPUT_ROOT="${OUTPUT_ROOT:?OUTPUT_ROOT is required}"
SHARD_ID="${SHARD_ID:?SHARD_ID is required}"
SETTING="${SETTING:?SETTING is required}"
PROTENIX_BIN="${PROTENIX_BIN:-protenix}"
MODEL_NAME="${MODEL_NAME:-protenix_mini_esm_v0.5.0}"
SEED="${SEED:-101}"
KERNEL_BACKEND="${KERNEL_BACKEND:-torch}"
LAYERNORM_TYPE="${LAYERNORM_TYPE:-torch}"

case "$SETTING" in
  c2_s2) CYCLES=2; STEPS=2 ;;
  c4_s2) CYCLES=4; STEPS=2 ;;
  *) echo "unsupported teacher setting: $SETTING" >&2; exit 2 ;;
esac

INPUT_JSON="$INPUT_ROOT/shard-${SHARD_ID}/input.json"
OUT="$OUTPUT_ROOT/$SETTING/shard-${SHARD_ID}/seed-$SEED"
[[ -s "$INPUT_JSON" ]] || { echo "missing input: $INPUT_JSON" >&2; exit 2; }
mkdir -p "$OUT"
printf '%s\n' "$PROTENIX_BIN pred -i $INPUT_JSON -o $OUT -s $SEED -n $MODEL_NAME -c $CYCLES -p $STEPS -e 1 --use_default_params false --use_msa false --use_template false --dtype bf16 --trimul_kernel $KERNEL_BACKEND --triatt_kernel $KERNEL_BACKEND --enable_tf32 false" > "$OUT/command.txt"

{
  date --iso-8601=seconds
  hostname
  echo "setting=$SETTING shard=$SHARD_ID"
  nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader || true
  /usr/bin/time -v "$PROTENIX_BIN" pred \
    -i "$INPUT_JSON" -o "$OUT" -s "$SEED" -n "$MODEL_NAME" \
    -c "$CYCLES" -p "$STEPS" -e 1 --use_default_params false \
    --use_msa false --use_template false --dtype bf16 \
    --trimul_kernel "$KERNEL_BACKEND" --triatt_kernel "$KERNEL_BACKEND" \
    --enable_tf32 false
} > "$OUT/run.log" 2>&1
