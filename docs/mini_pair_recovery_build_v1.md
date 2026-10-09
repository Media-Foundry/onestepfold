# Mini pair recovery engineering preparation

2026-10-09. User authorizes matched pretrained/random two-block post-recycle
pair recovery. No new sequences/teacher labels/ESM/MSA preparation. Only HIP0–5.
First build immutable unadapted B cache for existing48sites/912mutants, verify
all disabled two-noise outputs bitwise.912native last recycles/1824S1,no updates.
Target z remains a separate labeled archive path, never a predictor argument.
Compute raw/common/AA-centered target residual statistics, training scale uses
TRAIN27sites only. No new model outputs used to select scale or architecture.

Prototype: independent copies of Mini blocks14,15 (zero-based), pair-only
c_s=0, dropout0, native128channels. Compare original copied weights vs same
architecture native random initialization. Same new node-input/readout weights
perseed. Node input: actual candidate B_inputs,B_s,WT3pair row/column of mutation,
old/new AA16embeddings,siteflag.128hidden,small1e-3 left/right pair injection;
zero final128→128 output projection. Dense unrestricted residual, no symmetry,
rank/local/AA-centering constraint. Predictor returns original B_inputs/B_s.

Before training budget lock: validate parameter independence, matched common
initialization, no-edit identity, zero-state S1 replay, first/second-step gradient
flow, candidate order independence, and native per-candidate timing/memory.
Only discarded dry updates allowed at this stage. Main training and evaluation
budget will be separately locked before any learned quality result is inspected.
No claim this engineering preparation establishes transfer or acceleration.
