# Independent32 execution lock (source-context extension)

2026-09-30. Original geometry/evaluation protocol remains
`mini_anchored_independent_v1.md`; isolation is the calibrated v2 BLAST rule, source
extension v4/v5/v6 and user-approved homooligomer-chain admission supersede only
the original source-selection section. Retain28 exactly; add3VSV-A638,5JVL-A874,
3F6B-A525,6P63-C595, yielding8/8/8/8. Store source subgroup28 monomer/4 homooligomer
chains separately. No claim of absence from model pretraining or autonomous
monomer folding of an oligomer-derived chain.

Before GPU: validate all native/GT hashes, build chemical reference and topology
from native features only, verify geometry-module bytes against frozen2aa87043
execution lock, hash runtime code/imported Protenix/ESM/runner/configs and weights.
Native input packets contain no experimental labels. GT mapping stays separate
and is opened by posthoc scoring only.

At most8 GCD workers, static indices device,device+8,... . Per protein load frozen
Mini-ESM and native ESM2-3B, FP32/no autocast/no MC dropout. Compute4-cycle conditioning
once, share unchanged across3 independent identity-key noises300007/300017/300023.
This saves redundant deterministic conditioning work; still report4 cycles and one
diffusion call per sample. Preserve existing packed tensor layout, identity
augmentation, gamma0=0/lambda=1/eta=1 and stable-Euler endpoint implementation.
Actual schedule and4 Pairformer/1 diffusion call counts are checked/logged.

Raw prediction ceiling1800s per seed (first includes shared conditioning), plus
5400s external ceiling per protein process. Model load time is separately recorded.
On raw process failure keep existing completed seeds, mark missing seeds failed;
no alternative settings/retry. For every available raw output, run mean and tail
from identical initial inputs in separate processes,900s external ceiling each,
frozen3x60 L-BFGS and all other solver settings. Model exits before repairs to free
memory. Peak allocated/reserved memory and walltime recorded separately.

End-of-batch independent CPU pose/metric audit uses the existing audit implementation;
then fixed experimental observed-mask lDDT/TM/CA RMSD and protein bootstrap screening.
No best seed/iterate selection. Missing quality blocks positive quality screen;
96-instance/32-protein denominators never shrink. No validation-set tuning,
mutation search, training or derivative claim. Source-context and length strata
are descriptive subgroups, not posthoc selection rules.
