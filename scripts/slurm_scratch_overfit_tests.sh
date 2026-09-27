#!/bin/bash
#SBATCH --partition=debug
#SBATCH --job-name=scratch-loss-tests
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=00:10:00
set -euo pipefail
: "${CODE_ROOT:?}"
export PYTHONPATH="$CODE_ROOT/src"
export CUDA_VISIBLE_DEVICES= OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
cd "$CODE_ROOT"
/data/user/shuang886/.conda/envs/fold/bin/python -m pytest -q \
  tests/test_smooth_lddt_supervision.py tests/test_capacity_c.py
