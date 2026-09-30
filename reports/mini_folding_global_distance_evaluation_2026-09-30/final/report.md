# C4/S1 experimental global-distance candidate: fixed terminal

All three TRAIN423 continuations start at the same retained512 checkpoint and use the same 8192 ordered exposures / 2048 updates. The new candidate adds experimental global CA distance supervision to the coordinate-zero recipe, at a fixed TRAIN-calibrated weight. Native S2 remains auxiliary synthetic supervision, not experimental GT. Frozen ESM2/C4, native FP32, C4/S1/K1.

Scores use observed experimental GT. Each protein contributes the mean of its two fixed noises; no best-of-noise or intermediate-checkpoint selection. Geometry counts describe the explicit severe-collision and checked-stereocentre criteria, not comprehensive chemical correctness or deployment approval.

## observed_validation32: 32 proteins

|Model|AA-lDDT|Cα-lDDT|Zero severe + strict stereo, instances|Both noises, proteins|Severe pairs total|
|---|---:|---:|---:|---:|---:|
|native_s1|0.815917|0.899536|30/64|9/32|902|
|native_s2|0.828004|0.910778|37/64|15/32|353|
|retained|0.817664|0.902912|46/64|20/32|562|
|expanded|0.818402|0.902915|44/64|20/32|540|
|coordinate_zero|0.819737|0.905059|45/64|22/32|451|
|global_distance|0.819744|0.905226|45/64|21/32|438|

Positive quality differences favor the candidate. Intervals resample proteins, conditional on the two locked noises; they do not establish independence from pretraining.

|Candidate − reference|Metric|Mean Δ|95% CI|P01 Δ|P05 Δ|Worst5% Δ mean|Δ < −0.05, proteins|
|---|---|---:|---|---:|---:|---:|---:|
|global_distance − coordinate_zero|AA|+0.000007|[-0.000117, +0.000125]|-0.000816|-0.000669|-0.000783|0/32|
|global_distance − coordinate_zero|Cα|+0.000166|[-0.000068, +0.000416]|-0.001195|-0.000879|-0.001194|0/32|
|global_distance − expanded|AA|+0.001341|[+0.000772, +0.002029]|-0.001124|-0.000786|-0.001041|0/32|
|global_distance − expanded|Cα|+0.002310|[+0.001440, +0.003410]|-0.000298|-0.000126|-0.000255|0/32|
|global_distance − retained|AA|+0.002079|[+0.001257, +0.002928]|-0.003417|-0.000858|-0.002829|0/32|
|global_distance − retained|Cα|+0.002313|[+0.001165, +0.003594]|-0.004101|-0.001638|-0.003568|0/32|
|global_distance − native_s1|AA|+0.003827|[+0.001948, +0.005901]|-0.005341|-0.004023|-0.005063|0/32|
|global_distance − native_s1|Cα|+0.005689|[+0.002615, +0.009331]|-0.006593|-0.003182|-0.006014|0/32|
|global_distance − native_s2|AA|-0.008260|[-0.012287, -0.004776]|-0.042149|-0.027821|-0.039767|0/32|
|global_distance − native_s2|Cα|-0.005552|[-0.009932, -0.001924]|-0.044819|-0.024743|-0.041669|0/32|
|coordinate_zero − expanded|AA|+0.001334|[+0.000729, +0.002046]|-0.001464|-0.000832|-0.001302|0/32|
|coordinate_zero − expanded|Cα|+0.002144|[+0.001249, +0.003255]|-0.001978|-0.000422|-0.001654|0/32|
|expanded − retained|AA|+0.000738|[-0.000080, +0.001503]|-0.005954|-0.002069|-0.005071|0/32|
|expanded − retained|Cα|+0.000003|[-0.000888, +0.000863]|-0.006972|-0.002345|-0.005796|0/32|
|native_s2 − native_s1|AA|+0.012087|[+0.008207, +0.016551]|-0.000455|+0.001240|-0.000008|0/32|
|native_s2 − native_s1|Cα|+0.011241|[+0.006553, +0.017328]|-0.001357|-0.000386|-0.001131|0/32|

|Candidate − reference|New severe collision instances from zero|Lost strict stereo instances|
|---|---:|---:|
|global_distance − coordinate_zero|1|0|
|global_distance − expanded|1|1|
|global_distance − retained|4|1|
|global_distance − native_s1|3|0|
|global_distance − native_s2|5|1|
|coordinate_zero − expanded|1|1|
|expanded − retained|6|1|
|native_s2 − native_s1|5|8|

Descriptive length/assembly subsets; overlapping views, not additional independent tests.

