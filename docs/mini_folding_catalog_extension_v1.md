# Complete the source universe beyond the initial4096 cap

2026-09-30. The frozen783-candidate reconstruction found380 native-preflight passes;
mutual isolation leaves296 additions, for424 TRAIN proteins, short88 of512.
Do not change that result or train a silently smaller set.

Read the SAME256 catalog shards, verifying hashes against the original source
lock. Reuse scan_adapter_sources without changing source/length/assembly/sequence
criteria. Consider all supported sequence groups outside the original4096 pool,
excluding historical identities/PDB/accessions and all prior TRAIN/validation.
The original census had4390 groups after historical identity filters; this is
exhaustion of the capped universe, not an unbounded new data crawl.

Choose each sequence group's representative by the existing resolution/PDB/chain/
assembly ordering, then SHA256('folding-catalog-remainder-v1:20260930:'+group_id).
No quality/chemistry prediction filtering, no new length quotas. Keep separate
extension indices; old pool indices must not be silently reused.

Search new candidates against all historical reference sequences, the424 selected
TRAIN and both revealed validation32 panels, plus a complete new/new search.
Use identical BLAST2.17.0 binaries verified by the pre-fault hashes, effective
dbsize and original scoring/search settings. Twelve CPU threads, one hidden GPU
reserved only because of acd_u scheduling; no inference or training.

Next admission stage must independently reparse HSPs using the original exclusion
rule, run unchanged native/GT preflight, and select isolated rows in frozen order
until88 additions or exhaustion. Audit source mapping and full final isolation
before any caching/training. Preserve all failures. If this entire supported
universe still falls short, report the actual ceiling of this selection procedure;
it is not a proof no other dataset is possible. A new explicit training-size or
source-support protocol would then be needed, not retroactive relabeling as512.

This script releases catalog scan and sequence-isolation search only. Its success
is not a complete source packet release or a started folding experiment.
