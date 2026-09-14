# Archived research scope: glycan prototype

The primary project direction moved to one-step protein multi-chain folding on
2026-09-13. This document remains as the design record for the earlier glycan
ensemble experiment; see [protein_direction.md](protein_direction.md) for the
active scope.

Primary question:

> Can a fast joint conformational model reliably design the probability of a
> target geometric event on unseen legal glycan edits?

The first system keeps residue count, linkage positions, branch topology, and
anomeric state fixed. Only an allow-listed set of monosaccharide substitutions
is permitted. Coordinates are reconstructed from templates after predicting a
selected vector of glycosidic torsions; this does not claim to model every ring
flip or sugar deformation.

The comparison ladder is intentional:

1. Direct event predictor `h(G, q)`.
2. Independent marginal angle models.
3. Joint periodic density model.
4. One-step joint generator under the same representation and budget.
5. Enumeration/local search versus gradient-guided legal edits.

SweetFold may be evaluated as a structure proposal baseline. It is not treated
as a calibrated equilibrium sampler without a separate calibration study.