|Subset|Proteins|Candidate − reference|Mean AA Δ|Mean Cα Δ|
|---|---:|---|---:|---:|
|length_256_511|15|global_distance − coordinate_zero|+0.000023|+0.000083|
|length_256_511|15|global_distance − expanded|+0.001527|+0.002786|
|length_256_511|15|global_distance − retained|+0.002367|+0.002600|
|length_256_511|15|global_distance − native_s1|+0.004141|+0.006069|
|length_256_511|15|global_distance − native_s2|-0.009122|-0.005610|
|length_256_511|15|coordinate_zero − expanded|+0.001504|+0.002703|
|length_256_511|15|expanded − retained|+0.000840|-0.000185|
|length_256_511|15|native_s2 − native_s1|+0.013264|+0.011679|
|length_50_255|16|global_distance − coordinate_zero|+0.000047|+0.000294|
|length_50_255|16|global_distance − expanded|+0.001062|+0.001764|
|length_50_255|16|global_distance − retained|+0.002213|+0.002500|
|length_50_255|16|global_distance − native_s1|+0.004133|+0.005970|
|length_50_255|16|global_distance − native_s2|-0.005874|-0.003759|
|length_50_255|16|coordinate_zero − expanded|+0.001015|+0.001470|
|length_50_255|16|expanded − retained|+0.001151|+0.000735|
|length_50_255|16|native_s2 − native_s1|+0.010007|+0.009728|
|length_512_1024|1|global_distance − coordinate_zero|-0.000868|-0.000623|
|length_512_1024|1|global_distance − expanded|+0.003020|+0.003920|
|length_512_1024|1|global_distance − retained|-0.004375|-0.004971|
|length_512_1024|1|global_distance − native_s1|-0.005795|-0.004488|
|length_512_1024|1|global_distance − native_s2|-0.033500|-0.033378|
|length_512_1024|1|coordinate_zero − expanded|+0.003887|+0.004543|
|length_512_1024|1|expanded − retained|-0.007394|-0.008891|
|length_512_1024|1|native_s2 − native_s1|+0.027706|+0.028890|
|monomer|1|global_distance − coordinate_zero|+0.000120|+0.000141|
|monomer|1|global_distance − expanded|-0.000758|+0.000030|
|monomer|1|global_distance − retained|-0.000423|+0.001295|
|monomer|1|global_distance − native_s1|-0.002036|+0.003590|
|monomer|1|global_distance − native_s2|-0.004112|+0.000191|
|monomer|1|coordinate_zero − expanded|-0.000878|-0.000111|
|monomer|1|expanded − retained|+0.000335|+0.001264|
|monomer|1|native_s2 − native_s1|+0.002077|+0.003400|
|multimer_single_chain|31|global_distance − coordinate_zero|+0.000003|+0.000167|
|multimer_single_chain|31|global_distance − expanded|+0.001409|+0.002384|
|multimer_single_chain|31|global_distance − retained|+0.002160|+0.002346|
|multimer_single_chain|31|global_distance − native_s1|+0.004016|+0.005757|
|multimer_single_chain|31|global_distance − native_s2|-0.008394|-0.005737|
|multimer_single_chain|31|coordinate_zero − expanded|+0.001406|+0.002217|
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
|global_distance|0.809747|0.888904|189/256|84/128|2857|

Positive quality differences favor the candidate. Intervals resample proteins, conditional on the two locked noises; they do not establish independence from pretraining.

|Candidate − reference|Metric|Mean Δ|95% CI|P01 Δ|P05 Δ|Worst5% Δ mean|Δ < −0.05, proteins|
|---|---|---:|---|---:|---:|---:|---:|
|global_distance − coordinate_zero|AA|-0.000110|[-0.000208, -0.000015]|-0.002013|-0.001009|-0.001657|0/128|
|global_distance − coordinate_zero|Cα|-0.000053|[-0.000197, +0.000095]|-0.001962|-0.001486|-0.001940|0/128|
|global_distance − expanded|AA|+0.001634|[+0.000680, +0.002782]|-0.006589|-0.001990|-0.004344|0/128|
|global_distance − expanded|Cα|+0.002864|[+0.001611, +0.004422]|-0.003416|-0.001234|-0.003314|0/128|
|global_distance − retained|AA|+0.003292|[+0.002568, +0.004081]|-0.004850|-0.000813|-0.003563|0/128|
|global_distance − retained|Cα|+0.003537|[+0.002593, +0.004566]|-0.004009|-0.001014|-0.002809|0/128|
|global_distance − native_s1|AA|+0.008563|[+0.006363, +0.011329]|-0.011398|-0.001747|-0.006477|0/128|
|global_distance − native_s1|Cα|+0.010113|[+0.007282, +0.013786]|-0.009022|-0.001715|-0.005555|0/128|
|global_distance − native_s2|AA|-0.004312|[-0.006734, -0.002211]|-0.068184|-0.021274|-0.042938|2/128|
|global_distance − native_s2|Cα|-0.002790|[-0.005784, -0.000393]|-0.076098|-0.016559|-0.047678|2/128|
|coordinate_zero − expanded|AA|+0.001744|[+0.000799, +0.002868]|-0.006095|-0.001964|-0.004107|0/128|
|coordinate_zero − expanded|Cα|+0.002917|[+0.001708, +0.004423]|-0.004116|-0.001167|-0.002822|0/128|
|expanded − retained|AA|+0.001658|[+0.000759, +0.002486]|-0.020037|-0.004801|-0.011892|0/128|
|expanded − retained|Cα|+0.000673|[-0.000433, +0.001675]|-0.027395|-0.005817|-0.015542|0/128|
|native_s2 − native_s1|AA|+0.012875|[+0.009331, +0.017393]|-0.024920|-0.001812|-0.012695|0/128|
|native_s2 − native_s1|Cα|+0.012904|[+0.008549, +0.019057]|-0.025146|-0.003637|-0.013402|0/128|

