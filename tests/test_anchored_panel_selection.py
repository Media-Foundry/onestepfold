"""The isolation check must reject close constructs, not only exact IDs."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('panel_selector', Path(__file__).parents[1]/'scripts/select_anchored_independent.py')
selector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(selector)


def test_near_sequence_rule_rejects_exact_and_truncated_constructs():
    aligner = selector._new_homology_aligner()
    sequence = 'ACDEFGHIKLMNPQRSTVWY' * 5
    assert selector.near(sequence, sequence, aligner)
    assert selector.near(sequence, sequence[:70], aligner)
    assert not selector.near('A' * 100, 'W' * 100, aligner)
    assert not selector.near(sequence[:40], sequence[:40], aligner)


def test_backbone_missing_is_a_scope_exclusion(tmp_path):
    import json
    row = dict(sequence='A' * 60)
    (tmp_path/'gt.json').write_text(json.dumps(dict(chains=[row], qa=dict(
        modified_residue_count=0, chain_break_count=0, backbone4_coverage=.99))))
    (tmp_path/'gt.npz').write_bytes(b'not read after metadata exclusion')
    (tmp_path/'input_provenance.json').write_text('{}')
    (tmp_path/'prepared.json').write_text(json.dumps(dict(complete=True, files_sha256={
        n: selector.digest(tmp_path/n) for n in ['gt.json', 'gt.npz', 'input_provenance.json']})))
    assert selector.screen_structure(tmp_path, row) == 'modified_broken_or_missing_backbone'
