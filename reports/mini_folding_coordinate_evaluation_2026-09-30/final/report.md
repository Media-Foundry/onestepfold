# C4/S1 coordinate-weight ablation: fixed terminal

Both 423-protein arms start from the same retained checkpoint and receive the same ordered 8192 exposures / 2048 updates. Only the experimental-GT aligned-coordinate weight changes from 0.01 to 0. GT local-distance and chemistry supervision remain; native S2 is auxiliary synthetic supervision. This is not model initialization from zero. ESM2 and C4 conditioning remain frozen.

Scores use observed experimental GT. Each protein contributes the mean of its two fixed noises; no best-of-noise or intermediate-checkpoint selection. Geometry counts describe the explicit severe-collision and checked-stereocentre criteria, not comprehensive chemical correctness or deployment approval.

## observed_validation32: 32 proteins

|Model|AA-lDDT|Cα-lDDT|Zero severe + strict stereo, instances|Both noises, proteins|Severe pairs total|
|---|---:|---:|---:|---:|---:|
|native_s1|0.815917|0.899536|30/64|9/32|902|
|native_s2|0.828004|0.910778|37/64|15/32|353|
|retained|0.817664|0.902912|46/64|20/32|562|
|expanded|0.818402|0.902915|44/64|20/32|540|
|coordinate_zero|0.819737|0.905059|45/64|22/32|451|

Positive quality differences favor the candidate. Intervals resample proteins, conditional on the two locked noises; they do not establish independence from pretraining.

|Candidate − reference|Metric|Mean Δ|95% CI|P01 Δ|P05 Δ|Worst5% Δ mean|Δ < −0.05, proteins|
|---|---|---:|---|---:|---:|---:|---:|
|coordinate_zero − expanded|AA|+0.001334|[+0.000729, +0.002046]|-0.001464|-0.000832|-0.001302|0/32|
|coordinate_zero − expanded|Cα|+0.002144|[+0.001249, +0.003255]|-0.001978|-0.000422|-0.001654|0/32|
|coordinate_zero − retained|AA|+0.002072|[+0.001316, +0.002865]|-0.002798|-0.000849|-0.002364|0/32|
|coordinate_zero − retained|Cα|+0.002147|[+0.001102, +0.003361]|-0.003524|-0.001410|-0.003019|0/32|
|coordinate_zero − native_s1|AA|+0.003820|[+0.002002, +0.005851]|-0.004549|-0.003666|-0.004318|0/32|
|coordinate_zero − native_s1|Cα|+0.005523|[+0.002577, +0.009031]|-0.005577|-0.002627|-0.005106|0/32|
|coordinate_zero − native_s2|AA|-0.008267|[-0.012280, -0.004771]|-0.042201|-0.027526|-0.039566|0/32|
|coordinate_zero − native_s2|Cα|-0.005719|[-0.010173, -0.002050]|-0.046256|-0.024730|-0.042538|1/32|
|expanded − retained|AA|+0.000738|[-0.000080, +0.001503]|-0.005954|-0.002069|-0.005071|0/32|
|expanded − retained|Cα|+0.000003|[-0.000888, +0.000863]|-0.006972|-0.002345|-0.005796|0/32|
|native_s2 − native_s1|AA|+0.012087|[+0.008207, +0.016551]|-0.000455|+0.001240|-0.000008|0/32|
|native_s2 − native_s1|Cα|+0.011241|[+0.006553, +0.017328]|-0.001357|-0.000386|-0.001131|0/32|

|Candidate − reference|New severe collision instances from zero|Lost strict stereo instances|
|---|---:|---:|
|coordinate_zero − expanded|1|1|
|coordinate_zero − retained|4|1|
|coordinate_zero − native_s1|2|0|
|coordinate_zero − native_s2|4|1|
|expanded − retained|6|1|
|native_s2 − native_s1|5|8|

Descriptive length/assembly subsets; overlapping views, not additional independent tests.

