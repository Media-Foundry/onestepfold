#!/usr/bin/env python3
"""Read-only export of installed CCD backbone input reference geometry."""
import hashlib
import json
from pathlib import Path


def export_ccd_backbone_reference():
    from protenix.data.core import ccd
    amino_acids = dict(zip('ACDEFGHIKLMNPQRSTVWY',
        ['ALA','CYS','ASP','GLU','PHE','GLY','HIS','ILE','LYS','LEU','MET','ASN','PRO','GLN','ARG','SER','THR','VAL','TRP','TYR']))
    records = {}
    for aa, name in amino_acids.items():
        ref = ccd.get_ccd_ref_info(name, return_perm=False)
        indices = [ref['atom_map'][n] for n in ['N','CA','C','O']]
        assert ref['mask'][indices].all()
        records[aa] = dict(ccd=name, atom_names=['N','CA','C','O'],
            coordinates=ref['coord'][indices].tolist(),
            conformer_id=int(ccd.get_component_rdkit_mol(name).ref_conf_id))
    return dict(records=records, hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in [Path(ccd.__file__), ccd.RKDIT_MOL_PKL]},
        scope='input reference geometry; not chemical acceptance standard')


if __name__ == '__main__':
    print(json.dumps(export_ccd_backbone_reference(), indent=2))
