# Fixed initial-tail follow-up

|TRAIN|Update|AA mean|Fixed 7 AA|Re-ranked AA tail|Same 7?|CA initial-tail mean|
|---:|---:|---:|---:|---:|---|---:|
|2048|0|0.79201|0.42397|0.42397|True|0.46683|
|2048|512|0.79078|0.39925|0.39925|True|0.43205|
|2048|1024|0.79090|0.39040|0.39040|True|0.42169|
|2048|2048|0.79702|0.38311|0.38311|True|0.41311|
|2048|4096|0.80339|0.37934|0.37934|True|0.40792|
|8192|0|0.79201|0.42397|0.42397|True|0.46683|
|8192|512|0.78987|0.40511|0.40511|True|0.43968|
|8192|1024|0.79272|0.39711|0.39711|True|0.42981|
|8192|2048|0.79396|0.37005|0.36743|False|0.39486|
|8192|4096|0.80100|0.37377|0.37377|True|0.39915|

Exploratory reused-DEV analysis. Cohorts fixed by initial bridge, never used for training selection. Conditional within-cohort bootstrap, not independent confirmation; 2 K1 noises averaged, not best-of-K.
