#!/usr/bin/env bash
set -euo pipefail

CODE_ROOT="${CODE_ROOT:-/hpc2hdd/home/shuang886/Folding/catalog_pilot_code}"
ESM_ENV="${ESM_ENV:-/hpc2hdd/home/shuang886/Folding/envs/esmc}"
CACHE_ROOT="${CACHE_ROOT:?CACHE_ROOT is required}"
GROUPS="${GROUPS:-/hpc2hdd/home/shuang886/Folding/splits_v1/groups.jsonl.gz}"
TRAIN_MANIFEST="${TRAIN_MANIFEST:-/hpc2hdd/home/shuang886/Folding/splits_v1/train.jsonl.gz}"
OUTPUT="${OUTPUT:?OUTPUT is required}"
LIMIT="${LIMIT:-500}"

export PYTHONPATH="$CODE_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
exec "$ESM_ENV/bin/python" -u "$CODE_ROOT/scripts/probe_esmc_layers.py" \
  --cache-root "$CACHE_ROOT" \
  --groups "$GROUPS" \
  --train-manifest "$TRAIN_MANIFEST" \
  --output "$OUTPUT" \
  --limit "$LIMIT"