|Candidate − reference|New severe collision instances from zero|Lost strict stereo instances|
|---|---:|---:|
|global_distance − coordinate_zero|2|5|
|global_distance − expanded|7|6|
|global_distance − retained|5|7|
|global_distance − native_s1|2|5|
|global_distance − native_s2|10|12|
|coordinate_zero − expanded|9|6|
|expanded − retained|5|5|
|native_s2 − native_s1|15|16|

Descriptive length/assembly subsets; overlapping views, not additional independent tests.

|Subset|Proteins|Candidate − reference|Mean AA Δ|Mean Cα Δ|
|---|---:|---|---:|---:|
|length_256_511|55|global_distance − coordinate_zero|-0.000176|-0.000124|
|length_256_511|55|global_distance − expanded|+0.000788|+0.001472|
|length_256_511|55|global_distance − retained|+0.002359|+0.002198|
|length_256_511|55|global_distance − native_s1|+0.005919|+0.006780|
|length_256_511|55|global_distance − native_s2|-0.004618|-0.002261|
|length_256_511|55|coordinate_zero − expanded|+0.000964|+0.001596|
|length_256_511|55|expanded − retained|+0.001571|+0.000726|
|length_256_511|55|native_s2 − native_s1|+0.010536|+0.009041|
|length_50_255|64|global_distance − coordinate_zero|-0.000004|+0.000038|
|length_50_255|64|global_distance − expanded|+0.001162|+0.002540|
|length_50_255|64|global_distance − retained|+0.003808|+0.004142|
|length_50_255|64|global_distance − native_s1|+0.010918|+0.012802|
|length_50_255|64|global_distance − native_s2|-0.001103|-0.000285|
|length_50_255|64|coordinate_zero − expanded|+0.001166|+0.002502|
|length_50_255|64|expanded − retained|+0.002646|+0.001602|
|length_50_255|64|native_s2 − native_s1|+0.012021|+0.013087|
|length_512_1024|9|global_distance − coordinate_zero|-0.000461|-0.000259|
|length_512_1024|9|global_distance − expanded|+0.010164|+0.013681|
|length_512_1024|9|global_distance − retained|+0.005324|+0.007419|
|length_512_1024|9|global_distance − native_s1|+0.007975|+0.011365|
|length_512_1024|9|global_distance − native_s2|-0.025259|-0.023845|
|length_512_1024|9|coordinate_zero − expanded|+0.010625|+0.013940|
|length_512_1024|9|expanded − retained|-0.004840|-0.006262|
|length_512_1024|9|native_s2 − native_s1|+0.033234|+0.035209|
|monomer|5|global_distance − coordinate_zero|-0.000262|-0.000527|
|monomer|5|global_distance − expanded|+0.001256|+0.001652|
|monomer|5|global_distance − retained|+0.003734|+0.003338|
|monomer|5|global_distance − native_s1|+0.010520|+0.012416|
|monomer|5|global_distance − native_s2|-0.008987|-0.006123|
|monomer|5|coordinate_zero − expanded|+0.001517|+0.002179|
|monomer|5|expanded − retained|+0.002478|+0.001686|
|monomer|5|native_s2 − native_s1|+0.019507|+0.018539|
|multimer_single_chain|123|global_distance − coordinate_zero|-0.000104|-0.000033|
|multimer_single_chain|123|global_distance − expanded|+0.001650|+0.002914|
|multimer_single_chain|123|global_distance − retained|+0.003274|+0.003545|
|multimer_single_chain|123|global_distance − native_s1|+0.008483|+0.010020|
|multimer_single_chain|123|global_distance − native_s2|-0.004122|-0.002655|
|multimer_single_chain|123|coordinate_zero − expanded|+0.001753|+0.002947|
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
|global_distance|0.810024|0.890770|466/590|218/295|4345|

Positive quality differences favor the candidate. Intervals resample proteins, conditional on the two locked noises; they do not establish independence from pretraining.

