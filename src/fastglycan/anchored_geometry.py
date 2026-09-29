"""Joint residue-pose feasibility variables, not a differentiable solver layer."""
import torch
from torch import nn
from .articulated_output import _frame


def skew(v):
    x,y,z=v.unbind(-1);zero=torch.zeros_like(x)
    return torch.stack((zero,-z,y,z,zero,-x,-y,x,zero),-1).reshape(*v.shape[:-1],3,3)


class PoseVariables(nn.Module):
    """Raw global anchors plus independent proper local pose/bridge updates.

    Initialization is detached deliberately: this module defines optimization
    variables, not a gradient through the complete coordinate solver.
    """
    def __init__(self, adapter, raw):
        super().__init__()
        with torch.no_grad():
            initial=adapter(raw)
            if bool(initial['fallback_counts'].any()):raise ValueError('degenerate local frame or phase')
            projected=initial['coordinate']
        self.register_buffer('initial',projected.detach().clone())
        self.groups=nn.ModuleList();self.variables=nn.ParameterList()
        self.register_buffer('restore_order',adapter.restore_order.detach().clone())
        for group in adapter.groups:
            g=nn.Module();x=projected[group.indices]
            frame,_,_=_frame(x,group.n,group.ca,group.c)
            origin=x[:,group.ca:group.ca+1]
            g.register_buffer('base',(x-origin)@frame)
            g.register_buffer('origin',origin);g.register_buffer('frame',frame)
            g.register_buffer('moving',group.moving);g.register_buffer('indices',group.indices)
            g.rotations=group.rotations
            self.groups.append(g)
            self.variables.append(nn.Parameter(raw.new_zeros((len(x),6+len(group.rotations)))))

    def coordinates(self, values):
        pieces=[]
        for group,q in zip(self.groups,values,strict=True):
            x=group.base
            for j,rotation in enumerate(group.rotations):
                origin=x[:,rotation.parent:rotation.parent+1]
                axis=x[:,rotation.child:rotation.child+1]-origin
                axis=axis/torch.linalg.vector_norm(axis,dim=-1,keepdim=True)
                relative=x-origin;c=q[:,6+j].cos()[:,None,None];s=q[:,6+j].sin()[:,None,None]
                rotated=origin+relative*c+torch.linalg.cross(axis.expand_as(relative),relative)*s+(relative*axis).sum(-1,keepdim=True)*axis*(1-c)
                x=torch.where(group.moving[j,:,None],rotated,x)
            rotation=torch.matrix_exp(skew(q[:,3:6]))
            x=(x@rotation.transpose(-1,-2)+q[:,:3,None].transpose(-1,-2))@group.frame.transpose(-1,-2)+group.origin
            pieces.append(x.reshape(-1,3))
        return torch.cat(pieces)[self.restore_order]

    def forward(self):return self.coordinates(self.variables)


def safe_unit(x):return x/torch.linalg.vector_norm(x,dim=-1,keepdim=True).clamp_min(1e-10)


def phase(x,indices):
    a,b,c,d=x[indices].unbind(-2);axis=safe_unit(c-b)
    u=a-b;u=safe_unit(u-(u*axis).sum(-1,keepdim=True)*axis)
    v=d-c;v=safe_unit(v-(v*axis).sum(-1,keepdim=True)*axis)
    return torch.stack(((u*v).sum(-1),(torch.linalg.cross(u,v)*axis).sum(-1)),-1)


