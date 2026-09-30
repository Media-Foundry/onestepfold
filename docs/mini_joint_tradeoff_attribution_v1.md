# Archived joint-endpoint tradeoff attribution

Read-only follow-up to760c55ea. Same14 supported predictions,7 development proteins,
two archived C4/S1 noises;3CR6 skipped source retained. No new prediction, optimizer,
training, coordinate edits, independent32 access or acceptance changes.

Analyze five saved states: raw,whole-ideal local zero,start after coupled sidechain
fit,zero-start joint final,sidechain-start joint final. Pairwise contrasts fixed:
start-local,warm_final-start,zero_final-local,warm_final-zero_final,warm_final-raw,
zero_final-raw. Source archive/member/row/report/lock hashes must pass first.

Retain existing atom-averaged inter-residue lDDT:GT distance<15Å,strict thresholds
.5/1/2/4Å. Compute AA and CA separately, with THEIR OWN neighbours and normalization.
Use undirected pair weight(1/n_i+1/n_j)/Nvalid for additive decomposition; do not
confuse AA CA-centred scores with CA-only lDDT. Partitions:backbone(N/CA/C/O) pair
classes BB/BO/OO;sequence separation1/2–4/5+;their cross;four threshold contributions.
OXT belongs to 'other'. Report supports and contributions, not uniform pair means.

Along the SAME GT-defined evaluated pairs, additionally measure weighted absolute
pair-distance error to experimental GT and to raw. These are descriptive continuous
errors,not replacement gates;raw-defined contact selection is not used. Distinguish
smaller raw-coordinate displacement from preserved raw distances and GT accuracy.
Report all cases and proteins;average seeds within protein then equal proteins.

Decompose archived final rho100 objective into raw coordinate anchor,rotation and
torsion regularization,each connection term,mean repulsion,tail repulsion and budget.
Recompute anchor/regularizers/connection/budget from coords and saved angles/onsets;
mean/tail repulsion use previously independently audited archived terms, clearly
marked as such. Components must add to the audited final objective. No claim that
an additive objective or metric category proves a causal mechanism.

Independent check:directed dense matrices,per-centre normalization,all partitions,
continuous distances and summary contrasts. Directly recompute angular/coordinate
terms;existing source audit covers chemistry exclusions and repulsion. Preserve
all signed effects and cancellation. No correlation p-values or prevalence claims
from14 measurements of7 reused proteins. Finish with one concrete method decision,
not another initialization or weight sweep. Goal remains a chemically valid,
accurate,differentiable one-step output,not just improvement on these diagnostics.
