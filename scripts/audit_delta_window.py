"""CPU-only independent spectra, replay and non-overlapping cost audit."""
import argparse,hashlib,json,re
from pathlib import Path
import numpy as np


def audit_delta_window(root):
    def sha(path):
        h=hashlib.sha256()
        with path.open('rb') as f:
            for block in iter(lambda:f.read(8388608),b''):h.update(block)
        return h.hexdigest()
    report=json.loads((root/'report.json').read_text());lock=json.loads((root/'lock.json').read_text())
    assert report['complete'] and json.loads((root/'execution.json').read_text())['complete']
    assert report['counts']==dict(c4=76,cycles=304,s1=0,updates=0)
    assert len(report['records'])==12
    for path,h in lock['assets'].items():
        path=Path(str(path).replace('/data/user/shuang886/Folding',str(root.parent)))
        assert sha(path)==h,path
    for path,h in lock['code'].items():assert sha(root/'code'/path)==h,path
    for path,h in report['source_hashes'].items():assert sha(Path(path))==h,path
    prior=json.loads(Path(lock['previous_report']).read_text());old={r['label']:r for r in prior['records']}
    grouped={};strata={};timing=[];checked=0;wt=None;keys=[]
    for row in report['records']:
        assert row['conditioning_sha256']==old[row['label']]['conditioning_sha256']
        assert row['previous_archive_bitwise'] and row['all_rng_equal']
        path=root/'snapshots'/f"{row['label']}.npz";assert sha(path)==row['snapshot_sha256']
        values=dict(np.load(path));assert len(values)==66
        if row['is_wt']:wt=values
        else:
            assert values.keys()==wt.keys()
            for name,target in values.items():
                s=row['statistics'][name]
                assert target.shape[-1]==128 and len(s['channels'])==128
                delta=target.astype(np.float64)-wt[name].astype(np.float64)
                h=hashlib.sha256(str((target.shape,target.dtype.str)).encode()+np.ascontiguousarray(target).tobytes()).hexdigest()
                assert h==s['candidate_sha256']
                for c,entry in enumerate(s['channels']):
                    assert c==entry['channel']
                    d=delta[:,:,c];e=np.maximum(np.linalg.eigvalsh(d.T@d),0)[::-1];total=float(np.square(d).sum())
                    assert np.isclose(total,entry['energy'],rtol=1e-10,atol=1e-20)
                    if total:
                        cumulative=np.cumsum(e)/total
                        for q in (90,95,99):assert int(np.searchsorted(cumulative,q/100)+1)==entry[f'r{q}']
                        for rank in (2,4,8,16,24,32,48,64):assert np.isclose(e[:rank].sum()/total,entry[f'energy_r{rank}'],rtol=1e-8,atol=1e-9)
                    else:assert entry['zero_delta']
                    checked+=1
                    grouped.setdefault(name,[]).append(entry)
                    strata.setdefault(row['pdb'],{}).setdefault(name,[]).append(entry)
        plain=float(np.median(row['plain_c4_seconds']))
        for repeat,profile in enumerate(row['profiles']):
            events=profile['events'];assert len(events)==768
            identities={(x['cycle'],x['module'],x['kind']) for x in events};assert len(identities)==768
            totals={}
            for kind in ('contraction','trimul'):
                for cycle in (1,2,3,4):
                    for end in (8,12,16,24,32,40,48):
                        costs=[x['ms'] for x in events if x['cycle']==cycle and x['kind']==kind and int(re.match(r'b(\d+)',x['module'])[1])<=end]
                        assert len(costs)==2*end
                        totals[f'c{cycle}.b1-{end}.{kind}_ms']=float(sum(costs))
            timing.append(dict(label=row['label'],pdb=row['pdb'],repeat=repeat,plain_seconds=plain,
                profiled_seconds=profile['wall_seconds'],profile_to_plain=profile['wall_seconds']/plain,
                disjoint_costs=totals))
        keys.append(row['label'])
    assert checked==9*66*128,checked
    assert keys==[x['label'] for x in lock['inputs']]
    def summarize(mapping):
        output={}
        for stage,rows in mapping.items():
            item=dict(channel_candidate_observations=len(rows))
            for key in ('r90','r95','r99','energy_r8','energy_r16','energy_r24','energy_r32','outside_energy_fraction'):
                a=np.array([x[key] for x in rows if not x['zero_delta']])
                item[key]=dict(mean=float(a.mean()),median=float(np.median(a)),p05=float(np.quantile(a,.05)),p95=float(np.quantile(a,.95)),min=float(a.min()),max=float(a.max()))
            output[stage]=item
        return output
    result=dict(complete=True,records=12,mutants=9,channels=128,independent_spectra=checked,counts=report['counts'],
        report_sha256=sha(root/'report.json'),audit_source_sha256=sha(Path(__file__)),
        all_final_hashes_match_previous=True,summary=summarize(grouped),
        by_parent={k:summarize(v) for k,v in strata.items()},timing=timing,
        note='All-channel spectra from three selected mutants per site; not independent contexts. Nested timing levels kept separate.')
    (root/'independent_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(complete=True,records=12,spectra=checked,profile_to_plain_mean=float(np.mean([x['profile_to_plain'] for x in timing]))),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    audit_delta_window(p.parse_args().root)
