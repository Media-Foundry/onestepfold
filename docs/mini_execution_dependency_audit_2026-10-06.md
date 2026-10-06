# Native C4 dependency audit — 2026-10-06

Scope: the unchanged hard-candidate FP32 Mini C4/S1 screening path. This is a
source/dependency assessment supporting the locked execution-profile experiment,
not approval to install any cache or a claim of measured speedup. Protenix's
installed source hashes are recorded in the runtime artifact. GitNexus query and
context checks located the local feature, recycle, atom-pair and decoder paths;
installed external methods were inspected directly where graph coverage ends.

| Object/work | Actual dependencies / invalidation | Reuse scope to investigate |
|---|---|---|
| Parent-reference scoring pairs/distances | Exact parent GT coordinates, observation mask, atom/residue mapping, separation and score definition | Same parent/reference/protocol; already prepared outside sequence work |
| Native features and atom inventory | Entire hard sequence, topology/modifications/chain specification, CCD/reference data, native builder version, feature RNG/seed | Not shared across mutants. Static CCD lookup/loading may be separable from candidate construction |
| ESM embedding | Entire candidate sequence/tokens, ESM checkpoint, layer/config, precision and execution settings | Same exact sequence/settings only; a single mutation can affect all token embeddings |
| Raw relative-position feature `relp` | `asym_id`, `residue_index`, `entity_id`, `token_index`, `sym_id`, encoder r_max/s_max | Can match for these equal-length monomers; require equality of all five arrays and config, not just chain length |
| Embedded relative-position value | Raw relp plus the specific embedding module weights/dtype/device | Candidate invariant only under those conditions; trunk and diffusion have distinct embedding modules |
| Atom-pair d_lm/v_lm/pad_info | ref_pos, ref_space_uid, atom order/count, query/key windows32/128 and layout code | Rebuild when candidate atom inventory/reference changes; do not inherit WT atom cache |
| C4 initialization/s_inputs | Input embedding including native chemistry/features and ESM, relative positions, token bonds, optional constraints, weights | Candidate-specific. Equal shapes or a local mutation do not imply equal values |
| Recycle s/z | All initial inputs, preceding s/z, template/MSA/Pairformer weights/config and RNG sampling history | Preserve complete candidate computation; no new state substitution in this task |
| Diffusion pair_z cache | Exact final candidate z, relp, diffusion-conditioning weights (relpe, normalization, projections, two transitions), dtype/layout/execution configuration | No noise/sigma argument: same-candidate/four-noise reuse is a candidate for a later exact-output test; not a cross-mutant cache |
| Diffusion atom p_lm/c_l | pair_z, ref_pos/charge/mask/element/name characters, atom_to_token_idx, d_lm/v_lm/pad_info, r_l-present branch, atom encoder weights/window settings | Same fixed candidate graph and conditioning across its four noises; invalidated by any listed input or model change |
| Noisy decoder state and output | Initial coordinate/noise seed, schedule/sigma, s_inputs/s, pair/atom cache, model/config | Remains noise-specific. Batching changes layout and peak memory and needs its own replay validation |
| Geometry labels/exclusions | Candidate atom/residue identity, reference chemistry, covalent bonds, implementation rules and weights/masks | Reuse only for the same exact candidate graph/rules; source audit must distinguish topology from coordinate-dependent labels |
| Task/geometry evaluation | Actual output coordinates plus appropriate parent reference/candidate geometry metadata | Per output; cannot cache the score merely because conditioning or graph is unchanged |

`diffusion_from_conditioning` presently calls both prepare_cache methods before
each S1 noise, although their inputs remain the same for the four-noise workload.
The pair cache source has no stochastic call and no sigma/noisy-coordinate input.
The atom cache likewise uses reference chemistry and projected pair features;
`r_l=True` chooses the conditioning branch but is not a noisy coordinate tensor.
The profile experiment checks repeated output equality and RNG behavior directly.
Removing repeated calls has NOT yet been implemented or benchmarked.

Observed WT/mutant feature equality is an inventory, not a proof that every equal
leaf is semantically reusable. In particular, cache keys must include topology,
chain/token identities, model version and execution configuration; candidates
with insertions, ligands or changed assembly lie outside this panel. Opaque
objects are reported as unknown instead of assumed equal. Cross-sequence ESM,
trunk and atom caches are not classified as invariant.

All inference remains no-grad. A future inference cache is not automatically
valid for differentiable sequence optimization: detachment or stale reuse could
change the derivative even if hard forward examples match. This audit makes no
input-gradient or design-utility claim.

Performance prioritization is deferred to the profiler results. A correct reusable
object can still cost too little to matter, and identifying a costly stage does
not prove that a proposed rewrite is equivalent. The next implementation, if any,
must have a separately locked replay and full-workload comparison.

## Measured scope and two additional source findings

The completed18-input inventory found46 equal and57 changed leaves in each of
nine WT→A/C-mutant comparisons, with no opaque leaves. `relp` was equal; all
s_inputs/s/z differed. This observation is bounded by these equal-length monomers.
All18 candidate cache probes gave four identical outputs with no RNG advancement.

`identity_noise` independently hashes `(version, seed, chain_id, residue_id,
atom_name)` for each atom, initializes a private NumPy generator and draws three
values, then converts to FP32 on the destination and multiplies by2560. Its exact
keys do not include the residue type or full sequence. A future lookup of these
identity-keyed rows is therefore a candidate that can preserve the intended common
noise, provided algorithm version, atom ordering, dtype/device and scaling
arithmetic are preserved. This is not permission to share arbitrary candidate
atom coordinates/chemistry. No noise generator was changed in this audit.

The screening call uses `build_adapter_supervision`, which constructs full
smooth-lDDT labels and observed GT bond targets. However, `response_geometry`
reads only excluded pairs, radii, stereocentres and reference volumes; `screen_native`
computes its descriptive bond residuals from inventory/reference directly. The
smooth labels and GT bond targets are unused in this screening path. A separate
minimal geometry-label builder could avoid that work while preserving all input
validation and checked geometry fields. The training helper remains needed by
training callers and should not be globally simplified or deleted. No label
builder was changed here.
