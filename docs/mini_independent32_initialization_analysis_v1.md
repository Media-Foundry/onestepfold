# Independent32 initialization analysis (posthoc, read-only)

2026-09-30. Locked validation has finished with a negative continuation screen.
Mean and tail outputs both lose about 0.022–0.023 observed all-atom lDDT vs raw.
Before any method change, score the already saved, identical local initialization
against the same experimental mapping and masks. No new model predictions,
repairs, changed thresholds, target selection, or candidate optimization.

Keep all32 proteins and all three noises. Compare raw -> local initialization ->
frozen mean/tail output. Reuse the frozen experimental scoring and independently
cross-check atom-centered scores against its all-atom lDDT. Also describe backbone
and side-chain atom-centered scores, keeping all observed partners: these are
not backbone-only or side-chain-only pair metrics. Report their weighted additive
contributions to each protein's all-atom score change; do not infer a unique
structural mechanism from the atom class labels.

Summarize three-noise means per protein and bootstrap whole proteins as in the
original reporting (10000 draws, seed20260929). Stage differences are descriptive
posthoc diagnostics, not new acceptance gates or a new independent confirmation.
Preserve original validation rejection regardless of the result. This analysis
may identify which mapping merits future work but does not authorize tuning on
this panel or training a replacement.
