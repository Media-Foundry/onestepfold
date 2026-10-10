# Mini trajectory normalization diagnostic

**Complete; fixed no-training intervention; not promoted.** A single input-only
normalization rule was tested on the existing24 references/48 sites/912 mutants.
It did not improve the raw WT-progression baseline. The useful diagnostic result
is that a substantial pair-direction mismatch remains at the actual recycle
receiver, after its LayerNorm and linear projection. It is not merely a large
error in raw state coordinates that this receiver discards.

This narrows a hypothesis; it does not identify model capacity, data size, or
one optimizer as the unique cause of earlier learned recovery failures. No
learned trajectory correction was trained or evaluated in this batch.

## Fixed question and computational boundary

[Protocol](../../docs/mini_transport_normalization_v1.md) was frozen before any new
quality output. Mini and native weights, prepared candidate inputs/chemistry,
WT boundaries, decoder and noises230201/230211 remain unchanged. No upstream
MSA/ESM preparation, input encoding, loss, teacher reconstruction or optimizer
was introduced. Native MSA computation inside the candidate recycle still runs.

The native last update receives each carried state via
`f_s(x)=linear_s(LN_s(x))` and `f_z(x)=linear_z_cycle(LN_z_cycle(x))`.
These are the carried-state contributions before candidate initialization/MSA,
not a replacement definition of the entire native input.

The existing path uses `P3 = W3 + (M1-W1)`. The only new path is

    n(x) = (x - mean_channels(x)) / sigma(x)
    sigma(x) = sqrt(mean_channels((x-mean_channels(x))^2) + native_epsilon)
    P3_normalized = W3 + sigma(W3) * (n(M1)-n(W1))

The formula operates independently on every single/token vector and pair vector,
for both s and z. Both native epsilons are1e-5. All scales are derived from legal
prediction inputs; no target state, fitted coefficient, candidate-group mean or
development-selected threshold enters it. No-edit returns W3 bitwise. This is an
approximate transport law, not an algebraic identity with raw transport.

Both paths continue through the same real final candidate recycle and S1. Final
single is recomputed. Target M3 is loaded only after prediction/coordinate output
for diagnostics. M4 is also diagnostic-only. The old fixed-final-single oracle
and earlier speed multiplier do not transfer to this different interface.

## Where the mismatch remains

Metrics below are equal-parent averages on nine reused development proteins.
At the state boundary, prediction is compared with `M3-W3`; at the receiver,
`f(P3)-f(W3)` is compared with `f(M3)-f(W3)`. Each row has its own normalization
and target space. Cross-row numerical changes are not error contraction factors.

| AA-centered response | Raw transport NMSE | Normalized transport NMSE | Raw cosine | Normalized cosine |
|---|---:|---:|---:|---:|
|Carried s at cycle3|0.10675|0.46853|0.94533|0.72993|
|Carried z at cycle3|1.11272|1.18335|0.41905|0.39869|
|Receiver single contribution|0.21291|0.21487|0.88956|0.88926|
|Receiver pair contribution|1.23571|1.29850|0.37497|0.37634|

The pair error remains substantial where the last recycle actually consumes it.
The normalized rule barely changes its direction cosine, while receiver-space
predicted/teacher centered energy increases0.96934→1.07188. That combination
does not produce a useful correction. It does not support a claim that this
particular coordinate rescaling recovers missing candidate evolution.

Conversely, single raw-state error grows sharply while receiver-space error
changes little. Thus raw boundary MSE and the error seen by the next operator
are distinct diagnostics. This observation applies at this recycle boundary;
it does not invalidate all latent supervision or prior fixed-single experiments.

Across channels within each token/pair, raw error decomposes exactly into a
channel-constant mean term and a centered-channel term. The pooled held-protein
channel-mean fractions are0.225% for s and2.046% for z. Channel-constant shift
therefore does not dominate this raw error energy. This is **not** the across-AA
common component, and it does not quantify every direction that normalization
or downstream layers might suppress. Finite-precision LayerNorm is not claimed
bitwise invariant to arbitrary shifts.

Reference mean sigma(W3)/sigma(W1), averaged across24 parents, is1.00591 for s
and1.05002 for z. Parent means range0.99532–1.01876 and1.01241–1.10863 respectively.
These observed WT scale changes motivated no subsequent tuning; the formula
was already locked. They do not establish that every candidate has the same scale.

## Decoded held-protein quality

| Metric | Cold C2 | Raw WT progression | Normalized progression | Exact |
|---|---:|---:|---:|---:|
|Spearman|0.68616|0.74298|0.74250|1|
|Mean-score Top1|11/18|5/18|6/18|18/18|
|AA distance response RMSE, Å|0.43361|0.40680|0.40996|0|
|Old-select/new-Exact-evaluate regret|0.024324|0.030820|0.032646|0.008366|
|Geometry passes|296/684|405/684|403/684|438/684|
|Local RMSD P95, Å|2.2140|2.2627|2.4084|0|
|Maximum local RMSD, Å|5.6724|5.9054|5.8887|0|
|Outputs with local RMSD>1 Å|136|132|135|0|
|Severe collision pairs|2922|2632|2582|2747|
|Wrong chirality instances|379|342|340|304|

