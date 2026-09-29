# Raw-PDB source extension for remaining long-chain slots

2026-09-30. User requested expanding sources to complete32 before validation.
StageB pre-cutoff TRAIN extension v1 yielded new medium candidates but no supported
long candidates. Preserve that result; expand the source universe, not the isolation
rule or support criteria. No folding scores have been generated or used.

Read `catalog_v1/monomer_candidates.jsonl.gz`, only release<=2021-09-30, standard
20-amino-acid construct sequence,512–1024 residues, one-model X-ray/EM/neutron
record, author-determined assembly. Do not open temporal/test coordinates. Retain
previous qualified27 plus the first qualified medium extension (when available).
Exclude previous screened217 and StageB-extension148 groups; retain all historical
development group/PDB/accession exclusions. Require SIFTS and no accession shared
with the retained panel. Collapse identical sequences to lowest resolution then
PDB/chain/assembly ID before hash ordering. Different PDB IDs alone do not establish
independence. This is a new validation source, not a retrospective TRAIN relabel.

Rank SHA256(`anchored-raw-extension-v2:20260930:`+group_id), take at most256 new
long-chain groups before sequence search. Same calibrated BLAST21,070-reference
database, same significance/identity/coverage/domain rule; symmetric pair screening
against retained panel and between all new candidates at the fixed development
dbsize. No parameter changes to obtain a desired count.

Directly materialize the passing raw mmCIF monomer into the original atom37 schema,
then rematerialize a second time and require exact arrays. Record raw hashes,
source chain/assembly, actual GT masks and schema/protocol. Require complete observed
backbone, unmodified standard residues, no chain breaks or observed SG<2.3A. Apply
the same native chemical preflight including explicit covalent/disulfide/cyclic
source links. Choose first four fully qualified non-near/non-shared-accession records
in frozen order. Source failures are recorded, never repaired to pass the screen.

If four cannot be found, report the deficiency without relaxing rules. All32 candidate
identities and GT/native packets must be locked before any GPU validation. Geometry
and original32x3 evaluation protocol remain unchanged; no new training or design.