|Subset|Proteins|Candidate − reference|Mean AA Δ|Mean Cα Δ|
|---|---:|---|---:|---:|
|length_256_511|15|coordinate_zero − expanded|+0.001504|+0.002703|
|length_256_511|15|coordinate_zero − retained|+0.002344|+0.002518|
|length_256_511|15|coordinate_zero − native_s1|+0.004119|+0.005986|
|length_256_511|15|coordinate_zero − native_s2|-0.009145|-0.005693|
|length_256_511|15|expanded − retained|+0.000840|-0.000185|
|length_256_511|15|native_s2 − native_s1|+0.013264|+0.011679|
|length_50_255|16|coordinate_zero − expanded|+0.001015|+0.001470|
|length_50_255|16|coordinate_zero − retained|+0.002166|+0.002206|
|length_50_255|16|coordinate_zero − native_s1|+0.004086|+0.005675|
|length_50_255|16|coordinate_zero − native_s2|-0.005921|-0.004053|
|length_50_255|16|expanded − retained|+0.001151|+0.000735|
|length_50_255|16|native_s2 − native_s1|+0.010007|+0.009728|
|length_512_1024|1|coordinate_zero − expanded|+0.003887|+0.004543|
|length_512_1024|1|coordinate_zero − retained|-0.003507|-0.004348|
|length_512_1024|1|coordinate_zero − native_s1|-0.004927|-0.003865|
|length_512_1024|1|coordinate_zero − native_s2|-0.032632|-0.032755|
|length_512_1024|1|expanded − retained|-0.007394|-0.008891|
|length_512_1024|1|native_s2 − native_s1|+0.027706|+0.028890|
|monomer|1|coordinate_zero − expanded|-0.000878|-0.000111|
|monomer|1|coordinate_zero − retained|-0.000543|+0.001153|
|monomer|1|coordinate_zero − native_s1|-0.002156|+0.003449|
|monomer|1|coordinate_zero − native_s2|-0.004233|+0.000050|
|monomer|1|expanded − retained|+0.000335|+0.001264|
|monomer|1|native_s2 − native_s1|+0.002077|+0.003400|
|multimer_single_chain|31|coordinate_zero − expanded|+0.001406|+0.002217|
|multimer_single_chain|31|coordinate_zero − retained|+0.002157|+0.002179|
|multimer_single_chain|31|coordinate_zero − native_s1|+0.004012|+0.005590|
|multimer_single_chain|31|coordinate_zero − native_s2|-0.008397|-0.005905|
|multimer_single_chain|31|expanded − retained|+0.000751|-0.000038|
|multimer_single_chain|31|native_s2 − native_s1|+0.012409|+0.011494|

## original_train128: 128 proteins

|Model|AA-lDDT|Cα-lDDT|Zero severe + strict stereo, instances|Both noises, proteins|Severe pairs total|
|---|---:|---:|---:|---:|---:|
|native_s1|0.801184|0.878791|107/256|42/128|8134|
|native_s2|0.814059|0.891694|137/256|58/128|2356|
|retained|0.806455|0.885367|165/256|73/128|4311|
|expanded|0.808113|0.886040|183/256|82/128|3874|
|coordinate_zero|0.809857|0.888957|185/256|82/128|3036|

Positive quality differences favor the candidate. Intervals resample proteins, conditional on the two locked noises; they do not establish independence from pretraining.

|Candidate − reference|Metric|Mean Δ|95% CI|P01 Δ|P05 Δ|Worst5% Δ mean|Δ < −0.05, proteins|
|---|---|---:|---|---:|---:|---:|---:|
|coordinate_zero − expanded|AA|+0.001744|[+0.000799, +0.002868]|-0.006095|-0.001964|-0.004107|0/128|
|coordinate_zero − expanded|Cα|+0.002917|[+0.001708, +0.004423]|-0.004116|-0.001167|-0.002822|0/128|
|coordinate_zero − retained|AA|+0.003402|[+0.002704, +0.004163]|-0.003828|-0.000537|-0.002794|0/128|
|coordinate_zero − retained|Cα|+0.003590|[+0.002692, +0.004571]|-0.002734|-0.000850|-0.002248|0/128|
|coordinate_zero − native_s1|AA|+0.008673|[+0.006491, +0.011392]|-0.010084|-0.001588|-0.005888|0/128|
|coordinate_zero − native_s1|Cα|+0.010166|[+0.007384, +0.013806]|-0.007547|-0.001787|-0.004825|0/128|
|coordinate_zero − native_s2|AA|-0.004202|[-0.006644, -0.002090]|-0.069568|-0.020505|-0.042703|2/128|
|coordinate_zero − native_s2|Cα|-0.002738|[-0.005743, -0.000339]|-0.074061|-0.016218|-0.047612|2/128|
|expanded − retained|AA|+0.001658|[+0.000759, +0.002486]|-0.020037|-0.004801|-0.011892|0/128|
|expanded − retained|Cα|+0.000673|[-0.000433, +0.001675]|-0.027395|-0.005817|-0.015542|0/128|
|native_s2 − native_s1|AA|+0.012875|[+0.009331, +0.017393]|-0.024920|-0.001812|-0.012695|0/128|
|native_s2 − native_s1|Cα|+0.012904|[+0.008549, +0.019057]|-0.025146|-0.003637|-0.013402|0/128|

