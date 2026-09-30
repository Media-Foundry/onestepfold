import gzip
import json
import pytest
from fastglycan.adapter_sources import scan_adapter_sources


@pytest.mark.parametrize('change,expected',[(None,1),('late',0),('heteromer',0),('incomplete',0)])
def test_adapter_source_screen(tmp_path,change,expected):
    chain=dict(sequence='A'*60,is_protein=True,source_label_asym_id='A',entity_id='1',observed_residue_count=59,sifts_provenance=[dict(sp_primary='P1')])
    second=chain|dict(source_label_asym_id='B',observed_residue_count=60)
    d=dict(pdb_id='test',experimental=dict(resolution_high_angstrom=2.5,model_count=1,methods=['X-RAY DIFFRACTION'],initial_release_date='2020-01-01'),
        chains=[chain,second],assemblies=[dict(assembly_id='1',definition_source='author_determined')],
        assembly_compositions=[dict(assembly_id='1',source_asym_ids=['A','B'],nucleic_acid_chain_instance_count=0,other_polymer_chain_instance_count=0)],asu_observations={})
    if change=='late':d['experimental']['initial_release_date']='2022-01-01'
    if change=='heteromer':second['sequence']='G'*60
    if change=='incomplete':second['observed_residue_count']=59
    path=tmp_path/'catalog.jsonl.gz'
    with gzip.open(path,'wt') as f:f.write(json.dumps(d)+'\n')
    rows=scan_adapter_sources(path);assert len(rows)==expected
    if expected:assert rows[0]['source_label_asym_id']=='B' and rows[0]['sequence']=='A'*60
