import gzip
import json
import copy
from pathlib import Path
import pytest
from fastglycan.noise_diversity import diverse_exposure_order,make_noise_diversity_lock


def test_real_orders_preserve_samples_and_only_change_noise():
    with gzip.open(Path(__file__).parents[1]/'reports/mini_folding_rocm_matched_2026-10-01/weak_lock.json.gz','rt') as f:base=json.load(f)
    before=copy.deepcopy(base)
    kw=dict(cache='/cache',cache_files={},cache_digests={n:n for n in ['lock.json','artifact_manifest.json','audit.json']},hashes={},protocol_sha256='p',script_sha256='s')
    a=make_noise_diversity_lock(base,arm='fixed',**kw);b=make_noise_diversity_lock(base,arm='diverse',**kw)
    assert base==before and a['orders']==base['orders']
    assert len({r['seed'] for r in b['orders']['expanded']})==8192
    assert b['orders']['expanded'][0]['seed']==1800001 and b['orders']['expanded'][-1]['seed']==1808192
    assert all(a[k]==b[k] for k in a if k not in ['orders','noise_diversity'])
    assert [(r['group_id'],r['epoch']) for r in a['orders']['expanded']]==[(r['group_id'],r['epoch']) for r in b['orders']['expanded']]
    with pytest.raises(ValueError):diverse_exposure_order([])