|Candidate − reference|New severe collision instances from zero|Lost strict stereo instances|
|---|---:|---:|
|coordinate_zero − expanded|9|6|
|coordinate_zero − retained|6|7|
|coordinate_zero − native_s1|1|5|
|coordinate_zero − native_s2|10|11|
|expanded − retained|5|5|
|native_s2 − native_s1|15|16|

Descriptive length/assembly subsets; overlapping views, not additional independent tests.

|Subset|Proteins|Candidate − reference|Mean AA Δ|Mean Cα Δ|
|---|---:|---|---:|---:|
|length_256_511|55|coordinate_zero − expanded|+0.000964|+0.001596|
|length_256_511|55|coordinate_zero − retained|+0.002535|+0.002322|
|length_256_511|55|coordinate_zero − native_s1|+0.006094|+0.006904|
|length_256_511|55|coordinate_zero − native_s2|-0.004442|-0.002137|
|length_256_511|55|expanded − retained|+0.001571|+0.000726|
|length_256_511|55|native_s2 − native_s1|+0.010536|+0.009041|
|length_50_255|64|coordinate_zero − expanded|+0.001166|+0.002502|
|length_50_255|64|coordinate_zero − retained|+0.003812|+0.004104|
|length_50_255|64|coordinate_zero − native_s1|+0.010922|+0.012764|
|length_50_255|64|coordinate_zero − native_s2|-0.001099|-0.000323|
|length_50_255|64|expanded − retained|+0.002646|+0.001602|
|length_50_255|64|native_s2 − native_s1|+0.012021|+0.013087|
|length_512_1024|9|coordinate_zero − expanded|+0.010625|+0.013940|
|length_512_1024|9|coordinate_zero − retained|+0.005785|+0.007678|
|length_512_1024|9|coordinate_zero − native_s1|+0.008436|+0.011624|
|length_512_1024|9|coordinate_zero − native_s2|-0.024798|-0.023585|
|length_512_1024|9|expanded − retained|-0.004840|-0.006262|
|length_512_1024|9|native_s2 − native_s1|+0.033234|+0.035209|
|monomer|5|coordinate_zero − expanded|+0.001517|+0.002179|
|monomer|5|coordinate_zero − retained|+0.003996|+0.003865|
|monomer|5|coordinate_zero − native_s1|+0.010782|+0.012943|
|monomer|5|coordinate_zero − native_s2|-0.008725|-0.005596|
|monomer|5|expanded − retained|+0.002478|+0.001686|
|monomer|5|native_s2 − native_s1|+0.019507|+0.018539|
|multimer_single_chain|123|coordinate_zero − expanded|+0.001753|+0.002947|
|multimer_single_chain|123|coordinate_zero − retained|+0.003378|+0.003578|
|multimer_single_chain|123|coordinate_zero − native_s1|+0.008587|+0.010053|
|multimer_single_chain|123|coordinate_zero − native_s2|-0.004018|-0.002622|
|multimer_single_chain|123|expanded − retained|+0.001625|+0.000632|
|multimer_single_chain|123|native_s2 − native_s1|+0.012605|+0.012675|

## added_train295: 295 proteins

