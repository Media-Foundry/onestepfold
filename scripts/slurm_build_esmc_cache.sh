#!/usr/bin/env bash
set -euo pipefail

CODE_ROOT="${CODE_ROOT:-/hpc2hdd/home/shuang886/Folding/catalog_pilot_code}"
ESM_ENV="${ESM_ENV:-/hpc2hdd/home/shuang886/Folding/envs/esmc}"
ESM_PYTHONPATH="${ESM_PYTHONPATH:-}"
GROUPS="${GROUPS:-/hpc2hdd/home/shuang886/Folding/splits_v1/groups.jsonl.gz}"
OUTPUT_ROOT="${OUTPUT_ROOT:?OUTPUT_ROOT is required}"
MODEL_ID="${MODEL_ID:-biohub/ESMC-600M}"
HF_REVISION="${HF_REVISION:?HF_REVISION is required}"
CODE_REVISION="${CODE_REVISION:?CODE_REVISION is required}"
CODE_COMMIT="${CODE_COMMIT:-$CODE_REVISION}"
FEATURE_VARIANT="${FEATURE_VARIANT:-all}"
BATCH_TOKENS="${BATCH_TOKENS:-4096}"
SHARD_TOKENS="${SHARD_TOKENS:-16384}"
LOCAL_FILES_ONLY="${LOCAL_FILES_ONLY:-0}"
LIMIT="${LIMIT:-}"

export PYTHONPATH="$CODE_ROOT/src${ESM_PYTHONPATH:+:$ESM_PYTHONPATH}${PYTHONPATH:+:$PYTHONPATH}"
export HF_HOME="${HF_HOME:-/hpc2hdd/home/shuang886/Folding/hf_cache}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-$HF_HOME/transformers}"
export HF_HUB_DISABLE_XET="${HF_HUB_DISABLE_XET:-1}"
args=(
  --groups "$GROUPS"
  --output-root "$OUTPUT_ROOT"
  --model-id "$MODEL_ID"
  --hf-revision "$HF_REVISION"
  --code-revision "$CODE_REVISION"
  --code-commit "$CODE_COMMIT"
  --feature-variant "$FEATURE_VARIANT"
  --batch-tokens "$BATCH_TOKENS"
  --shard-tokens "$SHARD_TOKENS"
)
if [[ -n "$LIMIT" ]]; then
  args+=(--limit "$LIMIT")
fi
if [[ "$LOCAL_FILES_ONLY" == "1" ]]; then
  args+=(--local-files-only)
fi
exec "$ESM_ENV/bin/python" -u "$CODE_ROOT/scripts/build_esmc_cache.py" "${args[@]}"
