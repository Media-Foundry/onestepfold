# ESMC readiness for the folding mainline

**Subsequent structural outcome:** the fixed affine bridge was evaluated on
TRAIN32/observedDEV32 with the same retained C4/S1 core and reduced quality; it is
not promoted. See [matched results](mini_folding_esmc_comparison_findings_2026-09-30.md).
The extraction and fitting records below remain historical stage-specific evidence.

**Update2026-09-30:** a separate TRAIN-only interface initialization completed
(job662574, COMPLETED0:0,2m11s). It reuses the paired cache below and the existing fixed ridge method.
No folding prediction or core update is added, and global-distance training662548
continues unchanged. This supersedes only the earlier “not yet fit” execution
status below; the historical extraction/audit results remain unchanged. See
[locked bridge protocol](mini_folding_esmc_bridge_v1.md) and
[completed fit](mini_folding_esmc_bridge_findings_2026-09-30.md).

The current TRAIN128/TRAIN423 comparison keeps ESM2 and its frozen C4 conditioning.
This work prepares an ESMC alternative requested by the user; it does not alter
either training arm, generate validation structures, fit an interface, or choose
a new model. BindCraft work remains deferred.

**Completed:** retry662350 finished COMPLETED0:0 in1m02s. All455 sequences and
96886 residues are present in six verified shards. Worker acceptance checked all
sequence identities, finite tensor values, shapes/dtypes and offset coverage;
52/968-residue startup repeats are exact. Peak GPU allocation2,951,665,664 bytes.
An additional scheduler/hash audit verifies the completed job and all six shard
hashes, and confirms the active training lock is unchanged. This establishes cache
readiness under this runtime, not an ESMC folding-quality benefit. Storage is BF16;
the wrapper did not separately record the model's compute dtype.

## Paired native ESM2 features are also available

CPU-only audit662380 completed0:0 in1m54s (actual audit111.50s). All455 sequences
and96886 residues have finite, correctly shaped native ESM2 FP32 features
`[L,2560]` and ESMC BF16 features `[L,1152]`. Exact full-sequence SHA256 identities,
contiguous token/residue indices, single-chain layout, cache provenance and ESMC
offset lengths agree. Cohorts remain128 original TRAIN,295 added TRAIN and32 new
validation. The active training lock is unchanged.

All six ESMC shard hashes were rechecked, and both models' individual feature
tensor bytes were hashed. ESM2's full conditioning-container hashes are inherited
from the completed cache audit, not recomputed by this feature-only check. Residue
alignment is supported by the locked extraction code/provenance and native index
layout; this is not an independent re-extraction of either model. ESM2 features
already exist in each `conditioning.pt` under `features.esm_token_embedding`, so a
later matched interface fit does not require another ESM2 forward.

No experimental coordinates were read, no model was called, and no bridge was fit.
The32 validation feature identities were checked, but they must remain excluded
from interface fitting and model selection. Both feature sets being available
does not establish an ESMC folding benefit or interchangeability. Any later bridge
fit and folding comparison needs its own fixed protocol; the present C4/S1
training/evaluation is unchanged. The audit uses one CPU and hides the GPU reserved
by `acd_u`; it does not add GPU model computation.

Remote root: `/data/user/shuang886/Folding/folding_esm_pair_audit_v1_20260930`.
Reproducible script: `scripts/audit_folding_esm_pairs.py`.
Report, execution record and launcher are archived in
`reports/mini_folding_esmc_readiness_2026-09-30/paired_features/`.

## Existing assets are not a drop-in replacement

On HPC3, the final-layer cache at
`/data/user/shuang886/Folding/esmc_600m_final_v1` contains38400 sequence groups.
The prior29769 selection has intermediate-layer extraction assets. Exact full
sequence SHA256 plus length matching against the current455-source split gives:

|Current cohort|Sequences|Final-cache manifest matches|29769 selection matches|
|---|---:|---:|---:|
|Original TRAIN|128|3|3|
|Added TRAIN|295|7|7|
|New validation|32|1|1|

Thus444 current sequences lack an exact match in this final-cache manifest.
PDB identity or a similar sequence is not a valid substitute. The multilayer
column checks membership in the extraction selection, not current tensor validity
or filesystem availability. No full old-cache checksum/value audit was performed.
The existing512-sequence bridge fitting set has zero exact sequence overlaps with
these455, but this check alone does not establish homology isolation.

Existing bridge code explicitly maps ESMC1152 to the449-dimensional projected
input; native ESM2 uses2560 to449. Prior C1/S1 evaluation found an average and tail
loss from the affine bridge. That is evidence about that interface/training setup,
not a universal ESMC ranking or a current C4/S1 result. It is not reasonable to
silently replace the ESM2 tensor and reuse the native projection.

## Bounded uniform extraction

Inventory and dependency root:
`/data/user/shuang886/Folding/folding_esmc_readiness_v1_20260930`.
Its first job662348 failed after4s during import of an unbundled `gt_catalog`
from package initialization, before model loading or inference. Failed code/logs
remain unchanged. Retry root:
`/data/user/shuang886/Folding/folding_esmc_features_v1_20260930`.
Job662350 uses isolated package initializers with no optional structure imports;
the extractor/model code and scientific settings are unchanged. Dependencies are
an explicit symlink to the inventory root. Preserve that target when copying.
`acd_u`, one H100 allocation,4 CPUs,48GB host RAM,30-minute wall cap.
Re-extract all455 final-layer sequences (96886 residues) on the same runtime.
Repeating the11 overlaps avoids mixing different extraction backends. No MLC
comparison or GPU folding is added in this stage.

The pinned Biohub code is `bf343ba264b650dff7a073643725f9aaa1fdbe8d`; weights are
`28aed46fcaf217dfa59f78a589bb449aa3ae5d98`, already local. An isolated `deps/`
directory supplies missing packages via PYTHONPATH; the active `fold` environment
and all frozen training/evaluation code remain unchanged. Direct dependency
download on HPC3 failed; local downloaded CPython312 wheels were copied and
installed offline instead. Logs are retained. No model download is required.

Torch2.7.1 CUDA is inherited from the folding environment, below the Biohub
package's declared torch2.11 requirement. Successful imports alone are therefore
not acceptance: the actual GPU preflight and full extraction must run. Transformer
Engine/flash-attn/xformers are absent, so the library selects native PyTorch
normalization and SDPA. This is a separately recorded runtime, not a claim of
numerical equivalence to older caches or fused kernels.

Before release: original-TRAIN shortest52 and longest968 residues must produce
finite, residue-aligned features and exact repeated single-sequence forwards.
Then the unchanged extractor uses2048 batch-token and16384 shard-token budgets,
stores BF16 final features, removes BOS/EOS and verifies shape. Post-extraction
checks cover exact455 group identities/sequence hashes,423/32 roles, all shard
hashes, BF16 shapes, every tensor's finite values and contiguous nonoverlapping
residue offsets. Four existing cache-contract tests pass locally. The wrapper
and196 code/input/weight/metadata files are hash-bound before submission.

Completion requires `acceptance.json` plus scheduler COMPLETED0:0. A failed run
is preserved; imported modules or a partial manifest do not establish readiness.
Even a fully accepted cache is only sequence-feature preparation. A later
TRAIN-only interface fit must preserve the folding split, fixed C4/S1 sampler,
native chemistry and decoder checkpoint; evaluate quality/tails/chemistry with
matched controls before claiming an ESMC benefit. No such fit is launched here.
