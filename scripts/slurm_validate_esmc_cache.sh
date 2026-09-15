#!/usr/bin/env bash
set -euo pipefail

CODE_ROOT="${CODE_ROOT:-/hpc2hdd/home/shuang886/Folding/catalog_pilot_code}"
ESM_ENV="${ESM_ENV:-/hpc2ssd/softwares/anaconda3/envs/af3}"
ESM_PYTHONPATH="${ESM_PYTHONPATH:-}"
CACHE_ROOT="${CACHE_ROOT:?CACHE_ROOT is required}"
GROUPS="${GROUPS:-/hpc2hdd/home/shuang886/Folding/splits_v1/groups.jsonl.gz}"

export PYTHONPATH="$CODE_ROOT/src${ESM_PYTHONPATH:+:$ESM_PYTHONPATH}${PYTHONPATH:+:$PYTHONPATH}"
exec "$ESM_ENV/bin/python" -u "$CODE_ROOT/scripts/validate_esmc_cache.py" \
  --cache-root "$CACHE_ROOT" \
  --groups "$GROUPS"