|Model|AA-lDDT|Cα-lDDT|Zero severe + strict stereo, instances|Both noises, proteins|Severe pairs total|
|---|---:|---:|---:|---:|---:|
|native_s1|0.801504|0.881038|287/590|112/295|14299|
|native_s2|0.812092|0.891652|344/590|138/295|4255|
|retained|0.804582|0.885483|355/590|144/295|7483|
|expanded|0.809317|0.889017|443/590|204/295|5796|
|coordinate_zero|0.809924|0.890510|469/590|220/295|4644|

Positive quality differences favor the candidate. Intervals resample proteins, conditional on the two locked noises; they do not establish independence from pretraining.

|Candidate − reference|Metric|Mean Δ|95% CI|P01 Δ|P05 Δ|Worst5% Δ mean|Δ < −0.05, proteins|
|---|---|---:|---|---:|---:|---:|---:|
|coordinate_zero − expanded|AA|+0.000607|[+0.000151, +0.001145]|-0.006699|-0.002699|-0.005364|0/295|
|coordinate_zero − expanded|Cα|+0.001493|[+0.000881, +0.002197]|-0.006946|-0.002833|-0.005042|0/295|
|coordinate_zero − retained|AA|+0.005341|[+0.004447, +0.006270]|-0.005868|-0.000150|-0.006353|0/295|
|coordinate_zero − retained|Cα|+0.005027|[+0.003940, +0.006198]|-0.005468|-0.001123|-0.007298|1/295|
|coordinate_zero − native_s1|AA|+0.008420|[+0.006999, +0.009979]|-0.005680|-0.001729|-0.004353|0/295|
|coordinate_zero − native_s1|Cα|+0.009472|[+0.007764, +0.011419]|-0.003363|-0.001083|-0.002765|0/295|
|coordinate_zero − native_s2|AA|-0.002168|[-0.003486, -0.001075]|-0.031502|-0.012036|-0.026805|1/295|
|coordinate_zero − native_s2|Cα|-0.001142|[-0.002978, +0.000195]|-0.029871|-0.008753|-0.030713|1/295|
|expanded − retained|AA|+0.004734|[+0.003987, +0.005503]|-0.005163|-0.000596|-0.005752|0/295|
|expanded − retained|Cα|+0.003535|[+0.002674, +0.004434]|-0.005792|-0.001717|-0.008066|1/295|
|native_s2 − native_s1|AA|+0.010588|[+0.008716, +0.012669]|-0.014541|-0.003430|-0.012425|0/295|
|native_s2 − native_s1|Cα|+0.010613|[+0.008330, +0.013298]|-0.012491|-0.003552|-0.010708|0/295|

|Candidate − reference|New severe collision instances from zero|Lost strict stereo instances|
|---|---:|---:|
|coordinate_zero − expanded|14|7|
|coordinate_zero − retained|6|7|
|coordinate_zero − native_s1|2|6|
|coordinate_zero − native_s2|22|17|
|expanded − retained|14|11|
|native_s2 − native_s1|46|44|

Descriptive length/assembly subsets; overlapping views, not additional independent tests.

|Subset|Proteins|Candidate − reference|Mean AA Δ|Mean Cα Δ|
|---|---:|---|---:|---:|
|length_256_511|48|coordinate_zero − expanded|+0.000811|+0.001527|
|length_256_511|48|coordinate_zero − retained|+0.002273|+0.002204|
|length_256_511|48|coordinate_zero − native_s1|+0.002700|+0.003331|
|length_256_511|48|coordinate_zero − native_s2|-0.002972|-0.001675|
|length_256_511|48|expanded − retained|+0.001462|+0.000677|
|length_256_511|48|native_s2 − native_s1|+0.005672|+0.005006|
|length_50_255|242|coordinate_zero − expanded|+0.000531|+0.001448|
|length_50_255|242|coordinate_zero − retained|+0.005981|+0.005611|
|length_50_255|242|coordinate_zero − native_s1|+0.009635|+0.010750|
|length_50_255|242|coordinate_zero − native_s2|-0.001869|-0.000929|
|length_50_255|242|expanded − retained|+0.005450|+0.004163|
|length_50_255|242|native_s2 − native_s1|+0.011504|+0.011679|
|length_512_1024|5|coordinate_zero − expanded|+0.002338|+0.003293|
|length_512_1024|5|coordinate_zero − retained|+0.003860|+0.003870|
|length_512_1024|5|coordinate_zero − native_s1|+0.004526|+0.006551|
|length_512_1024|5|coordinate_zero − native_s2|-0.008929|-0.006299|
|length_512_1024|5|expanded − retained|+0.001522|+0.000577|
|length_512_1024|5|native_s2 − native_s1|+0.013455|+0.012850|
|monomer|8|coordinate_zero − expanded|-0.000284|+0.000419|
|monomer|8|coordinate_zero − retained|+0.002856|+0.002830|
|monomer|8|coordinate_zero − native_s1|+0.003340|+0.003439|
|monomer|8|coordinate_zero − native_s2|-0.001945|-0.000080|
|monomer|8|expanded − retained|+0.003139|+0.002411|
|monomer|8|native_s2 − native_s1|+0.005285|+0.003519|
|multimer_single_chain|287|coordinate_zero − expanded|+0.000632|+0.001522|
|multimer_single_chain|287|coordinate_zero − retained|+0.005411|+0.005088|
|multimer_single_chain|287|coordinate_zero − native_s1|+0.008562|+0.009640|
|multimer_single_chain|287|coordinate_zero − native_s2|-0.002174|-0.001171|
|multimer_single_chain|287|expanded − retained|+0.004779|+0.003566|
|multimer_single_chain|287|native_s2 − native_s1|+0.010736|+0.010811|

