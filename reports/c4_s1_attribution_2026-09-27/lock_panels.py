import gzip,hashlib,json
from pathlib import Path
root=Path(__file__).resolve().parents[2];a=root/'reports/stage0_confirmation_2026-09-19';out=Path(__file__).resolve().parent
old=json.loads((a/'repeat_lock.json').read_text());sources={}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
with gzip.open(a/'source/temporal_dev_v1.jsonl.gz','rt') as f:rows={r['group_id']:r for r in map(json.loads,f)}
score={}
for s in ('c4_s1','c4_s2','c4_s5'):
 p=a/'source'/f'{s}.json';sources[p.name]=sha(p);assert sources[p.name]==old['source_scores_sha256'][s];score[s]={r['group_id']:r for r in json.loads(p.read_text())['records']}
metrics=('tm_score_ca','all_atom_lddt');bad=set();gain=set();neutral=set()
for g in rows:
 ds=[score['c4_s1'][g][m]-score[ref][g][m] for ref in ('c4_s2','c4_s5') for m in metrics]
 if min(ds)<-.05:bad.add(g)
 if max(ds)>.05:gain.add(g)
 if max(map(abs,ds))<=.01:neutral.add(g)
# All discovered losses, no handpicked subset; one unique length-matched neutral control each.
controls=[]
for g in sorted(bad):
 c=min(neutral-set(controls),key=lambda x:(abs(rows[x]['sequence_length']-rows[g]['sequence_length']),x));controls.append(c)
b=sorted(bad|set(controls));pa=old['target_ids'];assert len(pa)==128 and len(set(pa))==128
lock=dict(schema='c4-s1-attribution-v1',locked=True,model='protenix_mini_esm_v0.5.0',cycles=4,seeds=[103,107,109,113],K=1,
 old_root='/data/user/shuang886/Folding/stage0_confirmation_v1_20260919',panel_a=pa,panel_b=b,panel_b_failures=sorted(bad),panel_b_controls=controls,
 panel_b_rule='Any discovery delta below -0.05 in either metric versus either reference; one greedy unique nearest-length neutral control (all four abs deltas <=0.01), group-ID order/tie break',
 no_new_test=True,no_training=True,source_sha256=sources,old_repeat_lock_sha256=sha(a/'repeat_lock.json'),
 primary_metrics=list(metrics),thresholds=[-.05,-.10],persistent_failure='k>=3 of4; operational label only',neutral_band=.01,
 primary_bootstrap='target clusters retaining all paired seed/config rows; 10000 resamples seed20260927',
 secondary_bootstrap='crossed targets and common seed columns, not independently nested seeds',
 panel_a_native='Add c4_s1; reuse accepted c4_s2/s5 only after exact historical coordinate replay',
 panel_b_native='C4S1/S2/S5 all4 seeds; MC dropout original0.4/0.4; selected diagnostic sample, not prevalence',
 panel_b_controlled='C4S1/S2/S5 all4 seeds; dropout off; reset sampling RNG independent of trunk; identical native initial noise; fixed identity rotation and zero translation with centering; gamma0=0 eta1; only integration schedule changes within block',
 controlled_seed='sha256(attribution-v1:group:seed) first8hex modulo(2**31-1)',
 backward_scope='No q-optimization job in this lock; fixed atom/MSA/ESM soft-input contract must first be specified',
 acceptance='Complete predictions, finite coordinates, exact sentinel replay, C4/S actual call counts, shared initial/conditioning hashes; statistical outcomes not automatic pass/fail')
(out/'lock.json').write_text(json.dumps(lock,indent=2)+'\n')
(out/'manifest.json').write_text(json.dumps({g:rows[g] for g in sorted(set(pa)|set(b))},indent=2)+'\n')
print('A',len(pa),'B',len(b),'Bfailures',len(bad),'Bcontrols',len(controls),'overlap',len(set(pa)&set(b)),'Bnew',len(set(b)-set(pa)))
