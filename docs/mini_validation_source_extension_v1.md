# Source extension for the32-protein validation panel

2026-09-30 user explicitly selected source expansion rather than reducing the panel.
Retain the27 qualified candidates from `caf00fa4`; fill one256–511 and four512–1024
slots. No short-chain substitutions for long-chain slots, no new prediction-based
selection. Geometry frozen2aa87043; original32x3 raw/mean/tail protocol unchanged.

Expand beyond the29.7k prepared representative packets to the existing full
pre-cutoff TRAIN manifest and its StageB structural index. Only rows present in
`splits_v1/train.jsonl.gz`, release<=2021-09-30, standard sequence and256–1024
residues are eligible. Do not open frozen temporal/test coordinates. Alternative
experimental representatives of a sequence may be considered using source metadata
only; choose lowest resolution then sample_id among complete-backbone, unmodified,
unbroken single-chain records. Missing sidechains remain masked.

Keep all v1 development group/PDB/SIFTS exclusions and the calibrated v2 BLAST
rule exactly. Also exclude the entire previously screened217 groups from new draws;
no retrying failed groups with another conformer to improve model outcomes. Require
source SIFTS mapping, no shared accession with historical exclusions or retained27.
Rank new groups by SHA256(`anchored-extension-v1:20260930:`+group_id); pre-screen
at most128 groups in each deficient stratum. Capture all eligibility counts and
source hashes before search. No homology threshold or geometry parameter retuning.

BLAST against the frozen21,070 development-reference database uses identical
calibrated options. Candidate/panel search contains new candidates plus retained27,
uses the same fixed development-residue `dbsize`, and excludes on a qualifying
hit in either direction. Greedily add source/chemistry-qualified candidates in
the fixed order until8 in each stratum. Sharing an accession is independently
disallowed. Fewer than32 means report deficiency, not loosen isolation.

For new sequences passing sequence isolation, extract stored experimental GT from
the recorded StageB tar, verify raw mmCIF hash and independently rematerialize
atom37 arrays using the original source chain/assembly. Require exact array replay.
Run the same native chemical preflight: original graph, reference replay, complete
backbone/masks, observed SG contacts, explicit source covalent/disulfide/cyclic
connections. Scope failures are recorded before formal panel lock, never replaced
using folding/solver results. No ESMC extraction is required for this data preparation.

Keep existing training manifests immutable. The new validation reservation list
must be excluded from future correction training. Final32 metadata/GT/native
packet hashes and software/runtime lock precede inference. This extension changes
only sample sources; it does not establish Mini pretraining independence.
