HPC二期
CPU资源池队列/分区
队列/分区名称	优先级	价格	资源限制	作业时长默认限制	资源单台规格
CPU规格	内存规格	数据盘规格
i64m512u	共享(低)	低档	1024核	7天	2 * Intel(R) Xeon(R) Platinum 8358P CPU 32C @ 2.60GHz	512GB	/
i64m512ue	独占(中)	中档	1024核
emergency_cpu	应急(高)	高档	512核
long_cpu	共享(低)	低档	1024核	14天
i64m512r	共享(低)	低档	128核	7天	2 * Intel(R) Xeon(R) Platinum 8358P CPU 32C @ 2.60GHz	512GB	6 * 1.92TB
i64m512re	独占(中)	中档	128核
a128m512u	共享(低)	低档	256核	7天	2 * AMD EPYC 7763 64-Core Processor 2450 64C @ 2.45GHz	512GB	/
a128m512ue	独占(中)	中档	128核
GPU资源池队列/分区
队列/分区名称	优先级	价格	资源限制	作业时长默认限制	资源单台规格
CPU规格	GPU规格	内存规格	数据盘规格
i64m1tga800u	共享(低)	CPU低档 GPU低档	128核 16卡	7天	2 * Intel(R) Xeon(R) Platinum 8358P CPU 32C @ 2.60GHz	8 * NVIDIA A800-SXM4-80GB	1024GB	6 * 1.92TB（部分节点）
i64m1tga800ue	独占(中)	CPU中档 GPU中档	64核 8卡
emergency_gpu	应急(高)	CPU高档 GPU高档	64核 8卡
long_gpu	共享(低)	CPU低档 GPU低档	128核 16卡	14天
i64m1tga40u	共享(低)	CPU低档 GPU低档	128核 16卡	7天	2 * Intel(R) Xeon(R) Platinum 8358P CPU 32C @ 2.60GHz	8 * NVIDIA A40-48GB	1024GB	/
i64m1tga40ue	独占(中)	CPU中档 GPU中档	64核 8卡
emergency_gpua40	应急(高)	CPU高档 GPU高档	64核 8卡
大内存资源池队列/分区
队列/分区名称	优先级	价格	资源限制	作业时长默认限制	资源单台规格
CPU规格	内存规格	数据盘规格
i96m3tu	共享(低)	低档	192核	7天	4 * Intel(R) Xeon(R) Gold 6348H CPU 24C @ 2.30GHz	3TB	/
i96m3tue	独占(中)	中档	192核

## OneStepFold Stage A

The full 244,406-entry catalog is submitted as five Slurm array buckets over
`long_cpu`, `i64m512r`, `i64m512re`, `a128m512u`, and `a128m512ue`. Each task owns
one deterministic SHA256 PDB-ID shard and requests the full node CPU capacity
and 500 GB memory (`64 CPU` on the i64 pools, `128 CPU` on the a128 pools).
`--exclusive` prevents co-location; the `r/re` and `u/ue` aliases share their
physical nodes and are serialized by Slurm. The task walltime is two hours,
with the 256 shards divided as 160/24/24/24/24. The scanner writes one
compressed JSONL shard and one error file per task, using `.part` files and
`--resume`.

```bash
scripts/submit_full_catalog_array.sh
```

The submission script loads Slurm itself and is intended to run from the
repository checkout. Override `CATALOG_DIR` when testing a separate output
root; never point two arrays at the same catalog directory.

The submitted job records are checked with:

```bash
squeue -u "$USER"
sacct -X -j JOBID --format=JobID,State,Elapsed,AllocCPUS,MaxRSS
find /hpc2hdd/home/shuang886/Folding/catalog_v1 -name 'shard-*.jsonl.gz' | wc -l
```

Do not run a second launcher against the same output directory. A full scan is
accepted only after successful and error counts sum to `244406`, PDB IDs are
unique, and all error/shard files have been audited.

## ESMC probe and cache

The ESMC operation runs on an A800 node after the GT/split artifacts are
frozen. The first job writes a 2,000-group all-layer probe; it is intentionally
separate from the eventual full cache so a layer-selection experiment does not
force a 37x larger corpus artifact.

The launcher expects the pinned revisions in the cache contract and an ESMC
runtime environment. On hpc2, the currently validated compatibility runtime is
the existing CUDA Torch environment plus the pinned Biohub source and its
dependency directory:

