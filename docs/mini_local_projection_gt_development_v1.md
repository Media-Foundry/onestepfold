# Experimental-GT local projection development v1

2026-09-30. This is a development diagnosis after the old-six raw-coordinate fit,
not a reopening of independent32 validation, a new deployment gate, or training.
Freeze selection before running either projection. No weight/budget search.

Source: the existing DiamondHill `esmc_pretrained_bridge_v1_20260927` bundle,
joined by sequence group and atom identity to `scratch_structure_data_v1_20260927`.
Use only `native_reference` predictions, seeds12345 and54321. That name denotes
native ESM2 model predictions, NOT experimental GT. These are historical C1/S1,
schedule[2560,0], gamma0=0, lambda1.003, eta1 outputs. Do not relabel them C4/S1
or claim deployment quality from this development comparison. No new inference.

Select eight unique PDB/accession sources, sorted by group SHA256, from lengths
64 through384 inclusive. Require canonical sequence; accepted GT metadata and
bundle hashes; single-chain contiguous residue mapping; complete observed native
heavy-atom inventory including any OXT present in that inventory; finite GT;
complete backbone and no annotated chain break or modified residue. No coordinate
imputation or arbitrary zero filling. Exclude apparent disulfides (SG–SG <2.5 Å)
from this local uncrosslinked representation. Retain assembly/hidden-context labels.
Structural context and other chemical-support limitations must remain explicit;
this source screen does not certify universal chemical support.

Exclude reserved32 by sequence group, PDB and SIFTS accession, and calibrated HSP
rule: aligned residue count≥50 and either (identity≥.30, shorter coverage≥.70,
E≤.001) or E≤1e-5. Use BLAST2.17.0 with the previous calibrated search settings,
reserved32 queries against all640 source sequences, and the original21070-reference
database residue count as fixed effective database size. Preserve command, version,
hashes, stderr and all HSP evidence. A search warning prevents an isolation claim
until checked. This is development-set separation, not pretraining exclusion.

Selection depends on source eligibility, never raw prediction quality, projection
loss or repair success. Require both archived native prediction files and their
hashes, correct atom shape and recorded C1/S1 contract. Missing eligibility must
be reported, not filled by relaxed rules. Further chemical-reference preflight is
required before fitting; selected failures stay visible and are not replaced.

For each selected protein, compare original experimental GT, its old local
projection and its fitted projection (self-projection); separately compare each
of two native predictions and their two projections against the same GT. Keep
GT and model inputs in separate arms. Fit all original native heavy atoms equally
using unchanged `fit_local_projection`: one FP64 CPU L-BFGS start, max_iter60,
max_eval90, final iterate only. No chain/clash optimization, best selection,
fallback, increased budget or task/contact loss. At most two single-thread workers,
900 seconds per fit; 24 fits total. No GPU/model training.

Report observed inter-residue all-atom and Cα lDDT with frozen atom correspondence,
backbone/side-chain displacement and atom-centred score contributions, checked
local chemistry, chain/clash outcomes, iterations/closures and cost. Both noises
remain separate as well as paired protein summaries; no best-of-two. Symmetric
atom naming is retained as in existing scoring; no posthoc symmetry remapping.
Independently replay saved parameters and check scores on frozen coordinates.
Missing/failed cases remain in denominators. No input-gradient or nearest-point
optimality claim. The independent32 rejection remains unchanged.

The question is whether closer fitting to raw actually reduces experimentally
measured projection damage, and how much distortion already occurs when the
input is experimental GT itself. It is not whether raw MSE alone decreased.
