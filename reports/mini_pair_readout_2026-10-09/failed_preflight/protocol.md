# Frozen Mini pair-recovery features: shared linear readout diagnostic

Locked 2026-10-09, after user authorization. This is eight new TRAIN-label fits,
not a zero-training audit or a continuation of the closed recovery experiment.
Four fixed 8208 checkpoints: pretrained/random x 272001/272003 from
pair_recovery_v1b_20261009. No checkpoint selection, new data, native recycle,
ESM/MSA preparation, architecture change, AdamW update, or S1 backward.

Freeze the entire recovery network, including final LayerNorm gamma/beta.
Capture H, the actual FP32 input to its bias-free 128->128 output layer, with
a read-only pre-hook. Original outputs must reconstruct bitwise through the
unchanged head. Readout matrix convention is R=H W, W=out.weight.T. Frozen
candidate B_inputs/B_s/B_z and target_C4_z come from the previous hashed cache.
Use FP64 E=FP64(target_z)-FP64(B_z) for linear algebra; separately check original
FP32 addition/subtraction and report any numerical discrepancy.

Full objective, with N=27, A=19, C=128:
J(W)=sum_i,a ||H_ia W-E_ia||_F^2 / (N A L_i^2 C q_i).
q_i is the original locked TRAIN site_scale_squared (including its original
floor 1.3615748444129276). No recomputation or use of held labels for weights.
This preserves uniform site/candidate exposure and within-candidate means;
concatenating pair rows without L_i^2 correction would change the objective.

Second, distinct objective: replace H_ia and E_ia with their deviations from
the nineteen-candidate mean at the same site and residue pair. Retain the same
q_i and row weights, not a new centered-energy normalization. This diagnostic
only evaluates centered latent responses; its common output is unconstrained
and is NOT decoded or presented as a complete pair predictor.

All pair rows and all channels, no subsampling. Streaming FP64 QR of weighted
augmented [H,E], row chunks 8192, then FP64 SVD of the reduced design. Fixed
rcond=1e-6 relative to its largest singular value, chosen before extraction to
avoid amplifying near-null directions of FP32 features. No tolerance/ridge sweep.
Solve a correction to the original W only in retained right-singular directions;
retain original W in discarded directions. Thus W_old remains feasible, and
the solution minimizes the objective over this declared numerical subspace.
It is not an unrestricted infinite-precision lower bound. Report every singular
value, effective rank, retained condition number, discarded energy, W norm,
old/new objectives, and projected stationarity. Do not form/invert normal
equations. AA-centered LayerNorm features have a structural null direction
when gamma is nonzero; record that relation instead of calling it collapse.

Preflight: synthetic weighted unequal-length sites, dense-SVD versus chunked-QR
agreement, rank-deficient/minimum-change behavior, centered common-offset
invariance, and head orientation/identity. Fixed real checks before label fit:
checkpoint/cache/code hashes; H-hook output equality; first TRAIN candidate of
each checkpoint replays both archived S1 noises; no parameters receive gradients.
After fitting, check all TRAIN objectives by a second direct pass (relative
tolerance 2e-8 in FP64, with 1e-10 absolute floor) and non-increase versus old W.
Report FP32 head/application errors separately, never silently change tolerance.
Original head's conditioning reconstruction is checked on all 912 candidates;
its two-noise S1 is replayed for the first candidate of every site (96/checkpoint).

TRAIN only: 15 parents,27 sites,513 candidates. Fit both heads before reading
held labels. Evaluate all 48 sites/912 candidates: TRAIN; three same-parent new
sites; nine held parents/eighteen sites separately. These remain development
data. Preserve original weighted objectives and equal-parent unweighted full,
common, centered NMSE/energy/cosine as different aggregation conventions.

Decode every full-objective fitted head, independent of latent results: actual
B_inputs/B_s, B_z+FP32(HW), actual receiver chemistry and the original two noises.
Also use the fixed next-AA donor residual (modulo the stored nineteen choices),
keeping receiver B/chemistry/noise. Compare to archived original recovery head,
disabled B, oracle_pair and Exact; no scaling, permutation or mixture search.
Centered head is latent-only. All four full heads evaluated; no winner chosen.
Report same-noise and mean-score ranking, score errors, old-select/new-Exact
regret, centered structural response, geometry conversions/severity and tails.
Keep 2EBE A30/E47 and 6ZRW, all failures and seeds. No NMSE decoder admission gate.

Four independent workers HIP0..3, with HIP4/5 available for bounded execution
checks; only HIP_VISIBLE_DEVICES selects devices. CPU QR uses 4 threads/worker.
No DP reduction or batch change. Main feature forwards: four x(513 fit+912 eval).
S1 per checkpoint: 96 original replays + 1824 full + 1824 mismatch =3744;
four pre-fit replays add8 calls, total14984. Source checkpoint and all native
parameters/reference caches must be unchanged. Runtime and memory reported,
not a new folding speed benchmark. Six-hour timeout, no automatic scientific
restart or budget extension; preserve implementation failures separately.

Interpretation: gains only in common signal do not solve AA recovery; improved
TRAIN centered fit without held improvement identifies a transfer gap in these
features. Little TRAIN gain constrains these fixed features plus a shared
linear head, not all input information or all pair architectures. A better
readout does not by itself identify AdamW, weight decay, or learning rate as
the cause. Functional gains, selection risk and geometry are separate gates.
