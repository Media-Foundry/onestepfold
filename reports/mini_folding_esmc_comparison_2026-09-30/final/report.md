# Matched ESMC/ESM2 C4/S1 interface comparison

Same retained512 diffusion checkpoint and chemistry. One TRAIN423-fitted affine bridge; frozen folding core. TRAIN32 and observed DEV32 remain separate, two fixed K1 noises averaged per protein. Not new independent confirmation.

## observed_dev32

|Model|AA-lDDT|CA-lDDT|Zero severe + strict /64|Both noises /32|Severe pairs|
|---|---:|---:|---:|---:|---:|
|retained|0.817664|0.902912|46|20|562|
|esmc|0.775075|0.853801|31|12|1279|

|Metric esmc-retained|Mean|95% CI|P01|P05|Worst5%|Below -0.05|
|---|---:|---|---:|---:|---:|---:|
|all_atom_lddt|-0.042589|[-0.07686826469917533, -0.01892687096653184]|-0.395411|-0.146287|-0.348785|8|
|ca_lddt|-0.049112|[-0.08999101679102577, -0.01969379383568954]|-0.475313|-0.202584|-0.439762|8|

New severe collision instances: 18; lost strict stereo: 8.

## train_probe32

|Model|AA-lDDT|CA-lDDT|Zero severe + strict /64|Both noises /32|Severe pairs|
|---|---:|---:|---:|---:|---:|
|retained|0.804773|0.885653|41|18|394|
|esmc|0.776735|0.856230|36|14|817|

|Metric esmc-retained|Mean|95% CI|P01|P05|Worst5%|Below -0.05|
|---|---:|---|---:|---:|---:|---:|
|all_atom_lddt|-0.028038|[-0.05981563279867898, -0.005709590378330575]|-0.327057|-0.096718|-0.263688|6|
|ca_lddt|-0.029423|[-0.0636322489146461, -0.005321983193778155]|-0.352130|-0.104666|-0.286657|6|

New severe collision instances: 7; lost strict stereo: 9.

## Global structure: aligned Cα RMSD (Å)

Lower RMSD is better. Positive candidate − reference differences mean deterioration, opposite to lDDT. These are the existing GT-aligned RMSD scores, without a new alignment or atom mask. Average both locked noises within each protein before aggregation. Intervals resample proteins, conditional on the fixed noises. This adds no acceptance threshold.

### observed_dev32: 32 proteins

|Model|Mean|Median|P95|P99|Worst5% mean|
|---|---:|---:|---:|---:|---:|
|retained|3.461940|1.645646|11.652819|21.681129|19.274131|
|esmc|4.846740|1.956400|17.569702|24.727910|23.188511|

|Candidate − reference|Mean Δ|95% CI|P95 Δ|P99 Δ|Worst5% Δ mean|RMSD increased, proteins|
|---|---:|---|---:|---:|---:|---:|
|esmc − retained|+1.384800|[+0.329992, +2.786813]|+7.768569|+15.013378|+13.718904|21/32|

### train_probe32: 32 proteins

|Model|Mean|Median|P95|P99|Worst5% mean|
|---|---:|---:|---:|---:|---:|
|retained|4.096304|1.743076|15.069876|21.068855|19.549990|
|esmc|5.535991|2.014727|17.918952|22.321598|21.387161|

|Candidate − reference|Mean Δ|95% CI|P95 Δ|P99 Δ|Worst5% Δ mean|RMSD increased, proteins|
|---|---:|---|---:|---:|---:|---:|
|esmc − retained|+1.439687|[+0.414898, +2.681039]|+9.471655|+10.920065|+10.523737|20/32|


Geometry checks are operational, not comprehensive chemistry certification. Timing excludes sequence encoders. No automatic model promotion.
