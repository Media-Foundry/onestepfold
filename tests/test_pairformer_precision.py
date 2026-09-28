import torch
from fastglycan.pairformer_precision import pullback,tree_dot,cast_tree


def test_extended_recycle_carries_input_contribution_without_double_count():
    # The reused b differs across q endpoints; cutting it to b0 is incorrect.
    q=torch.tensor(.4,dtype=torch.double,requires_grad=True)
    state=dict(s=q.square(),b=q.sin())
    def cycle(x):return dict(s=x['s'].tanh()+2*x['b'],b=x['b'])
    a=cycle(state);z=cycle(a);direct,=torch.autograd.grad(z['s'],q,retain_graph=True)
    terminal=dict(s=torch.ones_like(q),b=torch.zeros_like(q))
    ga,_=pullback(cycle,a,terminal);gs,_=pullback(cycle,state,ga)
    chain,=torch.autograd.grad(tuple(state.values()),q,grad_outputs=tuple(gs.values()))
    torch.testing.assert_close(chain,direct)
    assert gs['b']>2  # both cycles' reuse contributes
    h=.01
    plus=dict(s=(q+h).square(),b=(q+h).sin());minus=dict(s=(q-h).square(),b=(q-h).sin())
    delta={k:(plus[k]-minus[k])/(2*h) for k in plus}
    assert abs(float((tree_dot(gs,delta)-gs['s']*delta['s']).detach()))>1


def test_pullback_ignores_constant_zero_state_outputs():
    x={'b':torch.tensor(.2,dtype=torch.double)}
    g,y=pullback(lambda x:dict(z=torch.zeros_like(x['b']),b=3*x['b']),x,dict(z=torch.tensor(7.),b=torch.tensor(2.)))
    assert g['b']==6


def test_dtype_cast_preserves_fixed_integer_masks_and_alias_contract_is_explicit():
    x=dict(float=torch.tensor([1.]),index=torch.tensor([1]),mask=torch.tensor([True]))
    y=cast_tree(x,torch.double)
    assert y['float'].dtype==torch.double and y['index'].dtype==torch.int64 and y['mask'].dtype==torch.bool


def test_empty_constraint_returning_none_matches_native_initializer():
    from fastglycan.pairformer_precision import PairformerStages
    class Model(torch.nn.Module):
        def input_embedder(self,f,**kwargs):return f['x']
        def linear_no_bias_sinit(self,x):return x
        def linear_no_bias_zinit1(self,x):return x
        def linear_no_bias_zinit2(self,x):return x
        def relative_position_encoding(self,x):return x
        def linear_no_bias_token_bond(self,x):return x*0
        def constraint_embedder(self,x):return None
    m=Model();stages=PairformerStages(m,{})
    stages.features=lambda c:dict(x=c['x'],relp=torch.zeros(2,2,3),token_bonds=torch.zeros(2,2),constraint_feature={})
    x=torch.ones(2,3);result=stages.initialize(dict(x=x))
    torch.testing.assert_close(result['z_init'],torch.full((2,2,3),2.))
