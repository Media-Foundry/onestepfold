"""All fixed states and directions; no selection of a learning rate or model."""
import hashlib
import json
from pathlib import Path
import numpy as np


def analyze_stage_updates(root):
    manifest=json.loads((root/'manifest.json').read_text());assert manifest['complete']
    for rel,expected in manifest['files'].items():
        path=root/rel;assert hashlib.sha256(path.read_bytes()).hexdigest()==expected['sha256']
    assert json.loads((root/'verification.json').read_text())['complete']
    analysis=dict(complete=True,train_only=True,promoted=False,accepted_training_updates=0,states=[])
    for arm in ('final','hint'):
        for seed in (272001,272003):
            folder=root/'runs'/arm/str(seed)
            for step in (0,4104,8208):
                node=json.loads((folder/f'node_{step}.json').read_text())
                pairs=np.asarray(node['gradient_cosines']);mask=~np.eye(27,dtype=bool)
                row=dict(arm=arm,seed=seed,step=step,objective=node['baseline']['objective'],
                    full_gradient_norm=node['site_gradients'][0]['gradient_norm'],
                    negative_site_gradient_pairs=int(np.count_nonzero(pairs[mask]<0)),
                    total_directed_site_pairs=int(mask.sum()),
                    sites_opposed_to_full_gradient=sum(x['dot']<0 for x in node['site_gradients']),
                    scheduled_batch_clip_count=sum(x['clipped'] for x in node['scheduled_batches']),
                    scheduled_batch_full_ascent_count=sum(x['clipped_update']['dot']>0 for x in node['scheduled_batches']),
                    scheduled_batch_own_descent_count=sum(x['batch_own_clipped_update']['dot']<0 for x in node['scheduled_batches']),
                    mean_raw_gradient_cosine=node['mean_raw_gradient']['cosine'],
                    mean_clipped_gradient_cosine=node['mean_clipped_gradient']['cosine'],directions={})
                for name,record in node['probes'].items():
                    direction=dict(**record['direction'],fractions=[])
                    for frac in record['fractions']:
                        value=frac['evaluation'];base=node['baseline']
                        direction['fractions'].append(dict(fraction=frac['fraction'],loss_change=frac['loss_change'],
                            relative_loss_change=frac['loss_change']/base['objective'],
                            first_order_change=frac['actual_direction']['dot'],
                            final_common_change=value['final']['common']-base['final']['common'],
                            final_centered_change=value['final']['centered']-base['final']['centered'],
                            hint_common_change=value['hint']['common']-base['hint']['common'],
                            hint_centered_change=value['hint']['centered']-base['hint']['centered'],
                            sites_improved=sum(x['objective']<y['objective'] for x,y in zip(value['sites'],base['sites']))))
                    row['directions'][name]=direction
                analysis['states'].append(row)
    assert len(analysis['states'])==12
    (root/'analysis.json').write_text(json.dumps(analysis,indent=2,allow_nan=False)+'\n')
    for row in analysis['states']:
        changes={name:round(value['fractions'][-1]['loss_change'],7) for name,value in row['directions'].items()}
        print(row['arm'],row['seed'],row['step'],'cos',round(row['mean_raw_gradient_cosine'],4),
              round(row['mean_clipped_gradient_cosine'],4),'finite',changes)


if __name__=='__main__':
    analyze_stage_updates(Path(__file__).resolve().parent)
