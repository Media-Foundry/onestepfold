# Mini LoRA noise coverage: completed results

Execution: DiamondHill `lora_noise_v1_20261008`.
Report: [terminal analysis](../../docs/mini_lora_noise_findings_2026-10-09.md).
Protocol: [locked v1](../../docs/mini_lora_noise_v1.md).

`manifest.json` contains SHA256 of24 verbatim remote JSON artifacts.
`site_records.json` extracts1152 site-arm records from four remote scores.json.gz
files and records each original compressed file SHA256. It is a derived subset,
not a verbatim copy of those compressed archives. Full atom-level outputs stay
remote at `<arm>/runs/<seed>/scores.json.gz`.

Run `python reports/mini_lora_noise_2026-10-09/verify_results.py` from the repository root
with NumPy/SciPy available. It verifies hashes, completion, exposure counts,
replica agreement, replay status, per-noise geometry totals and independently
recomputes3456 Spearman values and1152 old-select/new-evaluate regrets.
`verification.json` also lists all changed held-site selections and derived
geometry/timing summaries. `derived_manifest.json` hashes these derived files.
No checkpoint/coordinate regeneration or training is performed by this script.

Four8208-step runs complete; controller closed, no promotion. Both noises were
TRAIN noises for dual, so this is not unseen-noise confirmation. All protein
panels remain development data. All source and prior launch files retained.
