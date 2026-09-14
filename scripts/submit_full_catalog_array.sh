#!/usr/bin/env bash
# Submit the 256 Stage A shards across the configured CPU node pools.

set -euo pipefail
module load slurm

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
catalog_dir="${CATALOG_DIR:-/hpc2hdd/home/shuang886/Folding/catalog_v1}"
log_dir="$catalog_dir/logs/slurm"
mkdir -p "$catalog_dir/errors" "$log_dir"

script="$repo_root/scripts/slurm_scan_catalog_bucket.sh"

submit_bucket() {
  local partition="$1"
  local offset="$2"
  local count="$3"
  local cpus="$4"
  local concurrency="$5"
  sbatch \
    --job-name=onefold-gt \
    --partition="$partition" \
    --array="0-$((count - 1))%$concurrency" \
    --cpus-per-task="$cpus" \
    --mem=500G \
    --exclusive \
    --time=02:00:00 \
    --output="$log_dir/%x-%A_%a.out" \
    --error="$log_dir/%x-%A_%a.err" \
    --export="ALL,CATALOG_DIR=$catalog_dir,SHARD_OFFSET=$offset,SHARD_COUNT=256,WORKERS=$cpus" \
    "$script"
}

# 256 total shards. r/re and u/ue share their physical node pools; Slurm
# serializes full-node requests there while allowing both buckets to queue.
submit_bucket long_cpu   0   160 64  106
submit_bucket i64m512r   160 24  64  13
submit_bucket i64m512re  184 24  64  13
submit_bucket a128m512u  208 24  128 16
submit_bucket a128m512ue 232 24  128 16
