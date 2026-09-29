#!/usr/bin/env python3
"""Source/chemistry checks only, before any folding or solver outputs."""
import argparse
import concurrent.futures
import hashlib
import json
import multiprocessing
import traceback
from pathlib import Path


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(item):
    row,root,base=item; folder=root/row['group_id'];folder.mkdir(exist_ok=False)
    result=dict(group_id=row['group_id'],length=len(row['sequence']),pdb_id=row['pdb_id'],passed=False)
    try:
        import gemmi
        import numpy as np
        import torch
        from fastglycan.models.soft_sequence_chart import native_sequence_features
        from fastglycan.articulated_output import ArticulatedOutput,AA
        from onestepfold.data.gt_materializer import ATOM37_INDEX
        torch.set_num_threads(1)
        source=base/'scratch_structure_data_v1_20260927/examples'/row['group_id']
        prepared=json.loads((source/'prepared.json').read_text());meta=json.loads((source/'gt.json').read_text())
        for n in ['gt.json','gt.npz','input_provenance.json']:
            assert sha(source/n)==prepared['files_sha256'][n]
        provenance=json.loads((source/'input_provenance.json').read_text())
        assert provenance['sequence']==row['sequence'] and provenance['raw_gt_rebuild_exact']
        assert len(meta['chains'])==1
        chain=meta['chains'][0]['source_label_asym_id'];pdb=row['pdb_id'].lower()
        cif=base/'Dataset/raw/pdb_mmcif'/pdb[1:3]/(pdb+'.cif.gz')
        assert sha(cif)==provenance['source_mmcif_sha256']
        block=gemmi.cif.read(str(cif)).sole_block();conn=block.get_mmcif_category('_struct_conn.')
        unsupported=[]
        for i,kind in enumerate(conn.get('conn_type_id',[])):
            if not (kind.startswith('covale') or kind=='disulf'):continue
            c1=conn['ptnr1_label_asym_id'][i];c2=conn['ptnr2_label_asym_id'][i]
            if chain not in [c1,c2]:continue
            n1=conn['ptnr1_label_atom_id'][i];n2=conn['ptnr2_label_atom_id'][i]
            r1=conn['ptnr1_label_seq_id'][i];r2=conn['ptnr2_label_seq_id'][i]
            ordinary=(c1==c2==chain and str(r1).isdigit() and str(r2).isdigit() and
                      abs(int(r1)-int(r2))==1 and {n1,n2}=={'C','N'})
            if not ordinary:unsupported.append(dict(type=kind,chains=[c1,c2],atoms=[n1,n2],residues=[r1,r2]))
        result['unsupported_source_connections']=unsupported
        if unsupported:raise ValueError('source covalent connection outside supported chemistry')
        features,atoms=native_sequence_features(row['sequence'])
        assert features['ref_mask'].bool().all() and len(set(atoms.chain_id))==1
        reference=features['ref_pos'].double().numpy();bonds=atoms.bonds.as_array();variants={}
        for i,aa in enumerate(row['sequence'],1):
            ix=np.flatnonzero(atoms.res_id==i);names=atoms.atom_name[ix].tolist();local={int(j):k for k,j in enumerate(ix)}
            assert all(n in names for n in ['N','CA','C','O'])
            assert 'OXT' not in names or i==len(row['sequence'])
            variants[AA[aa]+':'+','.join(names)]=dict(atom_names=names,bonds=[
                [local[int(x)],local[int(y)],int(o)] for x,y,o in bonds if int(x) in local and int(y) in local])
        links=[]
        for x,y,o in bonds:
            if atoms.res_id[x]!=atoms.res_id[y]:
                assert abs(int(atoms.res_id[x])-int(atoms.res_id[y]))==1 and {atoms.atom_name[x],atoms.atom_name[y]}=={'C','N'}
                links.append(tuple(sorted((int(atoms.res_id[x]),int(atoms.res_id[y])))))
        assert sorted(links)==[(i,i+1) for i in range(1,len(row['sequence']))]
        adapter=ArticulatedOutput(reference,atoms.atom_name,atoms.res_id,row['sequence'],variants).double()
        with torch.no_grad():
            replay=adapter(torch.tensor(reference))['coordinate'].numpy()
        error=float(np.max(np.abs(replay-reference)));assert error<1e-5
        with np.load(source/'gt.npz') as gt:
            ri=atoms.res_id.astype(int)-1;ai=np.array([ATOM37_INDEX[str(n)] for n in atoms.atom_name])
            mask=gt['atom37_mask'][ri,ai] & gt['residue_mask'][ri]
            coordinates=gt['atom37_positions'][ri,ai].copy();coordinates[~mask]=0
            assert np.isfinite(coordinates[mask]).all()
            assert mask[np.isin(atoms.atom_name,['N','CA','C','O'])].all()
        np.savez_compressed(folder/'mapping.npz',coordinates=coordinates,mask=mask,reference=reference,
                            atom_names=atoms.atom_name,residue_ids=atoms.res_id,chain_ids=atoms.chain_id)
        torch.save(dict(features=features,atoms=atoms),folder/'native.pt')
        (folder/'variants.json').write_text(json.dumps(variants,indent=2)+'\n')
        result.update(passed=True,atom_count=len(atoms),observed_atoms=int(mask.sum()),reference_replay_max_abs=error,
            source_hashes={n:sha(source/n) for n in ['gt.json','gt.npz','input_provenance.json','prepared.json']},
            cif_sha256=sha(cif),files={n:sha(folder/n) for n in ['mapping.npz','native.pt','variants.json']})
    except Exception:result['error']=traceback.format_exc()
    (folder/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--selection',type=Path,required=True)
    p.add_argument('--root',type=Path,required=True);p.add_argument('--base',type=Path,required=True);a=p.parse_args()
    a.root.mkdir(exist_ok=False)
    rows=json.loads(a.selection.read_text())
    with concurrent.futures.ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context('spawn')) as executor:
        results=list(executor.map(check,[(r,a.root,a.base) for r in rows]))
    (a.root/'report.json').write_text(json.dumps(dict(complete=True,total=len(rows),passed=sum(r['passed'] for r in results),
        rows=results,selection_sha256=sha(a.selection),source_sha256=sha(Path(__file__)),folding_started=False),indent=2)+'\n')


if __name__=='__main__':main()