```bash
module load slurm
sbatch --job-name=onefold-esmc-probe \
  --partition=i64m1tga800u --gres=gpu:a800:1 \
  --cpus-per-task=8 --mem=64G --time=04:00:00 \
  --export=ALL,CODE_ROOT=/hpc2hdd/home/shuang886/Folding/catalog_pilot_code,\
ESM_ENV=/hpc2ssd/softwares/anaconda3/envs/af3,\
ESM_PYTHONPATH=/hpc2hdd/home/shuang886/Folding/vendor/esm-bf343ba:/hpc2hdd/home/shuang886/Folding/esmc_py311_pkgs,\
GROUPS=/hpc2hdd/home/shuang886/Folding/splits_v1/groups.jsonl.gz,\
OUTPUT_ROOT=/hpc2hdd/home/shuang886/Folding/esmc_probe_all,\
HF_REVISION=28aed46fcaf217dfa59f78a589bb449aa3ae5d98,\
CODE_REVISION=bf343ba264b650dff7a073643725f9aaa1fdbe8d,\
LIMIT=2000 \
  /hpc2hdd/home/shuang886/Folding/catalog_pilot_code/scripts/slurm_probe_esmc_layers.sh
```

For that compatibility environment, prepend
`/hpc2hdd/home/shuang886/Folding/vendor/esm-bf343ba` and
`/hpc2hdd/home/shuang886/Folding/esmc_py311_pkgs` to `PYTHONPATH` in the job
export. The production Python 3.12 environment should use Torch 2.11+ and the
same Biohub commit; do not mix the two environments in a benchmark table.

After the probe selects a feature variant, use
`scripts/slurm_build_esmc_cache.sh` with the same revisions and an independent
output root. Inspect `feature_spec.json`, `summary.json`, the manifest count,
and shard checksums before exposing the cache to model training.

## Stage 0A Protenix sweep

The compatibility sweep uses the official `protenix_mini_esm_v0.5.0` checkpoint
and its ESM2 conditioner. It is independent of the ESMC cache. Prefer an
exclusive A800 node in `i64m1tga800ue` for the 3x3 matrix; request the full
node resources and keep the backend fixed across all settings:

```bash
module load slurm
sbatch --partition=i64m1tga800ue --gres=gpu:a800:1 \
  --exclusive --cpus-per-task=64 --mem=1024G --time=07-00:00:00 \
  --export=ALL,INPUT_JSON=/path/to/temporal_dev_v1.json,\
OUTPUT_ROOT=/path/to/stage0_runs,PROTENIX_BIN=/path/to/protenix \
  scripts/slurm_stage0_protenix.sh
```

The runner must use `--use_default_params false`, `--cycle`, `--step`, and
`--sample 1` for every point, and must record the pinned Protenix commit,
checkpoint SHA256, GPU/backend, PyTorch/CUDA versions, seed, peak VRAM, and
separate sequence/trunk/structure/confidence/end-to-end timings. Do not mix
ESMC features into this compatibility baseline.

Freeze the Stage 0 views before submitting the GPU array:

```bash
PYTHONPATH=src python scripts/select_temporal_dev.py \
  --groups /hpc2hdd/home/shuang886/Folding/splits_v1/groups.jsonl.gz \
  --quality-index /hpc2hdd/home/shuang886/Folding/quality_v1/quality_index.jsonl.gz \
  --output-root /hpc2hdd/home/shuang886/Folding/stage0_v1 \
  --dev-size 1024 --seed 101
```

The resulting `temporal_dev_v1.jsonl.gz` has 1,024 groups and the frozen
complement has the remaining HQ-valid groups. The full strict low-homology
group list is stored separately and is excluded from dev sampling even when a
group lacks an HQ-valid coordinate target. The same command writes the fixed
128-group `temporal_variance_v1.jsonl.gz` subset from within dev.

Convert the frozen dev manifest to the Protenix list-of-targets format before
submitting the GPU job:

```bash
PYTHONPATH=src python scripts/build_protenix_input.py \
  --manifest /hpc2hdd/home/shuang886/Folding/stage0_v1/temporal_dev_v1.jsonl.gz \
  --output /hpc2hdd/home/shuang886/Folding/stage0_v1/temporal_dev_v1.json \
  --index-output /hpc2hdd/home/shuang886/Folding/stage0_v1/temporal_dev_v1.index.jsonl.gz
```
