# ChordFold editing pilot v1

Four development pairs × two seeds. No training or recycle compression.

|Method|CA-lDDT|Global CA RMSD|Local target RMSD|Nonlocal motion|Local beats copy|Severe pairs|Zero severe + checked chirality|
|---|---:|---:|---:|---:|---:|---:|---:|
|copy_source|0.990252|0.3177|0.2351|0.0000|0/8|N/A|N/A|
|cold_s1|0.963771|0.8700|0.6856|1.0175|0/8|0|8|
|cold_s2|0.968678|0.8291|0.6745|0.9789|0/8|0|8|
|source_sigma16|0.971109|0.7352|0.5137|0.8921|0/8|1|7|
|source_sigma1|0.989290|0.3900|0.2492|0.2284|3/8|0|8|
|naive_refined|0.988462|0.3960|0.2597|0.2417|1/8|0|8|
|smooth_refined|0.988113|0.3987|0.2821|0.2451|1/8|0|8|
|naive_backbone|0.989965|0.3248|0.2468|0.0712|4/8|N/A|N/A|
|smooth_backbone|0.989520|0.3288|0.2748|0.0835|3/8|N/A|N/A|

Raw paired metrics, native chemistry limitations, timing and actual query counts are retained in report.json.
The sigma-domain edit is a proxy, not a validated transfer of ChordEdit theory. Copy has no target all-atom score.
