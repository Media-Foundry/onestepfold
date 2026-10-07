# Mini compensated last recycle v1 — 2026-10-07

New study authorized after the user proposed retaining a native last recycle.
Earlier WT3→Target1 and external-editor studies remain closed. S1-adapter work
is deferred; it is not combined with this intervention. Status: implementation
and integrity checks, no trained quality result.

## Function and inputs

One WT C4 captures completed WT cycle 3 and its exact execution RNG. Each real
candidate uses its own archived `s_inputs`, raw single-row query-MSA features,
atom graph and reference chemistry. No new MSA/ESM preparation, downloads, or
target input embedding are performed. The native input projection, recycle
bridge, MSA module and 16-block Mini Pairformer execute once per candidate,
followed by unchanged S1. MSA **module execution** is part of folding; preparation
of MSA/ESM inputs is outside this experiment.

`WT3 -> hard-edit compensator -> one native target recycle -> native S1`.

This is not strict WT-only prediction: candidate s_inputs are legitimate cached
input embeddings, originally obtained with candidate ESM/input encoding. Their
availability and excluded preparation cost must be disclosed. Candidate final
C4 s/z are forbidden in training/inference inputs. During preparation only,
extract s_inputs from archived files, discard final states and write a separate
input-only cache. Cold C4 replay may read target final states solely as audit
references; those references do not enter the adapted path.

Mini public FP32 v0.5.0 checkpoint remains frozen, including native last recycle
and S1. Zero-initialized residual heads reproduce unadapted WT3→Target1 at
initialization. No input/single/pair oracle at the decoder. Ordinary no-edit
returns the original WT prefix exactly. Prefix and RNG are read-only and each
candidate starts independently. No nonlinear activation replacement, low-rank
constraint, differential attention, LoRA or optimizer search.

Compensator: width256; normalize/project WT3 single and mutation-anchored
WT3 pair row/column; broadcast target-minus-original learned hard-AA embedding
and a mutation-site flag. Two residual node FFNs (expansion4). Linear dense
single residual; chunked dense pair residual from normalized WT3 pair content
and left/right node projections through width128 SiLU and a zero output head.
No candidate s_inputs enter the compensator: they enter only the native path.
Pair chunk16, fixed serial candidate shape. Actual parameter count is audited.

## Data, optimization and exposure

Reuse the prior multireference 24-parent / 48-site archive and n15 split without
selection: 15 TRAIN parents /27 sites /513 hard mutants; three same-parent
held sites; nine held parents /18 sites. All are development data, not a fresh
confirmation or a proof of distant-homology exclusion. Keep whole4PT4 held and
protected Y84/N25/S34. Existing6ZRW stress remains;6UFE92 is unavailable here.

Two fresh seeds272001/272003; **32 exposures per AA/site**, 304 visits/site,
27×304 = **8,208 updates per seed**, two distinct cyclic candidates/update.
Same sorted-site round robin and candidate order as prior n15. This is a new
bounded pilot, not convergence or an extension of old checkpoints. Save at
0,4,104,8,208; terminal is primary. No best-checkpoint selection or failed-seed
replacement. Infrastructure limit6h/run; failures retained, not interpreted as
scientific failure unless the intended computation completed.

AdamW lr1e-4, wd1e-4, eps1e-8, global norm clip1, no scheduler. Unchanged loss:
properly aligned all-heavy coordinate MSE +.25 CA-distance MSE +.01 severe
clash +.01 checked chirality. Average two candidate losses; training noise230201,
evaluate230201/230211. No latent/candidate-ranking/difference loss. Teacher
geometry may conflict with penalties; report both separately.

## Integrity and candidate correspondence

Local tests require cached initialization/split RNG parity to existing native
code, preserved state ownership, exact zero/no-edit, global correction and
gradients through one frozen native update. Native preflight must recover all
24 archived WT final states and all912 candidate C4 final states from cached
inputs, then replay their two-noise coordinates bitwise. Target split3+1 parity
is checked during those audits. Store only WT3 prefixes and candidate inputs.
Any failure stops before training; no tolerance relaxation after outcomes.

Two fresh adapters must reproduce unadapted continuation bitwise at step0.
The first backward should reach the two zero output heads; upstream gradients
are expected to be zero until those heads update. A second dry update must
reach AA and relation branches. Dry optimizations are discarded. Frozen native
parameters must receive no gradients or changes. Verify candidate order/cache
immutability, no-edit replay, and continuation replay at terminal.

At every checkpoint, decode all48 sites/19AA/two noises, including TRAIN, without
a latent gate. Conditions: correct edit; adapter disabled; one fixed wrong edit.
Wrong edits use the existing hash-cycle derangement per site, fixed before
fitting and shared across seeds/noises/checkpoints. Only the adapter query is
changed; native target inputs, chemistry, masks and noise remain actual. Thus
disabled/wrong branches still contain hard-AA information. This measures the
added adapter's correct correspondence, not the importance of all AA information.
Disabled results are immutable and may be replayed once and reused. At step0
zero heads make correct/wrong identical to disabled; verify before reusing.

## Evaluation and costs

Independent coordinate scoring, roles separated, parent-equal summaries:
centered19AA CA-distance response RMSE/NMSE; mean response; AA/CA lDDT;
same-noise and two-noise-mean Spearman, Top1/3/5, score MAE; old choice/new Exact
regret and Exact self-regret; parent median/worst and individual high-cost choices;
local RMSD P95/P99/max/>1A; absolute geometry and both directions of transitions.
Retain continuous signed volumes. Compare correct to disabled and wrong on both
TRAIN and held parents, with paired parent descriptive bootstrap intervals.
Reference-only and Exact remain additional references. Any gains must jointly
consider response, correspondence, geometry/tails and risk, not just one mean.

Time matched cached-input folding workloads, after identical warmup and
synchronization: cold19×C4+S1; WT C4 capture once +19×(unadapted lastcycle+S1);
WT capture once +19×(adapter+lastcycle+S1). Include native initialization, copies,
adapter, RNG handling and decoder-cache construction; separate disk/scoring.
MSA/ESM preparation, cold model load and output scoring are explicitly excluded.
Report concurrency, warm/cold reference costs and peak GPU allocation. Training
is not speed evidence. No claim of full pipeline speedup or biological truth.

Decision: train correspondence absent -> fit/optimization unresolved; present
only on TRAIN -> transfer unresolved; held correct better than disabled/wrong
but tails degrade -> tradeoff, no promotion; joint held quality and folding
cost improvement -> candidate for new independent confirmation only. No automatic
new prefix length, mixing coefficients, rank search or extra steps.
