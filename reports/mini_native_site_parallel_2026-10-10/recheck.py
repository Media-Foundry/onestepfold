"""Independent metadata/storage-byte and timing checks without importing Torch."""
import argparse
from collections import Counter, OrderedDict
import hashlib
import io
import json
from pathlib import Path
import pickle
import statistics
import zipfile


def tensor_metadata(storage, offset, shape, stride, requires_grad, hooks, metadata=None):
    return ('tensor', storage, offset, shape, stride, requires_grad, hooks, metadata)


class MetadataOnlyUnpickler(pickle.Unpickler):
    """Decode known tensor descriptors, never import Torch or execute checkpoint code."""
    def find_class(self, module, name):
        if (module, name)==('collections','OrderedDict'):
            return OrderedDict
        if module=='torch' and name in ('FloatStorage','DoubleStorage'):
            return name
        if (module, name)==('torch._utils','_rebuild_tensor_v2'):
            return tensor_metadata
        raise pickle.UnpicklingError(f'unexpected metadata constructor: {module}.{name}')

    def persistent_load(self, identity):
        assert identity[0]=='storage' and identity[3]=='cpu'
        return tuple(identity)


def recheck(root, manifest):
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    for name, expected in manifest['files'].items():
        assert digest(root/name) == expected, name
    lock = json.loads((root/'audit_lock.json').read_text())
    controller = json.loads((root/'controller.json').read_text())
    verification = json.loads((root/'verification.json').read_text())
    assert controller['complete'] and verification['complete']
    assert controller['audit_lock_sha256'] == digest(root/'audit_lock.json')
    assert controller['verification_sha256'] == digest(root/'verification.json')
    reports = [json.loads((root/f'rank_{rank}/report.json').read_text()) for rank in range(6)]
    totals = Counter()
    for rank, report in enumerate(reports):
        assert report['rank']==rank and report['complete']
        assert report['audit_lock_sha256']==controller['audit_lock_sha256']
        assert report['pci_bus']==lock['pci_buses'][rank]
        assert report['native_loader']['world_size']==1
        assert report['native_loader']['root_dir']==lock['protenix_root_dir']
        assert len(report['steps'])==12
        assert report['native_counts']==dict(c4=0,input_embedder=0,recycle=0,s1=0,updates=0)
        totals.update(report['counts'])
    assert dict(totals)==verification['counts']==dict(
        forwards=7182,backwards=7182,reference_forwards=378,reference_backwards=378)
    assert reports[0]['historical_gradient_relative_error'] <= 5e-5
    rows = reports[0]['steps']
    pairs, orders = [], []
    for order in range(2):
        for step in range(1,4):
            signatures=[]
            for method in ('serial','parallel'):
                row=next(x for x in rows if (x['order'],x['step'],x['method'])==(order,step,method))
                assert row['seconds']==max(row['rank_seconds'])
                for report in reports:
                    other=next(x for x in report['steps'] if (x['order'],x['step'],x['method'])==(order,step,method))
                    assert other['rank_seconds']==row['rank_seconds'] and other['seconds']==row['seconds']
                path=root/row['snapshot']; assert digest(path)==row['sha256']
                with zipfile.ZipFile(path) as archive:
                    # Tensor bytes are exact. Compare decoded metadata separately:
                    # pickle memoization can encode equal string objects differently.
                    # Shapes, dtypes, offsets, objective and AdamW metadata all remain.
                    members={name.split('/',1)[1]:archive.read(name) for name in archive.namelist()}
                    members.pop('.data/serialization_id',None)
                    assert 'data.pkl' in members and any(x.startswith('data/') for x in members)
                    metadata=MetadataOnlyUnpickler(io.BytesIO(members.pop('data.pkl'))).load()
                    signatures.append(dict(metadata=metadata, members={
                        name:hashlib.sha256(value).hexdigest() for name,value in members.items()}))
            assert signatures[0]==signatures[1], (order,step)
            pairs.append(dict(order=order,step=step,metadata_and_storage_bytes_equal=True,
                              archive_members=len(signatures[0]['members'])+1))
        times={method:sum(x['seconds'] for x in rows if x['order']==order and x['method']==method)
               for method in ('serial','parallel')}
        actual=dict(order=lock['orders'][order],**times,speedup=times['serial']/times['parallel'])
        assert actual==verification['orders'][order]
        orders.append(actual)
    total={method:sum(x[method] for x in orders) for method in ('serial','parallel')}
    speedup=total['serial']/total['parallel']
    assert speedup==verification['aggregate_speedup']
    summary={method:dict(mean_seconds=total[method]/6,
                        median_seconds=statistics.median(x['seconds'] for x in rows if x['method']==method),
                        min_seconds=min(x['seconds'] for x in rows if x['method']==method),
                        max_seconds=max(x['seconds'] for x in rows if x['method']==method))
             for method in ('serial','parallel')}
    result=dict(complete=True,verified_files=len(manifest['files']),archive_pairs=pairs,
                audit_lock_sha256=digest(root/'audit_lock.json'),counts=dict(totals),
                orders=orders,aggregate_speedup=speedup,step_times=summary,
                ideal_six_device_efficiency=speedup/6,
                reserved_device_seconds_ratio=6/speedup,
                loading_seconds=[x['loading_seconds'] for x in reports],
                warmup_seconds=[x['warmup_seconds'] for x in reports],
                peak_allocated_gib=[max(s['peak_allocated_bytes'] for s in x['steps'])/2**30 for x in reports],
                controller_wall_seconds=controller['observed_unix']-controller['started_unix'],
                numerical_reexecution=False,model_quality_measured=False,inference_speedup_measured=False)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=recheck(args.root,json.loads(args.manifest.read_text()))
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
