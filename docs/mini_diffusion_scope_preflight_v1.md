# Dense diffusion adaptation: engineering preflight

2026-09-30, after65041e09. This is a new trainable-scope intervention; no more
smooth-lDDT width/LR scans, no scratch initialization or Pairformer training.
The current835584parameter adapter touches56matrices in eight token blocks only.
That restriction is not proof of a capacity bottleneck. Check feasibility before
committing to a bounded dense-training comparison.

Compare two explicit native-parameter scopes:
- `token_dense`: the exact56native weight matrices targeted by the old rank8 adapter,
  updated directly without a low-rank factorization. Other token parameters stay frozen.
- `diffusion_dense`: all natively trainable parameters in `model.diffusion_module`, including its
  conditioning, reference/atom encoder, token transformer and atom decoder paths.
  ESM/trunk/Pairformer/confidence heads remain frozen.
Native fixed Fourier frequency/phase parameters stay frozen; record native trainable
flags before freezing the model, and audit these constants explicitly.
No parameters are randomly initialized and no adapter is installed. Scope selection
must leave every value and native state-dict key unchanged.

Use two already-frozen TRAIN inputs only: first exposure in the old training order,
and longest TRAIN sequence (ties bygroup ID). One original seed600001. For each scope
and each input, independently start from public native weights, require exact native
cache replay, compute full backward on the frozen calibrated0.1Å recipe, record each
selected tensor's gradient/zero/None status and norm. Perform ONE engineeringAdamW
step at1e-5, betas(.9,.999),eps1e-8,decay0,clip1; this is not a learning-rate search.
Save/reload that partial native checkpoint, require matching post-step output;
restore public weights and require original replay. Audit every excluded parameter
unchanged, all native state keys unchanged, no Pairformer call or random-stream change.
Record peak allocated/reserved memory and latency. Two scopes may run on twoGCDs.

Four forwards per input (initial gradient, post-step, public restoration, saved-step
replay): sixteenNFEs total. No cached-conditioning gradients are claimed to replace
live sequence gradients. Experimental GT remains authoritative; S2 auxiliary unchanged.
No validation input, optimizer trajectory continuation or quality-based target choice.
Engineering-step outputs are never used as training initializers or teacher labels.

Inactive selected parameters, nonfinite gradients/outputs, replay/freezing failures or
memory failures must be exposed and resolved before training. Do not silently remove
parameters to make an advertised full scope pass. Zero-valued finite gradients are
reported separately from absent graph paths and are not automatically a defect.

If preflight succeeds, lock a short dense-scope comparison with identical data,
objective, update count and optimizer between the two dense arms. The previousLoRA
result is a practical reference, not a pure capacity comparison: changing parameter
representation changes optimizer geometry and may require a different stated LR.
Do not infer equivalence of update norms or FLOPs from equal exposure/update budgets.
