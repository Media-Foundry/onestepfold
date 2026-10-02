"""Hash-checked teacher access with an explicit training-only guard."""
from pathlib import Path
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256
from fastglycan import stage0_confirm_runtime as rt


class FactorTeacherStore:
    def __init__(self,root,training_only=False):
        self.root=Path(root);self.lock=rt.load_json(self.root/'teacher_lock.json');self.training_only=training_only
        assert rt.load_json(self.root/'teacher_report.json')['complete']
        self.owner={pi:i for i,ps in enumerate(self.lock['assignments']) for pi in ps};self.rows={r['index']:r for r in self.lock['rows']}
        self.manifest={x['path']:x['sha256'] for x in rt.load_json(self.root/'teacher_manifest.json')};self.cache={};self.checked=set()

    def path(self,pi,label,suffix):
        p=self.root/f'teacher_{self.owner[pi]}'/f'{label}_{suffix}';rel=str(p.relative_to(self.root))
        if rel not in self.checked:assert sha256(p)==self.manifest[rel];self.checked.add(rel)
        return p

    def load(self,pi,pos=None,aa=None):
        row=self.rows[pi]
        if self.training_only and row['role']!='train':raise ValueError('validation teacher cannot enter training store')
        label=f'p{pi}_wt' if pos is None or aa==row['sequence'][pos] else f'p{pi}_s{pos+1}_{aa}'
        if label not in self.cache:
            c=torch.load(self.path(pi,label,'conditioning.pt'),map_location='cpu',weights_only=False)
            seq=row['sequence'] if pos is None else row['sequence'][:pos]+aa+row['sequence'][pos+1:];assert c['sequence']==seq
            inv=dict(np.load(self.path(pi,label,'inventory.npz')));co=np.load(self.path(pi,label,'coordinates.npz'))['coordinates']
            self.cache[label]=dict(label=label,sequence=seq,conditioning=tuple(c['conditioning']),inventory=inv,coordinates=co)
        return self.cache[label]
