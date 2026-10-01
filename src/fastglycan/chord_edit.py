"""EDM-sigma-domain backbone editing probes, not a ChordEdit equivalence claim.

Source and target retain different native atom graphs. Only explicitly matched
N/CA/C/O coordinates are subtracted; atom coordinates are never index-truncated.
"""
import numpy as np
import torch

BACKBONE_NAMES = ('N', 'CA', 'C', 'O')


def backbone_indices(atoms, length):
    lookup = {(int(r), str(n)): i for i, (r, n) in enumerate(zip(atoms.res_id, atoms.atom_name))}
    if len(lookup) != len(atoms):
        raise ValueError('requires one chain with unique residue/atom identities')
    try:
        return np.array([[lookup[i, a] for a in BACKBONE_NAMES] for i in range(1, length+1)])
    except KeyError as error:
        raise ValueError('missing backbone atom') from error


def backbone_frames(backbone):
    ca = backbone[:, 1]
    first = backbone[:, 2] - ca
    first_norm = first.norm(dim=-1, keepdim=True)
    if (first_norm < 1e-5).any(): raise ValueError('degenerate CA-C')
    first = first/first_norm
    second = backbone[:, 0] - ca
    second = second - (second*first).sum(-1,keepdim=True)*first
    norm = second.norm(dim=-1,keepdim=True)
    if (norm < 1e-5).any(): raise ValueError('degenerate N-CA-C')
    second = second/norm
    return torch.stack((first,second,torch.linalg.cross(first,second,dim=-1)),dim=-1)


def lift_backbone(coordinates, residue_ids, indices, original_backbone, new_backbone):
    """Transport target sidechains by proper residue frames, then set actual backbone.

    This is initialization only. It does not guarantee peptide or steric geometry.
    """
    ids = torch.as_tensor(residue_ids,device=coordinates.device,dtype=torch.long)-1
    f0,f1 = backbone_frames(original_backbone),backbone_frames(new_backbone)
    local = torch.einsum('ni,nij->nj',coordinates-original_backbone[ids,1],f0[ids])
    moved = torch.einsum('ni,nji->nj',local,f1[ids])+new_backbone[ids,1]
    moved[torch.as_tensor(indices,device=moved.device)] = new_backbone
    return moved


def initialize_target_atoms(source_atoms, source_coordinates, target_atoms, target_reference,
                            source_sequence, target_sequence):
    """Copy unchanged residue identities; initialize changed sidechains from native reference."""
    if len(source_sequence)!=len(target_sequence):raise ValueError('substitutions only')
    length=len(source_sequence);sb=backbone_indices(source_atoms,length);tb=backbone_indices(target_atoms,length)
    source_b=source_coordinates[torch.as_tensor(sb,device=source_coordinates.device)]
    reference_b=target_reference[torch.as_tensor(tb,device=target_reference.device)]
    result=lift_backbone(target_reference,target_atoms.res_id,tb,reference_b,source_b)
    lookup={(int(r),str(n)):i for i,(r,n) in enumerate(zip(source_atoms.res_id,source_atoms.atom_name))}
    for i,(res,name) in enumerate(zip(target_atoms.res_id,target_atoms.atom_name)):
        j=int(res)-1;key=(int(res),str(name))
        if source_sequence[j]==target_sequence[j] and key in lookup:
            result[i]=source_coordinates[lookup[key]]
    result[torch.as_tensor(tb,device=result.device)]=source_b
    return result


def chord_backbone_update(source, source_high, target_high, source_low, target_low,
                          *, sigma_high=16., sigma_low=12.):
    """Delta v=(D_src-D_tgt)/sigma; negative sigma step gives targetward motion.

    Directly adapting the two-time positive weights to sigma is a testable proxy,
    not a transfer of the image theorem. Both calls share backbone anchor/noise.
    """
    if not 0 < sigma_low < sigma_high:raise ValueError('invalid positive sigma window')
    if any(x.shape!=source.shape for x in [source_high,target_high,source_low,target_low]):
        raise ValueError('only matched backbone spaces can be compared')
    high=(source_high-target_high)/sigma_high
    low=(source_low-target_low)/sigma_low
    delta=sigma_high-sigma_low
    field=(sigma_high*low+delta*high)/(sigma_high+delta)
    return source-sigma_high*high,source-sigma_high*field,high,field


class ChordDenoiser:
    """Native conditioning caches, explicit sigma queries and true call accounting."""
    def __init__(self, model, features, conditioning):
        self.model=model;self.features=features;self.s_inputs,self.s,self.z=conditioning
        d=model.diffusion_module
        self.pair_z=d.diffusion_conditioning.prepare_cache(features['relp'],self.z,False)
        names=('ref_pos','ref_charge','ref_mask','ref_element','ref_atom_name_chars','atom_to_token_idx','d_lm','v_lm','pad_info')
        self.p_lm,self.c_l=d.atom_attention_encoder.prepare_cache(**{k:features[k] for k in names},r_l=True,z=self.pair_z,inplace_safe=False)
        self.calls=0

    def denoise(self, coordinates, sigma, *, center_restore=True):
        center=coordinates.mean(-2,keepdim=True) if center_restore else torch.zeros_like(coordinates[:1])
        d=self.model.diffusion_module;self.calls+=1
        x=(coordinates-center)[None]
        result=d(x_noisy=x,t_hat_noise_level=torch.as_tensor(sigma,device=x.device,dtype=x.dtype).expand(1),
            input_feature_dict=self.features,s_inputs=self.s_inputs,s_trunk=self.s,z_trunk=None,
            pair_z=self.pair_z,p_lm=self.p_lm,c_l=self.c_l,chunk_size=None,inplace_safe=False,
            enable_efficient_fusion=self.model.configs.enable_efficient_fusion)[0]
        return result+center

    def cold_sample(self, initial, steps):
        schedule=self.model.inference_noise_scheduler(N_step=steps,device=initial.device,dtype=initial.dtype)
        x=initial
        for sigma,next_sigma in zip(schedule[:-1],schedule[1:]):
            x=x-x.mean(-2,keepdim=True)
            denoised=self.denoise(x,sigma,center_restore=False)
            x=denoised+(next_sigma/sigma)*(x-denoised)
        return x
