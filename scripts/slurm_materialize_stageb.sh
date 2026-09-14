#!/usr/bin/env bash
set -euo pipefail

PILOT="${PILOT:-/hpc2hdd/home/shuang886/Folding/stageb_pilot/stageb_pilot.jsonl.gz}"
RAW_ROOT="${RAW_ROOT:-/hpc2hdd/home/shuang886/Folding/Dataset/raw/pdb_mmcif}"
OUTPUT_ROOT="${OUTPUT_ROOT:-/hpc2hdd/home/shuang886/Folding/processed_stageb_pilot}"
CODE_ROOT="${CODE_ROOT:-/hpc2hdd/home/shuang886/Folding/catalog_pilot_code}"
WORKER_COUNT="${WORKER_COUNT:-32}"
SHARD_SIZE="${SHARD_SIZE:-256}"

if [[ -z "${SLURM_ARRAY_TASK_ID:-}" ]]; then
    echo "SLURM_ARRAY_TASK_ID is required" >&2
    exit 2
fi

export PYTHONPATH="$CODE_ROOT/src"
exec python -u "$CODE_ROOT/scripts/materialize_stageb.py" \
    --pilot "$PILOT" \
    --raw-root "$RAW_ROOT" \
    --output-root "$OUTPUT_ROOT" \
    --worker-index "$SLURM_ARRAY_TASK_ID" \
    --worker-count "$WORKER_COUNT" \
    --shard-size "$SHARD_SIZE"
