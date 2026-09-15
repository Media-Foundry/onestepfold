#!/usr/bin/env bash
# Submit the full 84k monomer Stage B materialization as deterministic hash buckets.
set -euo pipefail

module load slurm

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
input_root="${INPUT_ROOT:-/hpc2hdd/home/shuang886/Folding/stageb_full_input}"
output_root="${OUTPUT_ROOT:-/hpc2hdd/home/shuang886/Folding/processed_stageb_v1}"
raw_root="${RAW_ROOT:-/hpc2hdd/home/shuang886/Folding/Dataset/raw/pdb_mmcif}"
code_root="${CODE_ROOT:-/hpc2hdd/home/shuang886/Folding/catalog_pilot_code}"
log_dir="$output_root/logs/slurm"
mkdir -p "$output_root/errors" "$log_dir"

sbatch \
  --job-name=onefold-stageb \
  --partition="${PARTITION:-i64m512r}" \
  --array="0-31%32" \
  --cpus-per-task=64 \
  --mem=500G \
  --exclusive \
  --time=04:00:00 \
  --output="$log_dir/%x-%A_%a.out" \
  --error="$log_dir/%x-%A_%a.err" \
  --export="ALL,PILOT=$input_root/stageb_full_input.jsonl.gz,RAW_ROOT=$raw_root,OUTPUT_ROOT=$output_root,CODE_ROOT=$code_root,WORKER_COUNT=32,SHARD_SIZE=256" \
  "$code_root/scripts/slurm_materialize_stageb.sh"
