#!/usr/bin/env python3
"""Export explicitly labelled CCD ideal geometry and native reference by identity."""
import argparse
import hashlib
import json
from pathlib import Path

import gemmi
import numpy as np


def export_ccd_ideal_templates(output):
    from protenix.data.core import ccd
    assert not output.exists();output.mkdir(parents=True)
    names=dict(zip('ACDEFGHIKLMNPQRSTVWY',
        ['ALA','CYS','ASP','GLU','PHE','GLY','HIS','ILE','LYS','LEU','MET','ASN','PRO','GLN','ARG','SER','THR','VAL','TRP','TYR']))
    source=Path(ccd.COMPONENTS_FILE)
    hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,ccd.RKDIT_MOL_PKL,Path(ccd.__file__)]}
    # Stream individual data blocks: avoid materializing the full CCD as Python objects.
    blocks={};current=None;buffer=[]
    with source.open() as stream:
        for line in stream:
            if line.startswith('data_'):
                if current in names.values():blocks[current]=''.join(buffer)
                current=line.strip()[5:];buffer=[]
            if current in names.values():buffer.append(line)
        if current in names.values():blocks[current]=''.join(buffer)
    assert set(blocks)==set(names.values())
    records={}
    for aa,code in names.items():
        text=blocks[code];block=gemmi.cif.read_string(text).sole_block()
        atoms=block.get_mmcif_category('_chem_comp_atom.')
        ix=[i for i,n in enumerate(atoms['atom_id']) if atoms['type_symbol'][i] not in ['H','D'] and atoms['pdbx_leaving_atom_flag'][i]=='N']
        inventory=[atoms['atom_id'][i] for i in ix];assert len(set(inventory))==len(inventory)
        ideal=np.array([[float(atoms['pdbx_model_Cartn_'+axis+'_ideal'][i]) for axis in ['x','y','z']] for i in ix])
        assert np.isfinite(ideal).all() and {'N','CA','C','O'}.issubset(inventory)
        native=ccd.get_ccd_ref_info(code,return_perm=False)
        indices=[native['atom_map'][n] for n in inventory];assert native['mask'][indices].all()
        table=block.get_mmcif_category('_chem_comp_bond.');bonds=[]
        for i,left in enumerate(table['atom_id_1']):
            right=table['atom_id_2'][i]
            if left in inventory and right in inventory:
                order={'SING':1,'DOUB':2,'TRIP':3,'AROM':4}[table['value_order'][i]]
                bonds.append([inventory.index(left),inventory.index(right),order])
        component=block.get_mmcif_category('_chem_comp.')
        record=dict(ccd=code,atom_names=inventory,elements=[atoms['type_symbol'][i] for i in ix],
            bonds=bonds,ideal=ideal.tolist(),native=native['coord'][indices].tolist(),
            native_conformer_id=int(ccd.get_component_rdkit_mol(code).ref_conf_id),
            stereo={atoms['atom_id'][i]:atoms['pdbx_stereo_config'][i] for i in ix},
            metadata={k:v for k,v in component.items() if any(s in k for s in ['ideal','model_coordinates','type','modified_date','release'])},
            component_sha256=hashlib.sha256(text.encode()).hexdigest())
        (output/(code+'.cif')).write_text(text);records[aa]=record
    (output/'templates.json').write_text(json.dumps(dict(records=records,hashes=hashes,
        explicit_ideal_columns=True,heavy_non_leaving_only=True),indent=2)+'\n')
    print(json.dumps(dict(templates=len(records),source=str(source),atoms=sum(len(r['atom_names']) for r in records.values()))))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    export_ccd_ideal_templates(p.parse_args().output)
