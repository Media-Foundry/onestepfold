import argparse,json
from pathlib import Path
from score_pair_recovery import score_pair_recovery

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--arm',required=True);p.add_argument('--seed',type=int,required=True)
    a=p.parse_args();lock=json.loads((a.root/'training_lock.json').read_text())
    for step in lock['checkpoints']:
        score_pair_recovery(a.root,a.arm,a.seed,step,site_keys=lock['eval_sites'] if lock['cohort']=='n1' else None,
                            paired_intervals=lock['cohort']!='n1')
    (a.root/'runs'/a.arm/str(a.seed)/'score_complete.json').write_text(json.dumps(dict(complete=True))+'\n')
