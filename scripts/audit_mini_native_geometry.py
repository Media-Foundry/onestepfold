#!/usr/bin/env python3
"""CPU-only native geometry attribution against archived experimental structures."""
import argparse, io, json, tarfile
from pathlib import Path
import numpy as np
from fastglycan.models.soft_sequence_chart import native_sequence_features
from fastglycan.hybrid_geometry import GeometryTopology
from fastglycan.geometry_audit import independent_allowed_pairs, pair_attribution, observed_bond_geometry
from fastglycan.paired_teacher_protocol import sha256, write_json
from onestepfold.data.gt_materializer import ATOM37_INDEX


def main():
    p=argparse.ArgumentParser()
    for name in ('root','reference-root','shard-root','out'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(exist_ok=False,parents=True)
    lock=json.load(open(a.root/'lock.json'));manifest=json.load(open(a.reference_root/'manifest.json'))
    report=dict(complete=False,scope='six existing development cases only; no new inference or policy changes',
                lock_sha256=sha256(a.root/'lock.json'),cases=[])
    for name,case in lock['cases'].items():
        seq=case['sequence'];meta=manifest[case['group']]
        assert meta['sequence']==seq and meta['stage0_view']=='temporal_dev_v1'
        f,atoms=native_sequence_features(seq);topology=GeometryTopology(atoms,f['ref_pos'].numpy())
        pairs=independent_allowed_pairs(atoms)
        assert np.array_equal(pairs,topology.pairs.numpy()),'covalent exclusion mismatch'
        shard=a.shard_root/Path(meta['shard']).name
        with tarfile.open(shard) as archive:
            payload=archive.extractfile(meta['npz']).read()
            with np.load(io.BytesIO(payload)) as data:
                # Native residue numbers are 1..L and sequence is asserted above.
                indices=np.asarray([ATOM37_INDEX[str(n)] for n in atoms.atom_name])
                residues=atoms.res_id.astype(int)-1
                ref=data['atom37_positions'][residues,indices].astype(np.float64)
                observed=data['atom37_mask'][residues,indices] & data['residue_mask'][residues]
        import hashlib
        run=json.load(open(a.root/f'{name}_s1/report.json'))
        row=dict(case=name,pdb=meta['pdb_id'],group=case['group'],gt_npz=meta['npz'],
                 gt_payload_sha256=hashlib.sha256(payload).hexdigest(),
                 atom_count=len(atoms),observed_atom_count=int(observed.sum()),
                 exclusions_exact=True,peptide_bonds=int(topology.peptide.sum()),
                 expected_peptide_bonds=len(seq)-1,baselines={})
        # Zero-filled missing GT coordinates are explicitly excluded from every reported GT pair.
        gt=pairs[observed[pairs].all(1)]
        row['experimental_geometry']=observed_bond_geometry(ref,topology,observed)
        row['experimental']=pair_attribution(atoms,ref,gt,observed=observed,reference=ref)
        for seed,b in run['baseline']['values'].items():
            path=a.root/f'{name}_s1'/b['coordinate_file']
            assert sha256(path)==b['coordinate_sha256']
            with np.load(path) as d:
                assert str(d['sequence'])==seq
                for field,attribute in [('atom_names','atom_name'),('residue_ids','res_id'),('chain_ids','chain_id')]:
                    assert np.array_equal(d[field],getattr(atoms,attribute)),field
                x=d['coordinates'].reshape(-1,3)
            value=pair_attribution(atoms,x,pairs,observed=observed,reference=ref)
            assert abs(value['all_atoms']['max_penetration']-b['geometry']['max_penetration'])<2e-5
            assert value['all_atoms']['severe_pairs']==b['geometry']['severe_pairs']
            value['observed_bond_geometry']=observed_bond_geometry(x,topology,observed)
            value['coordinate_sha256']=sha256(path);row['baselines'][seed]=value
        report['cases'].append(row);write_json(a.out/'report.json',report)
    report['complete']=True;write_json(a.out/'report.json',report)
    write_json(a.out/'acceptance.json',dict(complete=True,report_sha256=sha256(a.out/'report.json')))

if __name__=='__main__':main()
