import pytest
from fastglycan.sequence_isolation import HSP


def test_gap_columns_are_not_residue_coverage_or_identity():
    h = HSP('q','s',100,200,1e-4,'A'*40+'-'*60,'A'*100)
    e = h.evidence()
    assert e['identity'] == 1 and e['aligned_residues'] == 40
    assert e['shorter_coverage'] == .4 and not e['excluded']


def test_significance_and_domain_guard_are_separate():
    assert not HSP('q','s',100,100,.1,'A'*100,'A'*100).evidence()['excluded']
    h = HSP('q','s',300,400,1e-6,'A'*60,'A'*10+'W'*50).evidence()
    assert h['domain'] and not h['near'] and h['excluded']
    assert HSP('q','s',70,200,.001,'A'*50,'A'*15+'W'*35).evidence()['near']


def test_malformed_alignment_is_not_silently_accepted():
    with pytest.raises(ValueError):
        HSP('q','s',10,10,0,'AAAA','AAA').evidence()


def test_blast_id_aliases_restore_full_group_ids(tmp_path):
    import importlib.util
    from pathlib import Path
    spec=importlib.util.spec_from_file_location('calibrate',Path(__file__).parents[1]/'scripts/calibrate_sequence_isolation.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    g='a'*64; f=tmp_path/'sequences.fasta'
    module.fasta(f,[dict(id=g,sequence='A'*60)])
    assert f.read_text().splitlines()[0]=='>'+g[:32]
    t=tmp_path/'hits.tsv';t.write_text('query\t'+g[:32]+'\t60\t60\t1e-20\t'+'A'*60+'\t'+'A'*60+'\n')
    hit=next(module.decoded_hsps(t,{g[:32]:g}))
    assert hit.query=='query' and hit.subject==g and hit.evidence()['excluded']
