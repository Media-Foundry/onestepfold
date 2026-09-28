"""Original logits FD gate plus conservative, explicitly separate signal labels."""
import torch


def original_logit_directions(point, count=3, seed=731):
    generator=torch.Generator(device=point.device).manual_seed(seed)
    for _ in range(count):
        v=torch.randn(point.shape,device=point.device,dtype=point.dtype,generator=generator)
        v=v-v.mean(-1,keepdim=True)
        yield v/v.norm()


def fd_measurement(analytic, plus, minus, h, *, probability_delta_norm,
                   coordinate_delta_norm, relative_tolerance=.05, absolute_tolerance=1e-6):
    numerator=plus-minus;fd=numerator/(2*h);error=abs(fd-analytic)
    scale=max(abs(fd),abs(analytic));passed=error<=absolute_tolerance+relative_tolerance*scale
    relative_only=error<=relative_tolerance*scale
    relative_dominates=relative_tolerance*scale>absolute_tolerance
    resolved=numerator!=0 and probability_delta_norm>0 and coordinate_delta_norm>0
    return dict(h=h,analytic=analytic,loss_plus=plus,loss_minus=minus,numerator=numerator,
                finite_difference=fd,absolute_error=error,relative_error=error/max(scale,1e-12),
                pass_tolerance=passed,relative_only_pass=relative_only,
                relative_term_dominates=relative_dominates,nonzero_response=resolved,
                informative_pass=passed and relative_only and relative_dominates and resolved)


def summarize_directions(directions, *, finite, gradient_norm, repeat_max_abs):
    original=[];informative=[]
    for rows in directions:
        original.append(any(a['pass_tolerance'] and b['pass_tolerance'] for a,b in zip(rows,rows[1:])))
        informative.append(any(a['informative_pass'] and b['informative_pass'] for a,b in zip(rows,rows[1:])))
    base=bool(finite and gradient_norm>0 and repeat_max_abs==0)
    passed=base and all(original);informative_pass=base and all(informative)
    label='fail' if not passed else ('pass_informative' if informative_pass else 'pass_low_signal_or_absolute_tolerance_assisted')
    return dict(original_passed=passed,informative_passed=informative_pass,label=label,
                original_direction_plateaus=original,informative_direction_plateaus=informative)
