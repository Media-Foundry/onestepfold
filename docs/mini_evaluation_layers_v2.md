# Evaluation roles, revision 2 — 2026-09-30

Recorded after c6a1d98f and BEFORE the selected S1/S2/S5 diagnostic starts.
This changes interpretation and reporting, not solver objectives, historical
outcomes or any already-observed trial's primary endpoint.

The legacy joint check combines basic geometry, stricter checked chirality,
raw displacement budgets and maximum connection residual windows. Its connection
windows reject every protein in both experimental calibration halves. It is a
historical strict check, not a universal chemical-validity criterion or a sole
method-development veto. Existing historical `joint_pass` values remain intact.
New reports call this role `legacy_joint_pass`; for raw predictions without a
repair displacement contract it is not applicable, rather than artificially
passing displacement by comparison with themselves.

## Four separate layers

1. Implementation/data: identities, topology, masks, finite output, replay,
   hashes, complete denominators and failures.
2. Chemistry/connections: actual severe overlaps and atom identities, checked
   chirality, bond/peptide errors, continuous connection residuals, type-specific
   reference-band exceedance counts/fractions/positions, extreme individual
   values and cis/trans branch mismatches. No new chemical pass flag is defined.
3. Accuracy/preservation: experimental GT AA/Cα-lDDT and paired degradation,
   aligned Cα RMSD, and where applicable original raw displacement budgets
   (Cα RMS≤1 Å, heavy RMS≤2 Å), with local extreme displacements separately.
4. Task/computation: hard mutation utility across fixed independent noises,
   gradients through the actual output function, number of model calls and
   total latency. These remain unestablished by a raw-forward diagnostic.

## Connection reporting, not a replacement hard window

Use the already-frozen 32-protein calibration's equal-protein q95/q99 bands.
Keep following-Pro and other connections separate. Bands apply only to trans
connections; cis is unsupported and reported separately, never silently passed.
Report signed residual vectors, RMS, quantiles, maxima and residue positions.
The actual nearest branch and experimental-GT branch mismatch are separate from
residuals measured against the S1-selected branch. Closeness to a branch does
not establish that it is the correct branch.

Quantile exceedances are descriptive, not validated chemical abnormalities.
Do not turn q99 into an all-links-must-pass rule; chain length changes that
event's probability. Do not infer Z scores, hydrogen-inclusive clashscores or
universal severe-angle cutoffs from these data. Establishing new serious-angle
or length thresholds requires a separate prospective calibration protocol.
Meanwhile report full residuals and worst locations so a large individual
failure cannot disappear in a mean. Existing severe overlap (<1 Å), checked
wrong stereocentres, nonfinite/mapping failures and actual chain breaks are not
waived by the role change. Basic collision rules remain pilot diagnostics, not
complete physical validation.

## Locked studies and future decisions

The old independent32 failure and fresh8 outcomes remain unchanged. Fresh8 is
complete: small paired mean improvement was reproduced, but both 2B0A instances
retain real geometry/displacement failures. This is not merely a narrow-window
rejection. The calibration/verification sources and fresh8 are now development
information, not new independent validation data.

A future main-improvement plus noninferiority design may replace the requirement
that every metric's mean be strictly positive. Its margins must be justified and
locked before new results; NONE are selected here. No current accuracy loss is
reclassified as lossless. No new aggregate deployment acceptance is introduced.
