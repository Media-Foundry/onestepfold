# Matched step-count reference on a frozen failure/control pair

2026-09-30, after c6a1d98f. Raw-forward attribution only: no geometry solver,
weight changes, training, new candidates, or deployment change from C4/S1.

Targets:2B0A (both noise instances failed fresh-panel repair) and2Z0J (first
source-ordered panel member, retained as control). These are now an explicitly
selected diagnostic panel, not a new independent validation or prevalence sample.
Use the same native inputs and two noises400009/400031, never best-of selection.
Keep the frozen eight-protein confirmation results unchanged.

Run nativeFP32 Mini-ESM v0.5.0 / ESM2-3B, four recycles, no MSA/template, eval mode,
no MC dropout, identity rigid augmentation, identity-bound initial noise2560*Z.
Share the complete packed conditioning across S=1,2,5 for each protein. Use the
existing diffusion_from_conditioning stable Euler implementation unchanged:
gamma0=0,lambda=1,eta=1; each schedule comes from the model scheduler for that S.
Record actual schedules and count denoiser calls. This is controlled integration
under one sampling rule, not native stochasticS5 and not truncations of one path.

Before S2/S5 for each noise, S1 must replay archived coordinates bitwise. Record
input noise and conditioning hashes; neither may change during the calls. Check
CPU/CUDA RNG state before and after each denoising call. Require NFE=S, total
16 denoiser calls/protein,4 Pairformer calls/protein. A parity/hash/RNG failure
blocks attribution; retain failure rather than silently relaxing or reseeding.
GT is not loaded during inference; original input, code and weight hashes are
locked before execution. Two GCD workers, one protein each, reuse conditioning
instead of duplicating the ESM/trunk for each sampler. Timeout5400s/protein.

Save all12 outputs (four S1 replays plus eight new multi-step outputs). Evaluate
against the same experimental GT/masks and native topology: AA/Cα-lDDT, aligned
Cα RMSD, bond/peptide errors, strict checked Cα/ILE/THR centres, severe overlap
counts/rates, maximum penetration and worst atom identities, connection residuals
and cis/trans mismatches. Recompute lDDT and key geometry independently in NumPy.
Use `mini_evaluation_layers_v2.md`, frozen before launch. Keep old absolute and
connection checks descriptive, with no new thresholds. Report the frozen
equal-protein trans-Pro/nonPro q95/q99 bands as exceedance counts, fractions and
positions, with cis unsupported; these are NOT chemical acceptance thresholds.
`legacy_joint_pass` is null for this raw-only comparison (no repair displacement
contract); retain legacy connection residual checks separately. Record
runtime, memory and actual schedules, but do not claim a matched latency benchmark
from one fixed execution order with differing warm-up histories.

Interpret within each target/noise. Improvement of both quality and geometry on
2B0A supports an extra-denoising remedy for these inputs; it does not prove a
universal one-step defect or that distillation will reproduce it. Persistent
multi-step defects require a different explanation. A tradeoff between structural
accuracy and geometry is retained as a mixed result. Control regressions and
noise dependence must remain visible. No averaged metric can erase a bad seed.
Stop after this attribution; no automatic repair grid or LoRA training.
