# Separate C4/S1 ESMC interface initialization v1

Frozen before fitting, while global-distance training662548 is running. This is
preparation for the user's requested matched ESMC comparison, not a change to that
loss experiment or its reference. Use the already audited paired feature assets;
no repeated ESM extraction, structure prediction, GT coordinate supervision or
Mini parameter update. Keep the current ESM2/C4/S1 model unchanged.

Fit exactly the423 current TRAIN sequences, sorted by sequence SHA256. The32
observed DEV identities are checked for exclusion but their feature tensors are
not read by this stage. No older512-sequence fitting corpus is mixed in. The
native frozen449×2560 projection defines targets from cached ESM2 features;
ESMC final-layer1152 features define inputs. This is ESM2-interface regression,
not evidence that ESMC is intrinsically better or worse at folding.

Reuse ProjectionMoments unchanged: equal total weight per protein, centered
channel-standardized affine ridge, lambda0.001, variance floor1e-8, FP64 moments
and solve; store FP32 weight449×1152 and bias449. No hyperparameter sweep or
selection. Native projected targets are calculated in CPU FP32; BF16 ESMC cache
values are promoted exactly. Do not claim native GPU bitwise projection parity.

Require sequence/role/layout/dtype/finite/hash checks, native checkpoint SHA,
exact423 fit IDs, exact bridge save/load, finite training residuals and unchanged
active training lock. Check paired tensor bytes on both passes. Full ESM2 cache
container hashes inherit prior accepted provenance; unused coordinate and
conditioning tensors in those containers are not accessed. Six complete ESMC
shards are hash-checked, though only TRAIN slices are used for fitting.

Deliver bridge.pt, lock, training-only per-protein/cohort residuals and scheduler
acceptance. Compare residuals with the fitted TRAIN-mean constant as a descriptive
baseline. Feature residuals neither select a model nor establish structure benefit.
No intermediate layers, nonlinear bridges or folding-core fine-tuning this stage.
HPC3 acd_u, four CPU threads, GPU hidden,20-minute bounded job; partition may reserve
one GPU but it performs no model computation. Preserve failures, no auto-requeue.

Next structural comparison must recompute C4 from ESMC using unchanged hard
chemistry and a preselected common diffusion checkpoint, matched initial noise,
FP32 and C4/S1/K1. It cannot reuse ESM2-derived s/z as ESMC conditioning. Native
projection replay, unchanged non-interface weights and coordinate scoring against
experimental GT are required. Lock that execution separately before inference;
no ESMC folding run is authorized by a good regression score alone.
