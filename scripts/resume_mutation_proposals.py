#!/usr/bin/env python3
"""Audit saved gp/gq, then freeze proposals; does not rerun folding."""
import argparse,json,time
from pathlib import Path
import numpy as np
import torch
from fastglycan.paired_teacher_protocol import sha256,write_json
from fastglycan.hybrid_proposals import mutation_proposals
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);root=p.parse_args().root.resolve();out=root/'proposal';lock=json.loads((root/'lock.json').read_text());b=torch.load(out/'chain_probe.pt',map_location='cpu',weights_only=False)
q=b['q'].cuda().detach().requires_grad_(True);p0=q.softmax(-1);kernel,=torch.autograd.grad(p0,q,b['gp'].cuda());kernel=kernel.cpu();assert torch.equal(kernel,b['gq']),'sequence gradient differs from independent softmax pullback'
p64=b['p'].double();gp64=b['gp'].double();formula=p64*(gp64-(gp64*p64).sum(-1,keepdim=True));eps=torch.finfo(torch.float32).eps;gamma=24*eps/(1-24*eps);bound=gamma*p64.abs()*(gp64.abs()+(gp64.abs()*p64.abs()).sum(-1,keepdim=True));error=(formula-b['gq']).abs();assert bool((error<=bound+torch.finfo(torch.float32).tiny).all()),'exceeds 24-operation FP32 rounding bound'
assert sha256(Path(lock['coordinate_source']))==lock['coordinate_source_sha256'];assert torch.equal(b['coordinates'],torch.from_numpy(np.load(lock['coordinate_source'])['coordinates']))
assert all(torch.isfinite(b[k]).all() for k in ['gp','gq','coordinates'])
proof=dict(native_kernel_exact=True,formula32_original_check_passed=torch.allclose(b['expected'],b['gq'],rtol=1e-5,atol=1e-8),formula32_max_abs=float((b['expected']-b['gq']).abs().max()),formula64_max_abs=float(error.max()),formula64_relative_l2=float(error.norm()/b['gq'].norm()),roundoff_bound_max_ratio=float((error/bound.clamp_min(1e-30)).max()),roundoff_bound='gamma_24 * p * (abs(gp)+sum(abs(p*gp))), FP32 eps',saved_gradient_sha256=sha256(out/'chain_probe.pt'))
write_json(out/'chain_audit.json',proof)
options=mutation_proposals(lock['sequence'],b['gp'],budget=16,seed=lock['random_proposal_seed'])
for arm in options:
 for o in options[arm]:o['local_substitution_score']=o.pop('predicted_delta')
unique=[lock['sequence']]+list(dict.fromkeys(o['sequence'] for arm in options.values() for o in arm))
manifest=dict(parent=lock['sequence'],arms=options,sequences=unique,evaluation_seeds=lock['evaluation_seeds'],confirmation_seeds=lock['confirmation_seeds'],random_proposal_seed=lock['random_proposal_seed'],lock_sha256=sha256(root/'lock.json'))
assert not (root/'candidates.json').exists();write_json(root/'candidates.json',manifest);torch.save({k:b[k] for k in ['q','p','gp','gq','coordinates']},out/'gradient.pt')
r=json.loads((out/'report.json').read_text());r.update(complete=True,stage='complete',original_formula_check_failed=True,chain_audit_sha256=sha256(out/'chain_audit.json'),near_hard_archive_exact=True,gradient_seconds=b['gradient_seconds'],elapsed_seconds=None,objective=b['objective'],candidate_sha256=sha256(root/'candidates.json'),gradient_sha256=sha256(out/'gradient.pt'),unique_sequences=len(unique),resume_source_sha256=sha256(Path(__file__)));write_json(out/'report.json',r)
