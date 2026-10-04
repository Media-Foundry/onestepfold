"""Audit archived replication and prepare sequence-only candidates, without training."""
import argparse,csv,hashlib,json
from pathlib import Path
from fastglycan.context_coverage import aa_table_projection,repeated_source_inventory


def audit_context_coverage(out,pool):
    out.mkdir(parents=True,exist_ok=True)
    root=Path('reports/mini_task_readout_2026-10-03')
    load=lambda p:json.loads(p.read_text())
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    lock=load(root/'lock.json')
    selection=load(Path('reports/mini_factor_student_pilot_2026-10-02/selection.json'))
    protocol=load(Path('reports/mini_factor_student_pilot_2026-10-02/selection_protocol.json'))
    assert sha(pool)==protocol['pool_sha256']
    inventory=repeated_source_inventory(lock['contexts'],lock['aa'])
    with (out/'inventory.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(inventory[0]),lineterminator='\n');w.writeheader();w.writerows(inventory)
    analyses={};paths=[root/'lock.json',pool]
    for arm in ('restricted','expanded'):
        path=root/f'train_{arm}.json';cases=load(path)['cases'];paths.append(path)
        analysis=aa_table_projection(cases,lock['aa'])
        # Independent categorical least squares, including all 20 zero-WT columns.
        import numpy as np
        y=np.array([np.mean(c['target_delta'][:2],axis=0) for c in cases])
        types=sorted({c['wt'] for c in cases});design=np.array([[c['wt']==t for t in types] for c in cases],dtype=float)
        oracle=design@np.linalg.lstsq(design,y,rcond=None)[0]
        floor=float(np.square(oracle-y).sum()/np.square(y).sum())
        assert abs(floor-analysis['irreducible_global_normalized_mse'])<1e-12
        analysis['independent_lstsq_floor']=floor
        analysis['observed_aa_only_terminal_losses']={}
        for seed in (231301,231303):
            path=root/'runs'/f'{arm}_aa_only_s{seed}'/'report.json';paths.append(path)
            report=load(path);analysis['observed_aa_only_terminal_losses'][str(seed)]=float(np.mean([s['normalized_mse'] for s in report['history'][-1]['sites']]))
        analyses[arm]=analysis
    blocked=set(selection['blocked_components'])|{r['component'] for r in selection['rows']}
    excluded={'1en7','5i27','2d00','3pmd','1l12','1l04','1tay','1tdy','1gob','2rn2','1izr','1izq'}
    requests=[]
    for row in load(pool)['rows']:
        g=row['group_id'];component=selection['all_components'].get(g)
        if row['role']!='train' or component is None or component in blocked:continue
        if not 80<=len(row['sequence'])<=192 or not set(row['sequence'])<=set(lock['aa']):continue
        if row['pdb_id'].lower() in excluded or not row.get('accessions'):continue
        if not set('ADLT')<=set(row['sequence']):continue
        requests.append(dict(group_id=g,component=component,pdb_id=row['pdb_id'],sequence=row['sequence'],
                             accessions=row['accessions'],mapping_path=row['chemistry_packet']+'/mapping.npz',
                             source_role=row['role'],source_path=row['source']))
    (out/'candidate_requests.json').write_text(json.dumps(requests,indent=2)+'\n')
    (out/'analysis.json').write_text(json.dumps(dict(complete=True,inventory=inventory,training_shortcuts=analyses,
                                                    candidate_parent_count=len(requests),candidate_components=len({r['component'] for r in requests}),
                                                    blocked_components=sorted(blocked),source_hashes={str(p):sha(p) for p in paths},
                                                    source_protocol_sha256=sha(Path('reports/mini_factor_student_pilot_2026-10-02/selection_protocol.json')),
                                                    source_selection_sha256=sha(Path('reports/mini_factor_student_pilot_2026-10-02/selection.json')),
                                                    training_updates=0,new_c4=0,new_s1=0),indent=2,allow_nan=False)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--pool',type=Path,required=True)
    a=p.parse_args();audit_context_coverage(a.out,a.pool)
