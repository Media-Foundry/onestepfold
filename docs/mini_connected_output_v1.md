# Connected chemical output v1: bounded representation probe

Authorized 2026-09-29 after closure of raw-gradient plus generic repair. No training,
new sequence search, relaxation or modification of Mini weights. This is a fixed-graph,
parameter-free differentiable output prototype, not a deployment claim.

First test: reconstruct a single standard-amino-acid chain using reference intrabond
lengths/angles and proper residue frames/side-chain rotations. Unlike the old independent
residue projection, connect successive N/CA/C triples using measured raw phi/psi and
fixed trans omega. Peptide C-N length is 1.329 A (1.341 before PRO); cos(CA-C-N)=-0.4473,
cos(C-N-CA)=-0.5203, from AlphaFold residue_constants:
https://github.com/google-deepmind/alphafold/blob/main/alphafold/common/residue_constants.py
These are chosen ideal constants, not a claim all native peptides have identical geometry.
Use native Protenix chemical references, not experimental targets or repaired coordinates.
Orient internal carbonyl O opposite the next N around CA-C; terminal O/OXT keep extracted phase.

Scope: one contiguous chain, standard residues, terminal OXT allowed, no crosslinks. Cis peptides are
not represented in v1; report raw cis-like omega counts rather than silently asserting
universal coverage. Degenerate axes/dihedrals reject the case; no hidden fallback in the
connected path. Existing residue adapter fallback counters must all be zero. Local
proper transforms preserve reference stereochemistry including branched/ring groups;
verify CA and ILE/THR side-chain signed volumes. Do not assert general steric validity.

Bounded archived regression panel: parent only, controlled_s1 and native_s5, seeds
211/200003/200009 (six fixed inputs). All were already used for development. Native S5
is a second input condition, not a matched-noise causal contrast. Compare raw, old
independent-residue projection, and connected reconstruction. No held-out/GT read.
Use CPU on DiamondHill, no folding forward or GPU allocation. Save immutable source,
input, chemical reference and output hashes and actual arrays. Do not modify old archives.

Before real data: admissible-chain reconstruction/idempotence, proper rigid equivariance,
all intrabond lengths and chirality preservation, exact C-N/angles/trans omega, deterministic
output, degenerate rejection, FP64 gradcheck of the actual composed raw-to-output function.

Per real input: unchanged GeometryRules, all named severe pairs, raw-frame and aligned
CA displacement, heavy displacement, CA distance change, task proxy (descriptive only),
CA/side-chain stereochemistry, peptide planarity, finite backward and a fixed random-direction
FP64 check of this new output map only. This is not a new end-to-end sequence audit.
Existing preservation limits CA RMS<=1 A/heavy RMS<=2 A are unchanged. Also report aligned
CA RMS to separate rigid placement from folding deformation. Any preservation failure
blocks extending this direct reconstruction; any geometry failure blocks deployment.
No changes to thresholds, anchor placement, torsion extraction, constants or fitting after
seeing this panel; no optimization to rescue failures. Sequential drift is an expected risk
and a useful negative result. If blocked, report and stop; next architecture needs another
explicit decision. An eventual learned geometry-aware module requires independent training
structures and validation parents; these six outputs are regression cases only.

Preflight amendment before any output evaluation: the native parent inventory includes
terminal OXT. The first locked attempt rejected it during construction, with no output
produced. Keep that failed root intact. v1.1 supports OXT only on the last residue via
the unchanged proper local reconstruction; internal OXT still rejects. No constants,
cases, thresholds or results influenced this compatibility amendment.
