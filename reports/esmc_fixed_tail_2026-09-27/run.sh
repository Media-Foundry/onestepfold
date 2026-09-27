#!/bin/bash
#SBATCH --partition=debug
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:05:00
set -euo pipefail
ROOT=/data/user/shuang886/Folding/esmc_fixed_tail_v1_20260927
PARENT=/data/user/shuang886/Folding/esmc_pretrained_gt_hpc3_v1_20260927
export OMP_NUM_THREADS=1 CUDA_VISIBLE_DEVICES=
if [[ "$MODE" == final ]]; then
 /data/user/shuang886/.conda/envs/fold/bin/python "$ROOT/report_pretrained_fixed_tail.py" --parent "$PARENT" --continuation /data/user/shuang886/Folding/esmc_pretrained_gt_continuation_v1_20260927 --output "$ROOT/continuation"
else
 /data/user/shuang886/.conda/envs/fold/bin/python "$ROOT/report_pretrained_fixed_tail.py" --parent "$PARENT" --output "$ROOT/first_stage"
fi
