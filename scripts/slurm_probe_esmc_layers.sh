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
LIMIT="${LIMIT:-2000}"
FEATURE_VARIANT="${FEATURE_VARIANT:-all}"

export PYTHONPATH="$CODE_ROOT/src${ESM_PYTHONPATH:+:$ESM_PYTHONPATH}${PYTHONPATH:+:$PYTHONPATH}"
export HF_HOME="${HF_HOME:-/hpc2hdd/home/shuang886/Folding/hf_cache}"
export TRANSFORMERS_CACHE="${TRANSFORMERS_CACHE:-$HF_HOME/transformers}"

exec "$ESM_ENV/bin/python" -u "$CODE_ROOT/scripts/build_esmc_cache.py" \
  --groups "$GROUPS" \
  --output-root "$OUTPUT_ROOT" \
  --model-id "$MODEL_ID" \
  --hf-revision "$HF_REVISION" \
  --code-revision "$CODE_REVISION" \
  --code-commit "$CODE_REVISION" \
  --feature-variant "$FEATURE_VARIANT" \
  --limit "$LIMIT"
