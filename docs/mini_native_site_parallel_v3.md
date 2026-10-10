# Native Mini site-parallel audit: loader isolation correction

The v2 launch failed before cache warmup or optimizer updates. Each worker had
one visible HIP device, but Protenix's native `DIST_WRAPPER` inherited torchrun's
local rank and world size. Its loader attempted `cuda:3` on a one-device worker;
it would also try to create its own NCCL process group. Separately, omission of
`PROTENIX_ROOT_DIR` made the loader start downloads in its default directory.
The v2 source, lock and logs remain intact. No numerical or timing result was
obtained. Partial default-directory downloads are not accepted checkpoints.

Reuse the repository's existing `configure_torchrun_worker` unchanged. Preserve
the six-rank rendezvous explicitly, select one authorized HIP device, and remove
torchrun rank variables before importing the native runtime. Load each native
replica as rank0/world1, then initialize our six-rank Gloo group explicitly.
Restore the original serial experiment's `PROTENIX_ROOT_DIR` and torch LayerNorm
environment. All original weight and source hashes remain mandatory. No installed
Protenix source, frozen scientific code or model parameters are modified.

Before launch, test all six launch identities against the installed native
`DistWrapper`, along with the prior state-equality and HIP-policy tests. Check
the existing weight directory, source hashes and actual PCI availability. The
new lock binds the previous two failed locks, original numerical protocol, this
correction and exact runtime environment. Keep full error tracebacks in reports.

The [v1](mini_native_site_parallel_v1.md) three-update, two-order budget and strict
bytewise acceptance remain unchanged. This is a new disposable infrastructure
attempt, not a restart of a scientific run. No automatic retries or modification
of a failed attempt is allowed. The [v2](mini_native_site_parallel_v2.md) six-HIP
authorization remains enabled. Success cannot establish new model quality.
