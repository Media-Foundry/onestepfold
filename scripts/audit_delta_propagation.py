"""Independent archive/accounting and sampled spectral checks; CPU only."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np


def audit_delta_propagation(root):
    def digest(p):
        h=hashlib.sha256()
        with p.open('rb') as f:
            for b in iter(lambda:f.read(8388608),b''):h.update(b)
        return h.hexdigest()
    report=json.loads((root/'report.json').read_text())
    execution=json.loads((root/'execution.json').read_text())
    lock=json.loads((root/'lock.json').read_text())
    assert execution['complete'] and report['complete']
    assert report['counts']==dict(c4=187,cycles=748,s1=0,updates=0)
    assert len(report['records'])==60
    checked=0;wt=None;grouped={};sites={};nonlocal_energy={}
    for r in report['records']:
        path=root/'snapshots'/f"{r['label']}.npz"
        assert digest(path)==r['snapshot_sha256']
        snap=dict(np.load(path))
        if r['is_wt']:wt=snap
        assert r['plain_repeated_bitwise'] and r['hook_replay_bitwise'] and r['hook_rng_equal']
        # Whole-byte hashes additionally distinguish signed zero, unlike torch.equal.
        assert [r['statistics'][k]['candidate_sha256'] for k in ('s_inputs','final_s','final_z')]==r['conditioning_sha256']
        sites.setdefault(r['pdb'],[]).append(r['aa'])
        if r['is_wt']:continue
        for name,stats in r['statistics'].items():
            grouped.setdefault(name,[]).append(stats)
            sample_delta=snap[name].astype(np.float64)-wt[name].astype(np.float64)
            if sample_delta.ndim==3 and sample_delta.shape[0]==sample_delta.shape[1]:
                outside=sample_delta.copy();outside[r['position'],:,:]=0;outside[:,r['position'],:]=0
                total=float(np.square(sample_delta).sum())
                nonlocal_energy.setdefault(name,[]).append(dict(label=r['label'],
                    sampled_outside_row_column_energy_fraction=float(np.square(outside).sum()/total) if total else 0,
                    sampled_outside_row_column_max=float(np.abs(outside).max())))
            if 'spectra' not in stats:continue
            delta=snap[name].astype(np.float64)-wt[name].astype(np.float64)
            for i,row in enumerate(stats['spectra']):
                x=delta[:,:,i]
                # Different decomposition from the worker's direct SVD.
                energies=np.maximum(np.linalg.eigvalsh(x.T@x),0)[::-1]
                total=float(np.square(x).sum())
                assert np.isclose(total,row['energy'],rtol=1e-10,atol=1e-20)
                if total:
                    cumulative=np.cumsum(energies)/total
                    for q in (90,95,99):
                        assert int(np.searchsorted(cumulative,q/100)+1)==row[f'r{q}'],(r['label'],name,q)
                    for rank in (2,8,16,32):
                        fraction=float(energies[:rank].sum()/total)
                        assert np.isclose(fraction,row[f'energy_r{rank}'],rtol=1e-8,atol=1e-9),(r['label'],name,rank)
                else:assert row['zero_delta']
                checked+=1
    assert all(len(v)==20 and set(v)==set(lock['alphabet']) for v in sites.values())
    summaries={}
    for name,rows in grouped.items():
        item=dict(candidates=len(rows),bitwise_equal_fraction_mean=float(np.mean([r['bitwise_equal_fraction'] for r in rows])),
                  nonzero_fraction_mean=float(np.mean([r['nonzero_fraction'] for r in rows])))
        if 'spectra' in rows[0]:
            spectrum=[s for r in rows for s in r['spectra'] if not s['zero_delta']]
            item.update(unchanged_tile_fraction_mean=float(np.mean([r['unchanged_tile_fraction'] for r in rows])),
                        nonzero_spectra=len(spectrum))
            for key in ('r90','r95','r99','energy_r2','energy_r8','energy_r16','energy_r32'):
                item[key+'_mean']=float(np.mean([s[key] for s in spectrum])) if spectrum else None
        summaries[name]=item
    timing=[]
    for row in report['operator_timing']:
        records=[r for r in report['records'] if r['pdb']==row['pdb']]
        baseline=float(np.mean([np.median(r['c4_seconds']) for r in records]))
        events=row['events']
        names=('input_embedder','msa_module','pairformer_stack')
        parts={name:sum(e['ms'] for e in events if e['module']==name) for name in names}
        first=[e for e in events if e['module']=='msa_module.blocks.0.pair_stack.tri_mul_out'][0]
        timing.append(dict(pdb=row['pdb'],mean_candidate_c4_seconds=baseline,inclusive_ms=parts,
                           first_msa_trimul_ms=first['ms'],first_msa_trimul_fraction_of_plain_c4=first['ms']/1000/baseline))
    result=dict(complete=True,records=60,non_wt=57,sites=sites,sampled_spectra_checked=checked,
                counts=report['counts'],all_replay_assertions_pass=True,
                limitation='Sampled channel spectra independently recomputed; full-tensor equality is worker-observed, not independently regenerated.',
                report_sha256=digest(root/'report.json'),summary=summaries,timing=timing,
                sampled_nonlocal_energy=nonlocal_energy)
    (root/'independent_audit.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(complete=True,records=60,spectra=checked,timing=timing),indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    audit_delta_propagation(p.parse_args().root)
