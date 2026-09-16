#!/usr/bin/env bash
set -euo pipefail

CODE_ROOT="${CODE_ROOT:-/media/WDisk/Code/onestepfold}"
PYTHON="${PYTHON:-/home/husrcf/anaconda3/envs/AIAA/bin/python}"
ESM_SOURCE="${ESM_SOURCE:-/media/WDisk/Code/vendor/esm-bf343ba}"
GROUPS_PATH="${GROUPS_PATH:-/media/WDisk/Datasets/OneStepFold/splits_v1/groups.jsonl.gz}"
OUTPUT_ROOT="${OUTPUT_ROOT:-/media/WDisk/Datasets/OneStepFold/esmc_300m_final_v1}"
HF_HOME="${HF_HOME:-/media/WDisk/Models/hf_cache}"
HF_REVISION="${HF_REVISION:-f0d413606442e6b433d5e75e9aae3285ca9b137f}"
CODE_REVISION="${CODE_REVISION:-bf343ba264b650dff7a073643725f9aaa1fdbe8d}"
CODE_COMMIT="${CODE_COMMIT:-unknown}"

export HF_HOME HF_HUB_DISABLE_XET=1
export PYTHONPATH="$CODE_ROOT/src:$ESM_SOURCE${PYTHONPATH:+:$PYTHONPATH}"
mkdir -p "$OUTPUT_ROOT"

run_part() {
  local index="$1"
  local gpu="$2"
  local part
  part="$(printf 'part-%03d' "$index")"
  HIP_VISIBLE_DEVICES="$gpu" ROCR_VISIBLE_DEVICES="$gpu" \
    "$PYTHON" -u "$CODE_ROOT/scripts/build_esmc_cache.py" \
      --groups "$GROUPS_PATH" \
      --output-root "$OUTPUT_ROOT/$part" \
      --model-id biohub/ESMC-300M \
      --hf-revision "$HF_REVISION" \
      --code-revision "$CODE_REVISION" \
      --code-commit "$CODE_COMMIT" \
      --feature-variant final \
      --device cuda \
      --batch-tokens "${BATCH_TOKENS:-4096}" \
      --shard-tokens "${SHARD_TOKENS:-16384}" \
      --partition-count 2 \
      --partition-index "$index" \
      --local-files-only \
      >"$OUTPUT_ROOT/$part.log" 2>&1
}

run_part 0 0 &
pid0=$!
run_part 1 1 &
pid1=$!
status0=0
status1=0
wait "$pid0" || status0=$?
wait "$pid1" || status1=$?
if [[ "$status0" -ne 0 || "$status1" -ne 0 ]]; then
  printf 'ESMC partitions failed: part-000=%s part-001=%s\n' "$status0" "$status1" >&2
  exit 1
fi

"$PYTHON" -u "$CODE_ROOT/scripts/merge_esmc_cache_parts.py" \
  --parts-root "$OUTPUT_ROOT" \
  --groups "$GROUPS_PATH"

"$PYTHON" -u "$CODE_ROOT/scripts/validate_esmc_cache.py" \
  --cache-root "$OUTPUT_ROOT" \
  --groups "$GROUPS_PATH" \
  >"$OUTPUT_ROOT/validation.json"
