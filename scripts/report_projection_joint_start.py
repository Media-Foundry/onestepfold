#!/usr/bin/env python3
"""Describe every locked paired result, with source failures and extra cost explicit."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np

from fastglycan.paired_teacher_protocol import sha256, write_json


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args();r=a.root
    report=json.loads((r/'report.json').read_text());audit=json.loads((r/'audit.json').read_text())
    assert report['complete'] and audit['complete'] and audit['report_sha256']==sha256(r/'report.json')
    by={x['index']:x for x in report['rows']};arms={}
    for arm in ['zero','fitted']:
        rows=[x for x in by.values() if x['success'] and x['arm']==arm]
        values={}
        for stage in ['raw','local','start','final']:
            m=[x['metrics'][stage] for x in rows]
            values[stage]=dict(
                all_atom_lddt=float(np.mean([v['all_atom_lddt'] for v in m])) if m else None,
                ca_lddt=float(np.mean([v['ca_lddt'] for v in m])) if m else None,
                joint_pass=sum(v['joint_pass'] for v in m),
                connection_pass=sum(v['connection_pass'] for v in m),
                zero_severe=sum(v['geometry']['severe_pairs']==0 for v in m),
                severe_pairs_total=sum(v['geometry']['severe_pairs'] for v in m),
                all_checked_chirality=sum(v['all_checked_chirality_pass'] for v in m),
                preservation_pass=sum(v['preservation']['accepted'] for v in m),
                max_atom_displacement=max([v['preservation']['max_displacement'] for v in m],default=None),
                ca_rms_mean=float(np.mean([v['preservation']['ca_rms'] for v in m])) if m else None,
                backbone_raw_mse=float(np.mean([v['backbone_raw_mse'] for v in m])) if m else None,
                sidechain_raw_mse=float(np.mean([v['sidechain_raw_mse'] for v in m])) if m else None)
        arms[arm]=dict(available=len(rows),planned=16,stages=values,
            median_joint_seconds=float(np.median([x['solver_seconds'] for x in rows])) if rows else None,
            mean_joint_seconds=float(np.mean([x['solver_seconds'] for x in rows])) if rows else None,
            mean_recorded_extra_fit_seconds=float(np.mean([x['recorded_extra_fit_seconds'] for x in rows])) if rows else None,
            joint_iterations=sorted({sum(h['iterations'] for h in x['history']) for x in rows}),
            closures=[sum(h['calls'] for h in x['history']) for x in rows],
            extra_fit_iterations=sorted({x['extra_fit_iterations'] for x in rows}),
            max_peak_rss_kib=max([x['peak_rss_kib'] for x in rows],default=None))
    pairs=[]
    for index in range(0,32,2):
        left,right=by[index],by[index+1]
        row=dict(source_slot=index//4,seed=[12345,54321][(index//2)%2],paired=left['success'] and right['success'])
        if row['paired']:
            assert left['group_id']==right['group_id'] and left['seed']==right['seed']
            x,y=left['metrics']['final'],right['metrics']['final'];raw=left['metrics']['raw']
            row.update(group_id=left['group_id'],pdb_id=left['pdb_id'],raw_aa=raw['all_atom_lddt'],
                zero_aa=x['all_atom_lddt'],fitted_aa=y['all_atom_lddt'],zero_ca=x['ca_lddt'],fitted_ca=y['ca_lddt'],
                delta_aa=y['all_atom_lddt']-x['all_atom_lddt'],delta_ca=y['ca_lddt']-x['ca_lddt'],
                fitted_vs_raw_aa=y['all_atom_lddt']-raw['all_atom_lddt'],
                zero_joint=x['joint_pass'],fitted_joint=y['joint_pass'])
        pairs.append(row)
    proteins=[]
    for slot in range(8):
        rows=[x for x in pairs if x['source_slot']==slot]
        row=dict(source_slot=slot,complete=all(x['paired'] for x in rows))
        if row['complete']:
            row.update(group_id=rows[0]['group_id'],pdb_id=rows[0]['pdb_id'],
                **{k:float(np.mean([x[k] for x in rows])) for k in
                    ['raw_aa','zero_aa','fitted_aa','zero_ca','fitted_ca','delta_aa','delta_ca','fitted_vs_raw_aa']},
                zero_joint=sum(x['zero_joint'] for x in rows),fitted_joint=sum(x['fitted_joint'] for x in rows))
        proteins.append(row)
    complete=[p for p in proteins if p['complete']]
    delta=float(np.mean([x['delta_aa'] for x in complete])) if complete else None
    enough=audit['verified']==28 and audit['paired']==14 and len(complete)==7
    screen=enough and delta>0 and arms['fitted']['stages']['final']['joint_pass']>=arms['zero']['stages']['final']['joint_pass']
    summary=dict(report_sha256=sha256(r/'report.json'),audit_sha256=sha256(r/'audit.json'),
        script_sha256=sha256(Path(__file__)),arms=arms,pairs=pairs,proteins=proteins,
        complete_supported_pairs=enough,paired_protein_mean_delta_aa=delta,
        joint_transitions=dict(gain=sum(x['paired'] and not x['zero_joint'] and x['fitted_joint'] for x in pairs),
            loss=sum(x['paired'] and x['zero_joint'] and not x['fitted_joint'] for x in pairs)),
        bounded_c4_development_candidate=bool(screen),deployment_acceptance=False,
        scope='available7 historical development sequences, retained8-source denominator; no generalization claim')
    write_json(r/'summary.json',summary)
    with (r/'paired_proteins.csv').open('w',newline='') as f:
        fields=list(dict.fromkeys(k for row in proteins for k in row))
        writer=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');writer.writeheader();writer.writerows(proteins)
    print(json.dumps(dict(complete_supported_pairs=enough,delta_aa=delta,
        zero_joint=arms['zero']['stages']['final']['joint_pass'],
        fitted_joint=arms['fitted']['stages']['final']['joint_pass'],candidate=bool(screen))))


if __name__=='__main__':main()
