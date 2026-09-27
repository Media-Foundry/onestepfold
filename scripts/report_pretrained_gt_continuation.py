#!/usr/bin/env python3
"""Read-only fixed-checkpoint curves; does not select models or alter training."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from fastglycan.paired_teacher_protocol import sha256,write_json
from report_endpoint_objective import comparison,summaries,vectors

def geometry(rows):
    chirality = [r["geometry"]["ca_chirality"] for r in rows]
    chirality = [r for r in chirality if r["evaluable_count"]]
    return {
        "chirality_macro": float(np.mean([r["agreement_count"] / r["evaluable_count"] for r in chirality])) if chirality else None,
        "chirality_evaluable_rows": len(chirality),
        "distance_mae": {name: float(np.mean([r["geometry"]["local_distances"][name]["mae"] for r in rows if r["geometry"]["local_distances"][name]["mae"] is not None])) for name in ("N_CA", "CA_C", "C_O", "consecutive_C_N")},
    }


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--through-step',type=int,required=True)
    a=p.parse_args();root=a.root;out=a.output;out.mkdir(parents=True,exist_ok=False)
    lock=json.loads((root/'lock.json').read_text());manifest=json.loads((root/'data_manifest.json').read_text())
    assert a.through_step in lock['evaluation_steps'] and a.through_step>0
    steps=[s for s in lock['evaluation_steps'] if s<=a.through_step]
    source=json.loads((root/'code_v1/source_manifest.json').read_text())
    assert sha256(root/'code_v1/source_manifest.json')==lock['common_files']['code_v1/source_manifest.json']
    for name,digest in source['files'].items():assert sha256(root/'code_v1'/name)==digest,name
    groups=sorted(r['group_id'] for r in manifest['selection'] if r['split']=='validation')
    train=sorted(lock['train_probe_groups']);metrics=['all_atom_lddt','ca_lddt','tm_score_ca_observed']
    hashes={'lock.json':sha256(root/'lock.json')};baseline=[]
    for name,h in lock['baseline_scores'].items():
        path=Path(name);assert sha256(path)==h;d=json.loads(path.read_text());assert d['complete'];baseline.extend(d['rows']);hashes[name]=h
    ref={c:[x for x in baseline if x['condition']==c and x['split']=='validation'] for c in ['native_reference','esmc_bridge']}
    refvec={c:{m:vectors(v,m,groups) for m in metrics} for c,v in ref.items()}
    arrays={};history={};last_rows={}
    for size in [2048,8192]:
        history[str(size)]={}
        for step in steps:
            path=root/'scores'/('%d_%04d.json'%(size,step));d=json.loads(path.read_text())
            assert d['complete'] and d['size']==size and d['step']==step and len(d['rows'])==320
            assert d['lock_sha256']==sha256(root/'lock.json')
            assert d['source_manifest_sha256']==sha256(root/'code_v1/source_manifest.json')
            assert d['scoring_source_sha256']==source['files']['scripts/score_pretrained_esmc_gt.py']
            export=root/('train_%d'%size)/('evaluation_%04d.json'%step)
            assert d['worker_sha256']==sha256(export) and len(d['dense_lddt_checks'])==4
            hashes[str(path.relative_to(root))]=sha256(path);hashes[str(export.relative_to(root))]=sha256(export)
            dev=[x for x in d['rows'] if x['split']=='validation'];probe=[x for x in d['rows'] if x['split']=='train']
            v={m:vectors(dev,m,groups) for m in metrics};arrays[size,step]=v
            if step==0:
                for m in metrics:assert np.array_equal(v[m],refvec['esmc_bridge'][m])
            h={m:{k:float(z) for k,z in summaries(v[m]).items()} for m in metrics}
            h.update(train_probe={m:float(vectors(probe,m,train).mean()) for m in metrics},geometry=geometry(dev),samples_seen=step*4)
            history[str(size)][str(step)]=h;last_rows[size]=dev
    result={'complete':True,'interim':a.through_step<16384,'through_step':a.through_step,'primary_endpoint':16384,
            'history':history,'groups':groups,'inputs_sha256':hashes,'analysis_source_sha256':sha256(Path(__file__)),
            'comparisons':{},'baseline':{c:{m:{k:float(z) for k,z in summaries(v).items()} for m,v in vv.items()} for c,vv in refvec.items()},
            'scope':'Single training seed, fixed development view, two K1 draws averaged per protein; no checkpoint or hyperparameter selection'}
    lines=['# Pretrained ESMC scaling: fixed-checkpoint interim assessment','',
           f'Through update{a.through_step} ({4*a.through_step} sample presentations/arm). Primary endpoint is16384; this report does not modify training.',
           '', '|TRAIN size|Update|DEV lDDT|DEV TM|Worst5% lDDT|Worst5% TM|TRAIN32 lDDT|C–N MAE Å|Chirality|',
           '|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for size in [2048,8192]:
        for step in steps:
            h=history[str(size)][str(step)];lines.append(f"|{size}|{step}|{h['all_atom_lddt']['mean']:.5f}|{h['tm_score_ca_observed']['mean']:.5f}|{h['all_atom_lddt']['worst5_mean']:.5f}|{h['tm_score_ca_observed']['worst5_mean']:.5f}|{h['train_probe']['all_atom_lddt']:.5f}|{h['geometry']['distance_mae']['consecutive_C_N']:.5f}|{h['geometry']['chirality_macro']:.5f}|")
    pairs=[('8192_minus_2048',arrays[8192,a.through_step],arrays[2048,a.through_step])]
    pairs += [(str(size)+'_minus_'+c,arrays[size,a.through_step],refvec[c]) for size in [2048,8192] for c in refvec]
    parent=Path(lock['parent_root'])
    assert sha256(parent/'lock.json')==lock['parent_lock_sha256']
    previous={}
    for size in [2048,8192]:
        d=json.loads((parent/'scores'/('%d_4096.json'%size)).read_text())
        assert sha256(parent/'scores'/('%d_4096.json'%size))==lock['parent_score_sha256'][str(size)]
        dev=[r for r in d['rows'] if r['split']=='validation']
        previous[size]={m:vectors(dev,m,groups) for m in metrics}
        pairs.append((str(size)+'_minus_own_step4096',arrays[size,a.through_step],previous[size]))
    if a.through_step==16384:
        pairs.append(('equal_8_exposures_8192_minus_2048_unequal_compute',arrays[8192,16384],previous[2048]))
    result['original_decliners']={}
    for size in [2048,8192]:
        delta=previous[size]['all_atom_lddt']-refvec['esmc_bridge']['all_atom_lddt']
        mask=delta < -.05
        now=arrays[size,a.through_step]['all_atom_lddt']-refvec['esmc_bridge']['all_atom_lddt']
        result['original_decliners'][str(size)]=[{'group_id':g,'parent_minus_initial':float(delta[i]),'current_minus_initial':float(now[i]),'recovered_to_initial':bool(now[i]>=0)} for i,g in enumerate(groups) if mask[i]]
    lines+=['','|Comparison|Metric|Mean Δ [95% CI]|Worst5% Δ [95% CI]|Targets losing >.05|','|---|---|---|---|---:|']
    for name,x,y in pairs:
        d={m:comparison(x[m],y[m]) for m in metrics}
        d['lddt_or_tm_harm_gt005_count']=int(np.sum((x['all_atom_lddt']-y['all_atom_lddt']<-.05)|(x['tm_score_ca_observed']-y['tm_score_ca_observed']<-.05)))
        result['comparisons'][name]=d
        for m in ['all_atom_lddt','tm_score_ca_observed']:
            mean=d[m]['mean'];tail=d[m]['worst5_mean']
            lines.append(f"|{name}|{m}|{mean['delta']:+.5f} [{mean['ci95'][0]:+.5f},{mean['ci95'][1]:+.5f}]|{tail['delta']:+.5f} [{tail['ci95'][0]:+.5f},{tail['ci95'][1]:+.5f}]|{d[m]['loss_gt_005_count']}/128|")
    lines+=['','8192 proteins are not all encountered before2048 updates. Same updates/samples do not imply equal FLOPs or convergence. TRAIN32 is a common probe, not a full training-set evaluation.',
            'Bootstrap5000 seed20260926, protein-level exploratory intervals; unadjusted for homology and multiple comparisons. DEV is reused and highly homologous. Two noise views are not independent training repeats and are not best-of-K. Chemistry checks here are partial.']
    fig,axes=plt.subplots(2,2,figsize=(10,7),layout='constrained')
    for ax,(metric,stat,title) in zip(axes.flat,[('all_atom_lddt','mean','DEV mean all-atom lDDT'),('tm_score_ca_observed','mean','DEV mean TM-score'),('all_atom_lddt','worst5_mean','DEV worst 5% all-atom lDDT'),('tm_score_ca_observed','worst5_mean','DEV worst 5% TM-score')]):
        for size,color in [(2048,'#3366aa'),(8192,'#e1812c')]:
            ax.plot([4*s for s in steps],[history[str(size)][str(s)][metric][stat] for s in steps],'-o',label=f'TRAIN{size}',color=color)
        for c,style,label in [('native_reference',':','Native ESM2 reference'),('esmc_bridge','--','Initial ESMC bridge')]:
            ax.axhline(result['baseline'][c][metric][stat],color='0.4' if c=='native_reference' else '0.65',ls=style,lw=1,label=label)
        ax.set(title=title,xlabel='Protein sample presentations',ylabel='Score');ax.grid(alpha=.2)
    axes[0,0].legend(fontsize=8);fig.suptitle(f'Fixed one-cycle / one-structure evaluation — through update {a.through_step}\nTwo K=1 noise views averaged; primary endpoint: update 16384',fontsize=11)
    fig.savefig(out/'curves.png',dpi=160);fig.savefig(out/'curves.pdf');plt.close(fig)
    result['figure_sha256']={n:sha256(out/n) for n in ['curves.png','curves.pdf']}
    write_json(out/'report.json',result);(out/'report.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'complete':True,'through_step':a.through_step,'outputs':str(out)}),flush=True)


if __name__=='__main__':main()
