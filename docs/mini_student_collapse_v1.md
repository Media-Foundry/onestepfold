# Read-only student candidate-diversity audit v1

2026-10-03; following161712a2. Frozen coverage checkpoints only. No optimization,
checkpoint selection, new C4/ESM/S1, or changes to Mini/student forward.

Probe all four coverage runs at initialization and10920/21840/32760, all ten
TRAIN sites per run, all19 non-WT candidates:160 fixed state/site probes. Record
query embeddings, mix input/output, four node blocks, left/right/AA projections,
pair readout preactivations/GELUs/linear outputs, per-candidate centered RMS,
exact candidate identity, minima/maxima/zero fraction, backward activation norms,
parameter branch gradients and parameter changes from initialization/previous save.
Use original pure raw Δz NMSE for backward; do NOT call optimizer.step. Hooks
retain activations/adjoints but do not replace tensors or alter numerical outputs.
Hash checkpoints/source and replay loss against archived snapshots. Free parameters
are unchanged; inspect same state on all ten contexts rather than one selected case.

Initialization has a zero final readout by construction; that alone is not a
training failure. Logs only sample every64 ten-context cycles (first630
updates, steps631–640), checkpoints are much coarser. Report earliest observed
loss of diversity; do not infer its exact onset, hidden earlier recovery, or root
cause beyond observed layers. A saturation pattern is a local computational
observation, not proof a specific LR or initialization caused it. No repair/retry
until a separately defined experiment. Current C4/S1 derivative evidence unchanged.
