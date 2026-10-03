"""Read-only candidate-diversity probes; no optimization or model mutation."""
import torch


def tensor_diversity(tensor, candidates=19):
    x=tensor.detach().double()
    result=dict(shape=list(x.shape),rms=float(x.square().mean().sqrt()),minimum=float(x.min()),maximum=float(x.max()),
                zero_fraction=float((x==0).double().mean()),below_minus6_fraction=float((x<-6).double().mean()))
    if x.ndim and x.shape[0]==candidates:
        centered=x-x.mean(0,keepdim=True)
        result.update(candidate_centered_rms=float(centered.square().mean().sqrt()),
                      candidate_max_difference=float((x-x[:1]).abs().max()),
                      candidate_identical=bool(torch.equal(x,x[:1].expand_as(x))))
    return result


def parameter_branch(name):
    if name.startswith('query.'):return 'aa_query'
    if name.startswith(('readout.','left.','right.','aa_readout.','pair_content.')):return name.split('.')[0] if not name.startswith('readout.') else '.'.join(name.split('.')[:2])
    return name.split('.')[0]