|Candidate − reference|Metric|Mean Δ|95% CI|P01 Δ|P05 Δ|Worst5% Δ mean|Δ < −0.05, proteins|
|---|---|---:|---|---:|---:|---:|---:|
|global_distance − coordinate_zero|AA|+0.000100|[+0.000006, +0.000207]|-0.001820|-0.000759|-0.001302|0/295|
|global_distance − coordinate_zero|Cα|+0.000260|[+0.000104, +0.000434]|-0.001991|-0.001073|-0.001733|0/295|
|global_distance − expanded|AA|+0.000707|[+0.000224, +0.001276]|-0.007708|-0.002500|-0.005538|0/295|
|global_distance − expanded|Cα|+0.001753|[+0.001088, +0.002525]|-0.007510|-0.002586|-0.005189|0/295|
|global_distance − retained|AA|+0.005442|[+0.004545, +0.006389]|-0.006408|-0.000405|-0.006106|0/295|
|global_distance − retained|Cα|+0.005287|[+0.004186, +0.006492]|-0.006298|-0.000881|-0.006399|0/295|
|global_distance − native_s1|AA|+0.008520|[+0.007033, +0.010123]|-0.007136|-0.002208|-0.005030|0/295|
|global_distance − native_s1|Cα|+0.009732|[+0.007932, +0.011747]|-0.004377|-0.001362|-0.003185|0/295|
|global_distance − native_s2|AA|-0.002068|[-0.003335, -0.001001]|-0.029625|-0.011703|-0.026059|1/295|
|global_distance − native_s2|Cα|-0.000882|[-0.002637, +0.000417]|-0.026444|-0.009133|-0.028863|1/295|
|coordinate_zero − expanded|AA|+0.000607|[+0.000151, +0.001145]|-0.006699|-0.002699|-0.005364|0/295|
|coordinate_zero − expanded|Cα|+0.001493|[+0.000881, +0.002197]|-0.006946|-0.002833|-0.005042|0/295|
|expanded − retained|AA|+0.004734|[+0.003987, +0.005503]|-0.005163|-0.000596|-0.005752|0/295|
|expanded − retained|Cα|+0.003535|[+0.002674, +0.004434]|-0.005792|-0.001717|-0.008066|1/295|
|native_s2 − native_s1|AA|+0.010588|[+0.008716, +0.012669]|-0.014541|-0.003430|-0.012425|0/295|
|native_s2 − native_s1|Cα|+0.010613|[+0.008330, +0.013298]|-0.012491|-0.003552|-0.010708|0/295|

|Candidate − reference|New severe collision instances from zero|Lost strict stereo instances|
|---|---:|---:|
|global_distance − coordinate_zero|8|9|
|global_distance − expanded|12|8|
|global_distance − retained|7|6|
|global_distance − native_s1|3|3|
|global_distance − native_s2|19|19|
|coordinate_zero − expanded|14|7|
|expanded − retained|14|11|
|native_s2 − native_s1|46|44|

Descriptive length/assembly subsets; overlapping views, not additional independent tests.

|Subset|Proteins|Candidate − reference|Mean AA Δ|Mean Cα Δ|
|---|---:|---|---:|---:|
|length_256_511|48|global_distance − coordinate_zero|-0.000163|-0.000057|
|length_256_511|48|global_distance − expanded|+0.000648|+0.001470|
|length_256_511|48|global_distance − retained|+0.002110|+0.002147|
|length_256_511|48|global_distance − native_s1|+0.002537|+0.003274|
|length_256_511|48|global_distance − native_s2|-0.003135|-0.001732|
|length_256_511|48|coordinate_zero − expanded|+0.000811|+0.001527|
|length_256_511|48|expanded − retained|+0.001462|+0.000677|
|length_256_511|48|native_s2 − native_s1|+0.005672|+0.005006|
|length_50_255|242|global_distance − coordinate_zero|+0.000160|+0.000333|
|length_50_255|242|global_distance − expanded|+0.000690|+0.001782|
|length_50_255|242|global_distance − retained|+0.006140|+0.005944|
|length_50_255|242|global_distance − native_s1|+0.009795|+0.011083|
|length_50_255|242|global_distance − native_s2|-0.001710|-0.000596|
|length_50_255|242|coordinate_zero − expanded|+0.000531|+0.001448|
|length_50_255|242|expanded − retained|+0.005450|+0.004163|
|length_50_255|242|native_s2 − native_s1|+0.011504|+0.011679|
|length_512_1024|5|global_distance − coordinate_zero|-0.000245|-0.000247|
|length_512_1024|5|global_distance − expanded|+0.002093|+0.003046|
|length_512_1024|5|global_distance − retained|+0.003615|+0.003623|
|length_512_1024|5|global_distance − native_s1|+0.004281|+0.006304|
|length_512_1024|5|global_distance − native_s2|-0.009174|-0.006546|
|length_512_1024|5|coordinate_zero − expanded|+0.002338|+0.003293|
|length_512_1024|5|expanded − retained|+0.001522|+0.000577|
|length_512_1024|5|native_s2 − native_s1|+0.013455|+0.012850|
|monomer|8|global_distance − coordinate_zero|-0.000064|-0.000065|
|monomer|8|global_distance − expanded|-0.000348|+0.000354|
|monomer|8|global_distance − retained|+0.002791|+0.002765|
|monomer|8|global_distance − native_s1|+0.003276|+0.003374|
|monomer|8|global_distance − native_s2|-0.002009|-0.000145|
|monomer|8|coordinate_zero − expanded|-0.000284|+0.000419|
|monomer|8|expanded − retained|+0.003139|+0.002411|
|monomer|8|native_s2 − native_s1|+0.005285|+0.003519|
|multimer_single_chain|287|global_distance − coordinate_zero|+0.000105|+0.000269|
|multimer_single_chain|287|global_distance − expanded|+0.000737|+0.001791|
|multimer_single_chain|287|global_distance − retained|+0.005516|+0.005357|
|multimer_single_chain|287|global_distance − native_s1|+0.008666|+0.009909|
|multimer_single_chain|287|global_distance − native_s2|-0.002070|-0.000902|
|multimer_single_chain|287|coordinate_zero − expanded|+0.000632|+0.001522|
|multimer_single_chain|287|expanded − retained|+0.004779|+0.003566|
|multimer_single_chain|287|native_s2 − native_s1|+0.010736|+0.010811|