Normalized-minus-raw differences have descriptive nine-parent95% intervals:
Spearman−0.000487 [−0.01014,+0.00955]; response RMSE+0.003162 Å
[−0.000350,+0.007352]; regret+0.001827 [−0.000529,+0.006009]. All cross zero.
The batch does not establish a general worsening law, but it provides no reason
to promote this rule. Response RMSE improves on only3/9 parents.

Geometry is mixed:4 raw-passing outputs fail and2 raw-failing outputs pass.
Severe collision/incorrect-centre totals fall slightly, while P95 and total
passing count worsen. Net counts must not hide instance changes or severity.
Deviation is measured against same-noise C4, not experimental mutant structures.

Sixteen of18 old-noise selections remain the same. The two changed choices are:

|Site|Raw→normalized|Raw regret|Normalized regret|
|---|---|---:|---:|
|1YSB V5|R→P|0.014105|0.050158|
|2FKZ E44|P→M|0.003173|0|

Their net change divided by18 explains the entire mean regret increase. Mean-score
Top1 and old-noise selection are different metrics. The known2EBE failures and
1A7G S34 are retained; this intervention did not repair them.

## Other panels and post-recycle error

No parameters were trained: TRAIN is the historical role of these15 references,
not evidence of learning in this batch. Raw→normalized TRAIN response RMSE is
0.38447→0.38746 Å, Spearman0.74743→0.74374 and regret0.07254→0.07321.
Geometry passes423→421/1026. The only changed TRAIN choice is1DZR A179 P→G,
with regret0→0.020144.6/15 parents have a lower response RMSE.

All three same-protein new sites have higher response RMSE; the mean rises
0.48977→0.49758 Å. Spearman falls0.66725→0.61287, while old-noise selections and
regret0.39670 remain unchanged. The1A7G S34 high-cost R choice persists.
Geometry passes stay59/114, but P95 rises5.58958→5.63035 Å.

Held absolute latent RMSE, equal-parent means, is:

|State|Raw input error at cycle3|Normalized input error at cycle3|Raw final error|Normalized final error|
|---|---:|---:|---:|---:|
|s|1.28036|2.75954|0.75363|0.75896|
|z|4.78936|4.86360|3.68591|3.71712|

Units here are latent units, not Å. The final update reduces average normalized
input error but amplifies s error for7/342 candidates and z error for23/342.
The smaller single amplification count than the earlier raw path's45/342 is
not a quality improvement: this method starts with a much larger input error
and ends with slightly greater absolute error. Do not use a larger denominator
to imply a better corrective map.

## Verification, accounting and artifacts

All six fixed shards and all scoring jobs completed on authorized HIP0..5.
Nine focused CPU tests passed locally and on DiamondHill.24 no-edit WT outputs,
24 fixed raw candidate replays and24 normalized candidate isolation replays
passed bitwise state/coordinate checks; native weights and reference hashes
remained unchanged. The original experiments and their results were not modified.

New native work is984 recycle calls and1968 S1 calls, zero input-encoder calls
and zero updates. This includes replay checks. The912 first candidate states
and their target labels were cached by the preceding audit. A deployment
benchmark would have to charge the real first candidate recycle, reference
construction and all cache/normalization work. The concurrent diagnostic's
elapsed time is not a new folding speedup measurement.

Local verification checked1,834 archived file hashes, all912 predicted coordinate
NPZs for hashes/shape/finiteness,576 Spearman values,192 regrets and7,296 output
record accounting checks, including archived controls. Equal-parent summaries,
selection identities, geometric transitions and tail summaries were recomputed.
Coordinates were **not rescored locally**; the frozen scorer ran on DiamondHill.
[local_verification.json](terminal/local_verification.json) records this scope.

[Metrics](terminal/metrics.csv), [all selection changes](terminal/selection_changes.csv),
[full diagnostics](terminal/summary.json) and six per-shard records are included.
The [archive receipt](terminal/publication_receipt.json) identifies the44,085,988-byte
archive on DiamondHill, SHA256
`b2384139976bb2b39cf6b1b5509dbdb4a8ad9944b430073c62f23fa583c23cbe`.
It includes the frozen source, complete score records/controls and912 normalized
coordinate outputs; no model weight or full latent tensors are copied into Git.

## Decision

Close this fixed normalization rule without a coefficient or normalization grid.
It does not provide a deployable improvement over raw WT progression. Preserve
the receiver-space diagnostic: pair-direction mismatch remains after the native
input transforms, whereas raw single-state error can change much more than the
receiver error. Any future E3 learner should be evaluated in both spaces and at
the decoder; a lower raw latent loss alone is insufficient. This is guidance for
a separately locked learning experiment, not evidence that a new loss will fix
transfer. Existing development data remain development data; no new family-level
confirmation, architectural capacity result or practical accelerator is claimed.