## Matched original-TRAIN32 learning curves

Matched TRAIN32 probes only. Both arms have exactly the same training membership, order and per-protein exposure.

|Arm|New update|AA-lDDT|Cα-lDDT|Zero severe + strict stereo / 64|Severe pairs|
|---|---:|---:|---:|---:|---:|
|expanded_control|0|0.804773|0.885653|41/64|394|
|expanded_control|512|0.805367|0.885849|42/64|382|
|expanded_control|1024|0.805909|0.886087|41/64|396|
|expanded_control|2048|0.806617|0.886601|43/64|378|
|coordinate_zero|0|0.804773|0.885653|41/64|394|
|coordinate_zero|512|0.806174|0.887713|41/64|306|
|coordinate_zero|1024|0.807003|0.888415|45/64|246|
|coordinate_zero|2048|0.807633|0.889088|45/64|203|

## Cost and provenance

|Arm|Training seconds|Allocated peak GiB|Samples per protein, min–max|Clipped updates|
|---|---:|---:|---|---:|
|expanded_control|6217.4|16.182|19–20|1371|
|coordinate_zero|5113.4|16.182|19–20|994|

Complete outputs: **4550** over **455 proteins**. New evaluation prediction NFEs: **910**; engineering probes: **32**. Independent dense-distance metric maximum absolute discrepancy: **4.44e-16**.

Inference timings in evaluation.json cover diffusion with cached conditioning only. They omit live ESM2 and Pairformer, and are not end-to-end folding speed. Equal updates/exposures are not equal GPU time, FLOPs, or per-protein exposure.

Original TRAIN128 and added TRAIN295 remain separate. The previously observed validation32 is now development evidence, not an independent confirmation set. Most sources are complete chains from homooligomers; assembly context and pretraining exposure remain limitations. A promising result requires later fresh confirmation.

No model is automatically promoted by this report. Review mean quality, paired tails and newly introduced chemical failures jointly. This experiment does not establish BindCraft utility, binding affinity or a gradient through a changed output function.

## Global structure: aligned Cα RMSD (Å)

Lower RMSD is better. Positive candidate − reference differences mean deterioration, opposite to lDDT. These are the existing GT-aligned RMSD scores, without a new alignment or atom mask. Average both locked noises within each protein before aggregation. Intervals resample proteins, conditional on the fixed noises. This adds no acceptance threshold.

### added_train295: 295 proteins

|Model|Mean|Median|P95|P99|Worst5% mean|
|---|---:|---:|---:|---:|---:|
|native_s1|4.036220|2.050058|15.469900|29.776209|24.328383|
|native_s2|4.038035|1.958283|15.239342|30.093435|24.548916|
|retained|3.883915|1.993154|14.503863|26.720848|22.555374|
|expanded|3.704527|1.854728|13.563036|27.614306|21.771657|
|coordinate_zero|4.000924|1.960102|15.032316|29.303587|24.265186|

