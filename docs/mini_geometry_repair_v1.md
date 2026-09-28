# Restrained hard-output geometry repair v1 — locked 2026-09-29

Scope: development/regression experiment on exactly the archived 33 sequences ×
noises 211, 200003, 200009 (99 structures). Prior batch remains closed. No folding,
new substitutions, training, altered acceptance thresholds, or candidate selection.

## Fixed intervention

OpenMM Amber ff14SB + GBn2 implicit solvent, NoCutoff, no bond constraints;
CPU platform, two threads per process. No MD, contact objective or geometry-gate
penalties enter minimization. All original heavy atoms have a harmonic restraint
`0.5*k*|x-x_raw|^2`, k=1000 kJ mol^-1 nm^-2 (10 kJ mol^-1 Å^-2).
One minimization, maximum 2000 L-BFGS iterations, tolerance 10 kJ mol^-1 nm^-1.
Record force RMS and convergence/budget status, not merely absence of exceptions.

Preserve archived heavy-atom identities and covalent graph. PDBFixer may add
missing terminal OXT and hydrogens only; missing internal heavy atoms, altered
original-heavy bonds or ambiguous identities cause an explicit case failure.
Preparation uses seed 6271 and pH 7; record actual protonation variants and added
atoms. Restore original heavy coordinates exactly after preparation and before
minimization. Auxiliary atoms remain in full output, but all old metrics use the
original heavy-atom inventory. No automatic disulfide inference or residue repair.
Force-field/protonation assumptions are a baseline, not experimental truth.

## Frozen evaluation

Keep raw and repaired coordinates and metrics. Evaluate with unchanged
GeometryRules, task, geometry terms and graph-distance exclusions. Report severe
pair identities before/after, not just maximum penetration. Repaired candidates
are compared to the repaired parent under each matched noise, using the original
utility_decision/hard_accept. Both confirmation seeds must pass separately.

Structure preservation: raw-frame CA RMS displacement <=1 Å AND original-heavy
RMS displacement <=2 Å; also report aligned CA RMSD, maximum displacement and
CA pair-distance RMS change. These NEW intervention limits are pilot choices,
not retroactive changes to the old gate. Raw-frame bounds avoid hiding local
movement through superposition. Report geometry-only, preservation-only and
joint counts separately. Per-candidate utility/full acceptance is accompanied by
preservation of both candidate and parent. No best-of-parameter/noise selection.

Failed preparation/minimization/nonfinite cases remain failures in denominators;
no raw fallback counted as repaired. Use a uniform 1800-second per-case ceiling,
record timeout as failure. No candidate-specific retries or parameter changes.
Resume may skip only complete hash-bound case records. The batch ends after all99.

Artifacts bind input report/candidate/coordinate/topology hashes, protocol and
source hashes, package versions and force-field XML hashes. Full auxiliary atom
coordinates retained for audit. Unit tests precede launch. Preflight may check
API/mapping compatibility, but never tune settings against geometry/task outcomes.

Interpretation: repair success is not an independent design validation, not a
one-step differentiable oracle, and not evidence of binding. Any eventual use of
repaired forward outputs requires a separately specified gradient path. No
cross-sequence comparison of force-field energy as a design ranking.

References: [OpenMM guide](https://docs.openmm.org/latest/userguide/),
[PDBFixer manual](https://github.com/openmm/pdbfixer/blob/master/Manual.html).
