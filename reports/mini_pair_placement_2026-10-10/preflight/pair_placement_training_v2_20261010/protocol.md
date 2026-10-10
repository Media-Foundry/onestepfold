# Mini pair adaptation placement: early editable blocks, frozen native suffix

This is a new process/representation comparison after the closed reference-anchor
trial and the six-device training audit. It does not reopen their runs. The
remaining quality gap and the fixed-single/oracle-pair evidence are unchanged.

## Question and comparison

Does placing the same amount of trainable pair computation before the frozen
native global processing produce more useful candidate-specific features than
adapting the final two blocks?

Late: the established anchored Mini pair blocks14/15, with the actual candidate
block13 boundary. Early: anchored Mini pair blocks0/1, with the actual candidate
input to block0, followed by frozen native pair blocks2..15. Indices are zero
based. Both use the same node/edit injection attached immediately before their
two editable blocks. Trainable parameter count must equal1,315,332; node/edit
initialization must match per seed. Each arm copies the native weights from its
own true position and must initially reproduce the same unadapted candidate z.

The late frozen prefix is already available as an exact cache. The early frozen
suffix depends on adapted states and must execute and transmit input gradients.
It cannot be detached or claimed free. Early placement changes computational
depth and use of native priors, not only parameter count. Results describe the
whole placement intervention, not a proof of one layer's unique causal role.

## Fixed inputs, labels and reference branch

Reuse Mini v0.5.0, original prepared candidate inputs/chemistry, frozen WT3,
unadapted candidate B_inputs/B_s/B_z and target final pair labels. Capture the
candidate pre-block0 boundary by replaying its original one native recycle with
the saved RNG; verify B and the existing block13 boundary bitwise. Capture24
reference boundaries similarly. No ESM/MSA/feature preparation and no new mutant
C4 teacher. Native MSAModule within the already-defined recycle still executes.
It is distinct from upstream MSA preparation.

The main prediction input includes only that candidate's own legal states,
reference states, site and hard AA identities. B_inputs and B_s pass to S1 by
identity and never change. Target intermediate/final states are labels only.
Reference subtraction uses the same trainable path as the candidate, including
the frozen suffix input derivative; references are read-only. No-edit bypass,
candidate order/subset isolation, stale anchor checks and fixed native-weight
hashes remain required. Frozen continuation is runtime-owned, reconstructed from
the pinned native checkpoint and separately hashed, outside optimizer parameters.

## Engineering gate before learning

Use focused CPU tests for exact initialization, matched parameter budget,
unchanged inputs/single/native weights, candidate isolation, state reconstruction,
and finite-difference/joint-versus-streaming reference gradients through the
frozen suffix. Native checks cover all912candidate boundaries and24references,
both initializations and both placements, with exact baseline outputs. Any
failure is retained and no scientific fitting starts until diagnosed.

The new early path must also pass a serial/six-rank gradient and AdamW-state
comparison at fixed TRAIN inputs before the exact site-parallel trainer is
used. Compare two disposable updates from the same initialization, including
the complete moments; bytewise equality remains the criterion. This gate does
not add updates to the scientific runs or select a model by held quality.

## Locked learning comparison

Two placements × seeds272001/272003, all from scratch. Same15TRAIN references,
27sites,513mutants, frozen original TRAIN q values and full-TRAIN objective as
the closed anchor trial.128 full-gradient AdamW updates; lr1e-4, wd1e-4,
eps1e-8, betas(.9,.999), clip1. Same canonical per-site/candidate order, FP32
within-site gradients and CPU FP64 across-site mean. Six workers split sites
5/5/5/4/4/4; only root steps and broadcasts. No new loss, hint, rank constraint,
S1 backward, noise augmentation, decoder adaptation or candidate-dependent gate.

Save0/32/128 and use128 as primary. The same four runs and budgets are fixed
before any quality results. The new late endpoints must be compared with the
historical anchor states; differences must be explained, not hidden. No automatic
extension, checkpoint selection, layer-position grid, seed selection or scaling
search. A finite controller caps the complete experiment at six hours after
training starts, records any incomplete run and never restarts on observer expiry.

## Evaluation and decisions

At every fixed node evaluate all48existing sites using the full candidate path,
with correct assignment and the locked terminal wrong-assignment intervention.
Separate TRAIN, same-protein new sites and nine reused development proteins.
All fixed nodes decode regardless of NMSE. Report full/common/AA residual error,
direction and energy; decoded AA response, full structure fidelity, raw old-select/
new-evaluate regret, per-protein tails and geometric transitions/severity. Retain
6ZRW P80 and2EBE A30/E47 as known regressions, not individual tuning targets.
Exact, unadapted and fixed-single oracle pair references remain distinct.

Better TRAIN fitting alone does not establish transfer. Better averaged response
with worse high-cost selection or geometry is a tradeoff, not promotion. Both
seeds must support a quality benefit before any future expansion is considered;
final confirmation still requires untouched protein families.

Count boundary construction, reference work, all frozen suffix forwards and
input backwards, candidate updates, S1 evaluations and verification separately.
Measure actual cold/prepared-cache and warm candidate work before any speed
claim. The earlier4.16× training and2.7× folding multipliers do not transfer to
this different graph. No practical accelerator is established by initialization
identity, fitting, or a new isolated timing alone.
