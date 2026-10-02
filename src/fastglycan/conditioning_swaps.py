"""WT/target token-state swaps on fixed equal-length native target atom graphs."""
ARMS = ('exact', 'wt_trunk', 'chem_only', 'target_trunk_only', 'local_only', 'global_only')


def swap_conditioning(wt, target, position, arm):
    """Chem-only means WT neural context plus target chemical route, not no context.

    Chemistry is owned by the caller and remains target for EVERY arm. Never
    mutate archived tensors; all local strips include z[i,i] exactly once.
    """
    if arm not in ARMS:
        raise ValueError('unknown intervention')
    if len(wt) != 3 or len(target) != 3 or any(a.shape != b.shape for a,b in zip(wt,target)):
        raise ValueError('equal-length matched conditioning required')
    if not 0 <= position < target[1].shape[0]:
        raise ValueError('position out of range')
    if arm == 'exact':return target
    if arm == 'wt_trunk':return target[0], wt[1], wt[2]
    if arm == 'chem_only':return wt
    if arm == 'target_trunk_only':return wt[0], target[1], target[2]
    base, local = (wt,target) if arm == 'local_only' else (target,wt)
    s,z=base[1].clone(),base[2].clone()
    s[position]=local[1][position]
    z[position]=local[2][position]
    z[:,position]=local[2][:,position]
    return target[0],s,z


class DecoderFeatureTrace(dict):
    """Record direct feature reads without changing tensor values or layouts."""
    def __init__(self, values):
        super().__init__(values)
        self.reads=set()

    def __getitem__(self,key):
        self.reads.add(key)
        return super().__getitem__(key)

    def get(self,key,default=None):
        self.reads.add(key)
        return super().get(key,default)
