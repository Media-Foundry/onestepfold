import importlib.util
from pathlib import Path
import pytest


@pytest.fixture
def source_module(monkeypatch):
    pytest.importorskip('gemmi')
    folder=Path(__file__).parents[1]/'scripts';monkeypatch.syspath_prepend(str(folder))
    spec=importlib.util.spec_from_file_location('qualified_sources',folder/'qualify_discovered_chains.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m


class Block:
    def __init__(self,seq='AAA',connection=None):
        self.tables={'_struct_conn.':connection or {},'_entity_poly.':{'entity_id':['1','2'],'type':['polypeptide(L)']*2,'pdbx_seq_one_letter_code_can':['AAA',seq]},'_struct_asym.':{'id':['A','B'],'entity_id':['1','2']}}
    def get_mmcif_category(self,key):return self.tables[key]


def row():
    return dict(sequence='AAA',source_label_asym_id='A',source_assembly_composition=dict(source_asym_ids=['A','B'],nucleic_acid_chain_instance_count=0,other_polymer_chain_instance_count=0,protein_chain_instance_count=2))


def test_homomer_is_not_any_protein_multimer(source_module):
    assert source_module.source_context(row(),Block())['homooligomer']
    assert not source_module.source_context(row(),Block('AAT'))['homooligomer']
    r=row();r['source_assembly_composition']['nucleic_acid_chain_instance_count']=1
    assert not source_module.source_context(r,Block())['homooligomer']


def test_interchain_covalent_link_is_not_ordinary_peptide(source_module):
    conn=dict(conn_type_id=['covale'],ptnr1_label_asym_id=['A'],ptnr2_label_asym_id=['B'],ptnr1_label_atom_id=['C'],ptnr2_label_atom_id=['N'],ptnr1_label_seq_id=['1'],ptnr2_label_seq_id=['2'])
    assert source_module.source_context(row(),Block(connection=conn))['unsupported_connections']
    conn['ptnr2_label_asym_id']=['A']
    assert not source_module.source_context(row(),Block(connection=conn))['unsupported_connections']
