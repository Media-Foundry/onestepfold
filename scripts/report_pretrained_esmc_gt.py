#!/usr/bin/env python3
"""Fixed-endpoint nested-data comparison; intermediate checkpoints remain secondary."""
import argparse
import json
from pathlib import Path
import numpy as np
from fastglycan.paired_teacher_protocol import sha256,write_json
from report_endpoint_objective import comparison,summaries,vectors
from report_raw_warmstart import geometry


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();r=a.root
    lock=json.loads((r/'lock.json').read_text());manifest=json.loads((r/'data_manifest.json').read_text())
    source=json.loads((r/'code_v1/source_manifest.json').read_text())
    for name,digest in source['files'].items():assert sha256(r/'code_v1'/name)==digest,name
    metrics=['all_atom_lddt','ca_lddt','tm_score_ca_observed']
    groups=sorted(x['group_id'] for x in manifest['selection'] if x['split']=='validation')
    probe=sorted(lock['train_probe_groups']);scores={};inputs={};workers={}
    for size in lock['training_sizes']:
        worker=r/('train_%d'%size)/'report.json';w=json.loads(worker.read_text())
        assert w['complete'] and w['steps']==4096 and w['samples_seen']==16384 and w['frozen_heads_unchanged']
        assert w['initial_model_state_sha256']==lock['initial_model_state_sha256']
        assert w['lock_sha256']==sha256(r/'lock.json');workers[str(size)]=w;inputs[str(worker.relative_to(r))]=sha256(worker)
        logs=r/('train_%d'%size)/'training.jsonl';assert sha256(logs)==w['training_log_sha256']
        events=[json.loads(x) for x in logs.read_text().splitlines()]
        assert [x['step'] for x in events]==list(range(1,4097))
        assert sum(sum(z['length'] for z in x['rows']) for x in events)==w['residues_seen']
        for step in lock['evaluation_steps']:
            path=r/'scores'/('%d_%04d.json'%(size,step));d=json.loads(path.read_text())
            assert d['complete'] and d['size']==size and d['step']==step and len(d['dense_lddt_checks'])==4
            assert d['lock_sha256']==sha256(r/'lock.json')
            assert d['worker_sha256']==sha256(r/('train_%d'%size)/('evaluation_%04d.json'%step))
            assert d['source_manifest_sha256']==sha256(r/'code_v1/source_manifest.json')
            assert d['scoring_source_sha256']==source['files']['scripts/score_pretrained_esmc_gt.py']
            scores[size,step]=d['rows'];inputs[str(path.relative_to(r))]=sha256(path)
    baseline=[]
    for path,digest in lock['baseline_scores'].items():
        p=Path(path);assert sha256(p)==digest;d=json.loads(p.read_text());assert d['complete'];baseline.extend(d['rows'])
    refs={condition:[x for x in baseline if x['split']=='validation' and x['condition']==condition] for condition in ['native_reference','esmc_bridge']}
    result={'complete':True,'primary_step':4096,'inputs_sha256':inputs,'lock_sha256':sha256(r/'lock.json'),
            'source_manifest_sha256':sha256(r/'code_v1/source_manifest.json'),'groups':groups,'arms':{},'paired_8192_minus_2048':{},
            'scope':'Single adaptation seed; predeclared equal-update/sample endpoint; reused homologous DEV; no frozen temporal confirmation'}
    lines=['# Pretrained ESMC: TRAIN2048 versus TRAIN8192','','Final4096 updates,16384 samples each. Two fixed K1 draws averaged per protein; no best-of-K.','',
           '|Training size|Updates|DEV lDDT|DEV TM|Worst5% lDDT|TRAIN32 lDDT|C–N MAE Å|Chirality|',
           '|---:|---:|---:|---:|---:|---:|---:|---:|']
    final={}
    for size in lock['training_sizes']:
        history={}
        for step in lock['evaluation_steps']:
            rows=scores[size,step];dev=[x for x in rows if x['split']=='validation'];train=[x for x in rows if x['split']=='train']
            v={m:vectors(dev,m,groups) for m in metrics}
            if step==0:
                for m in metrics:assert np.array_equal(v[m],vectors(refs['esmc_bridge'],m,groups))
            history[str(step)]={m:{k:float(z) for k,z in summaries(v[m]).items()} for m in metrics}
            history[str(step)].update(geometry=geometry(dev),train_probe={m:float(vectors(train,m,probe).mean()) for m in metrics})
            h=history[str(step)];lines.append(f"|{size}|{step}|{h['all_atom_lddt']['mean']:.5f}|{h['tm_score_ca_observed']['mean']:.5f}|{h['all_atom_lddt']['worst5_mean']:.5f}|{h['train_probe']['all_atom_lddt']:.5f}|{h['geometry']['distance_mae']['consecutive_C_N']:.5f}|{h['geometry']['chirality_macro']:.5f}|")
            if step==4096:final[size]=v
        refdelta={name:{m:comparison(final[size][m],vectors(rr,m,groups)) for m in metrics} for name,rr in refs.items()}
        harm={name:sum(any(refdelta[name][m]['per_target_delta'][i]<-.05 for m in ['all_atom_lddt','tm_score_ca_observed']) for i in range(128)) for name in refs}
        w=workers[str(size)]
        result['arms'][str(size)]={'history':history,'final_minus_references':refdelta,'lddt_or_tm_harm_gt005':harm,
            'cost':{k:w[k] for k in ['steps','samples_seen','residues_seen','training_seconds','evaluation_seconds','checkpoint_seconds','elapsed_seconds']},
            'timed_worker_gpu_hours':4*w['elapsed_seconds']/3600,'per_protein_exposures':16384//size}
    result['paired_8192_minus_2048']={m:comparison(final[8192][m],final[2048][m]) for m in metrics}
    lines+=['','|Final metric|8192 −2048 mean [95% CI]|Worst5% difference [95% CI]|Targets losing >.05|','|---|---|---|---:|']
    for m,d in result['paired_8192_minus_2048'].items():
        x=d['mean'];y=d['worst5_mean'];lines.append(f"|{m}|{x['delta']:+.5f} [{x['ci95'][0]:+.5f},{x['ci95'][1]:+.5f}]|{y['delta']:+.5f} [{y['ci95'][0]:+.5f},{y['ci95'][1]:+.5f}]|{d['loss_gt_005_count']}/128|")
    lines+=['','Bootstrap5000 seed20260926, protein-level exploratory intervals, no homology/multiple-comparison correction. Same samples and updates do not imply equal FLOPs; measured cost is in JSON. Two exposures at8192 do not establish convergence. Partial chemistry metrics do not certify full chemical validity. No confidence or end-to-end timing claim.']
    write_json(r/'comparison.json',result);(r/'report.md').write_text('\n'.join(lines)+'\n');print('Final fixed-endpoint comparison complete',flush=True)


if __name__=='__main__':main()
