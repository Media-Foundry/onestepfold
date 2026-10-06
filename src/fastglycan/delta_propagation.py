"""Read-only, candidate-aligned diagnostics for native folding tensors.

Rank statistics are offline diagnostics, not a compressed execution algorithm.
"""
import hashlib
import time
import numpy as np


def tensor_digest(array):
    x = np.ascontiguousarray(array)
    return hashlib.sha256(str((x.shape, x.dtype.str)).encode() + x.tobytes()).hexdigest()


def delta_statistics(reference, candidate, position, *, spectral=True, tile=16):
    """All-element equality/support; FP64 spectra on eight fixed channels."""
    x, y = np.asarray(reference), np.asarray(candidate)
    if x.shape != y.shape or x.dtype != y.dtype:
        return dict(comparable=False, reference_shape=list(x.shape), candidate_shape=list(y.shape))
    if x.dtype != np.float32 or not (np.isfinite(x).all() and np.isfinite(y).all()):
        raise ValueError('finite FP32 aligned tensors required')
    eq = x.view(np.uint32) == y.view(np.uint32)
    d = y.astype(np.float64) - x.astype(np.float64)
    result = dict(comparable=True, shape=list(x.shape), bitwise_equal_fraction=float(eq.mean()),
                  nonzero_fraction=float(np.mean(d != 0)), delta_rms=float(np.sqrt(np.mean(d*d))),
                  delta_max=float(np.max(np.abs(d))), reference_sha256=tensor_digest(x),
                  candidate_sha256=tensor_digest(y))
    if x.ndim == 2:
        result['unchanged_tokens'] = int(np.all(eq, axis=-1).sum())
    if x.ndim != 3 or x.shape[0] != x.shape[1]:
        return result
    n = x.shape[0]
    same = eq.all(axis=-1)
    result.update(unchanged_pairs=int(same.sum()), unchanged_rows=int(same.all(1).sum()),
                  unchanged_columns=int(same.all(0).sum()))
    outside = np.ones((n,n), bool)
    outside[position,:] = False
    outside[:,position] = False
    result['changed_pairs_outside_mutation_row_column'] = int((~same & outside).sum())
    tiles = [same[j:j+tile,k:k+tile].all() for j in range(0,n,tile) for k in range(0,n,tile)]
    result['unchanged_tile_fraction'] = float(np.mean(tiles))
    if spectral:
        start = time.perf_counter()
        channels = list(range(0,x.shape[-1],max(1,x.shape[-1]//8)))[:8]
        rows = []
        for c in channels:
            singular = np.linalg.svd(d[:,:,c], compute_uv=False)
            energy = singular**2
            total = float(energy.sum())
            cumulative = np.cumsum(energy)/total if total else np.ones(n)
            row = dict(channel=c, energy=total, zero_delta=total==0,
                       singular_values=singular.tolist())
            for q in (90,95,99):
                row[f'r{q}'] = int(np.searchsorted(cumulative,q/100)+1) if total else 0
            for r in (2,8,16,32):
                row[f'energy_r{r}'] = float(cumulative[min(r,n)-1]) if total else None
            rows.append(row)
        result['spectra'] = rows
        result['spectral_seconds'] = time.perf_counter()-start
    return result


class DeltaObserver:
    """Capture native outputs and actual gated TriMul operands without replacing math."""
    def __init__(self, model):
        self.model = model
        self.handles = []
        self.originals = []
        self.values = {}
        self.cycle = 0

    def save(self, name, value):
        if name in self.values:
            raise RuntimeError('duplicate observation: '+name)
        self.values[name] = value.detach().float().cpu().numpy().copy()

    def __enter__(self):
        def output(module, name, select=lambda o:o, condition=lambda:True):
            def hook(m, a, o):
                if condition(): self.save(name() if callable(name) else name, select(o))
            self.handles.append(module.register_forward_hook(hook))
        output(self.model.input_embedder, 's_inputs')
        output(self.model.linear_no_bias_sinit, 's_init')
        output(self.model.linear_no_bias_zinit1, 'z_left')
        output(self.model.linear_no_bias_zinit2, 'z_right')
        output(self.model.relative_position_encoding, 'relpos_embedded')
        output(self.model.linear_no_bias_token_bond, 'bond_embedded')
        def msa_pre(m, args, kwargs):
            self.cycle += 1
            if self.cycle in (1,4):
                self.save(f'c{self.cycle}.msa_input', args[1] if len(args)>1 else kwargs['z'])
        self.handles.append(self.model.msa_module.register_forward_pre_hook(msa_pre,with_kwargs=True))
        output(self.model.msa_module, lambda:f'c{self.cycle}.msa_output', condition=lambda:self.cycle in (1,4))
        blocks = self.model.pairformer_stack.blocks
        for index in sorted(set((0,1,3,7,len(blocks)-1))):
            output(blocks[index],lambda i=index:f'c{self.cycle}.b{i+1}.z',lambda o:o[1],lambda:self.cycle in (1,4))
        first_msa = self.model.msa_module.blocks[0].pair_stack
        for prefix, block in [('msa_b1',first_msa),('main_b1',blocks[0])]:
            for sub in ('tri_mul_out','tri_mul_in'):
                mod = getattr(block,sub)
                tag = prefix+'.'+sub
                output(mod.layer_norm_in,tag+'.normalized',condition=lambda:self.cycle==1)
                output(mod,tag+'.output',condition=lambda:self.cycle==1)
                original = mod._combine_projections
                self.originals.append((mod, original))
                def combine(a,b,*args,_orig=original,_tag=tag,**kwargs):
                    if self.cycle==1:
                        self.save(_tag+'.A',a)
                        self.save(_tag+'.B',b)
                    return _orig(a,b,*args,**kwargs)
                mod._combine_projections = combine
            for sub in ('tri_att_start','tri_att_end','pair_transition'):
                output(getattr(block,sub),prefix+'.'+sub,condition=lambda:self.cycle==1)
        return self

    def __exit__(self, *args):
        for handle in self.handles: handle.remove()
        for module, original in self.originals:
            del module.__dict__['_combine_projections']
