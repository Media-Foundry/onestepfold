"""Independent geometric measurements for frozen connection-protocol audits."""
import numpy as np

TOLERANCES = dict(cn=.03, angle_c=.04, angle_n=.04, omega=.1, carbonyl=.1)


def normal_dihedral(points):
    """Signed radians via plane normals, without the production projection path."""
    x=np.asarray(points,dtype=np.float64)
    if x.shape[-2:]!=(4,3) or not np.isfinite(x).all():
        raise ValueError('expected finite quadruplets')
    b1=x[...,1,:]-x[...,0,:];b2=x[...,2,:]-x[...,1,:];b3=x[...,3,:]-x[...,2,:]
    n1=np.cross(b1,b2);n2=np.cross(b2,b3)
    n1norm=np.linalg.norm(n1,axis=-1);n2norm=np.linalg.norm(n2,axis=-1);axisnorm=np.linalg.norm(b2,axis=-1)
    if np.any(np.minimum(np.minimum(n1norm,n2norm),axisnorm)<1e-10):
        raise ValueError('degenerate dihedral')
    n1=n1/n1norm[...,None];n2=n2/n2norm[...,None];axis=b2/axisnorm[...,None]
    return np.arctan2(np.sum(np.cross(n1,n2)*axis,axis=-1),np.sum(n1*n2,axis=-1))


def cosine_from_distances(a,b,c):
    ab=np.linalg.norm(a-b,axis=-1);bc=np.linalg.norm(b-c,axis=-1);ac=np.linalg.norm(a-c,axis=-1)
    if np.any(np.minimum(ab,bc)<1e-10):raise ValueError('degenerate angle')
    return np.clip((ab**2+bc**2-ac**2)/(2*ab*bc),-1,1)


def measure_connections(coordinates,anchors,sequence,omega_sign=None):
    x=np.asarray(coordinates,dtype=np.float64);a=np.asarray(anchors,dtype=int)
    if x.ndim!=2 or x.shape[1]!=3 or not np.isfinite(x).all():raise ValueError('invalid coordinates')
    if a.shape!=(len(sequence),4) or len(a)<2 or a.min()<0 or a.max()>=len(x):raise ValueError('invalid anchors')
    ca,c,o=x[a[:-1,1]],x[a[:-1,2]],x[a[:-1,3]]
    n,na=x[a[1:,0]],x[a[1:,1]]
    omega=normal_dihedral(np.stack([ca,c,n,na],axis=1))
    carbonyl=normal_dihedral(np.stack([n,ca,c,o],axis=1))
    nearest=np.where(np.cos(omega)>=0,1.,-1.)
    sign=nearest if omega_sign is None else np.asarray(omega_sign,dtype=float)
    if sign.shape!=nearest.shape or not np.isin(sign,[-1,1]).all():raise ValueError('invalid omega branch')
    cn=np.linalg.norm(c-n,axis=1);cc=cosine_from_distances(ca,c,n);nc=cosine_from_distances(c,n,na)
    residuals=dict(cn=cn-np.array([1.341 if aa=='P' else 1.329 for aa in sequence[1:]]),
        angle_c=cc+.4473,angle_n=nc+.5203,
        omega=np.sqrt((np.cos(omega)-sign)**2+np.sin(omega)**2),
        carbonyl=np.sqrt((np.cos(carbonyl)+1)**2+np.sin(carbonyl)**2))
    target=np.where(sign>0,0.,np.pi)
    return dict(residuals=residuals,cn=cn,angle_c_cos=cc,angle_n_cos=nc,
        angle_c_degrees=np.degrees(np.arccos(cc)),angle_n_degrees=np.degrees(np.arccos(nc)),
        omega_degrees=np.degrees(omega),carbonyl_degrees=np.degrees(carbonyl),
        omega_deviation_degrees=np.degrees((omega-target+np.pi)%(2*np.pi)-np.pi),
        carbonyl_deviation_degrees=np.degrees((carbonyl-np.pi+np.pi)%(2*np.pi)-np.pi),
        nearest_omega_sign=nearest,omega_sign=sign)


def summarize_residuals(residuals):
    result={}
    for name,value in residuals.items():
        value=np.asarray(value,dtype=float);magnitude=np.abs(value);tol=TOLERANCES[name]
        if value.ndim!=1 or not len(value) or not np.isfinite(value).all():raise ValueError('invalid residual vector')
        result[name]=dict(edges=len(value),active=int((magnitude>.5*tol).sum()),
            rejected=int((magnitude>tol+1e-6).sum()),signed_mean=float(value.mean()),
            absolute_p50=float(np.quantile(magnitude,.5)),absolute_p95=float(np.quantile(magnitude,.95)),
            absolute_max=float(magnitude.max()),rms=float(np.sqrt(np.mean(value**2))),
            mean_penalty=float(np.maximum(magnitude/(.5*tol)-1,0).dot(np.maximum(magnitude/(.5*tol)-1,0))/len(value)))
    return result
