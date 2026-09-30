# Source expansion status and hardware incident

The planned TRAIN128→512 source expansion is incomplete. It produced no new
training run or model checkpoint. Binding-interface design now has priority;
no further reconstruction jobs are released pending that task's definition.

The DiamondHill 192-worker preparation controller326565 exited1 after59.23s.
The first192 preflights yielded86 provisional additions; there is no final512
selection. Kernel logs report hardware memory corruption sending SIGBUS to
workers326630 and326608, followed by BrokenProcessPool. Cgroup OOM counters are
zero. This is not an OOM diagnosis or a source rejection. New partial packets
are preserved but unused. No assertion is made that all earlier results are
invalid, or which hardware component failed. New DiamondHill computation stops
pending hardware recovery and validation.

HPC3 recovery root:
`/data/user/shuang886/Folding/diffusion_expanded_sources_hpc3_v1_20260930`

Migration reused only inherited128 packets and frozen source metadata, not new
packets from the failed run. Local verification traced8 metadata hashes and1152
inherited files to the pre-fault Git-archived source lock. The44,692,114-byte
transfer archive SHA256 is
`d300faa345dd346a6f0c32a3b659e881c7e44c76b7a9ce424a208a35817f6be2`.

HPC3 preflight662168 failed on an import-cache issue after archive extraction.
The file existed; invalidating Python import caches resolved the cold-path lookup.
Failed code/logs remain preserved remotely. Retry662184 COMPLETED0:0 in2m21s:

-1349 transferred members verified by size and hash;
-783 candidate CIF hashes and128 inherited CIF provenance hashes matched;
-two inherited sequences rebuilt with identical native atom identity, topology,
  feature keys/dtypes and values; floating maximum absolute difference0;
-inherited128 packets copied, migration lock saved. This is source compatibility,
  not folding/GPU numerical parity or complete audit of a new training set.

acd_u requires a minimum1 reserved GPU even for these CPU jobs. Visibility was
empty; the preflight used4 CPUs and no GPU computation. The proposed2×96-worker
reconstruction tasks were NOT submitted. No source selection, feature extraction
or model training automatically follows the completed preflight.

Artifacts: `reports/mini_expanded_sources_2026-09-30/`, including kernel evidence,
partial-run status, transfer lineage, both preflight logs and final lock/result.
Scientific admission rules remain unchanged. The user-specified interface task
will determine whether further training-data expansion is useful.
