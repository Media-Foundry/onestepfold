# Full-TRAIN stage optimization comparison

Status: launched, scientific results **incomplete**. This is a new experiment,
not a continuation or replacement of the closed update audit.

The [protocol](../../docs/mini_stage_fullbatch_v1.md) fixes the model, TRAIN data,
Final target and two paired seeds. AdamW and bounded L-BFGS each receive128
full-gradient evaluations. Different optimizer recipes, not equal accepted
updates or equal wall time. No development-based tuning or promotion.

`training_lock.json` records832 source hashes, the exact labels/initial states,
installed optimizer implementation and full work/evaluation budget. Its SHA256:
`ed09b10002eaa7d04a4f2ea5843bf33657188a64cfd04836934aa47679993eed`.

`launch.json` identifies controller947128. Four independent workers useHIP0–3;
HIP4 is reserved for tests/verification, HIP5's unrelated workload is untouched.
Initial live observation was1791597300.97; it is not evidence of later completion.
Read current process handles and reports before inferring runtime status.

`preflight_notes.json` retains local driver stalls and partial-package test
collection failures. The actual complete-source prelock tests pass3/3; the
controller rechecked the frozen sources and its three tests also pass. No
scientific results or success claims follow from these implementation tests.

The existing nine new-protein contexts remain development data. Correct AA
response, raw selection risk, geometry and actual folding cost remain separate
requirements. No new C4/recycle or ESM/MSA preparation is authorized in this batch.

`startup_verified.json` is the later observed-live snapshot: all four runs passed
the complete initial S1 replay and their first full TRAIN gradients match the
preceding audit exactly. The snapshot is still not a final scientific result.
Aggregate graph change risk is HIGH; `graph_review.json` records the reviewed
execution boundaries and known static-analysis limits.
