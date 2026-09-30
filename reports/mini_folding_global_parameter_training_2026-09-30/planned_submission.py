import pathlib,subprocess,json
r=pathlib.Path('/data/user/shuang886/Folding/folding_global_parameter_training_v1_20260930')
batch='''#!/bin/bash
set -euo pipefail
ROOT=/data/user/shuang886/Folding/folding_global_parameter_training_v1_20260930
BASE=/data/user/shuang886/Folding
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 LAYERNORM_TYPE=torch
export PROTENIX_ROOT_DIR="$BASE/protenix_stage0_pkg/v1_1/runtime"
export PYTHONPATH="$ROOT/code/src:$ROOT/code/scripts:$ROOT/code"
cd "$ROOT"
if [[ "$1" == prepare || "$1" == audit ]]; then export CUDA_VISIBLE_DEVICES='' ROCR_VISIBLE_DEVICES=''; fi
exec /data/user/shuang886/.conda/envs/fold/bin/python -u code/scripts/train_folding_global_parameter.py --root "$ROOT" --mode "$1" --baseline "$BASE/folding_global_distance_training_v1_20260930" --calibration "$BASE/folding_parameter_budget_v1_20260930_retry1"
'''
(r/'batch.sh').write_text(batch);jobs=[]
for mode in ['prepare','preflight','train','audit']:
 args=['sbatch','--parsable','--partition=acd_u','--nodes=1','--nodelist=ACD1-18','--ntasks=1','--cpus-per-task=8','--gres=gpu:1','--mem=64G','--time='+('04:00:00' if mode=='train' else '00:20:00'),'--no-requeue','--kill-on-invalid-dep=yes','--job-name=fold_gparam_'+mode,f'--output={r}/{mode}-%j.out']
 if jobs:args+=['--dependency=afterok:'+jobs[-1]['job']]
 job=subprocess.check_output(args+[str(r/'batch.sh'),mode],text=True).strip();jobs.append(dict(mode=mode,job=job,command=args+[str(r/'batch.sh'),mode]));(r/'submission.json').write_text(json.dumps(dict(jobs=jobs),indent=2)+'\n')
print(json.dumps([(x['mode'],x['job']) for x in jobs]))