## Matched original-TRAIN32 learning curves

Matched original-TRAIN32 probes; same training membership, order, noises and per-protein exposure. No checkpoint selection.

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
|global_distance|0|0.804773|0.885653|41/64|394|
|global_distance|512|0.806060|0.887755|42/64|292|
|global_distance|1024|0.806810|0.888346|44/64|245|
|global_distance|2048|0.807456|0.888967|48/64|207|

## Cost and provenance

|Arm|Training seconds|Allocated peak GiB|Samples per protein, min–max|Clipped updates|
|---|---:|---:|---|---:|
|expanded_control|6217.4|16.182|19–20|1371|
|coordinate_zero|5113.4|16.182|19–20|994|
|global_distance|4963.9|16.182|19–20|1010|

Complete outputs: **5460** over **455 proteins**. New evaluation prediction NFEs: **910**; engineering probes: **32**. Independent dense-distance metric maximum absolute discrepancy: **4.44e-16**.

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
|global_distance|3.973438|1.944572|14.840018|29.103734|24.110704|

|Candidate − reference|Mean Δ|95% CI|P95 Δ|P99 Δ|Worst5% Δ mean|RMSD increased, proteins|
|---|---:|---|---:|---:|---:|---:|
|global_distance − coordinate_zero|-0.027486|[-0.038522, -0.018442]|+0.009994|+0.045213|+0.028347|72/295|
|global_distance − expanded|+0.268911|[+0.189189, +0.371914]|+1.084196|+2.889448|+2.763806|243/295|
|global_distance − retained|+0.089523|[+0.012248, +0.222693]|+0.446910|+1.490016|+1.985017|151/295|
|global_distance − native_s1|-0.062783|[-0.115360, -0.018903]|+0.337972|+0.778012|+0.675953|116/295|
|global_distance − native_s2|-0.064597|[-0.092837, -0.039524]|+0.143123|+0.325273|+0.295078|126/295|
|coordinate_zero − expanded|+0.296397|[+0.210066, +0.406919]|+1.219407|+3.010910|+2.982343|244/295|
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
|global_distance|3.512218|1.771312|11.860650|21.293024|19.201931|

|Candidate − reference|Mean Δ|95% CI|P95 Δ|P99 Δ|Worst5% Δ mean|RMSD increased, proteins|
|---|---:|---|---:|---:|---:|---:|
|global_distance − coordinate_zero|-0.009183|[-0.023692, +0.005472]|+0.029626|+0.108083|+0.086885|9/32|
|global_distance − expanded|+0.058484|[-0.012932, +0.153358]|+0.446929|+0.915302|+0.788263|15/32|
|global_distance − retained|+0.050278|[-0.060486, +0.173532]|+0.677473|+1.104870|+1.009666|17/32|
|global_distance − native_s1|+0.023014|[-0.184457, +0.232632]|+0.519439|+1.766490|+1.425762|12/32|
|global_distance − native_s2|+0.099984|[-0.062877, +0.285741]|+1.067264|+1.769665|+1.699416|18/32|
|coordinate_zero − expanded|+0.067667|[-0.015687, +0.174349]|+0.553198|+1.010086|+0.894349|15/32|
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
|global_distance|4.503679|1.795778|20.361873|28.696811|26.102393|

|Candidate − reference|Mean Δ|95% CI|P95 Δ|P99 Δ|Worst5% Δ mean|RMSD increased, proteins|
|---|---:|---|---:|---:|---:|---:|
|global_distance − coordinate_zero|-0.021453|[-0.030867, -0.013163]|+0.009365|+0.025053|+0.025612|36/128|
|global_distance − expanded|+0.337242|[+0.201590, +0.494826]|+1.927179|+4.639006|+3.442698|104/128|
|global_distance − retained|+0.204046|[+0.102026, +0.328619]|+1.180094|+3.022051|+2.546400|76/128|
|global_distance − native_s1|-0.121032|[-0.195362, -0.055469]|+0.273583|+0.588484|+0.484193|44/128|
|global_distance − native_s2|-0.104538|[-0.149111, -0.063559]|+0.126679|+0.240801|+0.223357|40/128|
|coordinate_zero − expanded|+0.358695|[+0.216997, +0.522711]|+2.118651|+4.808865|+3.607581|102/128|
|expanded − retained|-0.133197|[-0.202578, -0.078049]|+0.042947|+0.158407|+0.108267|33/128|
|native_s2 − native_s1|-0.016495|[-0.091380, +0.054057]|+0.590335|+0.987420|+0.812134|60/128|

## Existing-coordinate distance and error-extent diagnostics

No new inference. Observed CA identities/GT are unchanged; whole-chain RMSD is independently replayed. Far pairs have sequence separation ≥24 and experimental distance ≥30 Å. Positive MAE/fragment RMSD changes are worse. Negative signed distance error means underestimation, not improvement. Radius-of-gyration ratio has no universal better direction. Empty bands remain null, with valid-protein counts. These are descriptive diagnostics, not extra independent confirmations.

