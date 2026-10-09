# Bounded replay of the stalled stage-aligned training prefix

Locked2026-10-10 after the n15 Final/272003 worker remained at the last written
step1420 for more than30minutes. The original process715286/proot715283 is
confirmed live; it is not classified as stopped or as a model-quality failure.
The original six-hour controller cap is unchanged. Other three n15 training
runs and all n1 runs completed. This is an execution diagnostic, not a new
architecture/objective experiment or a replacement scientific result.

Use the exact original checkpoint0, model/source/data/protocol hashes,
AdamW lr1e-4/wd1e-4/eps1e-8, clip1, two-candidate accumulation and original
27-site schedule. Independently replay updates1..1421 on availableHIP0. Compare
every recorded source loss and pre-clip gradient norm through1420. Record exact
equality and maximum absolute/relative deviations, rather than asserting the
unobserved entire parameter trajectory is bit-identical. Initial model digest
must match checkpoint0 and the declared initial digest. No additional random
seed, optimizer variant, weight change, data resampling or quality selection.

Save the replay model/optimizer at1420 and1421. Log candidate loading, forward,
backward, clipping and optimizer phases for the last two steps. No intrusive
hooks, target process signals, model memory writes or training-script changes.
No target-C4/native recycle/input encoder/S1 calls, no held-protein evaluation.
Both final and hint target caches retain their original label-only contracts.
This diagnostic adds at most1421 optimizer updates and2842 training candidate
forwards; it is not described as zero training or free cache inspection. Keep
these counts separate from the eight scientific runs.

15minute wall cap for this isolated diagnostic, with any timeout and partial
history retained. A successful replay does not prove the original process
has recovered, nor uniquely identify the GPU, proot or operator as root cause.
A divergent prefix cannot be represented as an exact resume. No automatic
continuation to8208 or replacement of the live original run is authorized by
this diagnostic protocol. Any necessary operational recovery must preserve
the failed attempt and explicitly account for repeated work.

UnrelatedHIP5 workload remains untouched. MSA/ESM preparation remains outside
this model-only cycle. Frozen Mini and all original scientific code are read
only. The independent read-only verification queue may process completed
models while waiting; that scheduling change adds no scientific updates.
