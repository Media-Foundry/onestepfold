import copy
import json
from pathlib import Path

import numpy as np
import pytest

from fastglycan.ideal_output_reference import ideal_output_reference


def test_named_templates_preserve_anchors_handedness_and_rigid_equivariance():
    templates=json.loads(Path('reports/mini_ccd_ideal_template_2026-09-30/reference/templates.json').read_text())['records']
    for aa,t in templates.items():
        names=t['atom_names'];n=len(names)
        # Deliberately reverse the actual atom inventory, so index-based mapping fails.
        order=np.arange(n)[::-1];actual=np.asarray(names)[order]
        native=np.asarray(t['native'])[order];x=np.tile(native,(3,1))
        ids=np.repeat([1,2,3],n);nn=np.tile(actual,3)
        key=t['ccd']+':'+','.join(actual)
        remap={int(old):new for new,old in enumerate(order)}
        variants={key:dict(atom_names=actual.tolist(),bonds=[(remap[a],remap[b],k) for a,b,k in t['bonds']])}
        y,records=ideal_output_reference(x,nn,ids,aa*3,variants,templates)
        keep=(ids!=2)|(nn=='CA');assert np.array_equal(x[keep],y[keep])
        assert len(records)==1
        repeat,_=ideal_output_reference(y,nn,ids,aa*3,variants,templates)
        np.testing.assert_allclose(repeat,y,atol=1e-13,rtol=0)
        q,_=np.linalg.qr(np.random.default_rng(91).normal(size=(3,3)));q[:,-1]*=np.linalg.det(q)
        equiv,_=ideal_output_reference(x@q+3,nn,ids,aa*3,variants,templates)
        np.testing.assert_allclose(equiv,y@q+3,atol=1e-13,rtol=0)
        target=np.asarray(t['ideal'])[order]
        np.testing.assert_allclose(np.linalg.norm(y[n:2*n,None]-y[None,n:2*n],axis=-1),
                                   np.linalg.norm(target[:,None]-target[None,:],axis=-1),atol=1e-13,rtol=0)
        broken=copy.deepcopy(variants);broken[key]['bonds'].pop()
        with pytest.raises(ValueError,match='adjacency'):ideal_output_reference(x,nn,ids,aa*3,broken,templates)
        bad=nn.copy();bad[n]='XXX'
        with pytest.raises(ValueError,match='inventory'):ideal_output_reference(x,bad,ids,aa*3,variants,templates)
