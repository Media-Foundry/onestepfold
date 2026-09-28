# Hard mutation utility: frozen batch and execution status

Protocol: [mini_hard_mutation_utility_v1.md](mini_hard_mutation_utility_v1.md).
Remote root: DiamondHill `/media/PM982/onestepfold/mini_hard_mutation_utility_v1_20260928`.

One audited control, alpha=.001, C4/S1 native FP32. Sixteen gradient proposals
and sixteen uniform random proposals (RNG6271), zero overlap:33 sequences
including parent,99 hard predictions under211/200003/200009. Candidate hash:
`b08f6bb6eaf3fc62d43b757853ac4f352f9ae077f3c718541dce155f4e1fcdfb`.
Fifteen ranked proposals are Y38 substitutions (one-based); the remaining is
R45P. Do not diversify or resample after observing this concentration.

The hand-written FP32 probability/logit chain test stopped before proposals.
The retained diagnostic shows independent native softmax pullback exactly
matches stored gq. FP64 formula error max3.00731e−7, relativeL2 4.32865e−5;
maximum ratio to the declared gamma24 rounding bound .076472. Near-hard
coordinates exactly replay archive. Candidate generation directly uses gp,
never divides by small probabilities. Gradient forward/backward took8.393s,
excluding loading, setup, failed attempts and the separate pullback audit.

An intervening load attempt had a ROCm unspecified launch failure. Both failures
are archived. After the variable-space audit, the manifest was frozen and hard
workers were submitted on GCD2–5, PIDs1855646–1855649. Last retrieved state:
all four workers in model loading. Subsequent SSH observations stalled; this is
not evidence of success or failure. Do not resubmit while their state is unknown.

No utility outcome is currently available locally. The evaluator reconstructs
native ESM, reference chemistry and topology for each hard sequence. The scorer
retains all deltas, per-noise decisions and both-confirmation endpoint counts,
separating task+nonregression from unchanged full hard_accept. It also audits
all stored coordinate/geometry scores and proposal ranking on CPU.
Four focused tests passed; all scripts compiled. Deployment remains rejected.

## Recovery after host reboot

Reconnected: host uptime was approximately one minute; no old worker process or
hard coordinate file survived. All four saved worker reports were still at load
with zero completed sequences. Archived these under attempts/reboot_interrupted.
Candidate hash remains unchanged. Restarted only hard evaluation on GCD2–5,
staggering model loads by20s. A detached controller automatically runs the CPU
scorer after all four workers exit successfully. No gradient or candidate rerun.
