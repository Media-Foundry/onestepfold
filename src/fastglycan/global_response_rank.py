"""Oracle centered global s/z response bases; no learned prediction or training."""
import torch

GLOBAL_RANKS = (0,1,2,3,5,8,10,12,15,18)
GLOBAL_VARIANTS = ('raw','balanced','s_only','z_only','separate_both')


class GlobalResponseBasis:
    """Nineteen non-WT rows, FP64 Gram arithmetic; return native FP32 states.

    Balanced scale is total WT-anchored response energy BEFORE centering.
    Independent s/z rank K uses two distinct coefficient spaces (up to 2K).
    """
    def __init__(self, wt_s, wt_z, mutant_s, mutant_z):
        if mutant_s.shape[0]!=19 or mutant_z.shape[0]!=19:
            raise ValueError('exactly nineteen non-WT endpoints required')
        self.original={'s':mutant_s,'z':mutant_z};self.centered={};self.base={};self.grams={};self.energies={};self.shapes={};self.vectors={};self.spectra={}
        for key,wt,values in [('s',wt_s,mutant_s),('z',wt_z,mutant_z)]:
            if values.shape[1:]!=wt.shape or not torch.isfinite(values).all():raise ValueError('invalid endpoint shape/value')
            delta=values.reshape(19,-1).double()-wt.reshape(1,-1).double()
            energy=delta.square().sum();mean=delta.mean(0);delta-=mean
            self.centered[key]=delta;self.base[key]=wt.reshape(-1).double()+mean;self.energies[key]=float(energy)
            self.grams[key]=delta@delta.T;self.shapes[key]=wt.shape
        for metric,g in [('raw',self.grams['s']+self.grams['z']),
                         ('balanced',sum(self.grams[k]/self.energies[k] if self.energies[k]>0 else torch.zeros_like(self.grams[k]) for k in ['s','z'])),
                         ('s',self.grams['s']),('z',self.grams['z'])]:
            val,vec=torch.linalg.eigh((g+g.T)*.5);val=val.flip(0).clamp_min(0);vec=vec.flip(1)
            self.vectors[metric]=vec;total=float(val.sum())
            self.spectra[metric]=dict(eigenvalues=val.cpu().tolist(),cumulative_energy=(val.cumsum(0)/val.sum()).cpu().tolist() if total>0 else None,centered_energy=total)

    def reconstruct(self, row, variant, rank):
        if variant not in GLOBAL_VARIANTS or rank not in GLOBAL_RANKS or not 0<=row<19:raise ValueError('invalid global projection request')
        result=[]
        for key in ['s','z']:
            if (variant=='s_only' and key=='z') or (variant=='z_only' and key=='s'):
                result.append(self.original[key][row]);continue
            metric=variant if variant in ['raw','balanced'] else key
            v=self.vectors[metric][:,:rank]
            coefficient=v@v[row] if rank else torch.zeros(19,dtype=torch.float64,device=v.device)
            predicted=(self.base[key]+coefficient@self.centered[key]).reshape(self.shapes[key])
            result.append(predicted.to(self.original[key].dtype))
        return tuple(result)

    def evidence(self):
        return dict(energies_before_centering=self.energies,spectra=self.spectra,shapes={k:list(v) for k,v in self.shapes.items()},
            centered_gram={k:v.cpu().tolist() for k,v in self.grams.items()},
            coefficients={metric:{str(k):(v[:,:k]@v[:,:k].T).cpu().tolist() for k in GLOBAL_RANKS} for metric,v in self.vectors.items()})
