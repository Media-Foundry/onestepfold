# GT coordinate-term ablation: training started

The [fixed single-factor protocol](mini_folding_coordinate_ablation_v1.md) is now
implemented and running on HPC3. This is still C4/S1/K1 folding, with frozen ESM2
and Pairformer. No ESMC switch, repair module, design task or additional candidate
has been added. There is no trained-quality result yet.

|Job|Work|Status at startup observation|
|---|---|---|
|662468|copy/provenance/contract preparation|COMPLETED0:0,6s|
|662469|GPU preflight and objective comparison|COMPLETED0:0,51s|
|662470|single TRAIN423 candidate,2048 updates|RUNNING|
|662471|terminal execution audit|afterok662470|

Root: `/data/user/shuang886/Folding/folding_coordinate_ablation_v1_20260930`.
Lock SHA256: `81ee94ffddaacf4d9881d01d4e2b98d308ee151d20a0838e520aa1c815f684ea`.
One H100 allocation under `acd_u`;3-hour cap, no automatic requeue. Preparation
and audit hide the otherwise unused GPU required by that partition. The prior
matched control took about104 minutes; this is a planning reference, not an ETA
guarantee for the new run.

## What is held fixed

All172 original frozen code files are byte-identical in the new private root.
The unchanged training loop is reused. A contract guard compares every original
scientific field, permitting only selection of its existing expanded arm and
`weights.coordinate:0.01→0`. It rejects hidden changes to data/order/noise,
optimizer, scope or other weights. Three focused contract/schedule/loader tests
pass, including deliberately invalid parameter, noise, membership and LR changes.

The candidate starts from the retained parent, not the previous TRAIN423 terminal.
Same423 training groups,8192 exposure records,2048 updates, accumulation4, optimizer
reset, LR schedule, gradient clipping and288 selected diffusion tensors. All other
weights remain:

|Term|Weight|
|---|---:|
|Experimental-GT aligned coordinate|0|
|Experimental-GT smooth-lDDT|1|
|Experimental-GT bonds|1.505408125612628|
|Checked chirality|1|
|Clash|0.0006600251156855778|
|Native S2 auxiliary preservation|0.025476389066842815|

Coordinate loss is still computed and logged. Experimental GT remains the source
of local distance and bond supervision; native S2 remains a synthetic auxiliary.

## Actual GPU preflight and training startup

On52/968-residue original-TRAIN engineering examples, all288 selected gradients
are finite/nonzero, parameters remain unchanged, public and parent replays pass.
The parent outputs match saved retained-model predictions bitwise. Unweighted
loss terms from separate grad/no-grad loss evaluations are exactly equal; the old
weighted total matches the original control preflight.

|Length|Old total|Coordinate-zero total|Removed contribution|Gradient norm|
|---|---:|---:|---:|---:|
|52|0.185917729|0.145554586|0.040363143|2.051267|
|968|0.359004737|0.288466508|0.070538229|1.927222|

Peak preflight allocation is16,763,567,616 bytes. An observer temporarily wraps the
loss function only during preflight, returns its original terms unchanged, then
restores it. The separate training process uses the unmodified original function.

At actual training startup, all64 initial probe coordinate hashes match the frozen
control bitwise. The first four exposures, before the first optimizer step, have
identical unweighted loss terms and the expected total-loss difference. This
confirms the intended change in the real training path; it is not evidence that
the learned candidate will improve quality.

## Remaining work

Complete training and independent audit without altering this lock. Implement the
fixed-terminal comparison with cached original references; only the candidate's
910 predictions are new, plus engineering checks whose exact count must be locked
before evaluation submission. The existing VAL32 is now development validation,
not fresh confirmation. No default-model promotion is supported by a startup
check or training loss decrease.

Artifacts: `reports/mini_folding_coordinate_ablation_2026-09-30/` contains the
launcher, submission, preparation, preflight, release and startup observations.
