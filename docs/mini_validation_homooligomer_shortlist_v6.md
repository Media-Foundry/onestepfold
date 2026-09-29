# Homooligomer chain qualification, before panel admission

2026-09-30. Full-source discovery yields125 isolated source-supported groups,
all from contextual assemblies. Pending user's explicit source-context choice,
perform CPU-only qualification of up to8 pairwise-independent homooligomer chain
candidates. Not an automatic change to the monomer validation panel.

Require author assembly, zero nucleic-acid/other-polymer chain instances, all
protein source chains have the exact same construct sequence, protein instance
count>1. Explicit covalent/disulfide connections involving target chain remain
unsupported except ordinary adjacent peptide C-N. Retain first qualifying variant
in locked resolution/PDB/sourcechain/assembly order per group. Group hash order
unchanged from v5. Greedily shortlist first8 with no shared accession or calibrated
sequence conflict with retained28 or each other, before native preflight.

Run unchanged native graph/reference/GT mapping checks. Retain every failure.
No model/repair outputs or threshold changes. Candidate labels include source
assembly composition; single-chain experimental GT is not proof of autonomous
monomer folding. Admission, if authorized, reserves first4 passing shortlisted
groups, keeps retained28 unchanged, and labels this source subgroup separately in
all downstream reporting. No temporal-test coordinate, trimming or imputation.

## User authorization

User explicitly confirmed: “允许，优先同源多聚体中的完整单链”. Source-context
admission is therefore authorized. Keep biological-assembly context visible and
all other requirements fixed; no additional approval required after preflight.
