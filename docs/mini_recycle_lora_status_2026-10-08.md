# Mini internal final-recycle adaptation — launch status

Implementation f81493ff; pre-outcome gradient-gate correction72c93314. Both pushed.
The independent protocol is [mini_recycle_lora_v1.md](mini_recycle_lora_v1.md).
Current frozen execution: `recycle_lora_v1d_20261008`,1116 code files,
lock SHA256 `cf5477c1377817fd1754887083104184ba4c0b01fb3ce1f18194f28105c7f698`.

## Current status

Preflight PASSED in412.684seconds;controller launched both fresh runs on HIP0/1.
Both seeds independently replayed912candidates×2noises bitwise:1824candidate
replays/3648coordinate outputs. Native scope/weight/cache/gradient checks passed;
655360 trainable parameters per bank. Four dry updates discarded, zero formal
updates during preflight. Counts1884nativecycles/3656S1;the inherited c4=0 counter
means the old forbidden entry was not called, NOT that no trunk work occurred.
Peak allocated4952169472bytes(4.61GiB).13localtests passed.

Each fixed run performs initial evaluation,8208updates and checkpoints4104/8208;
then independent CPU scoring and serial GPU replay/timing. At this snapshot workers
are running;no trained outcome, migration or speed conclusion. Only candidate-native
transition output weight residuals are trainable;original Mini,WT cache and S1
remain fixed. No external compensation head.

## Preserved pre-outcome failures

- v1: stopped on activation-checkpoint guard before any native cycle. Runtime now
  disables Pairformer backward recomputation so temporary candidate hooks cannot
  disappear during a recomputed forward. Native no-grad inference already does so.
- v1b: stopped before model load on an existing preparation directory. Work paths
  are now absolute and local to each execution bundle.
- v1c: all912candidate two-noise zero-init coordinate replays for seed272001 passed.
  The first dry backward stopped on zero LoRA up gradients at indices25/27, before
  any optimizer step. Diagnostic fixed TRAIN T37A, same seed, found native
  block12/13 single-transition output weights and inputs exactly zero, while
  adapter-output gradient norms were both0.0021113157. This is not a disconnected
  backward graph. Other30 up gradients were nonzero.

A separate read-only probe initially attached a gradient observer before the first
trainable addition and correctly failed on a frozen tensor with no gradient; the
corrected observer attached to adapter outputs. No training update in either probe.

v1d retains the same32locations,rank,initialization,objective and data. Gradient
validation now records every adapter's input nonzero count and output gradient.
Zero weight gradients are accepted only at indices25/27 AND only when measured
input is exactly zero and output gradient nonzero. All active up gradients and,
after one discarded update, active down gradients must remain nonzero. Local
regression test reproduces this zero-input/connected-output distinction.

## Evidence and limits

Compact remote JSON snapshots and SHA256 manifest are in
`reports/mini_recycle_lora_2026-10-08/`. Historical failure snapshots are preserved;
current controller snapshots are time-specific, not a final experiment report.
Two seeds,15trainparents27sites,9heldparents18sites and3same-parent held sites are
unchanged;all are development. Zero replay is a numerical integrity gate, not
teacher-response generalization. Native candidate s_inputs are archived legitimate
inputs;this is not a WT-only pipeline. ESM/MSA preparation remains excluded.
