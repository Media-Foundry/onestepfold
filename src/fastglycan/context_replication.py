"""Frozen accounting and label construction for the repeated-context curve."""
import numpy as np

AA='ACDEFGHIKLMNPQRSTVWY'
NOISES=(230201,230211,310003,310019)
MODEL_SEEDS=(231301,231303)
SCALE=0.5759913630974075
EXPOSURES=1024


def replication_jobs(selection):
    by_id={r['group_id']:i for i,r in enumerate(selection['rows'])}
    jobs=[]
    for size in (8,16,32):
        parents=[by_id[g] for g in selection['nested_train_tiers'][str(size)]]
        assert len(parents)==size and all(selection['rows'][i]['role']=='train' for i in parents)
        sites=[[i,selection['rows'][i]['sites'][a]] for i in parents for a in 'ADLT']
        steps=len(sites)*EXPOSURES
        for architecture in ('context','aa_only'):
            for seed in MODEL_SEEDS:
                jobs.append(dict(id=f'n{size}_{architecture}_s{seed}',size=size,architecture=architecture,seed=seed,
                                 parents=parents,train_sites=sites,steps=steps,
                                 snapshots=sorted({steps//2,32768,steps}),scale=SCALE,
                                 lr=.001,weight_decay=.0001,exposures_per_context=EXPOSURES))
    return jobs


def native_sequences(row,index):
    sequence=row['sequence']
    yield f'p{index}_wt',sequence,None,None
    for source in 'ADLT':
        position=row['sites'][source]
        assert sequence[position]==source
        for aa in AA:
            if aa!=source:
                yield f'p{index}_s{position+1}_{aa}',sequence[:position]+aa+sequence[position+1:],position,aa


def task_cases(row,index,endpoints):
    wt=endpoints[f'p{index}_wt'];wt_task=np.asarray(wt['task'],float)
    cases=[]
    for source in 'ADLT':
        position=row['sites'][source]
        records=[wt if aa==source else endpoints[f'p{index}_s{position+1}_{aa}'] for aa in AA]
        matrix=np.asarray([r['task'] for r in records],float).T
        assert matrix.shape==(4,20) and np.isfinite(matrix).all()
        cases.append(dict(parent_index=index,pdb_id=row['pdb_id'],component=row['component'],role=row['role'],
                          position=position,source_aa=source,wt=AA.index(source),
                          target_delta=(matrix-wt_task[:,None]).tolist(),wt_task=wt_task.tolist(),
                          teacher_geometry=[[r['geometry'][n] for r in records] for n in range(4)]))
    return cases
