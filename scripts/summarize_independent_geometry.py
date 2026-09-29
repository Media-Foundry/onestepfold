#!/usr/bin/env python3
"""Read-only supplement after the locked batch: strata, transitions, local changes."""
import argparse,collections,concurrent.futures,csv,json,multiprocessing,traceback
from pathlib import Path
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.independent_geometry_summary import distribution,protein_quality,geometry_transitions,atom_lddt,penetration_distribution


def signed(coordinates,centres):
    c,a,b,d=np.asarray(centres,dtype=int).reshape(-1,4).T
    return (np.cross(coordinates[a]-coordinates[c],coordinates[b]-coordinates[c])*(coordinates[d]-coordinates[c])).sum(-1)


def describe_one(args):
    root,out,protein,score_rows=args;torch.set_num_threads(1);g=protein['group_id'];folder=root/'proteins'/g
    target=out/g;target.mkdir();native_dir=Path(protein['chemistry']['packet_dir']);mapping_file=native_dir/'mapping.npz';assert sha256(mapping_file)==protein['chemistry']['files']['mapping.npz']
    with np.load(mapping_file) as f:mapping=dict(f)
    res=mapping['residue_ids'];names=mapping['atom_names'];mask=mapping['mask'];reference=mapping['reference'];bone=np.isin(names,['N','CA','C','O']);seq=protein['sequence']
    top=torch.load(folder/'topology.pt',map_location='cpu',weights_only=False)['topology'];pairs=top.pairs.numpy();radii=top.radii.numpy();centres=top.centres.numpy();volumes=top.volumes.numpy()
    side=[]
    for i,aa in enumerate(seq,1):
        if aa in 'IT':side.append([int(np.flatnonzero((res==i)&(names==n))[0]) for n in ['CB','CA','CG1' if aa=='I' else 'OG1','CG2']])
    side=np.array(side,dtype=int).reshape(-1,4);side_ref=signed(reference,side)
    rawreport=json.loads((folder/'raw/report.json').read_text());repairs={m:json.loads((folder/m/'report.json').read_text()) for m in ['mean','tail']};rows=[];local=[]
    def wrong(x):return signed(x,centres)*volumes<=0,signed(x,side)*side_ref<=0
    for seed in (300007,300017,300023):
        row=dict(next(x for x in score_rows if x['seed']==seed));row['raw_joint_pass']=None;row['mean_joint_pass']=None;row['tail_joint_pass']=None;row['descriptive_geometry']={};row['cost']={};row['supplement_errors']={}
        try:
            meta=rawreport['results'][str(seed)];assert sha256(Path(meta['file']))==meta['sha256']
            raw=np.load(meta['file'])['coordinates'];raw_atoms=atom_lddt(raw[mask],mapping['coordinates'][mask],res[mask]);raw_ca_wrong,raw_side_wrong=wrong(raw)
            row['descriptive_geometry']['raw']=dict(penetration=penetration_distribution(raw,pairs,radii))
            row['cost']['raw_diffusion_seconds']=meta['seconds']
        except Exception:row['supplement_errors']['raw']=traceback.format_exc();rows.append(row);continue
        for method in ['mean','tail']:
            item=next((x for x in repairs[method]['cases'] if x.get('seed')==seed and x.get('success')),None)
            if item is None:row['supplement_errors'][method]='missing successful fixed-budget repair';continue
            try:
                p=folder/method/'cases'/f"{item['case']:02d}"/'coordinates.npz';assert sha256(p)==item['coordinates_sha256'];data=np.load(p);assert np.array_equal(data['raw'],raw)
                final=data['final'];actual=item['metrics']['final'];before=item['metrics']['raw'];row[method+'_joint_pass']=actual['joint_pass']
                if row['raw_joint_pass'] is not None:assert row['raw_joint_pass']==before['joint_pass']
                row['raw_joint_pass']=before['joint_pass'];row['descriptive_geometry']['raw']['metrics']=before
                ca_wrong,side_wrong=wrong(final);new_ca=res[centres[np.flatnonzero(ca_wrong&~raw_ca_wrong),0]].tolist();new_side=res[side[np.flatnonzero(side_wrong&~raw_side_wrong),0]].tolist()
                delta=np.linalg.norm(final-raw,axis=-1);final_atoms=atom_lddt(final[mask],mapping['coordinates'][mask],res[mask]);observed_res=res[mask]
                for i,aa in enumerate(seq,1):
                    ix=res==i;obs=observed_res==i;sc=ix&~bone;ca=ix&(names=='CA');valid=obs&np.isfinite(raw_atoms)&np.isfinite(final_atoms)
                    local.append(dict(group_id=g,pdb_id=protein['pdb_id'],seed=seed,method=method,residue=i,amino_acid=aa,backbone_max_displacement=float(delta[ix&bone].max()),sidechain_max_displacement=float(delta[sc].max()) if sc.any() else None,ca_displacement=float(delta[ca][0]),raw_local_lddt=float(raw_atoms[valid].mean()) if valid.any() else None,final_local_lddt=float(final_atoms[valid].mean()) if valid.any() else None,local_lddt_delta=float((final_atoms[valid]-raw_atoms[valid]).mean()) if valid.any() else None,new_ca_chirality_error=i in new_ca,new_sidechain_chirality_error=i in new_side))
                row['descriptive_geometry'][method]=dict(metrics=actual,penetration=penetration_distribution(final,pairs,radii),new_ca_chirality_residues=new_ca,new_sidechain_chirality_residues=new_side,new_absolute_failure_labels=sorted(set(actual['absolute_failures'])-set(before['absolute_failures'])),new_connection_failure=before['connection_pass'] and not actual['connection_pass'],max_displacement_residue=int(res[np.argmax(delta)]),max_displacement_atom=str(names[np.argmax(delta)]))
                row['cost'][method]=dict(seconds=item['seconds'],solver_seconds=item['solver_seconds'],closures=sum(s['calls'] for s in item['history']),iterations=sum(s['iterations'] for s in item['history']),stages_at_iteration_cap=sum(s['iterations']>=60 for s in item['history']),peak_allocated_bytes=item.get('peak_allocated_bytes'),peak_reserved_bytes=item.get('peak_reserved_bytes'))
            except Exception:row['supplement_errors'][method]=traceback.format_exc()
        rows.append(row)
    write_json(target/'instances.json',rows)
    if local:
        with (target/'per_residue.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(local[0]));w.writeheader();w.writerows(local)
    return dict(group_id=g,rows=rows,raw_total_seconds=rawreport.get('seconds'),model_load_seconds=rawreport.get('load_seconds'),conditioning_seconds=rawreport.get('conditioning_seconds'))


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();root=a.root;out=a.out
    assert (root/'exit.json').exists(),'wait for authoritative pipeline completion'
    report=json.loads((root/'report.json').read_text());panel=json.loads((root/'panel32.json').read_text());assert report['complete'];assert len(report['rows'])==96
    out.mkdir(exist_ok=False);write_json(out/'analysis_lock.json',dict(input_report_sha256=sha256(root/'report.json'),runtime_lock_sha256=sha256(root/'runtime_lock.json'),panel_sha256=sha256(root/'panel32.json'),script_sha256=sha256(Path(__file__)),module_sha256=sha256(Path(__import__('fastglycan.independent_geometry_summary',fromlist=['x']).__file__)),scope='posthoc descriptive supplement; original screen unchanged'))
    with concurrent.futures.ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context('spawn')) as ex:
        result=list(ex.map(describe_one,[(root,out,x,[v for v in report['rows'] if v['group_id']==x['group_id']]) for x in panel]))
    rows=[row for x in result for row in x['rows']];gids=[x['group_id'] for x in panel];proteins,quality=protein_quality(rows,gids)
    subsets={'all':gids,**{f'length_stratum_{i}':[x['group_id'] for x in panel if x['stratum']==i] for i in range(4)},'monomer':[x['group_id'] for x in panel if 'source_context' not in x],'homooligomer_chain':[x['group_id'] for x in panel if 'source_context' in x]}
    groups={}
    for label,ids in subsets.items():
        selected=[x for x in rows if x['group_id'] in ids];_,q=protein_quality(selected,ids)
        cost={method:{k:distribution([x['cost'].get(method,{}).get(k) for x in selected]) for k in ['seconds','solver_seconds','closures','iterations','peak_allocated_bytes','peak_reserved_bytes']} for method in ['mean','tail']}
        groups[label]=dict(proteins=len(ids),instances=len(selected),quality=q,geometry=geometry_transitions(selected),repair_cost=cost)
    output=dict(complete=True,original_screen=report['screen'],original_independent_audit=dict(passed=report['independent_audit']['passed'],groups=report['independent_audit']['groups']),groups=groups,proteins=proteins,raw_cost={k:distribution([x.get(k) for x in result]) for k in ['raw_total_seconds','model_load_seconds','conditioning_seconds']},supplement_errors=[dict(group_id=x['group_id'],seed=x['seed'],errors=x['supplement_errors']) for x in rows if x['supplement_errors']],instance_rows=rows)
    write_json(out/'report.json',output)
    lines=['# Independent32 geometry validation summary','',f"Original continuation screen: `{report['screen']['continuation_screen']}`. This is an iterative geometry screen, not deployment or design approval.",'','| Group | Proteins | Raw pass | Mean pass | Tail pass | Tail all3 | Tail−raw AA-lDDT mean (protein) |','|---|---:|---:|---:|---:|---:|---:|']
    for name,x in groups.items():
        m=x['geometry']['mean'];t=x['geometry']['tail'];d=x['quality']['paired']['tail']['all_atom_lddt'].get('mean')
        lines.append(f"| {name} | {x['proteins']} | {t['raw_pass']}/{t['instances']} | {m['repaired_pass']}/{m['instances']} | {t['repaired_pass']}/{t['instances']} | {t['all3_proteins_pass']}/{x['proteins']} | {d if d is not None else 'missing'} |")
    lines+=['','Missing results remain in denominators. Quality uses complete three-seed protein means, never best-of-three. Lower/upper5% use ceil(0.05×n) proteins. Small subgroup intervals are descriptive. The original thresholds and solver budgets are unchanged.','',f"Detailed JSON and per-protein per-residue CSVs are in `{out}`."]
    (out/'report.md').write_text('\n'.join(lines)+'\n');print(json.dumps(output['original_screen']))


if __name__=='__main__':main()
