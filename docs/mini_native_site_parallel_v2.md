# Native Mini site-parallel audit: launch authorization correction

The first implementation attempt stopped before warmup/updates because the
controller omitted the existing `FASTGLYCAN_AUTHORIZED_HIP_0_5=1` flag. The
repository's runtime correctly rejected HIP4/5 without that explicit flag;
torchrun terminated all workers and the finite controller recorded failure.
The v1 directory, logs, source and lock remain unchanged. This was not a
numerical-equivalence result or a performance result.

The corrected controller supplies this existing authorization, matching the
user's already granted HIP0–5 scope and the independently verified PCI map.
No selector spoofing, policy change, model change, numerical tolerance change,
data change or budget extension is made. The new attempt has a separate root
and lock and must rerun CPU evidence tests plus the existing device-policy tests
before launch. All execution and acceptance rules in
[v1](mini_native_site_parallel_v1.md) remain in force. Its protocol bytes and
the failed attempt's lock hash are bound in the new lock for traceability.
