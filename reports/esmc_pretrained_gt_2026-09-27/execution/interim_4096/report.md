# Pretrained ESMC scaling: fixed-checkpoint interim assessment

Through update4096 (16384 sample presentations/arm). Primary endpoint remains4096; this report does not modify training.

|TRAIN size|Update|DEV lDDT|DEV TM|Worst5% lDDT|Worst5% TM|TRAIN32 lDDT|C–N MAE Å|Chirality|
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
|2048|0|0.79201|0.88586|0.42397|0.38911|0.78502|0.10248|0.99859|
|2048|512|0.79078|0.88886|0.39925|0.37995|0.78773|0.10284|0.99877|
|2048|1024|0.79090|0.88848|0.39040|0.38359|0.79653|0.09963|0.99862|
|2048|2048|0.79702|0.89098|0.38311|0.38948|0.80782|0.09340|0.99868|
|2048|4096|0.80339|0.89475|0.37934|0.39332|0.81873|0.08594|0.99895|
|8192|0|0.79201|0.88586|0.42397|0.38911|0.78502|0.10248|0.99859|
|8192|512|0.78987|0.88865|0.40511|0.39258|0.78430|0.10399|0.99907|
|8192|1024|0.79272|0.89026|0.39711|0.38909|0.79149|0.09641|0.99921|
|8192|2048|0.79396|0.88904|0.36743|0.36570|0.79979|0.09514|0.99880|
|8192|4096|0.80100|0.89470|0.37377|0.40929|0.80916|0.08750|0.99887|

|Comparison|Metric|Mean Δ [95% CI]|Worst5% Δ [95% CI]|Targets losing >.05|
|---|---|---|---|---:|
|8192_minus_2048|all_atom_lddt|-0.00240 [-0.00405,-0.00075]|-0.00558 [-0.01163,+0.00225]|0/128|
|8192_minus_2048|tm_score_ca_observed|-0.00005 [-0.00195,+0.00199]|+0.01597 [-0.00540,+0.02212]|0/128|
|2048_minus_native_reference|all_atom_lddt|-0.01617 [-0.02864,-0.00511]|-0.12761 [-0.17194,-0.07565]|19/128|
|2048_minus_native_reference|tm_score_ca_observed|-0.01913 [-0.03070,-0.00903]|-0.09128 [-0.16413,-0.01440]|17/128|
|2048_minus_esmc_bridge|all_atom_lddt|+0.01138 [+0.00648,+0.01615]|-0.04463 [-0.07783,-0.01558]|4/128|
|2048_minus_esmc_bridge|tm_score_ca_observed|+0.00889 [+0.00467,+0.01356]|+0.00421 [-0.01974,+0.04720]|0/128|
|8192_minus_native_reference|all_atom_lddt|-0.01856 [-0.03073,-0.00748]|-0.13319 [-0.17725,-0.08135]|23/128|
|8192_minus_native_reference|tm_score_ca_observed|-0.01918 [-0.03028,-0.00937]|-0.07531 [-0.14980,-0.00901]|17/128|
|8192_minus_esmc_bridge|all_atom_lddt|+0.00898 [+0.00386,+0.01380]|-0.05020 [-0.08809,-0.01937]|6/128|
|8192_minus_esmc_bridge|tm_score_ca_observed|+0.00885 [+0.00518,+0.01276]|+0.02018 [-0.00609,+0.04783]|1/128|

8192 proteins are not all encountered before2048 updates. Same updates/samples do not imply equal FLOPs or convergence. TRAIN32 is a common probe, not a full training-set evaluation.
Bootstrap5000 seed20260926, protein-level exploratory intervals; unadjusted for homology and multiple comparisons. DEV is reused and highly homologous. Two noise views are not independent training repeats and are not best-of-K. Chemistry checks here are partial.
