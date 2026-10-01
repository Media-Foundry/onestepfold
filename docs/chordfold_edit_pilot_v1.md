# ChordFold: bounded hard-condition structure-editing pilot v1

Locked before model predictions, 2026-10-01. This supersedes neither the completed
noise-diversity assessment nor the closed sequence-proposal experiments.

## Question and scope

Given an experimental source structure, its hard sequence and an equal-length
single-substitution target sequence, does a coupled backbone editing response
improve on copying the source and on ordinary target folding? Full source and
target C4 are retained. No warm-start, recycle compression, training, soft sequence,
mutation search, BindCraft or iterative geometry repair in this batch.

Use public `protenix_mini_esm_v0.5.0`, native FP32, ESM2-3B, C4, dropout off,
fixed identity-bound Gaussian noise. The recent fixed2048 checkpoint is a separate
development control; its high-sigma endpoint training would confound a first
multiple-sigma editing probe. All target native features, ESM and C4 are rebuilt.

## Development pairs

Search the prepared TRAIN structure assets, not the former four proposal parents.
Canonical sequences, length 80–180, resolution ≤2.5 Å, different PDB records and
exactly one substitution produced 2,618 candidate pairs from 7,080 sequences.
Sort by SHA256(`chordfold-pair-v1:20261001:` + source group + target group).
Require one chain, complete N/CA/C/O, no chain break or modified residue, no
explicit ligand/ion/other polymer/nucleic acid in the extracted context, and
shared SIFTS accession. Keep the first four distinct accessions. Waters allowed.

Preselected pairs: 1L12→1L04 (164 aa), 1TAY→1TDY (130), 1GOB→2RN2 (155),
1IZR→1IZQ (124). Fail preflight rather than replace a selected pair after seeing
predictions. Preserve source metadata, construct sequences, SIFTS bounds, GT masks,
input hashes and native atom identities. These are development pairs, not new
independent generalization or causal mutation-effect evidence. Crystal conditions,
construct history and unrecorded context may differ. Native chemistry does not
automatically include experimental disulfide topology: report SG proximity and
native bonds separately, and do not claim comprehensive chemical validation.

## Coordinate contract

Only common N/CA/C/O positions have a common vector space. Each query retains its
own complete native atom graph. Missing source atoms are initialized by placing
native reference conformers in observed residue N/CA/C frames; observed atoms are
then copied exactly. Target sidechains at changed residues are placed from target
reference in the source frame; unchanged atom identities are copied. No target
experimental coordinates enter inference. Initialization is not geometry repair.

Queries subtract the all-atom input centroid and restore that same centroid to
the returned coordinates, so both branches are expressed in the source frame.
Source and target share identity-bound unit noise and exactly matched backbone
noise; new atoms get their own noise. Seeds: **221003, 221021**.

## Frozen sigma-domain proxy

For the two native denoisers, project their outputs to common backbone B.
At sigma s, delta_v(s) = (D_source(B+noise*s) − D_target(B+noise*s))/s.
Full all-atom inputs have their separately initialized sidechains.

- high sigma = 16 Å; low sigma = 12 Å; delta = 4 Å.
- naive B = B_source − 16 delta_v(16).
- smoothed field = [16 delta_v(12) + 4 delta_v(16)] / 20.
- smoothed B = B_source − 16 smoothed_field.
- refinement: one target denoiser query at sigma = 1 Å, same identity noise.

These are prechosen engineering values, not fitted using target GT. The negative
sigma step follows v=(x−D)/sigma. Applying ChordEdit's two-time weighting directly
in EDM sigma is an explicitly **unvalidated protein proxy**, not a reproduction
of its image-model transport or a transfer of its theoretical guarantees.
Reference: [ChordEdit paper](https://arxiv.org/html/2602.19083v2),
[official implementation](https://github.com/ChordEdit/ChordEdit).

## Arms and real work

| Output | Individual denoiser calls per uncached edit |
|---|---:|
| Copy source backbone (no invented target all-atom score) | 0 |
| Target cold C4/S1, controlled deterministic sampler | 1 |
| Target cold C4/S2, same sampler rules | 2 |
| Target denoise source-initialized atoms at sigma16 | 1 |
| Target denoise source-initialized atoms at sigma1 | 1 |
| Naive backbone difference, target sidechain lift, sigma1 refinement | 3 |
| Smoothed backbone difference, same lift/refinement | 5 |

Save unrefined naive/smoothed backbones as additional diagnostics. Production
queries are sequential single-sample calls: batch size1. Shared queries can be
reused across experimental arms, but method cost still counts its required calls.
No silent source-response cache, parallel-batch NFE relabeling or best-seed choice.

Engineering checks: exact cold S1 parity with the existing native conditioning
sampler; identical-condition coupled cancellation using actual repeated calls at
both sigmas; finite outputs; backbone noise identity; reference/input hashes.
Record source-equals-target sigma1 refinement drift separately (it need not vanish).
Record exact same-variant replay with source states/responses cached and **target
features/ESM/C4 recomputed**. This measures a replay scenario, not distinct-target
throughput. Fail closed on engineering mismatch; no quality-driven reruns.

## Evaluation and closure

Four pair workers on DiamondHill, two seeds each, fixed runtime ceiling30min.
Target GT is opened only in a subsequent CPU scoring stage. Score all arms,
including failed or nonfinite instances in the denominator. If an engineering
error prevents predictions, preserve the failed run and version the fix.

Report observed-target AA/CA-lDDT, global aligned CA RMSD; copy baseline has only
backbone scores. Local region is sequence ±2 or source CA within8 Å of the
substitution, fixed using source only. Align target GT and predictions separately
to source using the common nonlocal CA support, then measure local target error,
nonlocal error and nonlocal motion. Report needed source→target changes and
predicted changes, with undefined zero-signal cosines left undefined. Contact
changes use CA<8 Å, sequence separation>2; report counts and reconstruction error.

Full target-inventory diagnostics: severe nonbonded pairs, max penetration,
strict checked CA/ILE/THR chirality, bond/peptide residuals and calibrated connection
distributions. No revival of legacy_joint_pass as a universal veto. No output
may be called chemically valid just because backbone displacement is small.
Raw experimental baselines and incomplete native disulfide handling are explicit.

Time model startup separately; synchronize GPU timings for native features/ESM,
C4, cache construction, each query and sidechain lift. First-edit totals include
source preparation where required; subsequent totals disclose exactly what was
cached. Report peak memory and actual aggregate calls, including audits/replays.
Do not compare these measurements directly to old A800 internal-only benchmarks.

Stop after all eight pair/noise cases. No sigma search, automatic training or
warm-start promotion. A successful no-edit cancellation is only an implementation
check. Editing must demonstrate useful targetward response beyond source copying,
without damaging unchanged structure or geometry, before latent-reuse becomes
the main experiment. A negative result rejects this frozen proxy, not all editing.
