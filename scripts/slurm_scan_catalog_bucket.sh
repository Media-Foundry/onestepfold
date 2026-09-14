#!/usr/bin/env bash
# One deterministic Stage A shard per Slurm array task.

set -euo pipefail

code_root="${CODE_ROOT:-/hpc2hdd/home/shuang886/Folding/catalog_pilot_code}"
raw_dir="${RAW_DIR:-/hpc2hdd/home/shuang886/Folding/Dataset/raw/pdb_mmcif}"
sifts_csv="${SIFTS_CSV:-/hpc2hdd/home/shuang886/Folding/Dataset/raw/sifts/2026-09-08/pdb_chain_uniprot.csv.gz}"
catalog_dir="${CATALOG_DIR:-/hpc2hdd/home/shuang886/Folding/catalog_v1}"
offset="${SHARD_OFFSET:-0}"
shard_count="${SHARD_COUNT:-256}"
workers="${WORKERS:-${SLURM_CPUS_PER_TASK:-1}}"
task_id="${SLURM_ARRAY_TASK_ID:?SLURM_ARRAY_TASK_ID is required}"
shard_id=$((offset + task_id))

if (( shard_id < 0 || shard_id >= shard_count )); then
  echo "invalid shard id: $shard_id (offset=$offset task=$task_id count=$shard_count)" >&2
  exit 2
fi

mkdir -p "$catalog_dir/errors" "$catalog_dir/logs"
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export PYTHONPATH="$code_root/src${PYTHONPATH:+:$PYTHONPATH}"

echo "host=$(hostname) job=${SLURM_JOB_ID:-none} array=${SLURM_ARRAY_JOB_ID:-none}_${task_id} shard=$shard_id cpus=${SLURM_CPUS_PER_TASK:-unknown} mem=${SLURM_MEM_PER_NODE:-unknown}"
exec python "$code_root/scripts/scan_mmcif_catalog.py" \
  --raw-dir "$raw_dir" \
  --sifts-csv "$sifts_csv" \
  --output "$catalog_dir/entries.jsonl.gz" \
  --errors "$catalog_dir/errors/errors.jsonl" \
  --workers "$workers" \
  --shard-id "$shard_id" \
  --num-shards "$shard_count" \
  --resume
