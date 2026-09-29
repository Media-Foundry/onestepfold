#!/usr/bin/env python3
"""Six frozen parent outputs, CPU-only connected representation probe."""
import argparse, inspect, json, os, time, traceback
from pathlib import Path
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256, write_json
from fastglycan.models.soft_sequence_chart import native_sequence_features
from fastglycan.articulated_output import ArticulatedOutput, AA
from fastglycan.connected_output import ConnectedOutput, phase
from fastglycan.geometry_repair import preservation
from fastglycan.hybrid_geometry import GeometryTopology
from fastglycan.repair_outcomes import absolute_failures
from fastglycan.sequence_gate_metrics import contact_objective
from fastglycan.collision_audit import collision_records


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--input',type=Path,required=True)
    a=p.parse_args();root=a.root.resolve();source=a.input.resolve();root.mkdir(parents=True,exist_ok=True)
    if (root/'lock.json').exists(): raise ValueError('existing locked probe; do not overwrite')
    torch.set_num_threads(2)
    archived=json.loads((source/'report.json').read_text());assert archived['complete']
    assert sha256(source/'topology.pt')==archived['topology_sha256']
    first=np.load(source/'controlled_s1_211.npz');seq=str(first['sequence'])
    features,atoms=native_sequence_features(seq)
    assert bool(features['ref_mask'].all())
    for key,value in [('atom_names',atoms.atom_name),('residue_ids',atoms.res_id),('chain_ids',atoms.chain_id)]:
        assert np.array_equal(first[key],value)
    assert len(set(atoms.chain_id))==1
    reference=features['ref_pos'].double().numpy()
    top=GeometryTopology(atoms,reference)
    oldtop=torch.load(source/'topology.pt',map_location='cpu',weights_only=False)
    for name in ['bonds','ideal','pairs','centres','volumes']:assert torch.equal(getattr(top,name),getattr(oldtop['topology'],name))
    bonds=atoms.bonds.as_array();variants={}
    for i,aa in enumerate(seq,1):
        ix=np.flatnonzero(atoms.res_id==i);lookup={int(j):k for k,j in enumerate(ix)};names=atoms.atom_name[ix].tolist()
        local=[(lookup[int(x)],lookup[int(y)],int(order)) for x,y,order in bonds if int(x) in lookup and int(y) in lookup]
        variants[AA[aa]+':'+','.join(names)]=dict(atom_names=names,bonds=local)
    for x,y,_ in bonds:
        if atoms.res_id[x]!=atoms.res_id[y]:
            assert abs(int(atoms.res_id[x])-int(atoms.res_id[y]))==1 and {atoms.atom_name[x],atoms.atom_name[y]}=={'C','N'},'unsupported crosslink'
    np.savez_compressed(root/'chemical_reference.npz',reference=reference,atom_names=atoms.atom_name,residue_ids=atoms.res_id,chain_ids=atoms.chain_id)
    write_json(root/'variants.json',variants)
    paths=[Path(inspect.getfile(m)) for m in [__import__('fastglycan.connected_output',fromlist=['x']),__import__('fastglycan.articulated_output',fromlist=['x']),__import__('fastglycan.articulated_reference',fromlist=['x']),__import__('fastglycan.hybrid_geometry',fromlist=['x']),__import__('fastglycan.geometry_repair',fromlist=['x']),__import__('fastglycan.sequence_gate_metrics',fromlist=['x']),__import__('fastglycan.collision_audit',fromlist=['x']),__import__('fastglycan.repair_outcomes',fromlist=['x'])]]
    paths += [Path(__file__), root/'code/docs/mini_connected_output_v1.md']
    cases=[dict(arm=arm,seed=s,file=str(source/archived['results'][arm][str(s)]['coordinate_file']),sha256=archived['results'][arm][str(s)]['coordinate_sha256']) for arm in ['controlled_s1','native_s5'] for s in [211,200003,200009]]
    for c in cases:assert sha256(Path(c['file']))==c['sha256']
    ccd=Path(os.environ['PROTENIX_ROOT_DIR'])/'common/components.cif'
    lock=dict(protocol='mini_connected_output_v1',cases=cases,source_hashes={str(f):sha256(f) for f in paths},
              reference_sha256=sha256(root/'chemical_reference.npz'),variants_sha256=sha256(root/'variants.json'),
              source_report_sha256=sha256(source/'report.json'),topology_sha256=sha256(source/'topology.pt'),ccd_sha256=sha256(ccd),
              torch_version=torch.__version__,sequence=seq,scope='one previously seen parent; fixed regression inputs only')
    write_json(root/'lock.json',lock)
    args=(reference,atoms.atom_name,atoms.res_id,seq,variants)
    local=ArticulatedOutput(*args).double();connected=ConnectedOutput(*args).double();connected32=ConnectedOutput(*args).float()
    ca=torch.tensor(np.flatnonzero(atoms.atom_name=='CA'))
    # Include side-chain centres not covered by the legacy CA gate.
    centres=[]
    for i,aa in enumerate(seq,1):
        if aa not in 'IT':continue
        names=['CB','CA','CG1' if aa=='I' else 'OG1','CG2']
        centres.append([int(np.flatnonzero((atoms.res_id==i)&(atoms.atom_name==n))[0]) for n in names])
    centres=np.array(centres,dtype=int).reshape(-1,4)
    def volumes(x):
        a,b,c,d=centres.T
        return (np.cross(x[b]-x[a],x[c]-x[a])*(x[d]-x[a])).sum(-1)
    refvol=volumes(reference);assert np.all(np.abs(refvol)>1e-4)
    report=dict(complete=False,lock_sha256=sha256(root/'lock.json'),cases=[])
    start=time.monotonic()
    for case in cases:
        row=dict(arm=case['arm'],seed=case['seed'],input_sha256=case['sha256'])
        try:
            packet=np.load(case['file']);raw=torch.tensor(packet['coordinates'].reshape(-1,3),dtype=torch.float64)
            x=raw.clone().requires_grad_(True);y=connected(x)
            rng=torch.Generator().manual_seed(6271)
            w=torch.randn(y.shape,generator=rng,dtype=torch.float64);v=torch.randn(x.shape,generator=rng,dtype=torch.float64);v/=v.norm()
            g=torch.autograd.grad((y*w).sum(),x)[0];ad=float((g*v).sum());fd=[]
            for h in [.001,.0001]:
                d=float(((connected(raw+h*v)-connected(raw-h*v))*w).sum()/(2*h))
                fd.append(dict(h=h,fd=d,ad=ad,absolute_error=abs(d-ad),passed=abs(d-ad)<=1e-6+.05*abs(ad)))
            row['derivative']=dict(finite=bool(torch.isfinite(g).all()),norm=float(g.norm()),checks=fd)
            with torch.no_grad():
                ys=y.detach();outputs={'raw':raw,'local':local(raw)['coordinate'],'connected':ys}
                row['cis_like_raw']=sum(float(phase(raw[prev[1]],raw[prev[2]],raw[cur[0]],raw[cur[1]])[0])>0 for prev,cur in zip(connected.anchors,connected.anchors[1:]))
                row['metrics']={}
                for name,z in outputs.items():
                    terms,geometry=top.terms(z);task,_=contact_objective(z[None],ca)
                    pairs=collision_records(z.numpy(),top,atoms.atom_name,atoms.res_id,atoms.chain_id,seq)
                    row['metrics'][name]=dict(geometry=geometry,absolute_failures=absolute_failures(geometry),
                        task=float(task),preservation=preservation(raw.numpy(),z.numpy(),ca.numpy()),
                        sidechain_centres=len(centres),sidechain_wrong=int((volumes(z.numpy())*refvol<=0).sum()),pairs=pairs)
                row['idempotence_max_abs']=float((connected(ys)-ys).abs().max())
                single=connected32(raw.float()).double()
                row['fp32_vs_fp64_max_abs']=float((single-ys).abs().max())
                file=root/f"{case['arm']}_{case['seed']}.npz"
                np.savez_compressed(file,**{k:v.numpy() for k,v in outputs.items()},atom_names=atoms.atom_name,residue_ids=atoms.res_id,chain_ids=atoms.chain_id)
                row.update(success=True,output_file=file.name,output_sha256=sha256(file))
        except Exception:row.update(success=False,error=traceback.format_exc())
        report['cases'].append(row);write_json(root/'report.json',report)
    report.update(complete=True,seconds=time.monotonic()-start)
    report['extend_direct_reconstruction']=all(r.get('success') and r['metrics']['connected']['preservation']['accepted'] for r in report['cases'])
    write_json(root/'report.json',report)
    print(json.dumps(dict(complete=True,seconds=report['seconds'],success=sum(r.get('success',False) for r in report['cases']),extend=report['extend_direct_reconstruction'])))
if __name__=='__main__':main()
