# Necessary Cα-span feasibility audit before a fixed-backbone method

2026-09-30. Previous fitted-start combination is closed after CA quality regression.
Before implementing hard Cα preservation, use only saved C4 artifacts to determine
whether each original adjacent-CA distance is compatible with the frozen chemical
CA-C/N-CA lengths and peptide residual ranges. No predictions, fitting, solver,
training, revised gate, alternate weights, or independent32 access.

For A=CA_i,B=C_i,C=N_next,D=CA_next, lengths a,b,c and angle cosines u,v,q=cos(omega):

    |D-A|² = a²+b²+c²−2abu−2bcv+2ac(uv−sqrt(1−u²)sqrt(1−v²)q).

Analytically certify monotonicity on each tested box before computing extrema.
Compare the old acceptance box (including its existing1e−6 residual slack) and the
calibrated zero-penalty box (q95trans,old half-tolerancescis) SEPARATELY. Neither
changes old acceptance. Audit each branch and their union. A point outside the
union cannot meet those local constraints while keeping both Cα positions fixed;
a point inside proves nothing about global chain, carbonyl, chirality or clashes.
Use1e−6Å numerical margin in violation classification, not as a new geometry gate.
Floating-point interval arithmetic is not a formal outward-rounded certificate.

Use all14supported C4 inputs and retain2unsupported prediction slots for3CR6.
Inspect raw, calibrated-zero final, fitted start/final, and experimental GT as a
separate reference. Current-model raw-selected branches apply to model outputs;
GT-selected branches apply only to GT reference checks. Alternative-branch support
is descriptive, not an automatic branch-change rule or use of GT to fix predictions.
Check coordinate-identity formula for every stage and preservation of CA-C/N-CA
lengths for projected/model-chemistry outputs. The original local constructor
defines these invariant lengths; raw/GT may have other internal lengths.

Report edge and protein-instance counts, gaps, worst identities, and a conservative
necessary CA-RMS movement lower bound obtained from disjoint violated edges. Never
sum shared endpoint costs as independent. Lower bounds do not establish an
achievable movement or explain all observed solver displacement/GT losses.

Stop after this read-only audit. Reject universal exact-CA anchoring if any supported
input violates the necessary old-gate bounds; retain per-case details. If all pass,
that is only permission to study feasibility, not acceptance of a new solver.
