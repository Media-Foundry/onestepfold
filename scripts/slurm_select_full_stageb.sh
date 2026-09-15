#!/usr/bin/env bash
set -euo pipefail

CATALOG_DIR="${CATALOG_DIR:-/hpc2hdd/home/shuang886/Folding/catalog_v1}"
CANDIDATES="${CANDIDATES:-$CATALOG_DIR/monomer_candidates.jsonl.gz}"
OUTPUT="${OUTPUT:-/hpc2hdd/home/shuang886/Folding/stageb_full_input/stageb_full_input.jsonl.gz}"
SUMMARY="${SUMMARY:-/hpc2hdd/home/shuang886/Folding/stageb_full_input/selection_summary.json}"
CODE_ROOT="${CODE_ROOT:-/hpc2hdd/home/shuang886/Folding/catalog_pilot_code}"

mkdir -p "$(dirname "$OUTPUT")"
exec python -u "$CODE_ROOT/scripts/select_stageb_pilot.py" \
  --catalog-dir "$CATALOG_DIR" \
  --candidates "$CANDIDATES" \
  --output "$OUTPUT" \
  --summary "$SUMMARY" \
  --stratified-count 84232 \
  --stress-count 0
