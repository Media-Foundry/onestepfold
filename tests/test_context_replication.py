import numpy as np
from fastglycan.context_replication import replication_jobs,native_sequences,task_cases,AA


def cohort():
    rows=[dict(group_id=str(i),component=str(i),pdb_id=str(i),role='train' if i<32 else 'confirmation_candidate',sequence='ADLT',sites=dict(A=0,D=1,L=2,T=3)) for i in range(40)]
    return dict(rows=rows,nested_train_tiers={str(n):[str(i) for i in range(n)] for n in (8,16,32)})


def test_budget_nested_and_no_confirmation_training():
    jobs=replication_jobs(cohort());assert len(jobs)==12
    for j in jobs:
        assert j['steps']==j['size']*4*1024
        assert 32768 in j['snapshots'] and j['snapshots'][-1]==j['steps']
        assert all(p<32 for p,pos in j['train_sites'])
        assert len(j['train_sites'])==4*j['size']


def test_sequences_and_noise_matched_labels():
    row=cohort()['rows'][0];seqs=list(native_sequences(row,0))
    assert len(seqs)==77 and len({s for _,s,_,_ in seqs})==77
    endpoints={label:dict(task=[k+n for n in range(4)],geometry=[{'id':k}]*4) for k,(label,_,_,_) in enumerate(seqs)}
    cases=task_cases(row,0,endpoints)
    for c in cases:
        values=np.array(c['target_delta']);assert values.shape==(4,20)
        assert np.array_equal(values[:,c['wt']],np.zeros(4))
        assert np.array_equal(values[0],values[-1])
        assert c['source_aa']==AA[c['wt']]
