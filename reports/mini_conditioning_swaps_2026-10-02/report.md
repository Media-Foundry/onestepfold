# Conditioning information-path swaps

Exact is a model reference, not experimental truth. Chemistry stays target in all arms.

|Arm|AA fidelity lDDT|Local CA RMSD|19-AA Spearman|Top1 match|Top1 regret|Chemistry pass/1900|
|---|---:|---:|---:|---:|---:|---:|
|exact|1.000000|0.000000|1.000000|1.000|0.000000|884|
|wt_trunk|0.974037|0.713121|0.252386|0.120|0.081457|925|
|chem_only|0.974035|0.712621|0.251211|0.130|0.079908|923|
|target_trunk_only|1.000000|0.006732|0.999316|1.000|0.000000|888|
|local_only|0.975943|0.643904|0.332368|0.140|0.045916|934|
|global_only|0.997361|0.238424|0.953632|0.830|0.002309|865|
