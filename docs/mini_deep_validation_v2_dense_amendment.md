# Deep Validation v2: correction of the dense control

Registered after the original A/B outcomes and BEFORE any whole-field dense outcome.
Original protocol,38runs,gate records and triggered H capture are retained unchanged.
This amendment corrects a limitation of our implementation of the user's requested
dense bottleneck control; it is not extra training of a failed checkpoint.

The original dense head maps each node's128 features through the same affine row
readout. Across19AA×84residues it predicts a1596×10752 matrix with a restricted row
representation. Post-hoc weighted least-squares analysis gives an attainable lower
bound of0.2942386, close to the observed0.2946946 best run. Thus it cannot answer
whether a dense whole-field generator can memorize these labels to NMSE0.1.

Correction: retain the small WT-only backbone; pool its candidate-specific node
states (mean plus mutation-site state), project to32 query features, then directly
read out84×84×128 values. This is about30M parameters and FIXED LENGTH, an explicit
capacity/output diagnostic rather than an efficient deployment model. No UV product
and no shared128-dimensional row space across AA×residues. The comparison changes
capacity AND output organization, so it cannot uniquely attribute success to one.

Before fitting, verify that the19 initial query feature vectors plus affine bias
have row rank19, and that a closed-form final-layer solution reconstructs all labels
in FP64 and FP32. Discard these fitted coefficients. Every training job starts with
the SAME fresh zero output head as prescribed, never the closed-form oracle.

Six continuous runs: seeds231301/231303 × LR1e-4/3e-4/1e-3,8192updates, full19AA batch,
same AdamW/weight decay1e-4/clip1/eps1e-8, same checkpoints512/1024/2048/4096/8192.
Only1W53 T37, no additional teacher/S1/geometry loss, no new hyperparameter sweep.
Only HIP_VISIBLE_DEVICES0–5; no CUDA_VISIBLE_DEVICES. Start after the original
controller AND its GPU audit finish to avoid overlapping allocations.

Report primary0.10 and secondary0.12 two-seed fit gates. Whole-field dense remains
ineligible for C–G transferable-factor promotion because of its fixed-length output
and different cost. A positive fit rescinds an interpretation that ALL tested final-
state generators failed; it does not erase original failures or H data. H remains a
captured diagnostic asset, not grounds to declare final-state regression impossible.
Do not train blockwise students or extend the original factor grid in this batch.
