# Native Mini site-parallel audit evidence

`terminal/` contains all six worker reports, the immutable v3 lock and protocol,
both controller jobs, fifteen-test preflight, per-step times, independent CPU
verification and a separate local hash/metadata/storage-byte/timing recheck.
`launch_failures/` retains both earlier attempts, including exact startup source.

Successful root:
`/media/IntelSSD/onestepfold/hpc3_mirror_20261001/Folding/native_site_parallel_v3_20261010`

Audit lock SHA256:
`627d1ff1be72cba0559d66fa79a42ebcc4d290e148b6f9f717c2a4c9bd0f923e`

Full terminal archive (885 files, 324,208,640 bytes):
`/tmp/native_parallel_terminal_v3_20261010.tar` on DiamondHill and local machine.
SHA256: `38b693d14e603a10bbf1dd7466ba0bd75cf030eca4088167e15567a088ca92f8`.
Local extracted copy: `/tmp/native_parallel_terminal_v3_20261010`.
The twelve tensor snapshots and full frozen source are retained there and in
the authoritative remote run. They are not duplicated as large binaries in Git;
`terminal/collection_manifest.json` binds every included byte by path and SHA.

Recheck without Torch or GPU execution:

```sh
python reports/mini_native_site_parallel_2026-10-10/recheck.py \
  --root /tmp/native_parallel_terminal_v3_20261010 \
  --manifest /tmp/native_parallel_terminal_v3_20261010.json \
  --output /tmp/native_parallel_terminal_v3_local_recheck.json
```

The native workers and separate CPU verifier compare the actual tensors and
AdamW state. The local checker additionally compares tensor storage bytes and
decoded metadata; pickle object memoization and archive filenames need not be
identical. No tolerance was substituted for the strict tensor check.

`execution_setup/install_v3.py` records the actual installer; it refuses an
existing destination. `collect_v3.py` only accepts a completed, independently
verified run. Neither is a general production training/restart launcher.

See the [findings](../../docs/mini_native_site_parallel_findings_2026-10-10.md)
for timing boundaries, memory accounting, unsuccessful launches and limitations.
