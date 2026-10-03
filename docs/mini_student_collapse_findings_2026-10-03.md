# Read-only audit: candidate variation disappears at the second readout GELU

Completed follow-up to `161712a2`, under [the frozen audit protocol](mini_student_collapse_v1.md).
No old checkpoint was updated, replaced, or retrained. This investigates the
student's execution state, not Mini/C4/S1 backward correctness.

## Scope and replay

Four coverage runs, their saved initialization and updates 10920/21840/32760,
each on its ten training contexts: 160 forward/backward probes, zero optimizer
updates, zero S1 or C4 calls. Replayed losses agree with archived training
snapshots to maximum absolute difference **8.5578759e-8**. The controller
completed in 18.44 seconds. All branch activations, activation gradients,
parameter gradients and parameter changes are retained in
[the artifact directory](../reports/mini_student_collapse_2026-10-03/).

## Where the failed seed stops distinguishing candidates

For `expanded_s231301`, AA query embeddings and node hidden states still differ
between candidates. The output of `readout.1`, immediately before the second
GELU (`readout.2`), is strongly negative. The second GELU emits an **exactly zero
tensor** at every one of the ten contexts in all three saved trained states.
The final affine layer therefore emits its candidate-independent bias.

Example: 1W53 T37 at update 32760:

| Location | Candidate-centered RMS |
|---|---:|
| AA query | 0.968777 |
| Initial node mix | 0.096723 |
| Fourth node block | 0.104242 |
| AA readout projection | 1.161548 |
| First readout GELU | 0.647351 |
| Input to second GELU | 0.442147 |
| Output of second GELU | **0** |
| Final response | **0** |

At this example, the second GELU input spans approximately -301.125 to -9.902.
Across all ten terminal contexts it spans -301.885 to -9.745. Nonzero upstream
candidate variation thus does not survive this implemented floating-point
nonlinearity. This is an observed state, not evidence of an activation-library
bug or an architectural impossibility.

The gradient norm at the GELU output is about **1.496e-5**, while its input
gradient norm is about **3.259e-29**. The final affine branch has parameter
gradient norm about 0.001738, compared with approximately 3.80e-26 for the
preceding affine branch and 1.05e-29 for the query branch. The graph is connected;
upstream gradients are numerically tiny. Parameters changed from initialization
and between checkpoints, but AdamW decay and optimizer history can also change
parameters: a nonzero parameter difference is not proof of useful learning.

The three learning controls retain candidate-dependent second-GELU outputs.
Their T37 terminal centered RMS values are 3.68, 3.59 and 3.90. The same layer is
therefore not universally forced to return zero by the data loader or probe.

## What the archive cannot establish

The first recorded step-level window, updates **631–640**, already has zero
centered prediction energy for all ten failed-run contexts. Every later recorded
window does too. There is no earlier temporal record sufficient to pinpoint the
transition or establish that this seed first learned and then lost candidate
differences. Saved intermediate states begin at update 10920.

The initial final affine weight is intentionally zero in all runs. Consequently
the initial response and upstream gradients are zero, while the final weight
has a nonzero gradient. This shared initialization alone does not identify why
only one run entered the observed negative-activation state.

No causal intervention tested learning rate, initialization, activation choice,
gradient conflict, or weight decay. None is declared the root cause. No seed was
retried. The failed seed stays in the previous experiment's denominator.

## Decision

The audit explains **where and how the saved failed execution loses candidate
variation**. It does not establish why optimization entered that state. It
provides no reason to reopen the already audited Mini derivative path. The next
bounded experiment is the separately registered direct task-readout comparison,
not another attempt to rescue the old response-regression run.

Runtime archive: `/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/student_collapse_v1_20261003`.
