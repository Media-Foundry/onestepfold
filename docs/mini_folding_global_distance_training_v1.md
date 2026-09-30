# C4/S1 experimental global-distance candidate v1

Scientific settings fixed after TRAIN-only calibration662526 and before candidate
training. Implementation of training integration, GPU preflight, submission and
terminal evaluation is still pending; this file does not claim a launched run.

Question: can experimental long-separation CA distance supervision recover global
shape lost by coordinate-zero training while retaining its local quality gains?
No extra inference iteration or changed ESM interface.

Start at retained full-diffusion512 parent SHA256
`7fc01820269b6f376f8313b79c4ab2bf8fcfd2a0b2a017a432033a51b73fd829`.
Do NOT continue from the coordinate-zero or old expanded terminal. Copy TRAIN423,
ordered8192 exposures/noises,2048updates, accumulation4,optimizer reset/schedule,
288diffusion tensors, frozenESM2/C4,FP32 andC4/S1/K1 from control lock SHA256
`1ec3f1c13fec5ea12981f9efef37957fec264c1bc0e659c9fc4a98519384c357`.

Loss weights:

|Term|Weight|
|---|---:|
|Experimental aligned-coordinate MSE (logged, not optimized)|0|
|Experimental smooth-lDDT|1|
|Experimental bond error|1.505408125612628|
|Chirality|1|
|Clash|0.0006600251156855778|
|NativeS2 auxiliary aligned-coordinate preservation|0.025476389066842815|
|Experimental global CA distance|**0.03290655679814053**|

Global term: same-chain observedCA pairs with sequencegap>=24, no upperGTdistance
cutoff, mean smooth-L1 of distances in Å with beta10 Å. Labels are GT, not nativeS2.
No missing-coordinate imputation. Original terms/masks/scoring remain unchanged.
This is one replacement of the experimental global term, not a coefficient grid.

The global weight is the locked TRAIN32 median-of-noise-averaged CA gradient-norm
ratio. Calibration manifest SHA256
`c867845c2410e1001cae3c48573ed195e36c2ddad5adcb9564cc3ff3a38b21b5`.
Use exact stored coefficient, no rounding or retuning. Preserve calibration report,
64vectors and code hashes in the run manifest. Coordinate-side calibration does
not prove a matched parameter-update budget or good training behavior.

Integration must preserve original trainer and native model code, ideally through
an isolated input/parts wrapper. Bind new labels to group identity and native atom
order; cached conditioning/teachers still read original validated TRAIN caches.
Preflight existing shortest/longest TRAIN engineering cases: public/retained
forward replay, original unweighted-term parity, finite new loss and selected
parameter gradients, exact checkpoint reload and no unintended parameter updates.
Release only after preflight; preserve failures without auto-requeue.

Exactly2048 updates. Keep original0/512/1024/2048 TRAIN32 probes and terminal
checkpoint; no best-probe selection or extension. HPC3 acd_u one GPU for training.
Audit full history/order/seeds, weighted losses, optimizer steps, frozen parameters,
terminal and initial fingerprints before terminal predictions.

Terminal comparison on same455 proteins and two assigned noises: one new candidate
plus archived nativeS1/nativeS2/retained/expanded/coordinate_zero references.
5460 scored outputs; only910 new candidate predictions plus a separately locked
engineering budget (target32, eight four-call inference preflights). Reuse all old
predictions with hashes. Complete GT scoring and independent metric checks before
aggregation. Separate originalTRAIN128/addedTRAIN295/observedDEV32. DEV is already
observed; any promising result still needs later fresh confirmation.

Paired candidate contrasts with BOTH coordinate_zero and expanded are central:
former asks whether global supervision helps; latter asks whether it improves the
previous local/global tradeoff. Also retain/nativeS1/S2 references. Report AA/CA
lDDT, globalRMSD and paired tails, severe collisions/strict checked stereo/new
failures, typed connections, far-distance diagnostic and actual cost. No automatic
promotion by one positive mean; retain mixed or negative results without tuning
on DEV. Do not add ESMC, optimizer/noise/data changes, LoRA, repair or design work.
