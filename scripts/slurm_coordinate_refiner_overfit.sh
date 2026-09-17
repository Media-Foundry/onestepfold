#!/bin/bash
#SBATCH --partition=acd_ue
#SBATCH --job-name=onefold-refiner-overfit
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --gres=gpu:1
#SBATCH --time=01:00:00

set -euo pipefail

module load anaconda3

CODE_ROOT="${CODE_ROOT:-/data/user/shuang886/Folding/projects/onestepfold}"
PYTHON_BIN="${PYTHON_BIN:-/data/user/shuang886/.conda/envs/fold/bin/python}"
TEACHER_ROOT="${TEACHER_ROOT:-/data/user/shuang886/Folding/stage1b/teacher_pairs_v3/output_diamondhill}"
MANIFEST="${MANIFEST:-$TEACHER_ROOT/control/teacher_pair_manifest_v1.jsonl.gz}"
ESMC_ROOT="${ESMC_ROOT:-/data/user/shuang886/Folding/esmc_600m_final_v1}"
OUTPUT_DIR="${OUTPUT_DIR:-/data/user/shuang886/Folding/stage1b/coordinate_refiner/overfit32_v1}"

cd "$CODE_ROOT"
export PYTHONPATH="$CODE_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
"$PYTHON_BIN" scripts/train_coordinate_refiner.py \
  --manifest "$MANIFEST" \
  --teacher-root "$TEACHER_ROOT" \
  --esmc-root "$ESMC_ROOT" \
  --output-dir "$OUTPUT_DIR" \
  --split train \
  --selection shortest \
  --limit 32 \
  --epochs "${EPOCHS:-400}" \
  --batch-size "${BATCH_SIZE:-8}" \
  --learning-rate "${LEARNING_RATE:-0.003}" \
  --hidden-dim "${HIDDEN_DIM:-128}" \
  --num-layers "${NUM_LAYERS:-2}" \
  --num-heads "${NUM_HEADS:-8}" \
  --seed 101 \
  --device cuda \
  --require-overfit
