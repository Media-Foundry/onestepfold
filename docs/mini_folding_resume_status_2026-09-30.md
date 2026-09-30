# Folding mainline restored: data expansion and next cycle

The active order is C4/S1 folding first, BindCraft later. Interface-target requests
and mutation searches are deferred. The retained full-diffusion checkpoint still
has the documented fresh32 AA0.801482 versus nativeS1 0.798813/S2 0.806460. No new
model quality result is claimed by this data-preparation work.

## Completed source work on HPC3

- Source array662214: two12-thread CPU allocations (one unused GPU reserved each),
  completed35s/54s. All783 fixed candidates rebuilt,380 native passes; mutual
  isolation retained296 additions, total424 including the original128.
- Selection/audit662216: completed3m07s, independently reparsed91,468 HSP records,
  checked5230 files,1152 inherited files, GT mapping and64 prior validation exclusions.
- Full catalog remainder search662218: completed51s. The unchanged catalog and
  support rules provided275 new identity-eligible groups beyond the original4096
  pool;66 remained after sequence search against history and current data.
- Admission662221: completed2m42s, added31 qualified isolated sources. Total455,
  short57 of512. Original incomplete512 flags remain false. This is the outcome
  of this fixed selection procedure, not a maximum independent-set proof.

No cutoff, chemistry or isolation rule was weakened. This is not the earlier
29.7k dataset: these are much more restricted sources isolated from historical
reference material. Current work does not meet the long-term30k training ambition.
DiamondHill is not used for new compute after the documented memory hardware error.

## Explicit size/split amendment before any new model predictions

Do not stall the folding experiment solely to reach the nominal512 target.
Under mini_folding_scaling_cycle_v1.md, preserve original TRAIN128; reserve32
never-predicted additional sources by frozen hash and length strata, before caching.
This yields TRAIN423 and newVAL32. Old source packets remain immutable; the new
role manifest explicitly records their former source-only TRAIN label.

| Set | Count | Length range | >=256 residues | Monomer sources |
|---|---:|---:|---:|---:|
| Expanded TRAIN |423|50–968|117|13|
| New validation |32|57–763|16|1|

The other sources come from supported homooligomer chains. Changed composition is
reported; the comparison is not an isolated causal estimate of data count alone.
Prior validation64 remain outside both sets. New validation is independent of
method development, not guaranteed absent from public pretrained models.

## Locked next experiment and execution boundary

Same retained full512 checkpoint, original128 versus expanded423; each2048 new
updates/8192 exposures, same reset AdamW/schedule and loss, full native diffusion
scope, frozen ESM2/Pairformer, C4/S1/K1. New validation only at the fixed terminal;
no checkpoint selection or best-of-noise. Both terminal quality and chemistry
remain necessary evidence. The split, per-arm orders and coefficients are locked
in cycle/lock.json in the local report archive.

Cache preparation662224 completed36s, verified source and public model hashes.
First cache shard662226_0 completed on H10080GB in141.51s:56conditioning entries,
52TRAIN reload replays passed,224Pairformer cycles/364diffusion NFEs,46.11GB peak
allocated memory. Remaining7 shards662228 are running after that successful
dependency, with automatic cancellation on invalid dependency. Cache
uses native ESM2/C4 and TRAIN-only S1/S2 references; validation gets conditioning
only. No experimental GT enters conditioning. This is NOT parameter training.
Cache integrity/replay audit and learned-checkpoint runtime preflight still precede
any optimizer update. No new model checkpoint has been created this cycle.

Remote roots under `/data/user/shuang886/Folding/`:
`diffusion_expanded_sources_hpc3_v1_20260930`,
`folding_source_extension_v1_20260930`, `folding_scale_cycle_v1_20260930`,
`folding_scale_cache_v1_20260930`.

Source455 root contains explicit symlinks to the424 inherited packet directories;
copy those targets when relocating. All selected packet bytes are hash-bound.
Reports: `reports/mini_folding_resume_2026-09-30/`. No model-quality, throughput or
training-convergence improvement can be inferred from source admission success.

## ESMC follow-up

User suggested testing ESMC. Retain a later matched conditioner-interface comparison
after this folding control: same core, data and budget, explicit dimensional and
distribution adaptation, original hard-endpoint replay and paired quality/chemistry.
Do not switch encoders during the current ESM2 data/optimization comparison or
assume existing ESMC multilayer caches can directly replace native ESM2 features.
No new ESMC experiment was launched by this note.
