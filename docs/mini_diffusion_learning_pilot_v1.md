# Native one-step diffusion learning: bounded two-arm pilot v1

2026-09-30, aftere3417907, before predictions/teacher generation or updates.
The source manifest128TRAIN/32VALIDATION and all its masks/isolation are immutable.
No Y38,2B0A,2Z0J or1U07 tuning. No further geometry-solver tuning or backbone
numerical-debugging campaign. Keep deploymentC4/S1/K1; S2 is training reference only.

## Comparison and budget

Two arms: GT+chemistry (`gt`) versus the SAME objective plus frozenS2 auxiliary
(`gt_s2`). Both load the original public Mini-ESM v0.5.0 checkpoint, frozenESM2-3B,
frozen four-cycle trunk/conditioning, rank8 adapter835584parameters from7c6979e8.
Identical zero-up initialization seed20260930, same data order/noise, FP32 native
attention/LayerNorm, no autocast/MC dropout/extra churn/rigid augmentation.

Each arm:16 complete visits of128proteins=2048protein exposures, batch4 via gradient
accumulation,512optimizer updates. Visit each protein once per epoch, SHA order
`diffusion-pilot-v1:epoch:<epoch>:<group>` with epochs numbered1–16; do not replace long/failed cases.
AdamW beta(.9,.999),eps1e-8,weight_decay0; clip global adapter norm1 after accumulation.
LR warms linearly to1e-5 over32updates, then cosine to1e-6 atupdate512. Cache train
noises600001/600011; alternate by epoch, each observed8times. Terminalupdate512 is
the evaluation checkpoint; no validation early stopping/best-of/checkpoint selection.
Two matched arms may run on two GCDs, sharing readonly caches. No hyperparameter grid.

## GT authority and loss

Experimental GT uses exact native identity and BOOLEAN observed mask BEFORE any
distance/alignment/lDDT arithmetic. Missing atom coordinates never become labels.
TeacherS2 is generated from untouched pretrained weights with the same conditioning,
initial noise and stableEuler rule. It is NOT experimental truth, selected by quality
or assumed chemically valid. Teacher loss covers its complete native inventory;
GT components cover only experimental observations. No symmetric atom renaming yet.

Raw components in `adapter_supervision.py`:
- A: observed all-atom proper-aligned MSE (Å²), detached FP64 alignment as existing.
- D: observed smooth-lDDT, fixed15Å neighborhood excluding same-residue pairs,
  per-atom mean, thresholds(.5,1,2,4)Å,temperature.1Å; different from reported hardlDDT.
- B: observed covalent bond MSE (Å²), equal mean of intraresidue/peptide categories;
  lengths from experimentalGT, not a narrow ideal template. No omega window loss.
- C: checkedCA andILE/THR stereo penalty mean relu(.2−signed_volume/reference_abs)²,
  trusted native-reference handedness, full predicted inventory.
- R: full allowed nonbonded repulsion=sum relu(penetration−1.5)²/Natom PLUS
  top16 mean [relu(penetration−1.9)/.1]²; graph distances<=3 excluded. Detached4Å
  radius search is a computational shortcut including every possibly positive term,
  not a GT mask or sampled subset. Active-pair/top-k changes are piecewise.
- T: proper-aligned full-inventory MSE to frozenS2 (Å²).

`L_gt = A/100 + D + 10*B + C + 0.1*R`.
`L_gt_s2 = L_gt + 0.25*T/100`.

These are explicit pilot weights, not calibrated optimum or equal-gradient weights.
No weight is fitted to1U07 or validation. The coordinate scale10Å keeps a global
fold signal while bounded local supervision remains material. Record components
and gradient norms on training data; do not change weights mid-run if imbalanced.
Chemistry penalties are guidance, not chemical guarantees or new acceptance rules.
There is no raw1Å displacement constraint: this is folding correction learning,
not the former near-raw repair task; previous repair outcomes remain unchanged.

## Cache and validation separation

Generate nativeFP32C4 conditioning once per all160proteins, using up to8GCDs and
load-balanced fixed length² scheduling. Keep original precision/layout and input
hashes. Only TRAIN receivesS1/S2 outputs at600001/600011; VALIDATION receives
conditioning only, no teacher labels or predictions in this cache stage.
Require per-target saved/reloaded conditioningS1 replay for training; finite tensors,
identity/hash/NFE checks for every target. Any failure remains visible; no reselection.
Cached conditioning is legitimate for frozen-trunk parameter training, NOT a
replacement for live sequence-conditioned computation when testing input gradients.

After BOTH terminal checkpoints are frozen: evaluate all32VALIDATION on new noises
600029/600043. Compare untouchedS1,S2 and the two S1students on the same initialnoise,
GTmask and graph. Never use confirmation noise for training. Evaluate TRAIN separately
for fitting/convergence, never pool it with validation. No best-of-noise.

Primary output is per-protein mean ΔAA-lDDT versus nativeS1 and between arms, with
paired target bootstrap CI. Secondary:CA-lDDT, paired lower tails/worst5%, severe
degradation rates<−.05, per-noise results, runtime/NFE/memory. Report full-inventory
collision/penetration, checked stereocentres, bond/peptide and typed connections
separately per evaluationv2. Report new damage to initially good outputs.
No new noninferiority margin or aggregate chemical/deployment pass is invented.
Both arms and all failures are reported, even if the auxiliary harms performance.

Stop after this matched pilot; no automatic extra epochs/seed search. No claim of
reliable design until the actual merged output's sequence gradient, hard mutation
utility and chemistry are separately established on appropriately held-out data.