class JointObjective(nn.Module):
    def __init__(self, raw, anchors, sequence, pairs, radii):
        super().__init__()
        self.register_buffer('raw',raw.detach().clone())
        self.register_buffer('anchors',torch.as_tensor(anchors,device=raw.device,dtype=torch.long))
        self.register_buffer('pairs',pairs.to(raw.device));self.register_buffer('radii',radii.to(raw))
        a=self.anchors
        self.register_buffer('psi_omega_indices',torch.stack((a[:-1,1],a[:-1,2],a[1:,0],a[1:,1]),-1))
        self.register_buffer('carbonyl_indices',torch.stack((a[1:,0],a[:-1,1],a[:-1,2],a[:-1,3]),-1))
        co=phase(raw,self.psi_omega_indices)[:,0]
        self.register_buffer('omega_target',torch.stack((torch.where(co>=0,torch.ones_like(co),-torch.ones_like(co)),torch.zeros_like(co)),-1))
        self.register_buffer('cn_target',raw.new_tensor([1.341 if s=='P' else 1.329 for s in sequence[1:]]))

    def residuals(self,x):
        a=self.anchors;ca=x[a[:-1,1]];c=x[a[:-1,2]];n=x[a[1:,0]];nc=x[a[1:,1]]
        return dict(cn=torch.linalg.vector_norm(c-n,dim=-1)-self.cn_target,
            angle_c=(safe_unit(ca-c)*safe_unit(n-c)).sum(-1)+.4473,
            angle_n=(safe_unit(c-n)*safe_unit(nc-n)).sum(-1)+.5203,
            omega=torch.linalg.vector_norm(phase(x,self.psi_omega_indices)-self.omega_target,dim=-1),
            carbonyl=torch.linalg.vector_norm(phase(x,self.carbonyl_indices)-x.new_tensor([-1.,0.]),dim=-1))

    def forward(self,x,values,rho):
        zero=x.sum()*0
        displacement=(x-self.raw).square().sum(-1)
        heavy=displacement.mean();ca=displacement[self.anchors[:,1]].mean()
        rotations=torch.cat([q[:,3:6] for q in values])
        torsions=torch.cat([q[:,6:].flatten() for q in values])
        regular=heavy+.1*rotations.square().sum(-1).mean()+(.01*(1-torsions.cos()).mean() if torsions.numel() else zero)
        residuals=self.residuals(x);connection=zero
        tolerances=dict(cn=.03,angle_c=.04,angle_n=.04,omega=.1,carbonyl=.1)
        for name,r in residuals.items():
            if r.numel():connection=connection+torch.relu(r.abs()/(.5*tolerances[name])-1).square().mean()
        repulsion=zero
        for pair in self.pairs.split(65536):
            distances=torch.linalg.vector_norm(x[pair[:,0]]-x[pair[:,1]],dim=-1)
            depth=self.radii[pair[:,0]]+self.radii[pair[:,1]]-distances
            repulsion=repulsion+torch.relu(depth-1.5).square().sum()/len(x)/.25
        budget=torch.relu(ca-1).square()+torch.relu(heavy-4).square()
        return regular+rho*(connection+repulsion+budget),dict(anchor=heavy,connection=connection,repulsion=repulsion,budget=budget)


def solve(variables,objective,callback=None):
    """Fixed three-stage diagnostic. No autograd claim through LBFGS updates."""
    history=[]
    for rho in [1.,10.,100.]:
        optimizer=torch.optim.LBFGS(variables.parameters(),lr=1.,max_iter=60,max_eval=90,
            history_size=20,line_search_fn='strong_wolfe',tolerance_grad=1e-7,tolerance_change=1e-10)
        calls=0
        def closure():
            nonlocal calls
            optimizer.zero_grad();x=variables();loss,terms=objective(x,variables.variables,rho)
            if not bool(torch.isfinite(loss)):raise ValueError('nonfinite solver objective')
            loss.backward()
            if any(p.grad is None or not bool(torch.isfinite(p.grad).all()) for p in variables.parameters()):raise ValueError('nonfinite or absent parameter gradient')
            calls+=1
            if callback and calls%10==0:callback(dict(rho=rho,calls=calls,loss=float(loss.detach())))
            return loss
        optimizer.step(closure)
        with torch.no_grad():
            loss,terms=objective(variables(),variables.variables,rho)
        state=optimizer.state[next(variables.parameters())]
        history.append(dict(rho=rho,calls=calls,iterations=int(state.get('n_iter',0)),loss=float(loss),terms={k:float(v) for k,v in terms.items()}))
        if callback:callback(history[-1])
    return variables().detach(),history
