# Fixed checkpoint32 coordinate follow-up

Seed272001 only, pre-specified step32. This is an interim analysis of existing
structures; no model forward, training update or candidate-input preparation
was added. It is not the final two-seed experiment or independent confirmation.

`provenance.json` records the immutable training/evaluation/checkpoint hashes,
the CPU-only scorer invocation, completion and output hashes. `score_interim.py`
is the exact small entry script; it called the unchanged frozen scorer inside
an isolated directory. `summary_32.json` contains the scored panel summaries.
`functional_comparison.json` adds matched historical32 comparisons, every changed
choice and geometry transitions. `recompute.py` recreates that file from the
scored rows and checks unchanged controls, aggregation, choice/regret accounting
and geometry counts. Run it from the repository root.

The full20,148,671-byte `scores_32.json.gz` is retained locally in this folder
and remotely at
`/tmp/anchor_interim_score_272001_32_6e5f0183/runs/anchor/272001/scores_32.json.gz`.
It is not duplicated in Git for this interim analysis. Its SHA256 is
`69bfd1fc1295968d549422ea343fadfa43f3d0458911ebdd2109bfeef4d570f2`.
It is required to rerun `recompute.py`. The final controller will rescore the
same fixed node; compare its summaries and rows before closing the full trial.
Elapsed-time and compressed-file bytes may differ on that repeat.

Native checkpoint tensor replay is still pending. The other seed and fixed128
main endpoints are pending. Current training and its original code, optimizer,
budgets, device assignments and selection policy were not changed in response
to these numbers.
