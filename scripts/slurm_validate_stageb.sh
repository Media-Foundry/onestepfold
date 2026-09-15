#!/usr/bin/env bash
set -euo pipefail

CODE_ROOT="${CODE_ROOT:-/hpc2hdd/home/shuang886/Folding/catalog_pilot_code}"
STAGEB_ROOT="${STAGEB_ROOT:-/hpc2hdd/home/shuang886/Folding/processed_stageb_v1}"
SUMMARY="${SUMMARY:-$STAGEB_ROOT/stageb_v1_summary.json}"

exec python -u "$CODE_ROOT/scripts/validate_stageb_pilot.py" \
  --root "$STAGEB_ROOT" \
  --output "$SUMMARY"
