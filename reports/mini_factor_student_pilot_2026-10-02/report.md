# Factor-only student pilot: exact target s remains oracle

TRAIN rows evaluate four predeclared fit-probe parents; validation rows evaluate all eight held-out parents.

|Role|Arm|Latent NMSE|rho|Top1|regret|Local mean A|>1A|Geometry pass|New fail vs Baseline|
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
|train|baseline|0.0000|0.999232|16/16|0.000000|0.0028|0/304|91/304|0|
|train|wt_z|1.0000|0.422807|5/16|0.058260|0.7231|52/304|90/304|2|
|train|oracle_r32|0.0474|0.995285|15/16|0.000249|0.0175|0/304|89/304|2|
|train|student_0|1.0553|0.484649|5/16|0.036037|0.5823|48/304|90/304|2|
|train|student_1|0.9758|0.443531|5/16|0.058260|0.6305|48/304|90/304|2|
|validation|baseline|0.0000|0.999671|32/32|0.000000|0.0048|0/608|360/608|0|
|validation|wt_z|1.0000|0.300877|10/32|0.256189|0.8761|165/608|362/608|40|
|validation|oracle_r32|0.0640|0.994518|30/32|0.000021|0.0439|0/608|353/608|13|
|validation|student_0|1.0017|0.305811|9/32|0.341726|0.8794|168/608|357/608|42|
|validation|student_1|0.9984|0.299726|10/32|0.249414|0.8745|165/608|357/608|42|
