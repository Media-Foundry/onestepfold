# C4 hard-mutant response rank, v1 (2026-10-02)

Question: within a fixed real sequence context and a single substitution site,
are the 19 non-WT C4 endpoint differences concentrated in 3–5 directions?
This is a descriptive, post-hoc compression experiment. It does not train a head,
choose deployment anchors, predict coefficients, or establish structure quality.

## Frozen inputs and budget

Use the public Mini-ESM checkpoint and ESM2-3B with native hard features, full C4,
FP32, eval mode, MC dropout off, no external MSA/templates. Diffusion is not called:
this first phase measures the requested local trunk slices, not hard-folding
accuracy. The previous fixed2048 intervention only updated diffusion; it is not
necessary to introduce that checkpoint into this trunk-only experiment.

Choose 10 distinct TRAIN sequence groups from the already prepared 423-protein
development pool, four in 80–128 aa, three in129–192, three in193–256. Order by
SHA256(`hard-response-rank-v1:20261002:`+group_id), exclude previous four backbone
proposal parents and eight Chord records, require distinct nonempty SIFTS
accessions across parents. This is not an independently clustered test set.
Choose five distinct positions per parent in hash order using
`hard-response-site-v1:20261002:`+group_id+`:`+zero-based-position.
No gradient, response magnitude, GT quality or resulting spectrum enters selection.

At each of 50 sites evaluate all20 canonical hard AAs in `ACDEFGHIKLMNPQRSTVWY`
order. WT is shared across the five sites: 10 WT+950 mutants=960 unique hard
sequences. Repeat the WT and the first non-WT mutant at the first selected site
per parent for exact replay: 20 extra calls, **980 full-C4 forwards /3920 recycle
calls /0 denoiser calls**. All target features, reference chemistry and live ESM
are regenerated, including repeats. No source-state warm-start or soft mixtures.
Eight GCD workers, assigned whole proteins, 30-minute bounded runtime, no auto
quality-driven extension. Runtime error is retained in the denominator.

## Saved endpoints and common comparison space

For every AA at site i save FP32 `s[i]`, `z[i,:]`, `z[:,i]`, plus `s_inputs[i]`
as an explicitly separate decoder-interface diagnostic. Save WT slices for all
five sites; store atom inventory names/count/hash for each distinct native graph.
Token positions remain aligned in equal-length single substitutions; all-atom
arrays are never subtracted across different inventories. Native ESM and chemical
features are target-specific at every endpoint.

The primary matrix contains the three requested slices, with 19 non-WT rows:
`[delta_s_i, flatten(delta_z_i_row), flatten(delta_z_i_col)]`. Source and mutant
endpoints are converted to FP64 **before** subtraction. A 19×19 FP64 Gram matrix
gives singular values and cumulative energy for K=1,2,3,4,5 (full spectrum also
retained). No full L×L pair state is flattened/saved for rank analysis in v1.

Report separate s/row/column spectra, raw concatenation, per-feature block scaling
(divide each block by sqrt(number of features)), and equal-block-energy scaling
(divide by the uncentered block's Frobenius norm). These are sensitivity analyses,
not deployment preprocessing learned without endpoints. Never normalize each AA
response separately, since that would erase real response amplitude information.
The primary duplicates z_ii in row/column as proposed; a diagonal-deduplicated
sensitivity is reported. Do not assume the pair state is symmetric.

For all variants report WT-anchored and mutant-mean-centered spectra separately.
The latter subtracts the mean of the 19 non-WT responses, not a mean including
the zero WT column. Shared mean energy is explicitly reported. Uncentered rank
cannot exceed19; centered rank cannot exceed18. Being below these algebraic caps
is not itself a discovery. Zero-energy matrices are uninformative, not “rank1
success.” Report Frobenius energies and response norms alongside normalized spectra.

## Evidence and interpretation

Deliver per-site K1–5 energy, rank95/rank99, entropy effective rank, participation
rank, normalization sensitivity, and per-protein summaries. Use proteins as the
outer bootstrap unit (10,000 seeded resamples); five sites within one protein are
not five independent proteins. Report exact proportions E3≥95% and E5≥95%, not a
new deployment pass/fail threshold. Validate Gram results against direct SVD on
saved matrices and preserve replay failures/zero signal rather than excluding them.

Low post-hoc rank means these measured endpoint vectors admit a short basis.
It does **not** establish how to choose a few hard queries without seeing all
endpoints, how to infer held-out coefficients, a context-independent amino-acid
coefficient table, global conditioning reconstruction, decoder sensitivity, or
speedup. The decoder also reads s_inputs/reference chemistry; low local s/z rank
does not reconstruct those paths. WT Jacobian residuals are a later separate
experiment, not silently substituted for hard endpoints here.

The prior 0/4 versus1/4 selected-candidate outcome used development-noise **hard**
scores to select among real substitutions. It is not a direct 19-AA Jacobian
ranking experiment. Its finite-mutation utility limitation motivates this new
question, but does not prove a particular low-rank architecture in advance.

Stop after this batch and analysis. No automatic global-z expansion, response-head
training, extra sites or coefficient fitting based on favorable spectra.
