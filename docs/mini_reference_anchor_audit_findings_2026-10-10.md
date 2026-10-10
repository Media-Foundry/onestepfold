# Reference-anchor audit: implementation passed; learning untested

The same native pair suffix is now run on a legal WT reference, and its drift
from native WT C4 is subtracted from each candidate. This changes the training
graph without changing parameter count or initial predictions. All1,824
initial candidate predictions across48 sites/two seeds matched both the old
class and unadapted output bit for bit; candidate single/input remain unchanged.

| Initial full-TRAIN measurement | Seed272001 | Seed272003 |
|---|---:|---:|
| Original full gradient norm |3.024749|3.024669|
| Anchored full gradient norm |0.203719|0.203697|
| Original common gradient norm |3.019848|3.019771|
| Anchored common gradient norm |0.150703|0.150690|
| AA gradient norm (unchanged) |0.063418|0.063407|
| Original full/AA cosine |0.087705|0.087670|
| Anchored full/AA cosine |0.882849|0.882843|

All27 TRAIN sites in each seed have better full/AA alignment and a smaller
common gradient. Eight previously nonpositive full/AA site cosines become zero
nonpositive cases. The native copied weights are identical between seeds;
only the edit-branch initialization differs. These are not two independent
model-family confirmations. Initial objective remains0.8683360244777337.

At fixed parameters, a candidate-common subtraction leaves centered AA
predictions and their objective gradient unchanged in real arithmetic. It
does not add AA capacity or teacher information. The improved alignment comes
from the altered common-gradient reference pullback. It is an instantaneous
gradient result, not AdamW update alignment, optimization or generalization.

The streaming reference-gradient proxy matches the joint19-candidate autograd
graph with relative errors1.490e-6/1.490e-6, below locked5e-5. The original full
gradient matches the preceding audit exactly. Twelve CPU tests passed, including
FP64 finite differences, shared pullback and stale/foreign anchor rejection.
For a fixed historical trained checkpoint, centered subtraction differs by at
most6.425e-5, within the explicit FP32 rounding bound3.090e-4; no-edit and
candidate-order identity hold. That post-hoc test did not evaluate quality.

The audit created24 WT-only boundary caches by exactly replaying WT3->WT4,
not new mutant teachers. Cost:230.993s total audit,473,680,104 cache bytes,
11,790,952,448 peak allocated device bytes. No optimizer, S1, full C4 or input
encoder call occurred. Both original and anchored backward work is recorded;
this is not a speed benchmark.

All839 source hashes and24 reference caches were verified before export.
Local NumPy independently reproduced all vector differences, norms and six
cosines per seed. This arithmetic check did not repeat native backpropagation.
Archive SHA256: a6f1298f01f7e400044abe6b29032a76507f3b9e297b4ef911c34654e1530ec1.
The report, lock, tests, vectors and executed source are in
`reports/mini_reference_anchor_audit_2026-10-10/collected`.

The evidence supports one separately locked same-budget training comparison.
It does not establish that reference subtraction repairs an old checkpoint,
that common gradients were the sole bottleneck, or that folding quality has
improved. The existing oracle-pair interface and all negative controls remain.
