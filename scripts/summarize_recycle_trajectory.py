"""Summarize all fixed trajectory paths; no fitting or selection of variants."""
import argparse
import gzip
import json
from pathlib import Path

import numpy as np

from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.reference_editor_metrics import summarize_editor_sites,paired_parent_interval


def summarize_trajectory(root):
    sites,outputs,latent,errors=[],[],[],[];sources={};counts={}
    for shard in range(2):
        path=root/f'scores_{shard}.json.gz';sources[path.name]=sha256(path)
        with gzip.open(path,'rt') as f: data=json.load(f)
        assert data['complete'];sites.extend(data['sites']);outputs.extend(data['outputs'])
        record=json.loads((root/f'shard_{shard}.json').read_text());assert record['complete']
        latent.extend(record['latent']);errors.extend(record['candidate_errors'])
        for key,value in record['counts'].items():counts[key]=counts.get(key,0)+value
    assert len(sites)==144 and len(outputs)==5472 and len(latent)==48 and len(errors)==912
    assert len({(r['site_key'],r['arm']) for r in sites})==144
    assert len({(r['site_key'],r['arm'],r['noise'],r['aa']) for r in outputs})==5472
    lookup={(r['site_key'],r['arm']):r for r in sites}
    # Verify the action and raw regret directly from the saved score arrays.
    for row in sites:
        exact=np.array(lookup[row['site_key'],'exact']['tasks']);pred=np.array(row['tasks'])
        selected=int(pred[0].argmin())
        expected=float(exact[1,selected]-exact[1].min())
        assert np.isclose(expected,row['old_select_new_regret'],rtol=1e-12,atol=1e-12)
    summary,contrasts,geometry,latent_summary,boundary_errors={},{},[],{},{ }
    for role in sorted({r['role'] for r in sites}):
        summary[role]={};contrasts[role]={}
        for arm in ('exact','cold_c2','wt_progress'):
            ss=[r for r in sites if r['role']==role and r['arm']==arm]
            oo=[r for r in outputs if r['role']==role and r['arm']==arm]
            value=summarize_editor_sites(ss,oo)
            for field in ('cold_c2_pass_to_fail','cold_c2_fail_to_pass'):
                value[field]=sum(r[field] for r in oo)
            for field,key in (('severe_pairs','severe_pairs'),('wrong_centres','checked_chirality_wrong')):
                value[field]=sum(r['geometry'][key] for r in oo)
            summary[role][arm]=value
            for parent in sorted({r['parent'] for r in oo}):
                group=[r for r in oo if r['parent']==parent]
                geometry.append(dict(role=role,arm=arm,parent=parent,outputs=len(group),
                    passed=sum(r['geometry']['zero_severe_strict_checked_chirality'] for r in group),
                    severe_pairs=sum(r['geometry']['severe_pairs'] for r in group),
                    wrong_centres=sum(r['geometry']['checked_chirality_wrong'] for r in group),
                    new_failures=sum(r['cold_c2_pass_to_fail'] for r in group),
                    repairs=sum(r['cold_c2_fail_to_pass'] for r in group)))
        for ref in ('cold_c2','exact'):
            contrasts[role]['wt_progress-'+ref]={metric:paired_parent_interval(
                summary[role]['wt_progress']['parent_summaries'],summary[role][ref]['parent_summaries'],metric)
                for metric in ('spearman','regret','centered_response_rmse')}
        group=[r for r in latent if r['role']==role];parents=sorted({r['parent'] for r in group})
        boundary_errors[role]={}
        for field in ('s','z'):
            values=[r for r in errors if r['role']==role]
            def parent_mean(metric):
                return float(np.mean([np.mean([metric(r['states'][field]) for r in values
                    if r['parent']==parent]) for parent in parents]))
            boundary_errors[role][field]=dict(
                before_rmse_parent_mean=parent_mean(lambda r:r['before_mse']**.5),
                after_rmse_parent_mean=parent_mean(lambda r:r['after_mse']**.5),
                before_mse_parent_mean=parent_mean(lambda r:r['before_mse']),
                after_mse_parent_mean=parent_mean(lambda r:r['after_mse']),
                candidates=len(values),
                tiny_denominators=sum(r['states'][field]['tiny_denominator'] for r in values))
        latent_summary[role]={}
        for stage in ('before','cold_c2','wt_progress'):
            latent_summary[role][stage]={}
            for field in ('s','z'):
                metrics={}
                for part in ('raw','common','centered'):
                    metrics[part]={}
                    for metric in ('nmse','cosine','energy_ratio','error_energy'):
                        parent_values=[]
                        for parent in parents:
                            vals=[]
                            for row in group:
                                if row['parent']!=parent:continue
                                value=(row['before'] if stage=='before' else row['after'][stage])[field][part][metric]
                                if value is not None:vals.append(value)
                            if vals:parent_values.append(float(np.mean(vals)))
                        metrics[part][metric]=float(np.mean(parent_values)) if parent_values else None
                latent_summary[role][stage][field]=metrics
    write_json(root/'summary.json',dict(complete=True,summary=summary,contrasts=contrasts,
        geometry_by_parent=geometry,latent_summary=latent_summary,score_hashes=sources,
        native_counts=counts,sites=sites,per_candidate_errors=errors,boundary_errors=boundary_errors,
        independent_confirmation=False,promoted=False,training_updates=0,speed_claim=False))
    print('TRAJECTORY_SUMMARY_COMPLETE',counts,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
    summarize_trajectory(p.parse_args().root)
