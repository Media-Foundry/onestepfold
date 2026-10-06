# WT prefix reuse — launch and integrity status, 2026-10-06

This is a new bounded no-training experiment following native budget closure
7d9206cf. C4 remains default; the two tested mixed paths are WT2→Target2 and
WT3→Target1. Cold C2/C4 are rerun as matched references. The prior eight DEV
proteins and separate 2V66 stress parent are unchanged.

[Protocol](mini_prefix_reuse_v1.md) fixes the full scoring and timing contract.
Each warm method pays once for full WT preparation/C4/snapshots/four-noise
screening, plus every candidate's own native features, live ESM, continuation,
decoder, scoring and coordinate writes. Only token s/z and explicit execution
RNG are reused; target chemistry and the final full conditioning belong to the
actual mixed path. No oracle target s, new training or candidate-specific tuning.

## Initial integrity stop and correction

`prefix_reuse_v1_20261006`, PID2146050, began 08:45:14 UTC and stopped after80.025s
at the pre-screen integrity gate. The assertion that eval/no-dropout trunk does
not advance RNG was false. No screening or selection quality was evaluated.
The original source archive, hashes, controller terminal state and logs remain
preserved; this is an implementation-gate stop, not a method quality failure.

The installed native MSAModule calls MSA sampling in evaluation. Its sampling
utility draws the sample size using torch.randint, even when that size has only
one possible value. Merely resetting a seed cannot represent an arbitrary saved
cycle boundary. The corrected wrapper captures exact Python, NumPy, torch CPU
and initialized-device RNG state with each prefix, then restores it after target
initialization and before remaining recycle updates. It checks final RNG state
and all returned conditioning tensors against unsplit native execution. Hooks
record which native modules advance RNG during each integrity case.

Eight local tests pass, including original bridge parity, target reinjection,
cache immutability/order independence, invalid-state rejection and two stochastic
split-recovery tests with interleaved unrelated RNG consumption. The previous
native source snapshot's 1,074 files match byte-for-byte. Seven new experiment
files bring the frozen source set to1,081. The public model, original full-recycle
function and old scoring implementations are unchanged.

## Corrected launch

`prefix_reuse_v1b_20261006`, PID2147283, began **08:51:11 UTC / 16:51:11 HKT**.
Root: `/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/prefix_reuse_v1b_20261006`.
Local metadata mirror: `/home/husrcf/Code/onestepfold_runtime/prefix_reuse_v1b_20261006`.

Controller stages: prepare → four-worker integrity gate → four-worker inference →
CPU fidelity/selection scoring → collection → independent audit → summary.
Integrity covers18 inputs (each parent's WT and a real target), two boundaries
each. Target prefixes exist only inside this audit. Screen expected counts:
2,763 conditioning calls,6,246 recycles,11,052 S1 evaluations. Reused WT baseline
outputs produce11,088 output records. C4 archive replay2,772 plus36 source-WT
replays. Four real methods,693 unique sequences; no new independent proteins.

This document is a launch record, not a quality or speed result. The terminal
execution.json and independent_audit.json must both complete before final claims.
The controller stops on integrity, execution or accounting failure; no automatic
method search follows. Initial gate-stop artifacts are archived alongside this
launch so the execution history remains explicit.

## Integrity gate passed; screening running

All four gate workers completed:18 inputs,18 zero-state C4 comparisons and36
segment recoveries are bitwise identical to native, including final RNG state.
Module traces locate RNG advancement in MSAModule (four calls per native C4).
Shared prefix tensors remain unchanged. The controller advanced to inference;
there are no terminal quality or timing conclusions yet. Startup evidence is in
[the artifact directory](../reports/mini_prefix_reuse_2026-10-06/).