### observed_validation32

|Model|Metric|Proteins with support|Mean|
|---|---|---:|---:|
|native_s1|Far MAE (Å)|32|2.804205|
|native_s1|Far signed error (Å)|32|-2.050783|
|native_s1|Remaining95% RMSD (Å)|32|2.596343|
|native_s1|Fragment32 RMSD (Å)|32|1.557395|
|native_s1|Predicted/GT Rg|32|0.968116|
|native_s2|Far MAE (Å)|32|2.493720|
|native_s2|Far signed error (Å)|32|-1.404029|
|native_s2|Remaining95% RMSD (Å)|32|2.523528|
|native_s2|Fragment32 RMSD (Å)|32|1.535282|
|native_s2|Predicted/GT Rg|32|0.981348|
|retained|Far MAE (Å)|32|2.549523|
|retained|Far signed error (Å)|32|-1.479334|
|retained|Remaining95% RMSD (Å)|32|2.588742|
|retained|Fragment32 RMSD (Å)|32|1.519734|
|retained|Predicted/GT Rg|32|0.979446|
|expanded|Far MAE (Å)|32|2.496806|
|expanded|Far signed error (Å)|32|-1.317378|
|expanded|Remaining95% RMSD (Å)|32|2.597663|
|expanded|Fragment32 RMSD (Å)|32|1.527416|
|expanded|Predicted/GT Rg|32|0.982856|
|coordinate_zero|Far MAE (Å)|32|2.592216|
|coordinate_zero|Far signed error (Å)|32|-1.539329|
|coordinate_zero|Remaining95% RMSD (Å)|32|2.665356|
|coordinate_zero|Fragment32 RMSD (Å)|32|1.536232|
|coordinate_zero|Predicted/GT Rg|32|0.978699|
|global_distance|Far MAE (Å)|32|2.551755|
|global_distance|Far signed error (Å)|32|-1.431465|
|global_distance|Remaining95% RMSD (Å)|32|2.657737|
|global_distance|Fragment32 RMSD (Å)|32|1.530814|
|global_distance|Predicted/GT Rg|32|0.980981|

|Candidate − reference|Metric|Proteins|Mean Δ|95% CI|
|---|---|---:|---:|---|
|global_distance − coordinate_zero|Far MAE (Å)|32|-0.040460|[-0.070669, -0.016111]|
|global_distance − coordinate_zero|Far signed error (Å)|32|+0.107864|[+0.075862, +0.144268]|
|global_distance − coordinate_zero|Remaining95% RMSD (Å)|32|-0.007619|[-0.021325, +0.006201]|
|global_distance − coordinate_zero|Fragment32 RMSD (Å)|32|-0.005418|[-0.008896, -0.002318]|
|global_distance − coordinate_zero|Predicted/GT Rg|32|+0.002282|[+0.001680, +0.002976]|
|global_distance − expanded|Far MAE (Å)|32|+0.054949|[-0.000448, +0.121709]|
|global_distance − expanded|Far signed error (Å)|32|-0.114087|[-0.298308, +0.011556]|
|global_distance − expanded|Remaining95% RMSD (Å)|32|+0.060074|[-0.005854, +0.147508]|
|global_distance − expanded|Fragment32 RMSD (Å)|32|+0.003398|[-0.008174, +0.016751]|
|global_distance − expanded|Predicted/GT Rg|32|-0.001875|[-0.005665, +0.000509]|
|global_distance − retained|Far MAE (Å)|32|+0.002233|[-0.112999, +0.101899]|
|global_distance − retained|Far signed error (Å)|32|+0.047869|[-0.119031, +0.204950]|
|global_distance − retained|Remaining95% RMSD (Å)|32|+0.068995|[-0.026083, +0.178920]|
|global_distance − retained|Fragment32 RMSD (Å)|32|+0.011080|[-0.005165, +0.028892]|
|global_distance − retained|Predicted/GT Rg|32|+0.001535|[-0.001577, +0.004469]|
|global_distance − native_s1|Far MAE (Å)|32|-0.252449|[-0.540046, -0.042671]|
|global_distance − native_s1|Far signed error (Å)|32|+0.619318|[+0.384375, +0.923853]|
|global_distance − native_s1|Remaining95% RMSD (Å)|32|+0.061394|[-0.110726, +0.250968]|
|global_distance − native_s1|Fragment32 RMSD (Å)|32|-0.026581|[-0.066284, +0.012772]|
|global_distance − native_s1|Predicted/GT Rg|32|+0.012865|[+0.008817, +0.018015]|
|global_distance − native_s2|Far MAE (Å)|32|+0.058036|[-0.099459, +0.233229]|
|global_distance − native_s2|Far signed error (Å)|32|-0.027437|[-0.183167, +0.131555]|
|global_distance − native_s2|Remaining95% RMSD (Å)|32|+0.134209|[-0.005091, +0.306541]|
|global_distance − native_s2|Fragment32 RMSD (Å)|32|-0.004469|[-0.043431, +0.033290]|
|global_distance − native_s2|Predicted/GT Rg|32|-0.000367|[-0.003361, +0.002590]|

