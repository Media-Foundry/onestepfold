#!/usr/bin/env python3
"""CPU-only preparation and source/weight lock before independent GPU outputs."""
import argparse,concurrent.futures,importlib,inspect,json,multiprocessing,shutil
from pathlib import Path
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.hybrid_geometry import GeometryTopology


def prepare_one(item):
 root,row=item;g=row['group_id'];folder=root/'proteins'/g;folder.mkdir(parents=True,exist_ok=False);packet=Path(row['chemistry']['packet_dir'])
 torch.set_num_threads(1)
 for name,h in row['chemistry']['files'].items():assert sha256(packet/name)==h
 native=torch.load(packet/'native.pt',map_location='cpu',weights_only=False);atoms=native['atoms']
 with np.load(packet/'mapping.npz') as f:reference={k:f[k] for k in ['reference','atom_names','residue_ids','chain_ids']}
 for k,v in [('atom_names',atoms.atom_name),('residue_ids',atoms.res_id),('chain_ids',atoms.chain_id)]:assert np.array_equal(reference[k],v)
 assert np.array_equal(reference['reference'],native['features']['ref_pos'].double().numpy())
 np.savez_compressed(folder/'chemical_reference.npz',**reference);shutil.copy2(packet/'variants.json',folder/'variants.json')
 top=GeometryTopology(atoms,reference['reference']);torch.save(dict(topology=top,sequence=row['sequence'],**reference),folder/'topology.pt')
 return dict(group_id=g,atoms=len(atoms),allowed_nonbonded_pairs=len(top.pairs),files={str(folder/n):sha256(folder/n) for n in ['chemical_reference.npz','variants.json','topology.pt']})


def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--base',type=Path,required=True);a=p.parse_args();r=a.root;b=a.base
 assert not (r/'runtime_lock.json').exists();data=json.loads((r/'data_lock.json').read_text());assert data['complete'] and sha256(r/'panel32.json')==data['panel_sha256']
 for f,h in data['artifact_hashes'].items():assert sha256(Path(f))==h
 panel=json.loads((r/'panel32.json').read_text())
 old=json.loads((b/'anchored_tail_v1_20260929/lock.json').read_text());frozen={}
 for file,h in old['source_hashes'].items():
  path=Path(file)
  if '/src/fastglycan/' in file:
   name='fastglycan.'+path.stem;actual=Path(inspect.getfile(importlib.import_module(name)));assert sha256(actual)==h,('frozen geometry changed',actual);frozen[str(actual)]=h
 with concurrent.futures.ProcessPoolExecutor(max_workers=4,mp_context=multiprocessing.get_context('spawn')) as ex:prepared=list(ex.map(prepare_one,[(r,x) for x in panel]))
 source={str(p):sha256(p) for p in sorted((r/'code').rglob('*.py'))}
 for name in ['protenix','esm','runner','configs']:
  folder=Path(inspect.getfile(importlib.import_module(name))).parent
  source.update({str(p):sha256(p) for p in sorted(folder.rglob('*.py'))})
 checkpoint=b/'protenix_stage0_pkg/v1_1/runtime/checkpoint';weights={str(checkpoint/n):sha256(checkpoint/n) for n in ['protenix_mini_esm_v0.5.0.pt','esm2_t36_3B_UR50D.pt','esm2_t36_3B_UR50D-contact-regression.pt']}
 write_json(r/'runtime_lock.json',dict(data_lock_sha256=sha256(r/'data_lock.json'),panel_sha256=sha256(r/'panel32.json'),source_hashes=source,frozen_geometry=frozen,weights_sha256=weights,prepared=prepared,model='protenix_mini_esm_v0.5.0',dtype='fp32',cycles=4,steps=1,noises=[300007,300017,300023],devices=list(range(8)),repair_timeout=900,raw_per_seed_timeout=1800,per_protein_raw_external_timeout=5400,torch_version=torch.__version__,gt_in_model=False,gt_in_repair=False,source_context=dict(monomer=28,homooligomer_chain=4),protocol_sha256={str(p):sha256(p) for p in (r/'code/docs').glob('mini_independent32_execution*.md')}))
 print('runtime locked32 before GPU outputs',flush=True)


if __name__=='__main__':main()
