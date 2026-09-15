#!/usr/bin/env bash
set -euo pipefail

INPUT_JSON="${INPUT_JSON:?INPUT_JSON is required}"
OUTPUT_ROOT="${OUTPUT_ROOT:?OUTPUT_ROOT is required}"
PROTENIX_BIN="${PROTENIX_BIN:-protenix}"
PROTENIX_PYTHON="${PROTENIX_PYTHON:-python}"
PROTENIX_PYTHONPATH="${PROTENIX_PYTHONPATH:-}"
PROTENIX_ROOT_DIR="${PROTENIX_ROOT_DIR:-}"
MODEL_NAME="${MODEL_NAME:-protenix_mini_esm_v0.5.0}"
SEED="${SEED:-101}"
RUN_VARIANCE="${RUN_VARIANCE:-0}"
VARIANCE_INPUT_JSON="${VARIANCE_INPUT_JSON:-$INPUT_JSON}"
STAGE0_SETTING="${STAGE0_SETTING:-all}"
VARIANCE_SEEDS=(101 103 107 109 113)

if [[ -n "$PROTENIX_PYTHONPATH" ]]; then
  export PYTHONPATH="$PROTENIX_PYTHONPATH${PYTHONPATH:+:$PYTHONPATH}"
fi
if [[ -n "$PROTENIX_ROOT_DIR" ]]; then
  export PROTENIX_ROOT_DIR
fi

declare -a SETTINGS=(
  "c1_s1 1 1"
  "c1_s2 1 2"
  "c1_s5 1 5"
  "c2_s1 2 1"
  "c2_s2 2 2"
  "c2_s5 2 5"
  "c4_s1 4 1"
  "c4_s2 4 2"
  "c4_s5 4 5"
)

if [[ "$STAGE0_SETTING" == "all" ]]; then
  SELECTED_SETTINGS=("${SETTINGS[@]}")
else
  SELECTED_SETTINGS=()
  for setting in "${SETTINGS[@]}"; do
    read -r name cycles steps <<< "$setting"
    if [[ "$name" == "$STAGE0_SETTING" ]]; then
      SELECTED_SETTINGS+=("$setting")
    fi
  done
  if [[ "${#SELECTED_SETTINGS[@]}" -ne 1 ]]; then
    echo "Unknown Stage 0 setting: $STAGE0_SETTING" >&2
    exit 2
  fi
fi

mkdir -p "$OUTPUT_ROOT/meta/$STAGE0_SETTING" "$OUTPUT_ROOT/logs"
{
  date --iso-8601=seconds
  hostname
  command -v "$PROTENIX_BIN"
  "$PROTENIX_BIN" --version || true
  printf 'protenix_pythonpath=%s\n' "${PYTHONPATH:-}"
  printf 'protenix_root_dir=%s\n' "${PROTENIX_ROOT_DIR:-}"
  printf 'model_name=%s\n' "$MODEL_NAME"
  printf 'stage0_setting=%s\n' "$STAGE0_SETTING"
  nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader || true
  "$PROTENIX_PYTHON" - <<'PY'
import sys
import torch

print("python", sys.version.replace("\n", " "))
print("torch", torch.__version__)
print("cuda", torch.version.cuda)
print("tf32", torch.backends.cuda.matmul.allow_tf32)
PY
} > "$OUTPUT_ROOT/meta/$STAGE0_SETTING/environment.txt" 2>&1

run_one() {
  local input_json="$1"
  local seed="$2"
  local name="$3"
  local cycles="$4"
  local steps="$5"
  local root="$6"
  mkdir -p "$root"
  cat > "$root/command.txt" <<EOF
$PROTENIX_BIN pred -i $input_json -o $root -s $seed -n $MODEL_NAME -c $cycles -p $steps -e 1 --use_default_params false --use_msa false --use_template false --dtype bf16
EOF
  {
    echo "{\"name\":\"$name\",\"seed\":$seed,\"cycles\":$cycles,\"steps\":$steps}"
    /usr/bin/time -v "$PROTENIX_BIN" pred \
      -i "$input_json" \
      -o "$root" \
      -s "$seed" \
      -n "$MODEL_NAME" \
      -c "$cycles" \
      -p "$steps" \
      -e 1 \
      --use_default_params false \
      --use_msa false \
      --use_template false \
      --dtype bf16
  } > "$root/run.log" 2>&1
}

for setting in "${SELECTED_SETTINGS[@]}"; do
  read -r name cycles steps <<< "$setting"
  run_one "$INPUT_JSON" "$SEED" "$name" "$cycles" "$steps" \
    "$OUTPUT_ROOT/$name/seed-$SEED"
done

if [[ "$RUN_VARIANCE" == "1" ]]; then
  for seed in "${VARIANCE_SEEDS[@]}"; do
    for setting in "${SELECTED_SETTINGS[@]}"; do
      read -r name cycles steps <<< "$setting"
      run_one "$VARIANCE_INPUT_JSON" "$seed" "$name" "$cycles" "$steps" \
        "$OUTPUT_ROOT/variance/$name/seed-$seed"
    done
  done
fi

cat > "$OUTPUT_ROOT/meta/$STAGE0_SETTING/timing_components.json" <<'EOF'
{
  "sequence_ms": null,
  "trunk_ms": null,
  "structure_ms": null,
  "confidence_ms": null,
  "end_to_end_wall_ms": "available in each run.log via /usr/bin/time -v",
  "status": "Protenix CLI does not expose component timers; add internal hooks before paper benchmark"
}
EOF