### original_train128

|Model|Metric|Proteins with support|Mean|
|---|---|---:|---:|
|native_s1|Far MAE (Å)|128|4.063210|
|native_s1|Far signed error (Å)|128|-3.376799|
|native_s1|Remaining95% RMSD (Å)|128|3.618748|
|native_s1|Fragment32 RMSD (Å)|128|1.888006|
|native_s1|Predicted/GT Rg|128|0.945882|
|native_s2|Far MAE (Å)|128|3.566957|
|native_s2|Far signed error (Å)|128|-2.675569|
|native_s2|Remaining95% RMSD (Å)|128|3.594904|
|native_s2|Fragment32 RMSD (Å)|128|1.807704|
|native_s2|Predicted/GT Rg|128|0.960454|
|retained|Far MAE (Å)|128|3.410409|
|retained|Far signed error (Å)|128|-2.506688|
|retained|Remaining95% RMSD (Å)|128|3.361259|
|retained|Fragment32 RMSD (Å)|128|1.776817|
|retained|Predicted/GT Rg|128|0.961609|
|expanded|Far MAE (Å)|128|3.273227|
|expanded|Far signed error (Å)|128|-2.348797|
|expanded|Remaining95% RMSD (Å)|128|3.251921|
|expanded|Fragment32 RMSD (Å)|128|1.756574|
|expanded|Predicted/GT Rg|128|0.964275|
|coordinate_zero|Far MAE (Å)|128|3.578645|
|coordinate_zero|Far signed error (Å)|128|-2.676349|
|coordinate_zero|Remaining95% RMSD (Å)|128|3.543313|
|coordinate_zero|Fragment32 RMSD (Å)|128|1.806612|
|coordinate_zero|Predicted/GT Rg|128|0.959971|
|global_distance|Far MAE (Å)|128|3.508212|
|global_distance|Far signed error (Å)|128|-2.562777|
|global_distance|Remaining95% RMSD (Å)|128|3.525831|
|global_distance|Fragment32 RMSD (Å)|128|1.800392|
|global_distance|Predicted/GT Rg|128|0.962322|

|Candidate − reference|Metric|Proteins|Mean Δ|95% CI|
|---|---|---:|---:|---|
|global_distance − coordinate_zero|Far MAE (Å)|128|-0.070433|[-0.096124, -0.046711]|
|global_distance − coordinate_zero|Far signed error (Å)|128|+0.113572|[+0.087463, +0.141052]|
|global_distance − coordinate_zero|Remaining95% RMSD (Å)|128|-0.017482|[-0.025962, -0.010148]|
|global_distance − coordinate_zero|Fragment32 RMSD (Å)|128|-0.006220|[-0.009076, -0.003589]|
|global_distance − coordinate_zero|Predicted/GT Rg|128|+0.002350|[+0.001868, +0.002865]|
|global_distance − expanded|Far MAE (Å)|128|+0.234984|[+0.115566, +0.373785]|
|global_distance − expanded|Far signed error (Å)|128|-0.213979|[-0.358147, -0.088997]|
|global_distance − expanded|Remaining95% RMSD (Å)|128|+0.273910|[+0.152382, +0.416472]|
|global_distance − expanded|Fragment32 RMSD (Å)|128|+0.043818|[+0.024485, +0.064929]|
|global_distance − expanded|Predicted/GT Rg|128|-0.001954|[-0.003965, -0.000185]|
|global_distance − retained|Far MAE (Å)|128|+0.097803|[+0.006786, +0.210734]|
|global_distance − retained|Far signed error (Å)|128|-0.056088|[-0.171337, +0.034110]|
|global_distance − retained|Remaining95% RMSD (Å)|128|+0.164572|[+0.074374, +0.278038]|
|global_distance − retained|Fragment32 RMSD (Å)|128|+0.023575|[+0.008049, +0.041026]|
|global_distance − retained|Predicted/GT Rg|128|+0.000713|[-0.000982, +0.002224]|
|global_distance − native_s1|Far MAE (Å)|128|-0.554998|[-0.810788, -0.341432]|
|global_distance − native_s1|Far signed error (Å)|128|+0.814022|[+0.590365, +1.071004]|
|global_distance − native_s1|Remaining95% RMSD (Å)|128|-0.092917|[-0.154996, -0.042450]|
|global_distance − native_s1|Fragment32 RMSD (Å)|128|-0.087614|[-0.130627, -0.049466]|
|global_distance − native_s1|Predicted/GT Rg|128|+0.016440|[+0.012224, +0.021095]|
|global_distance − native_s2|Far MAE (Å)|128|-0.058745|[-0.103088, -0.015511]|
|global_distance − native_s2|Far signed error (Å)|128|+0.112793|[+0.055729, +0.174067]|
|global_distance − native_s2|Remaining95% RMSD (Å)|128|-0.069073|[-0.108399, -0.032954]|
|global_distance − native_s2|Fragment32 RMSD (Å)|128|-0.007311|[-0.028056, +0.013229]|
|global_distance − native_s2|Predicted/GT Rg|128|+0.001868|[+0.000986, +0.002764]|