|Candidate − reference|Mean Δ|95% CI|P95 Δ|P99 Δ|Worst5% Δ mean|RMSD increased, proteins|
|---|---:|---|---:|---:|---:|---:|
|coordinate_zero − expanded|+0.296397|[+0.210066, +0.406919]|+1.219407|+3.010910|+2.982343|244/295|
|coordinate_zero − retained|+0.117009|[+0.034730, +0.257506]|+0.503448|+1.695821|+2.154421|161/295|
|coordinate_zero − native_s1|-0.035297|[-0.079453, +0.003382]|+0.337275|+0.828922|+0.723314|120/295|
|coordinate_zero − native_s2|-0.037111|[-0.060274, -0.015740]|+0.191556|+0.357919|+0.323610|141/295|
|expanded − retained|-0.179388|[-0.241083, -0.112329]|+0.034282|+0.121806|+0.478803|49/295|
|native_s2 − native_s1|+0.001814|[-0.041686, +0.045939]|+0.611392|+1.326366|+1.033626|125/295|

### observed_validation32: 32 proteins

|Model|Mean|Median|P95|P99|Worst5% mean|
|---|---:|---:|---:|---:|---:|
|native_s1|3.489204|1.573082|10.892134|22.101648|19.148385|
|native_s2|3.412233|1.754606|10.865222|21.580090|18.891090|
|retained|3.461940|1.645646|11.652819|21.681129|19.274131|
|expanded|3.453734|1.796725|11.927012|21.076156|19.130369|
|coordinate_zero|3.521401|1.741552|11.823336|21.342520|19.198512|

|Candidate − reference|Mean Δ|95% CI|P95 Δ|P99 Δ|Worst5% Δ mean|RMSD increased, proteins|
|---|---:|---|---:|---:|---:|---:|
|coordinate_zero − expanded|+0.067667|[-0.015687, +0.174349]|+0.553198|+1.010086|+0.894349|15/32|
|coordinate_zero − retained|+0.059461|[-0.046356, +0.183495]|+0.650788|+1.136967|+1.014645|15/32|
|coordinate_zero − native_s1|+0.032197|[-0.164167, +0.229933]|+0.561408|+1.686264|+1.383808|14/32|
|coordinate_zero − native_s2|+0.109168|[-0.046769, +0.291242]|+1.146763|+1.694889|+1.666253|18/32|
|expanded − retained|-0.008206|[-0.128343, +0.099190]|+0.244792|+0.835158|+0.691251|11/32|
|native_s2 − native_s1|-0.076971|[-0.200983, +0.034706]|+0.493329|+0.584831|+0.578211|13/32|

### original_train128: 128 proteins

|Model|Mean|Median|P95|P99|Worst5% mean|
|---|---:|---:|---:|---:|---:|
|native_s1|4.624712|1.964632|21.161587|28.986198|26.384139|
|native_s2|4.608217|1.878926|20.634387|28.956992|26.535705|
|retained|4.299634|1.888598|18.974450|27.493645|24.871859|
|expanded|4.166437|1.782504|18.274787|25.690375|23.789405|
|coordinate_zero|4.525132|1.789962|20.420787|28.808740|26.190894|

|Candidate − reference|Mean Δ|95% CI|P95 Δ|P99 Δ|Worst5% Δ mean|RMSD increased, proteins|
|---|---:|---|---:|---:|---:|---:|
|coordinate_zero − expanded|+0.358695|[+0.216997, +0.522711]|+2.118651|+4.808865|+3.607581|102/128|
|coordinate_zero − retained|+0.225499|[+0.117899, +0.356327]|+1.203671|+3.065465|+2.687091|81/128|
|coordinate_zero − native_s1|-0.099579|[-0.170937, -0.036665]|+0.384300|+0.644466|+0.520207|44/128|
|coordinate_zero − native_s2|-0.083084|[-0.122905, -0.046723]|+0.174018|+0.255225|+0.245756|42/128|
|expanded − retained|-0.133197|[-0.202578, -0.078049]|+0.042947|+0.158407|+0.108267|33/128|
|native_s2 − native_s1|-0.016495|[-0.091380, +0.054057]|+0.590335|+0.987420|+0.812134|60/128|
