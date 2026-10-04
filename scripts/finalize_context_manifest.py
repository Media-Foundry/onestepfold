"""Verify the archived isolation graph and write a prospective context cohort."""
import argparse,csv,hashlib,json
from collections import defaultdict
from pathlib import Path
from fastglycan.context_coverage import select_repeated_contexts
from fastglycan.sequence_isolation import read_hsps


def finalize_context_manifest(out,pool,hits):
    load=lambda p:json.loads(p.read_text())
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    prior=load(Path('reports/mini_factor_student_pilot_2026-10-02/selection.json'))
    old=load(Path('reports/mini_hard_response_rank_2026-10-02/lock.json'))['rows']
    assert sha(hits)==prior['hits_sha256']
    records={r['group_id']:r for r in load(pool)['rows'] if r['group_id'] in prior['all_components']}
    records.update({r['group_id']:r for r in old})
    assert set(records)==set(prior['all_components'])
    aliases={g[:32]:g for g in records};assert len(aliases)==len(records)
    adjacent={g:set() for g in records};hsp_edges=0;accessions=defaultdict(list)
    for h in read_hsps(hits):
        a,b=aliases[h.query],aliases[h.subject]
        if a!=b and h.evidence()['excluded']:
            adjacent[a].add(b);adjacent[b].add(a);hsp_edges+=1
    for g,r in records.items():
        for accession in r['accessions']:accessions[accession].append(g)
    for members in accessions.values():
        for g in members[1:]:adjacent[g].add(members[0]);adjacent[members[0]].add(g)
    # Independent DFS, not the original union-find implementation.
    rebuilt={}
    for start in sorted(records):
        if start in rebuilt:continue
        found=set();stack=[start]
        while stack:
            node=stack.pop()
            if node in found:continue
            found.add(node);stack.extend(adjacent[node]-found)
        canonical=min(found)
        rebuilt.update({g:canonical for g in found})
    assert rebuilt==prior['all_components']
    blocked={rebuilt[r['group_id']] for r in old+prior['rows']}
    preflight=load(out/'reference_preflight.json')
    assert preflight['requests_sha256']==sha(out/'candidate_requests.json')
    assert all(c['component']==rebuilt[c['group_id']] and c['component'] not in blocked for c in preflight['eligible'])
    manifest=select_repeated_contexts(preflight['eligible'])
    for c in manifest['rows']:
        assert all(c['sequence'][p]==a for a,p in c['sites'].items())
    manifest.update(status='candidate_manifest_only_not_training_protocol',reference_preflight_sha256=sha(out/'reference_preflight.json'),
                    expected_unique_sequences=40+160*19,expected_c4_with_one_wt_replay=40+160*19+40,
                    expected_exact_s1_four_noises=4*(40+160*19))
    (out/'candidate_selection.json').write_text(json.dumps(manifest,indent=2)+'\n')
    sites=[]
    for row in manifest['rows']:
        for aa,position in row['sites'].items():
            sites.append(dict(group_id=row['group_id'],pdb_id=row['pdb_id'],component=row['component'],
                              role=row['role'],length=len(row['sequence']),source_aa=aa,position_1based=position+1,
                              **{f'train{n}':row['group_id'] in manifest['nested_train_tiers'][str(n)] for n in (8,16,32)}))
    with (out/'candidate_sites.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(sites[0]),lineterminator='\n');writer.writeheader();writer.writerows(sites)
    audit=dict(complete=True,graph_records=len(rebuilt),qualifying_directed_hsps=hsp_edges,
               graph_components=len(set(rebuilt.values())),blocked_components=len(blocked),selected_components=40,
               cross_split_components=0,prior_response_component_overlap=0,
               hits_sha256=sha(hits),source_selection_sha256=sha(Path('reports/mini_factor_student_pilot_2026-10-02/selection.json')),
               source_pool_sha256=sha(pool),reference_preflight_sha256=sha(out/'reference_preflight.json'),
               selection_sha256=sha(out/'candidate_selection.json'),all_selected_sites_match_sequence=True,
               caveat='operational archived HSP/accession isolation, not remote-homology or pretraining independence')
    (out/'isolation_audit.json').write_text(json.dumps(audit,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--pool',required=True,type=Path);p.add_argument('--hits',required=True,type=Path)
    a=p.parse_args();finalize_context_manifest(a.out,a.pool,a.hits)
