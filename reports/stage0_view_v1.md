# Stage 0A View Freeze

The Stage 0 compatibility baseline uses the frozen quality/split artifacts and
does not use the ESMC cache. `scripts/select_temporal_dev.py` was run on hpc2
with seed `101`, a dev size of `1024`, and a variance subset size of `128`.

The resulting counts are:

| View | Exact sequence groups | Coordinate targets |
| --- | ---: | ---: |
| Temporal candidates before HQ filtering | 6,711 | 12,940 records in the original split |
| HQ-valid temporal candidates | 3,464 | one deterministic target per group |
| `temporal_dev_v1` | 1,024 | 1,024 |
| `temporal_variance_v1` | 128 | 128, subset of dev |
| `frozen_temporal_test_v1` | 2,440 | 2,440 |
| Non-HQ temporal candidates | 3,247 | excluded from Stage 0 views |
| Strict low-homology groups | 15 | 8 have an HQ target; all 15 remain frozen |

For each exact group, the selected HQ record is ordered by frame coverage
descending, canonical heavy-atom coverage descending, resolution ascending,
and PDB ID ascending. Dev sampling is proportional over the joint strata:

```text
length x resolution x apo_like x experimental_method
```

The five output manifests, the complete strict low-homology group list, and
the Protenix JSON inputs are under:

```text
/hpc2hdd/home/shuang886/Folding/stage0_v1
```

The dev and test group sets are disjoint. A second generation with the same
inputs and seed produced identical SHA256 values for the dev, frozen-test,
group, and strict-low-homology manifests. The Protenix JSON inputs contain
1,024 and 128 top-level targets respectively, with unique names and sequence
lengths no greater than 1,024.

The nine inference points are the full factorial:

```text
(cycles, steps) = (1,1), (1,2), (1,5),
                  (2,1), (2,2), (2,5),
                  (4,1), (4,2), (4,5)
```

No Protenix inference has been claimed yet. The runtime is pinned to the
`protenix==1.1.0` wheel (SHA256 recorded in the protocol) and the
`protenix_mini_esm_v0.5.0` checkpoint (SHA256 recorded in the protocol). A
compute-node smoke test must still confirm the CUDA extension/backend path
before the sweep is submitted.
