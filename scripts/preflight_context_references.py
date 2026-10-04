"""Read existing reference mappings only; no torch, C4, ESM or downloads."""
import argparse,hashlib,json
from pathlib import Path
import numpy as np


def preflight_context_references(requests,out,physical_root):
    rows=json.loads(requests.read_text());results=[];failures=[]
    for row in rows:
        try:
            original=Path(row['mapping_path'])
            path=physical_root/original.relative_to('/data/user/shuang886/Folding')
            with np.load(path) as f:
                names=f['atom_names'];ca=names=='CA';x=f['coordinates'][ca];mask=f['mask'][ca].astype(bool)
            assert x.shape==(len(row['sequence']),3)
            assert np.isfinite(x[mask]).all()
            positions={a:[i for i,b in enumerate(row['sequence']) if a==b and mask[i]] for a in 'ADLT'}
            record=dict(row,eligible_positions=positions,observed_ca=int(mask.sum()),
                        mapping_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            if all(positions.values()):results.append(record)
            else:failures.append(dict(row,reason='no_observed_CA_for_source_type',positions=positions))
        except Exception as e:
            failures.append(dict(row,reason=repr(e)))
    out.write_text(json.dumps(dict(complete=True,requests_sha256=hashlib.sha256(requests.read_bytes()).hexdigest(),
                                   checked=len(rows),eligible=results,failures=failures,new_c4=0,new_s1=0),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--requests',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--physical-root',required=True,type=Path)
    a=p.parse_args();preflight_context_references(a.requests,a.out,a.physical_root)
