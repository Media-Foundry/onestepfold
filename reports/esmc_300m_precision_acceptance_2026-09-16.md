# ESMC-300M Precision Cache Acceptance

The two W7900 cards on `Precision` generated a complete ESMC-300M final-layer
cache for the same 38,400 quality-valid exact sequence groups used by the main
ESMC-600M cache.

| field | value |
| --- | ---: |
| model | `biohub/ESMC-300M` |
| Hugging Face revision | `f0d413606442e6b433d5e75e9aae3285ca9b137f` |
| Biohub/esm revision | `bf343ba264b650dff7a073643725f9aaa1fdbe8d` |
| groups | 38,400 / 38,400 |
| residues | 11,615,845 |
| shards | 719 / 719 validated |
| dtype | BF16 |
| storage | 21 GB |
| partition wall times | 840.2 s / 847.4 s |

The cache used deterministic two-way SHA256 partitioning. The merged manifest
references tensors in `part-000/` and `part-001/` without rewriting them. The
validator checked exact group coverage, sequence lengths, feature/model
revisions, BF16 tensor shapes, and every shard checksum.

Artifacts:

```text
/media/WDisk/Datasets/OneStepFold/esmc_300m_final_v1
manifest SHA256: 70e91b5e0cb1837be5509fb6ee6b82a23217709172eda9e14489b82c32a8b42a
feature spec SHA256: 33a7fd1d172e93a14886c3057534985d8d2c30a087eaf1abf495456ff4036302
```

This is a conditioner-scale ablation artifact. ESMC-600M remains the primary
conditioner, and the ROCm pure-PyTorch runtime is not used as a cross-backend
latency benchmark.
