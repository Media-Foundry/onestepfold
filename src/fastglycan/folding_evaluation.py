"""Protein-weighted continuation evaluation, with original and added TRAIN split."""
import numpy as np


def summarize_folding_cohorts(records, lock):
    lookup={(r['group_id'],r['seed'],r['model']):r for r in records}
    if len(lookup)!=len(records):raise ValueError('duplicate prediction record')
    rows={r['group_id']:r for r in lock['rows']}
    membership=[g for groups in lock['cohorts'].values() for g in groups]
    if len(membership)!=len(set(membership)) or set(membership)!=set(rows):
        raise ValueError('cohorts must partition the locked proteins')
    expected={(g,s,m) for g,r in rows.items() for s in (lock['train_seeds'] if r['role']=='train' else lock['validation_seeds']) for m in lock['models']}
    if set(lookup)!=expected:raise ValueError('missing or unexpected prediction; no reduced denominator')
    result={};paired=[]
    for cohort,groups in lock['cohorts'].items():
        n=len(groups)
        boot=np.random.default_rng(lock['bootstrap']['seed']).integers(0,n,size=(lock['bootstrap']['replicates'],n))
        arrays={};models={}
        for model in lock['models']:
            means=[];items=[];both=0
            for g in groups:
                seeds=lock['train_seeds'] if rows[g]['role']=='train' else lock['validation_seeds']
                pair=[lookup[g,s,model] for s in seeds];items.extend(pair)
                means.append([np.mean([v[k] for v in pair]) for k in ['all_atom_lddt','ca_lddt']])
                both+=all(v['geometry']['severe_pairs']==0 and v['geometry']['strict_checked_chirality'] for v in pair)
            arrays[model]=np.asarray(means)
            models[model]=dict(mean_aa=float(arrays[model][:,0].mean()),mean_ca=float(arrays[model][:,1].mean()),
                zero_and_strict_both_noises=both,instances=len(items),
                severe_pairs=sum(v['geometry']['severe_pairs'] for v in items),
                zero_and_strict_instances=sum(v['geometry']['severe_pairs']==0 and v['geometry']['strict_checked_chirality'] for v in items))
        contrasts=[]
        for candidate,reference in lock['contrasts']:
            delta=arrays[candidate]-arrays[reference];quality={};new_clash=lost_stereo=0
            for column,metric in enumerate(['all_atom_lddt','ca_lddt']):
                x=delta[:,column]
                quality[metric]=dict(mean=float(x.mean()),median=float(np.median(x)),
                    ci95=np.quantile(x[boot].mean(1),[.025,.975]).tolist(),p01=float(np.quantile(x,.01)),
                    p05=float(np.quantile(x,.05)),worst5_mean=float(np.sort(x)[:max(1,int(np.ceil(.05*n)))].mean()),
                    below_minus_005=int((x<-.05).sum()),positive_proteins=int((x>0).sum()))
            for i,g in enumerate(groups):
                seeds=lock['train_seeds'] if rows[g]['role']=='train' else lock['validation_seeds']
                per_noise=[]
                for s in seeds:
                    a=lookup[g,s,candidate];b=lookup[g,s,reference]
                    new_clash+=a['geometry']['severe_pairs']>0 and b['geometry']['severe_pairs']==0
                    lost_stereo+=not a['geometry']['strict_checked_chirality'] and b['geometry']['strict_checked_chirality']
                    per_noise.append(dict(seed=s,delta_aa=a['all_atom_lddt']-b['all_atom_lddt'],delta_ca=a['ca_lddt']-b['ca_lddt']))
                paired.append(dict(cohort=cohort,group_id=g,length=len(rows[g]['sequence']),
                    candidate=candidate,reference=reference,delta_aa=float(delta[i,0]),delta_ca=float(delta[i,1]),per_noise=per_noise))
            contrasts.append(dict(candidate=candidate,reference=reference,quality=quality,
                introduced_severe_on_zero_instances=new_clash,lost_strict_chirality_instances=lost_stereo))
        strata={}
        strata_ids={f'length_{lo}_{hi}':[i for i,g in enumerate(groups) if lo<=len(rows[g]['sequence'])<=hi]
            for lo,hi in [(50,255),(256,511),(512,1024)]}
        for label,monomer in [('monomer',True),('multimer_single_chain',False)]:
            strata_ids[label]=[i for i,g in enumerate(groups) if
                ('source_assembly_composition' in rows[g] and
                (rows[g]['source_assembly_composition']['protein_chain_instance_count']==1)==monomer)]
        for label,indices in strata_ids.items():
            if not indices:continue
            strata[label]=dict(proteins=len(indices),models={m:dict(mean_aa=float(a[indices,0].mean()),
                mean_ca=float(a[indices,1].mean())) for m,a in arrays.items()},
                paired=[dict(candidate=c,reference=r,mean_delta_aa=float((arrays[c][indices,0]-arrays[r][indices,0]).mean()),
                    mean_delta_ca=float((arrays[c][indices,1]-arrays[r][indices,1]).mean())) for c,r in lock['contrasts']],
                scope='descriptive subset; not independent confirmation or model selection')
        result[cohort]=dict(proteins=n,models=models,contrasts=contrasts,strata=strata)
    return dict(summary=result,paired=paired,scope='development folding confirmation; protein bootstrap, no best-of-noise or deployment certification')
