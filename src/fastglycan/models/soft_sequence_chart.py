"""Piecewise native-inventory relaxation of Protenix sequence inputs.

Each chart uses the *current argmax sequence's* native atom inventory. All 20
probabilities affect ESM, residue features and expected reference features on
that inventory. Absent atom names contribute zero reference features. One-hot
endpoints exactly recover the current native features. Crossing argmax boundaries
rebuilds chemistry and can be discontinuous; callers MUST measure those jumps.
This does not claim a globally smooth variable-atom-count representation.
"""
from __future__ import annotations
import copy
import hashlib
import numpy as np
import torch
from .soft_esm import AMINO_ACIDS, hard_sequence, soft_esm2
from .differentiable_mini import prepare_atom_pairs

REFERENCE_FEATURES=('ref_pos','ref_charge','ref_mask','ref_element','ref_atom_name_chars')


def native_sequence_features(sequence, *, seed=101):
    from protenix.data.inference.json_to_feature import SampleDictToFeatures
    from protenix.data.utils import make_dummy_feature, data_type_transform
    from protenix.utils.seed import seed_everything
    # Preserve caller RNG, including CUDA, rather than changing diffusion noise.
    import random
    numpy_state=np.random.get_state();python_state=random.getstate()
    try:
        with torch.random.fork_rng():
            seed_everything(seed,deterministic=True)
            builder=SampleDictToFeatures(dict(name='sequence_gate',sequences=[
                dict(proteinChain=dict(sequence=sequence,count=1))]))
            features,atoms,tokens=builder.get_feature_dict()
            features=make_dummy_feature(features_dict=features,dummy_feats=['msa','template'])
            features=data_type_transform(feat_or_label_dict=features)
    finally:
        np.random.set_state(numpy_state);random.setstate(python_state)
    return features,atoms


def device_tree(value,device):
    if isinstance(value,torch.Tensor):return value.to(device)
    if isinstance(value,dict):return {k:device_tree(v,device) for k,v in value.items()}
    if isinstance(value,list):return [device_tree(v,device) for v in value]
    if isinstance(value,tuple):return tuple(device_tree(v,device) for v in value)
    return copy.deepcopy(value)


class SequenceChart:
    def __init__(self,sequence,model,esm,alphabet,templates,*,seed=101):
        self.sequence=sequence;self.model=model;self.esm=esm;self.alphabet=alphabet
        self.device=next(model.parameters()).device
        native,self.atoms=native_sequence_features(sequence,seed=seed)
        self.native=device_tree(native,self.device)
        self.native=model.relative_position_encoding.generate_relp(self.native)
        self.token_idx=self.native['atom_to_token_idx'].long()
        self.ca_indices=torch.tensor(np.flatnonzero(self.atoms.atom_name=='CA'),device=self.device)
        assert len(self.ca_indices)==len(sequence)
        self.bank={}
        # Build one candidate feature value for each current atom slot and amino acid.
        for name in REFERENCE_FEATURES:
            value=self.native[name]
            self.bank[name]=torch.zeros((value.shape[0],20,*value.shape[1:]),device=self.device,dtype=torch.float32)
        self.restype_bank=torch.stack([templates[a][0]['restype'][0].float() for a in AMINO_ACIDS]).to(self.device)
        for ai,aa in enumerate(AMINO_ACIDS):
            tf,ta=templates[aa]
            lookup={(int(res),str(atom)):i for i,(res,atom) in enumerate(zip(ta.res_id,ta.atom_name))}
            pairs=[(i,lookup[(int(res),str(atom))])
                   for i,(res,atom) in enumerate(zip(self.atoms.res_id,self.atoms.atom_name))
                   if (int(res),str(atom)) in lookup]
            if pairs:
                destination,source=zip(*pairs)
                di=torch.tensor(destination,device=self.device)
                si=torch.tensor(source)
                for name in REFERENCE_FEATURES:
                    self.bank[name][di,ai]=tf[name][si].to(self.device,dtype=torch.float32)
        # Exact hard endpoint in this chart, including the seeded native conformer.
        ai=torch.tensor([AMINO_ACIDS.index(sequence[t]) for t in self.token_idx.tolist()],device=self.device)
        rows=torch.arange(len(self.token_idx),device=self.device)
        for name in REFERENCE_FEATURES:self.bank[name][rows,ai]=self.native[name].float()

    def features(self,probabilities,*,check_chart=True):
        if check_chart and hard_sequence(probabilities)!=self.sequence:
            raise ValueError('argmax changed: rebuild the native chemical chart before forward')
        f=dict(self.native)
        f['restype']=probabilities @ self.restype_bank
        f['profile']=f['restype']
        for name,bank in self.bank.items():
            p=probabilities[self.token_idx]
            f[name]=(bank*p.reshape(*p.shape,*([1]*(bank.ndim-2)))).sum(1)
        f['esm_token_embedding']=soft_esm2(self.esm,self.alphabet,probabilities)
        return prepare_atom_pairs(f)

    def initial_noise(self,seed):
        # Atom-name-keyed noise remains common for shared atoms after graph rebuilding.
        noise=[]
        for res,name in zip(self.atoms.res_id,self.atoms.atom_name):
            key=f'{seed}:{int(res)}:{str(name)}'.encode()
            rng=np.random.default_rng(int.from_bytes(hashlib.sha256(key).digest()[:8],'little'))
            noise.append(rng.standard_normal(3))
        return torch.tensor(np.asarray(noise),device=self.device,dtype=torch.float32)[None]*2560


def first_argmax_boundary(q0,q1):
    a=q0.double();b=q1.double();winner=a.argmax(-1)
    margin=a.gather(1,winner[:,None])-a
    final_margin=b.gather(1,winner[:,None])-b
    crossings=(margin>0)&(final_margin<0)
    times=torch.where(crossings,margin/(margin-final_margin).clamp_min(1e-20),torch.inf)
    t=float(times.min())
    if not 0<t<1:raise ValueError('no interior argmax crossing on this displacement')
    return t

