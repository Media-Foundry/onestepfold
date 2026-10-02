# Matched source-AA coverage development experiment v1

Locked before training/decoding, 2026-10-03. Historical four-context experiment
96a9c665 remains closed. This batch changes training context coverage only.
No new teacher C4/ESM, downloads, parameter architecture, spatial rank, loss, Δs
prediction, functional training, or checkpoint promotion.

## Data and comparison

Use hash-checked `factor_student_pilot_v1_20261002` only: 24 proteins, two sites
each. Preserve its sequence-component train/validation provenance. The original
validation proteins remain excluded from updates. Also exclude 1JHG N25, 1A7G
S34, and all of 4PT4. All results are development evidence, not new independent
confirmation: this archive and its splits have influenced earlier decisions.

Both arms have ten sites on the SAME eight proteins, with identical per-protein
site counts and chain-length distribution. Six contexts are common; four swap
within a protein. Coordinates/quality are not used to choose sites.

| Protein | Length | Restricted | Expanded |
|---|---:|---|---|
| 1W53 | 84 | T37, Y84 | T37, Y84 |
| 1JHG | 101 | A2 | A2 |
| 1A7G | 82 | N65 | N65 |
| 2P7T | 103 | A44, T86 | A44, T86 |
| 5GPE | 129 | A11 | D72 |
| 1DZR | 183 | A179 | L13 |
| 2ED6 | 170 | T90 | V137 |
| 4HUT | 191 | A44 | I25 |

These are all ten eligible T/Y/A/N archived training sites. The expanded set
covers T/Y/A/N/D/L/V/I, not S. Adding S would require changing the matched protein
set or violating the held-site exclusion. This limitation stays explicit.
Source-AA and within-protein local environment still change together; this is
not a causal isolation of residue identity. Inventory includes observed-GT Cα
neighbor count within 8 Å and a five-residue sequence window; neighbor count is
NOT solvent accessibility. Do not infer missing environment descriptors.

## Training

Unchanged `NonlinearResponseReadout('pair')`, 3,627,904 parameters; raw FP32 hard
Δz supervision, mean of 19 per-candidate NMSEs with original mean-energy floor
1e-6. WT s/z, mutation position and discrete AA are model inputs. No target
conditioning is supplied to the student. AdamW lr1e-3, wd1e-4, eps1e-8, clip1;
no scheduler. Fresh seeds231301/231303 are paired across arms. Identical
round-robin parent order; each update contains all19 non-WT AAs at one site.

Each run ends at32760 updates =3276 full-AA exposures/site. Save initial state
and checkpoints10920/21840/32760; intermediate checkpoints provide TRAIN latent
curves only. Primary is ALWAYS32760; no best-checkpoint selection or extension.
This roughly retains the earlier total32768-update budget, with less exposure
per site than its8192: historical old4 versus new10 is NOT a matched contrast.
The two current arms have exactly matched budget and exposure.

## Functional evaluation

Decode every terminal model at ALL48 sites, regardless of NMSE. Four terminal
students plus Exact, Baseline, WT-z, oracle channel-R32. Four noises in locked
order230201/230211/270101/270103; same old/new groups as prior development, no
claim that these are fresh untouched validation noises.

Exact uses target s_inputs/s/z. All other arms use WT s_inputs, **oracle target
s**, target atom graph/reference chemistry; z is exact target (Baseline), WT,
oracleR32, or WT plus student prediction. S1 fixed FP32 runner/state/noise and
archived atom identity/topology checked. No ESM/C4 calls permitted. Replay old
Exact/Baseline and WT coordinates bitwise, and repeat new Baseline noises for
first non-WT candidate at every site. Expected29376 S1 calls:29184 mutant arm
calls +96 WT +96 new-noise replays. 30720 scored rows include reused WT rows.

Score parent experimental-backbone Cα Huber-distance proxy, not mutant GT or
biological utility. Report 19-AA Spearman, Top1, top3/5 overlap, regret, MAE,
RMSE, bias/scale; arithmetic noise means fixed. Old-noise mean selects once,
new-noise teacher scores evaluate that same choice; compare teacher's own
old-selected candidate and new oracle best separately.

Report each arm's train/seen-protein-new-site/unseen-protein separately, split
further by source AA covered/uncovered. Compare both arms on the common held
panel (34 sites): two held sites in seen proteins +32 sites on16 unseen proteins.
The eight sites trained by one arm but not the other remain separately labeled.
Main summaries average sites within a protein then give proteins equal weight.
Missing strata are explicit; mutant/noise rows are not independent proteins.
Compare each model against the SAME site's WT-z and Baseline. Report the full
48-site table to avoid changes in stratum membership hiding effects.

Keep AA/Cα lDDT fidelity, local RMSD mean/P95/P99/max/>1Å, absolute geometry
passes and BOTH directions of transitions. Existing geometry means zero
nonbonded<1Å pairs and strict checked CA/ILE/THR chirality ONLY, not complete
chemistry. Save failed centre identities and continuous oriented volumes;
retain all centres for T37N. No threshold changes. 6UFE92 is outside this batch.

## Prior-checkpoint error analysis

Before new training, evaluate all six archived old4 checkpoints on their eight
sites. For each of19 candidates record predicted/teacher energy, amplitude
ratio r, cosine c, NMSE, zero flags and normalization-floor status. Verify
NMSE=(||t||²+||p||²−2p·t)/max(||t||², floor) in original mean-square units.
The simpler1+r²−2rc only holds without floor activation and nonzero t.
Teacher-optimal scalar and its error are OFFLINE oracle diagnostics only;
negative scalars are reported, never used to alter predictions or calibrate a
held protein. Apply the same unscaled diagnostics to new terminal outputs.

## Integrity, costs, stop

Freeze source/protocol/teacher/checkpoint hashes. Keep failed attempts in the
record; no automatic model/hyperparameter change or rerun on scientific failure.
Only HIP_VISIBLE_DEVICES selects permitted devices; use existing physical-device
guard. Four workers maximum. Stop each stage on nonfinite/error/2h worker timeout.
Record exposures, optimization state, gradients, runtime, memory and C4/S1 counts.
Audit initialization pairing, exclusions, context counts, scoring and replays.
After all locked evaluations, report results and stop. No deployment decision,
automatic teacher expansion, Δs predictor or continuation follows this batch.
