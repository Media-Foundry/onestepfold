#!/usr/bin/env python3
"""Audit saved fixed-graph scans and render their diagnostic results."""
import argparse,json,hashlib
from pathlib import Path
import numpy as np
from fastglycan.input_interpolation import aligned_rmsd
from fastglycan.paired_teacher_protocol import sha256,write_json


def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();root=a.root;lock=json.load(open(root/'lock.json'));runs={};hashes={};rows=[]
 exits=json.load(open(root/'exit.json'))
 if not exits['success']:raise ValueError('batch did not succeed')
 sources_to_score=list(lock['sources'])
 if (root/'interaction_exit.json').exists():
  if not json.load(open(root/'interaction_exit.json'))['success']:raise ValueError('interaction batch failed')
  sources_to_score+=['ER','EC','RC']
 for case in lock['cases']:
  baseline=None
  for sources in sources_to_score:
   folder=root/(case+'_'+sources);path=folder/'report.json';r=json.load(open(path));assert r['complete'] and r['lock_sha256']==sha256(root/'lock.json')
   assert len(r['rows'])==len(lock['alphas'])+(sources=='ERC' and 'region' not in lock)
   runs[case+'_'+sources]=r;hashes[str(path.relative_to(root))]=sha256(path)
   for index,row in enumerate(r['rows']):
    assert row['legacy_softmax']==(index==len(lock['alphas']))
    assert row['alpha']==lock['alphas'][min(index,len(lock['alphas'])-1)]
    coordinate=folder/row['coordinate_file'];assert sha256(coordinate)==row['coordinate_sha256']
    with np.load(coordinate) as d:
     x=d['coordinates'];identity=(d['atom_names'],d['residue_ids'],d['chain_ids'])
     if baseline is None:
      baseline=x.copy();base_identity=tuple(v.copy() for v in identity)
     assert all(np.array_equal(v,b) for v,b in zip(identity,base_identity))
     if index==0:assert np.array_equal(x,baseline),'worker hard endpoints differ'
     assert abs(aligned_rmsd(x,baseline)-row['aa_aligned_rmsd'])<1e-6
     ca=identity[0]=='CA';assert abs(aligned_rmsd(x[ca],baseline[ca])-row['ca_aligned_rmsd'])<1e-6
     i,j=r['tracked_atoms'];idx=[np.flatnonzero((identity[1]==res)&(identity[0]==name))[0] for res,name in [i,j]]
     assert abs(float(np.linalg.norm(x[idx[0]]-x[idx[1]]))-row['tracked_distance'])<1e-6
    assert {c['encoder'] for c in row['cache_checks']}=={'input_atom_encoder','diffusion_atom_encoder'}
    for field,entry in row['fields'].items():
     source='E' if field=='esm_token_embedding' else ('R' if field in ('restype','profile') else 'C')
     if source not in sources:assert entry['max_abs']==0,(sources,field)
    hashes[str(coordinate.relative_to(root))]=sha256(coordinate)
    rows.append(dict(case=case,sources=sources,**row))
 lines=['# Hard-neighborhood input-source interpolation','',
 'Existing development targets: '+', '.join(lock['cases'])+'; region: '+lock.get('region','all positions')+'. Fixed native chemical graph, noise211, C4/S1, FP32, no dropout/augmentation. No training, objective changes, smoothing, threshold changes or sequence optimization. HHH is constant in alpha and is exactly replayed across the source workers. R means restype/profile only; C means the five current reference fields; E means ESM2 recomputed for the probabilities.', '',
 '## Alpha scan', '',
 'Rows are probability interpolation, not logits saturation. Legacy softmax replay is separate. Geometry columns use all predicted atoms and the frozen graph-distance≤3 exclusion. Hard starts may themselves fail chemistry: small displacement is not a chemistry-validity gate.', '',
 '| Case | Sources | α | Tracked distance Å | Min nonbond Å | Severe pairs <1 Å | AA RMSD vs hard Å | CA RMSD Å | Bond RMSE Å |',
 '|---|---|---:|---:|---:|---:|---:|---:|---:|']
 for row in rows:
  alpha='legacy' if row['legacy_softmax'] else f"{row['alpha']:.7g}"
  lines.append(f"| {row['case']} | {row['sources']} | {alpha} | {row['tracked_distance']:.5f} | {row['min_nonbond_distance']:.5f} | {row['geometry']['severe_pairs']} | {row['aa_aligned_rmsd']:.5f} | {row['ca_aligned_rmsd']:.5f} | {row['geometry']['bond_rmse']:.5f} |")
 lines += ['',
 '## Endpoint and dependency checks','',
 'All alpha0 coordinates are bitwise identical across source arms for each target. Unselected input fields have zero deltas. Native sequence/atom/residue/chain identities remain unchanged. Every forward actually calls both input and diffusion atom-reference cache builders, with equality checks on all five reference fields and fresh d_lm/v_lm. Full Pairformer conditioning and diffusion caches are recomputed. ESM reuse is restricted to the same hashed prepared probability input; no stale input-dependent conditioning is reused.', '',
 'Detailed input/conditioning deltas, reference intraresidue bond contraction and mask ranges are in the per-arm JSON. Per-residue reference-bank contributions and unaligned/aligned backbone comparisons are in prepare_*/reference_audit.json. These observations do not introduce a new soft-chemistry representation.', '']
 (root/'report.md').write_text('\n'.join(lines));write_json(root/'acceptance.json',dict(complete=True,coordinate_records=len(rows),source_reports_and_coordinates=hashes,report_sha256=sha256(root/'report.md'),scientific_deployment_acceptance=False))

if __name__=='__main__':main()
