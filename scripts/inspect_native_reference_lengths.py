#!/usr/bin/env python3
"""Read-only runtime provenance of saved native reference backbone lengths."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import torch


def inspect_native_reference_lengths(source):
    import protenix
    from protenix.data.core import ccd
    package = Path(protenix.__file__).parent
    files = [package / name for name in [
        'data/core/ccd.py', 'data/core/parser.py', 'data/core/featurizer.py',
        'data/inference/json_to_feature.py']]
    files.append(ccd.RKDIT_MOL_PKL)
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    selection = json.loads((source / 'selection.json').read_text())
    records, skipped = [], []
    for row in selection:
        folder = source / 'chemistry' / row['group_id']
        if not (folder / 'native.pt').exists():
            skipped.append(row['pdb_id'])
            continue
        packet = torch.load(folder / 'native.pt', map_location='cpu', weights_only=False)
        mapping = np.load(folder / 'mapping.npz')
        atoms, features = packet['atoms'], packet['features']
        ref = features['ref_pos'].double().numpy()
        assert np.array_equal(ref, mapping['reference'])
        bonds = []
        for i, aa in enumerate(row['sequence'], 1):
            ix = np.flatnonzero(atoms.res_id == i)
            lookup = {str(atoms.atom_name[j]): int(j) for j in ix}
            residue = str(atoms.res_name[ix[0]])
            cached = ccd.get_ccd_ref_info(residue, return_perm=False)
            mol = ccd.get_component_rdkit_mol(residue)
            for left, right in [('CA', 'C'), ('N', 'CA')]:
                native = float(np.linalg.norm(ref[lookup[left]] - ref[lookup[right]]))
                cache = float(np.linalg.norm(cached['coord'][cached['atom_map'][left]] -
                                            cached['coord'][cached['atom_map'][right]]))
                bonds.append(dict(residue=i, residue_name=residue, atoms=[left, right],
                    native_length=native, cached_length=cache,
                    absolute_difference=abs(native-cache), reference_conformer_id=int(mol.ref_conf_id)))
        error = max(b['absolute_difference'] for b in bonds)
        assert error < 2e-5
        records.append(dict(pdb_id=row['pdb_id'], group_id=row['group_id'],
            native_sha256=hashlib.sha256((folder/'native.pt').read_bytes()).hexdigest(),
            mapping_sha256=hashlib.sha256((folder/'mapping.npz').read_bytes()).hexdigest(),
            maximum_cache_difference=error, bonds=bonds))
    return dict(complete=True, source=str(source), source_hashes=hashes, records=records,
        skipped=skipped, scope='saved native input and current runtime CCD reference; no regenerated model or solver outputs')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(inspect_native_reference_lengths(args.source), indent=2))
