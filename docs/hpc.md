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
