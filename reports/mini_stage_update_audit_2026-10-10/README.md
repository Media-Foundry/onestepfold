# Fixed-state TRAIN update diagnostic

Status: **all twelve fixed states complete and independently verified**. No
optimizer recipe or new model is promoted. See the [locked protocol](../../docs/mini_stage_update_audit_v1.md)
and [full findings](../../docs/mini_stage_update_audit_findings_2026-10-10.md).

This separate experiment evaluates all four accepted n15 stage-aligned models
at0/4104/8208. All27 TRAIN sites and513 candidates define the full objective.
No new native computation, held labels, S1 evaluation or accepted training updates.
The660 planned AdamW steps are isolated, in-memory counterfactuals from saved
parameters and moments, not a continued optimization trajectory.

The initial installation incorrectly hashed pytest's mutable cache. Its four
workers failed before model construction. The unchanged six-file diagnostic
overlay was installed with only the original825 declared scientific files;
the original deadline is retained. Initial failure records will be preserved
alongside the completed manifest, never rewritten as successful training.

The corrected runtime is
`/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/stage_update_audit_v1_20261010_integrity1`.
Lock SHA256: `ea9c8f9927047dcfa9f27cf9b5a14c90dba6c806fe1fa4fab45e6b4bc41f7afe`.
Controller833059 closed successfully; all four workers were observed absent.
The CPU verifier/export follow-up also closed successfully. Actual count56052
candidate forwards,6804 backwards and660 isolated AdamW step calculations.
Large parameter-gradient vectors remain in the runtime archive;
the independent NumPy verifier reads them there. No dense pair tensors or
new usable model checkpoints are exported to Git.

`analyze_results.py` requires the complete twelve-state export and independent
verification. It retains every fixed direction/fraction and distinguishes
full-objective changes from final common and AA-centered error changes. It
does not pick an optimizer, step size or checkpoint from the results.

`manifest.json` covers41 exported files. `verification.json` records independent
NumPy/FP64 checks of2112 derivatives and2916 per-site objective records. The
complete archive SHA256 is
`be884fe2dc148733e5b64ff1633ab70b8dfcbfd3ac9205b5c046b25073b40829`;
local checksum/import verification is in `transfer_verification.json`.
`finite_step_changes.png` / `.pdf` display all fixed fractions and directions.

`runtime_snapshot/` is the earlier incomplete30-file snapshot with four completed
initialization nodes and live worker observations. Its completion flag remains
false. It must not be confused with the later full export. The initial pytest
cache failure remains in `initial_integrity_failure/`, with zero model calls.
