# Mini trajectory transport in normalized coordinates: bounded diagnostic

Date:2026-10-11. This is a new no-training experiment authorized by the user's
request to diagnose and try a targeted change after61464f87. It does not reopen
placement fitting, search positions, add a student, or select old checkpoints.

## Hypothesis and fixed intervention

The native last recycle reads carried single/pair through its own LayerNorm and
linear projection. Raw boundary state error therefore includes directions that
are treated differently by the actual receiver. A channel-constant shift within
one token/pair is distinct from a common correction across AA candidates.

Test whether transporting candidate cycle1 differences in standardized channel
coordinates is more appropriate than transporting raw coordinates across depth.
For each token single, or each pair vector separately, define

    mu(x) = mean_channels(x)
    sigma(x) = sqrt(mean_channels((x-mu(x))^2) + native_eps)
    n(x) = (x-mu(x))/sigma(x)
    raw P3 = W3 + (M1-W1)
    normalized P3 = W3 + sigma(W3) * (n(M1)-n(W1))

Apply this one fixed rule to both s and z. Native epsilon is read from the pinned
Mini cycle normalization module and saved. No target, per-site fitted coefficient,
label mean, empirical floor, hyperparameter search or candidate-group mean is
accepted by the predictor. This is an approximation to candidate cycle3, not an
algebraically exact replacement of raw transport. The per-vector standardization
may discard useful information; testing it does not assume scale mismatch is the
cause. The zero-edit difference is exactly zero and must return W3 bitwise.

Continue with one unchanged native candidate recycle, genuine prepared candidate
s_inputs/MSA/chemistry, saved WT RNG3 and unchanged S1/two noises230201/230211.
Final single is recomputed. Total inference work remains two candidate recycles
plus WT construction, normalization, cache and decode costs. No speed multiplier
is inferred from these counts or the concurrent audit time.

## Cohort, controls and diagnosis

Use the already locked24parents/48sites/912mutants. Report15TRAIN references,
27sites/513mutants;3same-protein new sites;9held development references/18sites
separately. No new independent confirmation is claimed. All19 non-WT candidates
and both noises are retained. Compare Exact, cold C2, raw WT progression and the
single normalized method on identical candidates. The old three controls are
immutable archived outputs, with hashes; replay raw transport for the first
candidate of every parent to verify native execution remains compatible.

Predict/decode first, then load target M3 strictly for diagnostic statistics.
For raw and normalized P3 report full/common/AA-centered response NMSE, cosine
and energy relative to M3-W3. Also compute those metrics at the receiver's
LayerNorm-plus-linear projection, with the correspondingly transformed W3 and
M3. Units and denominators differ across these spaces; do not compare their raw
MSE numerically as biological importance. No diagnostic result changes the rule.

Decompose per-candidate raw state error over channels into squared channel mean
and centered-channel error (an exact MSE decomposition). Report the per-site
mean and pooled energy fraction, not a claimed causal explanation of decoder
error. Record WT3/WT1 sigma ratios and absolute before/after-native error norms,
including individual error amplification. A lower average is not a contraction
guarantee. No per-candidate oracle scaling or oracle state swapping is decoded.

## Quality and correctness gates

No-edit replay on all24WTs must reproduce native WT4 and both archived coordinates.
Raw replay on one fixed candidate per parent must reproduce both archived raw
transport coordinates. Re-run the first normalized candidate after the other
candidates for that parent and require bitwise states/coordinates, proving no
cache contamination or candidate order dependence. Input/reference checksums
and original weights remain unchanged. Do not relax a failed gate based on quality.

Decode every candidate regardless of latent NMSE. Retain centered AA distance
response, full structure fidelity, per-noise and mean-score ranking/Top1,
old-noise selection/new-Exact-noise raw regret, protein risk tails, severe clashes,
chirality and local displacement, plus geometry transitions in both directions
against raw and C2. Keep all known2EBE/6ZRW/1A7G failure sites. Teacher is a model
reference, not experimental truth. No scaling, mix, subset or seed selection.

## Execution and stopping

Six disjoint parent shards on authorized HIP0..5, fixed modulo6, four parents and
152mutants each. No optimizer or new teacher C4 is run. Cached M1/M3 were generated
and charged by the prior audit; their load/hash/diagnostic time is charged here.
Expected native work:912 new final updates +24 no-edit +24 raw replay +24 isolation
=984 native recycles,1968 S1 calls,0input-encoder calls,0updates. Preparation of
missing labels is not allowed silently. The first candidate M1 is an inference
cost although cached in this diagnostic. No upstream ESM/MSA preparation.

Use frozen source/lock, preserve failures, two-hour execution cap and no automatic
retry of scientific failures. CPU scoring may run concurrently after successful
shards. Source experiments and their files are read-only. If the normalized path
improves latent error but worsens selection/geometry, report a tradeoff and do not
promote. If it fails, close this coordinate-transport hypothesis without scanning
normalization variants or coefficients. This remains an engineering/development
diagnostic; a later learned E3 correction needs a separate locked experiment.
