#!/usr/bin/env bash
set -euo pipefail

CODE_ROOT="${CODE_ROOT:-/hpc2hdd/home/shuang886/Folding/catalog_pilot_code}"
STAGEB_ROOT="${STAGEB_ROOT:-/hpc2hdd/home/shuang886/Folding/processed_stageb_v1}"
SI_MANIFEST="${SI_MANIFEST:-/hpc2hdd/home/shuang886/Folding/catalog_v1/sequence_identity_100_manifest.jsonl.gz}"
POLICY="${POLICY:-$CODE_ROOT/configs/gt_quality_v1.toml}"
OUTPUT_ROOT="${OUTPUT_ROOT:-/hpc2hdd/home/shuang886/Folding/quality_v1}"

export PYTHONPATH="$CODE_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
exec python -u "$CODE_ROOT/scripts/filter_stageb_quality.py" \
  --stageb-root "$STAGEB_ROOT" \
  --si-manifest "$SI_MANIFEST" \
  --policy "$POLICY" \
  --output-root "$OUTPUT_ROOT"
