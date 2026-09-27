# Four-stage gate completion audit

The user explicitly confirmed the four stages on2026-09-28. This audit distinguishes
an implemented and exercised gate from a scientifically passing model. A failed
scientific gate must remain failed; it cannot be repaired by changing thresholds
or by relabeling partial gradients as complete sequence gradients.

| Requirement | Implementation/evidence | Current verification |
|---|---|---|
| Native hard-input forward equivalence | run_mini_sequence_gates.native_replay; compare native ESM, all mixed feature fields and original runner coordinates | First3 targets completed;362-residue run passed initial replay and continues |
| Full modeled sequence input path | q→softmax→native ESM2, restype/profile, reference position/charge/mask/element/name; differentiable atom-pair preprocessing;4recycles | Locally differentiable current-inventory chart; global continuity explicitly unproven |
| Numerical derivative gate | 3directions×5h, repeatability, nonzero/finite norms, adjacent-h plateau | Passed first100-residue target;8BZN S1 and194-residue control failed one or more directions; do not overwrite |
| S1/S2 same-start comparison | identical q0/noise, both50-update arms, cross-loss at0/10/20/30/40/50 | First3target pairs complete;9QR4 pair running |
| Hard sequence input rebuilding | native SampleDictToFeatures regenerated from final argmax sequence, exact hard-feature/ESM endpoints, native coordinate replay | First3target pairs complete |
| Independent noise confirmation | baseline/final hard sequences under103/107 and S1/S2,8coordinate artifacts per arm | First3target pairs complete; practical improvement not guaranteed and first target fails |
| Geometry guards | separate bond, peptide C–N, chirality and severe atom clash audit, not merely Cα proxy | Implemented/scored first target; final all-run audit pending |
| Atom-inventory boundary behavior | evaluate identical q in old/new charts at observed argmax changes, aligned Cα RMSD and loss jump | V2 implemented;8BZN observed up to0.922A; not a global continuity proof |
| Deterministic inference | explicit atom-name-keyed noise, no MC dropout, eval/frozen parameters, fixedC4/S1 orS2 | Native replay and repeated gradients tested; independent seed not expected identical |
| Artifact integrity | sequence_gate_audit validates51updates, cross-scores, logits/sequence,8coordinate sets, CPUloss replay and file hashes | First3target pairs audited locally; final8arm audit pending |
| Backups and documentation | scoped Git commits; bounded remote snapshots; local result archives | Implementation df8c8eef pushed; final audit/report pending |

The model is NOT accepted for deployment. The monomer contact proxy does not
validate an interface/binding objective. Mixed reference features are an explicit
surrogate, not physical conformers. The current map uses all20probabilities within
a native-inventory chart but remains piecewise at atom-count/name changes. No
claim of a globally smooth full all-atom sequence map is warranted.

Remaining work for the current implementation batch: finish the already-running
9QR4 arms, audit every output/coordinate set, render the aggregate results, record
all failing gates and remaining limitations, and back up the final report. Do not
launch training or a new method tree to turn this batch's scientific failures into
passing results.
