# Repeated-source, multi-environment learning curve — prospective design

Status: data candidate manifest prepared on2026-10-04; **teacher collection and
training not started**. This is a reviewable next experiment, not a claim that
more data will solve transfer. It follows the completed context-coverage audit.

## Question and fixed components

Can the existing reference-conditioned ContextTaskReadout obtain a reproducible
advantage over the existing AATaskReadout when every source AA is seen across
many independent protein environments? Keep their implementations fromf858c875,
scalar native Exact task-delta target, global-scale squared loss, optimizer and
reference features. Do not add a new output head, Δs, ranking or geometry loss.
This studies scalar screening, not structural response distillation.

The old generator's activation collapse is a separate stability question; it
does not motivate changing the score models inside this data comparison.

## Data

Use the sequence-only candidate manifest:32train parents,8confirmation candidates,
each with one A/D/L/T site. Nested8/16/32parent tiers contain32/64/128contexts.
The same source types and four-site balance per parent hold in every tier. Each
site has19nonWT candidates; WT anchors are shared within parent. Components and
old response parents remain disjoint. Selection uses no response outcomes.

Before collection, lock the final native-input eligibility, public teacher
weights, code hashes, native atom/GT mapping, shared-noise identity and explicit
failure denominator. Reference-only preflight already passed, but does not
replace native chemistry/input checks. Range failures are retained; replacements
must follow a predeclared metadata-only order before viewing response scores.

Keep original16held proteins as development history. New8are reserved for one
predeclared joint learning-curve analysis, not intermediate model selection.
Their source structures come from historical folding TRAIN; isolation is only
for response-method development and uses the documented HSP/accession graph.

## Budget organization to freeze before execution

Recommended bounded design: two fresh initialization seeds, two existing models,
three nested tiers =12runs. Use identical paired initialization within a model.
No best-checkpoint or best-seed selection.

Use1024full19-AA exposures per context as a prospective matched-exposure endpoint:
32768 /65536 /131072updates for8/16/32parents. Also save the common32768-update
checkpoint in all tiers to expose the fixed-compute comparison. These answer
different questions: the former spends more compute on larger data; the latter
gives larger datasets fewer exposures per context. Report both, never choose
whichever looks more favorable afterward. This is a new finite budget, not
continuation of the old ten-site experiment.

Keep one common loss scale across tiers, fixed before any new labels: reuse the
previous expanded-TRAIN RMS constant0.5759913630974075. This is an existing
training preprocessing constant, not a new-test calibration. Report raw MSE as
well. Do not fit a different scale per tier or import label statistics from a
larger tier into the smaller one; either would change what the comparison means.

Score both old-label-noise and locked evaluation-noise means, with fixed old-only
candidate choice evaluated on the other noises. Freeze noise values, precise
sampling order, time limits and error handling in an executable lock before
collecting labels. All12runs, failures and endpoints remain in the report.
No teacher ETA is promised from old timings alone; record actual feature/ESM/C4
and S1 costs separately. No automatic budget extension for poor curves.

## What must be evaluated

Primary comparison: context versus AA-only on identical new-protein cases,
reported per source type and protein, plus teacher-referenced ranking, Top1,
top-k recall, old-select/new-evaluate regret and its protein-level median/tail.
Include all pairwise seed differences, not only the best seed.

Keep full TRAIN curves and per-site errors as well as globally normalized MSE.
Report singleton counts (zero at these tiers), source-type duplication, label
energy concentration, AA-table training floor and the residual after that table.
This avoids equating a tiny global loss with having learned context dependence.
Scores remain raw task changes, not calibrated AA probabilities.

No cheap scorer produces coordinates. Report archived Exact geometry of selected
candidates without calling it a geometry repair; any future structural replacement
requires its own decoded-coordinate test. The new scoring heads require the
reference backbone as a legal input, and never read target s/z/s_inputs.

If retaining WT-z as a privileged reference, account separately for its target-s
and S1 cost. It is not the equally informed AA-only control. Do not import old
WT-z numbers from different proteins or score-reference definitions.

## Interpretation and stopping

A context-over-AA-only advantage that appears only in TRAIN or only one seed
does not establish transfer. Improvement with more contexts supports this scale
intervention under the fixed configuration, not data sufficiency in general.
No improvement bounds this configuration and budget, not all context models.

End after the locked curve and audit. Do not tune on the new eight parents,
restart a failed seed, alter reference features, or append more epochs under
the same confirmation label. Only after reviewing this experiment should a
different native-prior approximation or larger data-scale study be considered.
