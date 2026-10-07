# Mini reference-editor pilot artifacts

[Findings](../../docs/mini_reference_editor_findings_2026-10-07.md) and
[protocol](../../docs/mini_reference_editor_v1.md).

Successful run: `reference_editor_v1a_20261007`, worker/controller complete.
`report.json.gz` is lossless gzip of the worker report (histories, checkpoint and
coordinate hashes, invariants, gradient audit, timing); `scores.json.gz` holds
independently computed full per-output metrics and site summaries.
`summary.json` contains terminal/intermediate stratified summaries.
`checkpoint_replay.json` proves all6saved checkpoints replay on matched inputs
(12additionalS1calls). `lock.json` pins1094sourcefiles, archived teacher provenance,
architecture, seeds, sites and budget. `local_tests.txt` records8focusedtests.
`pilot_results.png` displays training loss and terminal two-noise-mean ranking.

`interrupted_host_reboot/` preserves the initial host reboot status.
`pretraining_order_failure/` preserves the original implementation/lock/terminal
failure and the standalone diagnostic; no parameter updates occurred there.
The1e-4gate was not loosened: v1a uses fixed single-candidate kernel shapes.
The diagnostic observation JSON transcribes captured terminal measurements,
not an additional trained run. Both old roots remain on DiamondHill.

Full coordinates and checkpoints, plus immutable training source, remain at:
`pc@DiamondHill:/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/reference_editor_v1a_20261007/`.
Local reports mirror: `/home/husrcf/Code/onestepfold_runtime/reference_editor_v1a_20261007`.
No large weight/latent/checkpoint files are added to Git.

Successful worker3808S1/1024updates/zeroC4/zeroinput-encoder calls; replay12S1.
Public Mini135.22M frozen, new editor9.35M trainable; no oracle target conditioning.
All labels are computational mutant structures. Parent experimental backbone is
ONLY a legacy score target. Three proteins/five sites are development data.
The model-only timing excludes original reference ESM/C4 cache construction,
external preparation and output I/O; not an end-to-end speedup benchmark.
