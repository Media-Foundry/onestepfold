# Mini multi-reference editor preparation — 2026-10-07

**Preparation only; no new training or S1/ESM/C4 execution.**

[Protocol](../../docs/mini_reference_editor_multiref_v1.md) defines the planned
3/15-reference × workspace/direct × two-seed comparison. The direct control and
runner remain to be implemented and audited before training.

- `archive_verification.json`: fresh DiamondHill read-only SHA-256 and size check
  of all 2,808 files in the existing teacher manifest; zero mismatches, 9,721,483,922
  bytes. Metadata hashes also match the locally committed archive metadata.
- `plan.json`: source commit, teacher hashes, 24 parent records, 48 site records,
  role by dataset size, original-AA coverage, eight run schedules and training
  decode budget. Historical source split is preserved as metadata, not overwritten.
- `sites.csv`: compact auditable site assignment table; both zero-based and
  one-based positions, WT AA, candidate alphabet and archive path prefix.

Data derive solely from `reports/mini_factor_student_pilot_2026-10-02/`.
The original 16-train/8-validation archive becomes 15 training parents after
holding out entire 4PT4. Three additional site exclusions preserve Y84/N25/S34.
The large training set has 27 sites / 513 mutants, same-protein holdout 3/57,
common nine held proteins 18/342. All are development data. The n3 subset is
1W53/2DP9/1DZR, selected by smallest parent index per original length stratum.

Assertions checked: all paths for 24 WT and 912 mutant packets exist in the
manifest; metadata hashes agree; parent components are distinct under the
historical component definition; split memberships, 19-AA alphabets, counts and
77,824-update / 155,648-training-decode arithmetic agree. Payload hashes establish
file integrity, not scientific validity, new coordinate replay or new homology
analysis. Expected direct-model parameter count is derived from the specified
module shapes, not from an implemented or trained direct model.

The completed `bef762d0` pilot is unchanged scientifically. Its serial candidate
forward retains and concatenates outputs; dense pair outputs still occupy memory
for the requested candidate count. It is not a streaming memory bound.
