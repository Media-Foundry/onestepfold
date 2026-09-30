"""Source-only eligibility for a bounded native diffusion learning pilot."""
import gzip
import hashlib
import json


def scan_adapter_sources(path):
    rows=[]
    with gzip.open(path,'rt') as handle:
        for line in handle:
            d=json.loads(line);e=d['experimental'];resolution=e.get('resolution_high_angstrom')
            if not resolution or not 0<resolution<=2.5 or e.get('model_count')!=1:
                continue
            if 'X-RAY DIFFRACTION' not in e.get('methods',[]) or not e.get('initial_release_date') or e['initial_release_date']>'2021-09-30':
                continue
            chains={c['source_label_asym_id']:c for c in d['chains']}
            compositions={c['assembly_id']:c for c in d['assembly_compositions']}
            for assembly in d['assemblies']:
                if assembly['definition_source'] not in ['author_determined','author_and_software']:
                    continue
                comp=compositions.get(assembly['assembly_id'])
                if not comp or comp['nucleic_acid_chain_instance_count'] or comp['other_polymer_chain_instance_count']:
                    continue
                proteins=[chains[x] for x in comp['source_asym_ids'] if chains[x]['is_protein']]
                if not proteins or len({c['sequence'] for c in proteins})!=1:
                    continue
                # Choose among complete observed chains before any GT geometry or model score.
                complete=[c for c in proteins if c.get('observed_residue_count',0)==len(c['sequence'])]
                if not complete:continue
                c=min(complete,key=lambda x:x['source_label_asym_id']);seq=c['sequence']
                if not 50<=len(seq)<=1024 or not set(seq)<=set('ACDEFGHIKLMNPQRSTVWY'):continue
                acc=sorted({x['sp_primary'] for x in c['sifts_provenance']})
                if not acc:continue
                g=hashlib.sha256(seq.encode()).hexdigest()
                rows.append(dict(group_id=g,pdb_id=d['pdb_id'],sequence=seq,sequence_length=len(seq),
                    sequence_sha256=g,source_label_asym_id=c['source_label_asym_id'],entity_id=c['entity_id'],
                    chain_record=c,experimental=e,asu_observations=d['asu_observations'],
                    resolution_high_angstrom=resolution,assembly_id=assembly['assembly_id'],
                    assembly_definition_source=assembly['definition_source'],source_assembly_composition=comp,
                    accessions=acc,stratum=int(len(seq)>=256),split='adapter_pilot_source',catalog_shard=str(path)))
    return rows
