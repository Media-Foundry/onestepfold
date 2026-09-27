# Pretrained ESMC: TRAIN2048 versus TRAIN8192

Final4096 updates,16384 samples each. Two fixed K1 draws averaged per protein; no best-of-K.

|Training size|Updates|DEV lDDT|DEV TM|Worst5% lDDT|TRAIN32 lDDT|C–N MAE Å|Chirality|
|---:|---:|---:|---:|---:|---:|---:|---:|
|2048|0|0.79201|0.88586|0.42397|0.78502|0.10248|0.99859|
|2048|512|0.79078|0.88886|0.39925|0.78773|0.10284|0.99877|
|2048|1024|0.79090|0.88848|0.39040|0.79653|0.09963|0.99862|
|2048|2048|0.79702|0.89098|0.38311|0.80782|0.09340|0.99868|
|2048|4096|0.80339|0.89475|0.37934|0.81873|0.08594|0.99895|
|8192|0|0.79201|0.88586|0.42397|0.78502|0.10248|0.99859|
|8192|512|0.78987|0.88865|0.40511|0.78430|0.10399|0.99907|
|8192|1024|0.79272|0.89026|0.39711|0.79149|0.09641|0.99921|
|8192|2048|0.79396|0.88904|0.36743|0.79979|0.09514|0.99880|
|8192|4096|0.80100|0.89470|0.37377|0.80916|0.08750|0.99887|

|Final metric|8192 −2048 mean [95% CI]|Worst5% difference [95% CI]|Targets losing >.05|
|---|---|---|---:|
|all_atom_lddt|-0.00240 [-0.00405,-0.00075]|-0.00558 [-0.01163,+0.00225]|0/128|
|ca_lddt|-0.00282 [-0.00472,-0.00097]|-0.00876 [-0.01537,+0.00198]|1/128|
|tm_score_ca_observed|-0.00005 [-0.00195,+0.00199]|+0.01597 [-0.00540,+0.02212]|0/128|

Bootstrap5000 seed20260926, protein-level exploratory intervals, no homology/multiple-comparison correction. Same samples and updates do not imply equal FLOPs; measured cost is in JSON. Two exposures at8192 do not establish convergence. Partial chemistry metrics do not certify full chemical validity. No confidence or end-to-end timing claim.
