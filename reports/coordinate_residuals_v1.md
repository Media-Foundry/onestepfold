# Stage 1A Coordinate Residuals

temporal_dev_v1 only; frozen temporal test was not read.

Records: 1024; joint-hard subgroup: 76.
This compares standalone c2_s2 and c4_s2 predictions; it is not an in-forward hidden-state residual.

| subgroup | count | Kabsch Cα RMSD median | pair-distance RMSD median | residue p90 | active fraction | top-10 energy | pair local <=8 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| all | 1024 | 1.0764 | 0.7516 | 0.8366 | 0.0734 | 0.6585 | 0.0116 |
| hard | 76 | 5.2344 | 3.4220 | 7.0681 | 0.9080 | 0.2748 | 0.0027 |
| nonhard | 948 | 0.9261 | 0.6468 | 0.7471 | 0.0640 | 0.6755 | 0.0126 |