### added_train295

|Model|Metric|Proteins with support|Mean|
|---|---|---:|---:|
|native_s1|Far MAE (Å)|294|4.321283|
|native_s1|Far signed error (Å)|294|-3.864679|
|native_s1|Remaining95% RMSD (Å)|295|3.131782|
|native_s1|Fragment32 RMSD (Å)|295|1.924606|
|native_s1|Predicted/GT Rg|295|0.940490|
|native_s2|Far MAE (Å)|294|3.874310|
|native_s2|Far signed error (Å)|294|-3.228543|
|native_s2|Remaining95% RMSD (Å)|295|3.122770|
|native_s2|Fragment32 RMSD (Å)|295|1.865591|
|native_s2|Predicted/GT Rg|295|0.954549|
|retained|Far MAE (Å)|294|3.810024|
|retained|Far signed error (Å)|294|-3.158035|
|retained|Remaining95% RMSD (Å)|295|2.990563|
|retained|Fragment32 RMSD (Å)|295|1.856322|
|retained|Predicted/GT Rg|295|0.953640|
|expanded|Far MAE (Å)|294|3.606580|
|expanded|Far signed error (Å)|294|-2.958485|
|expanded|Remaining95% RMSD (Å)|295|2.854311|
|expanded|Fragment32 RMSD (Å)|295|1.792734|
|expanded|Predicted/GT Rg|295|0.957289|
|coordinate_zero|Far MAE (Å)|294|3.856251|
|coordinate_zero|Far signed error (Å)|294|-3.195585|
|coordinate_zero|Remaining95% RMSD (Å)|295|3.088704|
|coordinate_zero|Fragment32 RMSD (Å)|295|1.864296|
|coordinate_zero|Predicted/GT Rg|295|0.954970|
|global_distance|Far MAE (Å)|294|3.771811|
|global_distance|Far signed error (Å)|294|-3.076743|
|global_distance|Remaining95% RMSD (Å)|295|3.066192|
|global_distance|Fragment32 RMSD (Å)|295|1.851321|
|global_distance|Predicted/GT Rg|295|0.957426|

|Candidate − reference|Metric|Proteins|Mean Δ|95% CI|
|---|---|---:|---:|---|
|global_distance − coordinate_zero|Far MAE (Å)|294|-0.084439|[-0.108451, -0.064020]|
|global_distance − coordinate_zero|Far signed error (Å)|294|+0.118842|[+0.098528, +0.142915]|
|global_distance − coordinate_zero|Remaining95% RMSD (Å)|295|-0.022512|[-0.033232, -0.013963]|
|global_distance − coordinate_zero|Fragment32 RMSD (Å)|295|-0.012975|[-0.018924, -0.008716]|
|global_distance − coordinate_zero|Predicted/GT Rg|295|+0.002456|[+0.002091, +0.002865]|
|global_distance − expanded|Far MAE (Å)|294|+0.165231|[+0.087231, +0.266634]|
|global_distance − expanded|Far signed error (Å)|294|-0.118258|[-0.220865, -0.039192]|
|global_distance − expanded|Remaining95% RMSD (Å)|295|+0.211881|[+0.138375, +0.308095]|
|global_distance − expanded|Fragment32 RMSD (Å)|295|+0.058586|[+0.043897, +0.074054]|
|global_distance − expanded|Predicted/GT Rg|295|+0.000137|[-0.001270, +0.001452]|
|global_distance − retained|Far MAE (Å)|294|-0.038212|[-0.150163, +0.135582]|
|global_distance − retained|Far signed error (Å)|294|+0.081292|[-0.096406, +0.196672]|
|global_distance − retained|Remaining95% RMSD (Å)|295|+0.075629|[+0.000736, +0.206353]|
|global_distance − retained|Fragment32 RMSD (Å)|295|-0.005001|[-0.025255, +0.016650]|
|global_distance − retained|Predicted/GT Rg|295|+0.003786|[+0.001512, +0.005903]|
|global_distance − native_s1|Far MAE (Å)|294|-0.549472|[-0.671434, -0.438042]|
|global_distance − native_s1|Far signed error (Å)|294|+0.787936|[+0.672964, +0.911047]|
|global_distance − native_s1|Remaining95% RMSD (Å)|295|-0.065590|[-0.113270, -0.028011]|
|global_distance − native_s1|Fragment32 RMSD (Å)|295|-0.073286|[-0.103627, -0.047270]|
|global_distance − native_s1|Predicted/GT Rg|295|+0.016936|[+0.014281, +0.019847]|
|global_distance − native_s2|Far MAE (Å)|294|-0.102499|[-0.139381, -0.067255]|
|global_distance − native_s2|Far signed error (Å)|294|+0.151800|[+0.113502, +0.191682]|
|global_distance − native_s2|Remaining95% RMSD (Å)|295|-0.056578|[-0.081659, -0.034846]|
|global_distance − native_s2|Fragment32 RMSD (Å)|295|-0.014271|[-0.030892, +0.003462]|
|global_distance − native_s2|Predicted/GT Rg|295|+0.002877|[+0.002120, +0.003615]|
