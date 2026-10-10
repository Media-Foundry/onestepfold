"""CPU-only collection and NumPy verification of a completed reference audit."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

import numpy as np
import torch


def export_reference_anchor_audit(root):
    read=lambda p:json.loads(p.read_text())
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    lock,controller,report=[read(root/n) for n in ('audit_lock.json','controller.json','report.json')]
    assert controller['complete'] and controller['phase']=='closed' and controller['exit_code']==0
    assert controller['report_sha256']==sha(root/'report.json')
    assert report['complete'] and report['parameter_updates']==0 and not report['new_training_started']
    assert controller['lock_sha256']==report['audit_lock_sha256']==sha(root/'audit_lock.json')
    assert sha(root/'protocol.md')==lock['protocol_sha256']
    for name,digest in lock['code'].items():assert sha(root/'code'/name)==digest,name
    for rec in report['reference_records']:assert sha(root/rec['path'])==rec['sha256']
    assert report['native_counts']==dict(c4=0,input_embedder=0,recycle=24,s1=0,updates=0)
    assert len(report['reference_records'])==24 and len(report['seeds'])==2
    dest=root/'export';dest.mkdir(exist_ok=False)
    checks=[]
    for seed in report['seeds']:
        path=root/seed['vector_path'];assert sha(path)==seed['vector_sha256']
        tensors=torch.load(path,map_location='cpu',weights_only=True)
        vectors={k:v.numpy() for k,v in tensors.items()}
        for key,a,b in [('aa','raw','common'),('anchored','raw','reference'),('anchored_common','common','reference')]:
            np.testing.assert_allclose(vectors[key],vectors[a]-vectors[b],rtol=1e-9,atol=1e-12)
        norms={k:float(np.linalg.norm(v)) for k,v in vectors.items()}
        for k,value in norms.items():np.testing.assert_allclose(value,seed['full']['norms'][k],rtol=1e-12)
        for key,a,b in [('raw_aa_cosine','raw','aa'),('anchored_aa_cosine','anchored','aa'),
                        ('raw_common_cosine','raw','common'),('anchored_common_cosine','anchored','anchored_common'),
                        ('common_aa_cosine','common','aa'),('anchored_common_aa_cosine','anchored_common','aa')]:
            value=float(vectors[a].dot(vectors[b])/(norms[a]*norms[b]))
            np.testing.assert_allclose(value,seed['full'][key],rtol=1e-11,atol=1e-12)
        assert seed['gradient_reference_relative_error']<=5e-6
        assert seed['pullback']['relative']<=5e-5
        assert len(seed['sites'])==27
        for site in seed['sites']:
            np.testing.assert_allclose(site['raw'],site['common']+site['centered'],rtol=1e-12,atol=1e-12)
        np.savez_compressed(dest/f"vectors_{seed['seed']}.npz",**vectors)
        rows=seed['sites']
        checks.append(dict(seed=seed['seed'],sites_improved_alignment=sum(
            r['anchored_aa_cosine']>r['raw_aa_cosine'] for r in rows),
            sites_lower_common_gradient=sum(r['norms']['anchored_common']<r['norms']['common'] for r in rows),
            sites_raw_nonpositive_aa=sum(r['raw_aa_cosine']<=0 for r in rows),
            sites_anchored_nonpositive_aa=sum(r['anchored_aa_cosine']<=0 for r in rows)))
    t=report['trained_state_check'];assert t['centered_max_abs']<=t['fp32_rounding_bound']
    assert t['no_edit_exact'] and t['order_independent']
    for name in ['audit_lock.json','protocol.md','controller.json','controller.log','launch.json','tests.log','imports.log','audit.log','report.json']:
        shutil.copy2(root/name,dest/name)
    for name in lock['overlay']:
        p=dest/'scientific_code'/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/'code'/name,p)
    verification=dict(complete=True,independent_numpy_vector_checks=True,
        native_backward_repeated=False,all_original_source_hashes_verified=True,
        source_files=len(lock['code']),seed_checks=checks,parameter_updates=0,promoted=False,
        exporter_sha256=sha(Path(__file__)),audit_lock_sha256=sha(root/'audit_lock.json'))
    (dest/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
    shutil.copy2(Path(__file__),dest/'export_reference_anchor_audit.py')
    manifest=dict(complete=True,bulk_reference_tensors_exported=False,
        files={str(p.relative_to(dest)):sha(p) for p in dest.rglob('*') if p.is_file()})
    (dest/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    archive=root/'reference_anchor_audit_export.tar.gz'
    with tarfile.open(archive,'x:gz') as tar:tar.add(dest,arcname='.')
    result=dict(complete=True,archive_sha256=sha(archive),checks=checks)
    (root/'export_receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    export_reference_anchor_audit(parser.parse_args().root)
