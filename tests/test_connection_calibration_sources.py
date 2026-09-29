import copy
import gzip
import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/extend_connection_calibration.py'
SPEC = importlib.util.spec_from_file_location('calibration_extension', SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_full_catalog_filter_retains_homomers_but_excludes_heteromers_and_temporal(tmp_path):
    chain = dict(source_label_asym_id='A', is_protein=True, sequence='A' * 60,
                 entity_id='1', sifts_provenance=[dict(sp_primary='TEST')])
    record = dict(pdb_id='test', experimental=dict(resolution_high_angstrom=1.2,
        model_count=1, methods=['X-RAY DIFFRACTION'], initial_release_date='2020-01-01'),
        chains=[chain, chain | {'source_label_asym_id': 'B'}],
        assemblies=[dict(assembly_id='1', definition_source='author_determined')],
        assembly_compositions=[dict(assembly_id='1', source_asym_ids=['A', 'B'],
            protein_chain_instance_count=2, nucleic_acid_chain_instance_count=0,
            other_polymer_chain_instance_count=0)], asu_observations={})
    heteromer = copy.deepcopy(record); heteromer['chains'][1]['sequence'] = 'C' * 60
    temporal = copy.deepcopy(record); temporal['experimental']['initial_release_date'] = '2022-01-01'
    poor_resolution = copy.deepcopy(record); poor_resolution['experimental']['resolution_high_angstrom'] = 1.6
    path = tmp_path / 'shard.jsonl.gz'
    with gzip.open(path, 'wt') as out:
        for r in [record, heteromer, temporal, poor_resolution]:
            out.write(json.dumps(r) + '\n')
    rows = MODULE.scan_calibration_shard(path)
    assert len(rows) == 1 and rows[0]['source_label_asym_id'] == 'A'
    assert rows[0]['source_assembly_composition']['protein_chain_instance_count'] == 2
