# Pretrained Mini diffusion-only pivot: analysis, no new experiment

User abandons scratch as the active direction and requests discussion before execution.
New first-stage contract: public pretrained Protenix-Mini, four unchanged recycles,
one diffusion NFE, K1; usable deterministic conditional soft-sequence derivatives.
Chord/recycle specialization, ESMC adaptation and scratch full-data training are not
active implementation objectives. No new inference or training was launched this turn.

Stopped TRAIN32 worker1629458 by SIGTERM after verifying saved epoch500 last.pt.
Controller recorded exit-15 and user_stop.json; this is a user stop, not numerical
failure or a completed capacity gate. Live progress was522 exposures/16704 updates.
Epoch500 worker metrics: AA lDDT mean0.88029, minimum0.83267, pooled RMSD0.72467A,
C-N RMSE0.332A; gate not passed. Saved checkpoint and all data remain available.
The full29769 scratch DDP training never started. This budget decision does not prove
scratch can never match a pretrained model.

## Existing evidence

- Stage0 used protenix_mini_esm_v0.5.0 (ESM2-3B, MSA-off), not mini_default.
  On1024 development targets, old AA lDDT means: c4_s1=.8465, c4_s2=.8529,
  c4_s5=.8458; P05 .6929/.6938/.6905. Old metric includes same-residue pairs and
  is not directly interchangeable with current observed cross-residue lDDT.
- Paired c4_s1 minus c4_s5: AA mean+.000680 (95% CI[-.000350,+.001733]);
  AA degradation>.05 on14/1024, TM-style degradation>.05 on25/1024, either34/1024
  (3.32%). Against c4_s2, AA mean-.006407, either degradation37/1024 (3.61%).
  These are discovery-seed results, not confirmed equivalence.
- Independent repeat/confirmation included c4_s5/c4_s2/c2_s2, not c4_s1.
  On256 confirmation targets, c4_s2 vs c4_s5 AA mean+.00776; paired warm time
  ratio.920. Retaining four recycles protects an already useful quality component;
  five-to-one diffusion is not a fivefold full-pipeline speedup.
- Frozen decoder gradients to pair-state leaves passed finite differences (shortest
  relative errors.0002032/.00005409; longest951residues14.410GiB). This is not
  soft-sequence differentiation or four-recycle backward evidence.
- Pair/first-response emulator and ESMC endpoint supervision did not pass their
  joint structure/tail gates. They did not test fixed-pretrained-conditioner,
  diffusion-only same-noise consistency. Do not relabel these old failures as that test.

Sources: reports/stage0_confirmation_2026-09-19/reanalysis.md,
reports/stage0_confirmation_2026-09-19.md,
docs/stage1b_decoder_gradient_audit_v1.md,
reports/stage1b_response_supervision_2026-09-18.md,
reports/esmc_endpoint_weight1_2026-09-26.md.

## Source-level findings

Inspected installed Protenix1.1.0 on DiamondHill and current official config.
mini_default has no ESM input and uses MSA; mini_esm uses ESM2 and disables MSA
by default. These checkpoint families are not interchangeable. mini_default is
aligned with the requested new baseline, but requires a query/MSA policy for design.
Target MSA may remain fixed; changing binder sequence while keeping stale binder
features is not a full differentiable sequence path.

Both Mini variants already set gamma0=0, eta=1, S=5, C=4. In generator.py lambda
multiplies sqrt(t_hat^2-sigma_previous^2) times Gaussian noise. With gamma0=0 this
term vanishes: lambda1.003->1 is not an independent quality improvement. The proposed
naive1/ODE1 conditions may coincide exactly; verify configuration equality before
allocating experiments. Initial noise and per-step rigid augmentations remain random.
Pin them and disable all dropout for a deterministic oracle; gamma0=0 alone is not
seed independence. S1 ends atzero; eta1 returns the denoiser estimate algebraically.
Actual sigma includes sigma_data16: s_max160 corresponds to2560 coordinate noise.

Installed protenix.py234-239 enables recycle autograd only for training AND final
cycle. Full four-cycle derivatives need an explicit functional execution path,
forward-equivalence tests, and activation-memory measurements. The existing
ESMCFoldCore also calls detached_tree(features), invalid for a soft-sequence oracle.
Freezing model weights does not inherently stop input derivatives, but these guards do.

Most important interface issue: amino-acid mutations change sidechain atom counts,
elements, names, masks, bonds and chemical reference inputs. A q-weighted residue
embedding with unchanged original atom features can leak the original sequence and
is not a complete all-atom sequence relaxation. Start with a precisely specified
fixed-inventory derivative diagnostic; separately define and validate relaxed atom
features and hard-sequence rebuilding. ESM features must also track q if mini_esm is used;
frozen cached ESM embeddings cannot claim that derivative path.

## Minimal proposal for discussion

1. Fix exact mini_default checkpoint/runtime and MSA/query/chemical-input policy.
   Reuse old mini_esm scores as context only. Retain C4 and do not adapt ESMC.
2. Three distinct forward conditions, C4S5/C4S2/C4S1, native Mini ODE coefficients;
   add naive1 only if runtime audit shows a real difference. Use experimental GT,
   fixed K1, dropout-off common conditioning, explicit noise/augmentation tensors,
   and re-score reused predictions under a common metric where compatible.
3. Before training, validate hard-input replay, four-cycle graph, frozen parameter
   hashes, directional finite differences in sequence-logit space, deterministic
   repeated gradients, gradient norm/per-length diagnostics, and actual forward+
   backward latency/memory. Different fixed noise seeds are robustness checks;
   they need not produce identical outputs or gradients.
4. Short soft-sequence optimization should reduce the intended objective without
   degrading geometry. Do not demand strict monotonicity from every stochastic
   step. Check projected/hard sequences with rebuilt inputs and independent fixed
   noise; target/interface validation needs complex data, not monomer lDDT alone.
5. Only if the interface passes and C4S1 quality is insufficient, discuss bounded
   diffusion-only same-noise consistency. Preserve a low-noise/GT boundary anchor,
   masks, atom symmetries, frame alignment and protein normalization. Bare
   stop-gradient MSE is not a complete anti-collapse specification. Freezing and
   caching conditioning is valid for diffusion-weight training, not for changing q.

DCFold v1 supports pretrained Protenix origin,368M-vs135M comparison, same-noise
stop-gradient diffusion consistency and separate module training. Exact checkpoint
is unspecified in the checked text; its reproducibility statement promises release,
and this search did not locate an official downloadable code/weight package.
Do not treat its recipe as bitwise reproducible. In particular time versus physical
sigma and zero-noise boundary handling require explicit implementation choices.
Its appendix Gaussian Fisher derivation retains squares atEq20 but omits them in
Eq21: independently deriving E[(d log p/dt)^2] for alpha=1 gives
2D*(sigma_dot/sigma)^2 conditional on x0. This flags a formula inconsistency;
it is not proof of the authors' implemented scheduler or marginal Fisher formula.
Do not copy TGM blindly; it is deferred in this phase.

Primary references:
https://arxiv.org/html/2605.17899v1
https://raw.githubusercontent.com/bytedance/Protenix/main/configs/configs_model_type.py
