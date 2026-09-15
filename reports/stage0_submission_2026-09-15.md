# Stage 0A Submission Record

This is an operational submission record, not an accuracy report. No
Protenix structure metric is claimed until the jobs complete and their outputs
are validated against the frozen `stage0_v1` manifests.

## Runtime

- Partition: `i64m1tga800ue`
- Per-point resources: one `A800`, 8 CPUs, 64G RAM, 12-hour limit
- Runtime package: `protenix==1.1.0`
- Model: `protenix_mini_esm_v0.5.0`
- Triangle kernels: PyTorch (`torch`)
- Layer norm: PyTorch (`LAYERNORM_TYPE=torch`)
- Precision: BF16, TF32 disabled
- Input: 1,024 frozen temporal-dev targets, maximum length 1,024
- Seed: 101, one sample

The Protenix wheel SHA256 is
`074fa0395c9cd980257a868f55fc9ccd0d432440e3f56a8bbdf234d21bcb388e`.
The Mini checkpoint SHA256 is
`1301bba9ad322518eace60fd244ded7904439f55317e90d402cc7a0c06026664`.
The ESM2-3B conditioner (`esm2_t36_3B_UR50D.pt`) SHA256 is
`7de8b4082ba15891959ab368b77ce3886697af1efb16d3c9e9e7b0c5d3f07500`.

## Smoke Gate

Job `12754884` completed on `gpu1-43` in 12 seconds. It verified CUDA,
Torch 2.9.1+cu128, A800 visibility, Protenix 1.1.0 import, and CLI startup.
It did not run structure inference.

Functional one-target job `12755045` was submitted with a 30-minute limit. The
full sweep is gated on `afterok:12755045`.

## Full Sweep

The nine independent jobs are:

```text
c1_s1  12755102
c1_s2  12755103
c1_s5  12755104
c2_s1  12755105
c2_s2  12755106
c2_s5  12755107
c4_s1  12755108
c4_s2  12755109
c4_s5  12755110
```

At submission they were all `PENDING (Dependency)` on the functional smoke;
the smoke itself was `PENDING (Priority)`. Each point writes to its own output
directory under `/hpc2hdd/home/shuang886/Folding/stage0_v1/protenix_runs` and
can be retried independently with `STAGE0_SETTING=<name>`.
