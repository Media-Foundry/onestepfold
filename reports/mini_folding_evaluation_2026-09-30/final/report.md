# C4/S1 fixed-terminal folding comparison

Frozen ESM2 + C4 conditioning; only the native diffusion parameters were trained. Both arms start from the retained checkpoint, reset optimizer state and receive 2048 new updates / 8192 new exposures. This is not training from zero.

Scores use observed experimental GT. Each protein contributes the mean of its two fixed noises; no best-of-noise or intermediate-checkpoint selection. Geometry counts describe the explicit severe-collision and checked-stereocentre criteria, not comprehensive chemical correctness or deployment approval.

## new_validation32: 32 proteins

|Model|AA-lDDT|Cα-lDDT|Zero severe + strict stereo, instances|Both noises, proteins|Severe pairs total|
|---|---:|---:|---:|---:|---:|
|native_s1|0.815917|0.899536|30/64|9/32|902|
|native_s2|0.828004|0.910778|37/64|15/32|353|
|retained|0.817664|0.902912|46/64|20/32|562|
|train128|0.816664|0.900883|42/64|18/32|523|
|expanded|0.818402|0.902915|44/64|20/32|540|

Positive quality differences favor the candidate. Intervals resample proteins, conditional on the two locked noises; they do not establish independence from pretraining.

|Candidate − reference|Metric|Mean Δ|95% CI|P01 Δ|P05 Δ|Worst5% Δ mean|Δ < −0.05, proteins|
|---|---|---:|---|---:|---:|---:|---:|
|expanded − train128|AA|+0.001739|[+0.000876, +0.002794]|-0.001757|-0.000552|-0.001513|0/32|
|expanded − train128|Cα|+0.002032|[+0.001070, +0.003189]|-0.000833|-0.000613|-0.000796|0/32|
|native_s2 − native_s1|AA|+0.012087|[+0.008207, +0.016551]|-0.000455|+0.001240|-0.000008|0/32|
|native_s2 − native_s1|Cα|+0.011241|[+0.006553, +0.017328]|-0.001357|-0.000386|-0.001131|0/32|
|retained − native_s1|AA|+0.001747|[+0.000384, +0.003226]|-0.005023|-0.004120|-0.004870|0/32|
|retained − native_s1|Cα|+0.003376|[+0.001162, +0.005934]|-0.005854|-0.002441|-0.004934|0/32|
|train128 − retained|AA|-0.001001|[-0.001803, -0.000281]|-0.007475|-0.004890|-0.006860|0/32|
|train128 − retained|Cα|-0.002029|[-0.003088, -0.001084]|-0.008886|-0.008715|-0.008867|0/32|
|train128 − native_s1|AA|+0.000746|[-0.000964, +0.002518]|-0.007131|-0.006755|-0.007059|0/32|
|train128 − native_s1|Cα|+0.001347|[-0.001272, +0.004254]|-0.011070|-0.009234|-0.010930|0/32|
|train128 − native_s2|AA|-0.011340|[-0.015449, -0.007638]|-0.042339|-0.034426|-0.040181|0/32|
|train128 − native_s2|Cα|-0.009895|[-0.014423, -0.006072]|-0.049976|-0.030667|-0.046414|1/32|
|expanded − retained|AA|+0.000738|[-0.000080, +0.001503]|-0.005954|-0.002069|-0.005071|0/32|
|expanded − retained|Cα|+0.000003|[-0.000888, +0.000863]|-0.006972|-0.002345|-0.005796|0/32|
|expanded − native_s1|AA|+0.002485|[+0.000761, +0.004271]|-0.007615|-0.004872|-0.006880|0/32|
|expanded − native_s1|Cα|+0.003379|[+0.000709, +0.006466]|-0.008410|-0.006450|-0.008410|0/32|
|expanded − native_s2|AA|-0.009601|[-0.013642, -0.006038]|-0.042215|-0.030252|-0.040647|0/32|
|expanded − native_s2|Cα|-0.007863|[-0.012210, -0.004214]|-0.045935|-0.027802|-0.043557|0/32|

|Candidate − reference|New severe collision instances from zero|Lost strict stereo instances|
|---|---:|---:|
|expanded − train128|3|3|
|native_s2 − native_s1|5|8|
|retained − native_s1|0|2|
|train128 − retained|6|4|
|train128 − native_s1|3|2|
|train128 − native_s2|8|2|
|expanded − retained|6|1|
|expanded − native_s1|3|1|
|expanded − native_s2|6|0|

Descriptive length/assembly subsets; overlapping views, not additional independent tests.

|Subset|Proteins|Candidate − reference|Mean AA Δ|Mean Cα Δ|
|---|---:|---|---:|---:|
|length_256_511|15|expanded − train128|+0.001677|+0.001741|
|length_256_511|15|native_s2 − native_s1|+0.013264|+0.011679|
|length_256_511|15|retained − native_s1|+0.001774|+0.003469|
|length_256_511|15|train128 − retained|-0.000837|-0.001927|
|length_256_511|15|train128 − native_s1|+0.000938|+0.001542|
|length_256_511|15|train128 − native_s2|-0.012326|-0.010137|
|length_256_511|15|expanded − retained|+0.000840|-0.000185|
|length_256_511|15|expanded − native_s1|+0.002614|+0.003283|
|length_256_511|15|expanded − native_s2|-0.010649|-0.008396|
|length_50_255|16|expanded − train128|+0.002041|+0.002448|
|length_50_255|16|native_s2 − native_s1|+0.010007|+0.009728|
|length_50_255|16|retained − native_s1|+0.001920|+0.003470|
|length_50_255|16|train128 − retained|-0.000890|-0.001713|
|length_50_255|16|train128 − native_s1|+0.001030|+0.001757|
|length_50_255|16|train128 − native_s2|-0.008977|-0.007971|
|length_50_255|16|expanded − retained|+0.001151|+0.000735|
|length_50_255|16|expanded − native_s1|+0.003071|+0.004205|
|length_50_255|16|expanded − native_s2|-0.006936|-0.005523|
|length_512_1024|1|expanded − train128|-0.002155|-0.000260|
|length_512_1024|1|native_s2 − native_s1|+0.027706|+0.028890|
|length_512_1024|1|retained − native_s1|-0.001420|+0.000483|
|length_512_1024|1|train128 − retained|-0.005239|-0.008631|
|length_512_1024|1|train128 − native_s1|-0.006659|-0.008148|
|length_512_1024|1|train128 − native_s2|-0.034365|-0.037038|
|length_512_1024|1|expanded − retained|-0.007394|-0.008891|
|length_512_1024|1|expanded − native_s1|-0.008814|-0.008409|
|length_512_1024|1|expanded − native_s2|-0.036520|-0.037299|
|monomer|1|expanded − train128|+0.001540|+0.000486|
|monomer|1|native_s2 − native_s1|+0.002077|+0.003400|
|monomer|1|retained − native_s1|-0.001612|+0.002296|
|monomer|1|train128 − retained|-0.001205|+0.000778|
|monomer|1|train128 − native_s1|-0.002818|+0.003074|
|monomer|1|train128 − native_s2|-0.004895|-0.000325|
|monomer|1|expanded − retained|+0.000335|+0.001264|
|monomer|1|expanded − native_s1|-0.001278|+0.003560|
|monomer|1|expanded − native_s2|-0.003355|+0.000161|
|multimer_single_chain|31|expanded − train128|+0.001745|+0.002082|
|multimer_single_chain|31|native_s2 − native_s1|+0.012409|+0.011494|
|multimer_single_chain|31|retained − native_s1|+0.001856|+0.003411|
|multimer_single_chain|31|train128 − retained|-0.000994|-0.002120|
|multimer_single_chain|31|train128 − native_s1|+0.000861|+0.001291|
|multimer_single_chain|31|train128 − native_s2|-0.011548|-0.010203|
|multimer_single_chain|31|expanded − retained|+0.000751|-0.000038|
|multimer_single_chain|31|expanded − native_s1|+0.002607|+0.003373|
|multimer_single_chain|31|expanded − native_s2|-0.009803|-0.008121|

## original_train128: 128 proteins

|Model|AA-lDDT|Cα-lDDT|Zero severe + strict stereo, instances|Both noises, proteins|Severe pairs total|
|---|---:|---:|---:|---:|---:|
|native_s1|0.801184|0.878791|107/256|42/128|8134|
|native_s2|0.814059|0.891694|137/256|58/128|2356|
|retained|0.806455|0.885367|165/256|73/128|4311|
|train128|0.813520|0.890399|206/256|93/128|3339|
|expanded|0.808113|0.886040|183/256|82/128|3874|

Positive quality differences favor the candidate. Intervals resample proteins, conditional on the two locked noises; they do not establish independence from pretraining.

|Candidate − reference|Metric|Mean Δ|95% CI|P01 Δ|P05 Δ|Worst5% Δ mean|Δ < −0.05, proteins|
|---|---|---:|---|---:|---:|---:|---:|
|expanded − train128|AA|-0.005407|[-0.007029, -0.003749]|-0.033264|-0.017577|-0.027109|0/128|
|expanded − train128|Cα|-0.004360|[-0.006430, -0.002296]|-0.031850|-0.015924|-0.031617|1/128|
|native_s2 − native_s1|AA|+0.012875|[+0.009331, +0.017393]|-0.024920|-0.001812|-0.012695|0/128|
|native_s2 − native_s1|Cα|+0.012904|[+0.008549, +0.019057]|-0.025146|-0.003637|-0.013402|0/128|
|retained − native_s1|AA|+0.005271|[+0.003561, +0.007481]|-0.004704|-0.002682|-0.005635|0/128|
|retained − native_s1|Cα|+0.006576|[+0.004397, +0.009583]|-0.005195|-0.002025|-0.004807|0/128|
|train128 − retained|AA|+0.007065|[+0.004823, +0.009282]|-0.045245|-0.000039|-0.028443|0/128|
|train128 − retained|Cα|+0.005032|[+0.002283, +0.007759]|-0.058682|-0.001912|-0.036759|3/128|
|train128 − native_s1|AA|+0.012336|[+0.009024, +0.016198]|-0.036769|-0.001366|-0.027902|0/128|
|train128 − native_s1|Cα|+0.011609|[+0.007474, +0.016728]|-0.050187|-0.001893|-0.035749|2/128|
|train128 − native_s2|AA|-0.000539|[-0.004162, +0.002710]|-0.075713|-0.038804|-0.065769|6/128|
|train128 − native_s2|Cα|-0.001295|[-0.005215, +0.002177]|-0.088208|-0.046357|-0.075636|6/128|
|expanded − retained|AA|+0.001658|[+0.000759, +0.002486]|-0.020037|-0.004801|-0.011892|0/128|
|expanded − retained|Cα|+0.000673|[-0.000433, +0.001675]|-0.027395|-0.005817|-0.015542|0/128|
|expanded − native_s1|AA|+0.006929|[+0.004757, +0.009656]|-0.019207|-0.003529|-0.011460|0/128|
|expanded − native_s1|Cα|+0.007249|[+0.004532, +0.010788]|-0.023712|-0.003685|-0.014838|0/128|
|expanded − native_s2|AA|-0.005946|[-0.009019, -0.003258]|-0.085536|-0.033253|-0.059485|3/128|
|expanded − native_s2|Cα|-0.005655|[-0.009341, -0.002575]|-0.095136|-0.028732|-0.071406|5/128|

|Candidate − reference|New severe collision instances from zero|Lost strict stereo instances|
|---|---:|---:|
|expanded − train128|29|12|
|native_s2 − native_s1|15|16|
|retained − native_s1|1|6|
|train128 − retained|5|7|
|train128 − native_s1|3|4|
|train128 − native_s2|5|9|
|expanded − retained|5|5|
|expanded − native_s1|1|4|
|expanded − native_s2|11|10|

Descriptive length/assembly subsets; overlapping views, not additional independent tests.

|Subset|Proteins|Candidate − reference|Mean AA Δ|Mean Cα Δ|
|---|---:|---|---:|---:|
|length_256_511|55|expanded − train128|-0.002606|-0.001981|
|length_256_511|55|native_s2 − native_s1|+0.010536|+0.009041|
|length_256_511|55|retained − native_s1|+0.003560|+0.004582|
|length_256_511|55|train128 − retained|+0.004177|+0.002707|
|length_256_511|55|train128 − native_s1|+0.007736|+0.007289|
|length_256_511|55|train128 − native_s2|-0.002800|-0.001752|
|length_256_511|55|expanded − retained|+0.001571|+0.000726|
|length_256_511|55|expanded − native_s1|+0.005131|+0.005308|
|length_256_511|55|expanded − native_s2|-0.005406|-0.003733|
|length_50_255|64|expanded − train128|-0.008176|-0.006611|
|length_50_255|64|native_s2 − native_s1|+0.012021|+0.013087|
|length_50_255|64|retained − native_s1|+0.007110|+0.008660|
|length_50_255|64|train128 − retained|+0.010822|+0.008213|
|length_50_255|64|train128 − native_s1|+0.017932|+0.016874|
|length_50_255|64|train128 − native_s2|+0.005911|+0.003787|
|length_50_255|64|expanded − retained|+0.002646|+0.001602|
|length_50_255|64|expanded − native_s1|+0.009756|+0.010262|
|length_50_255|64|expanded − native_s2|-0.002265|-0.002825|
|length_512_1024|9|expanded − train128|-0.002844|-0.002887|
|length_512_1024|9|native_s2 − native_s1|+0.033234|+0.035209|
|length_512_1024|9|retained − native_s1|+0.002652|+0.003946|
|length_512_1024|9|train128 − retained|-0.001997|-0.003376|
|length_512_1024|9|train128 − native_s1|+0.000655|+0.000570|
|length_512_1024|9|train128 − native_s2|-0.032579|-0.034639|
|length_512_1024|9|expanded − retained|-0.004840|-0.006262|
|length_512_1024|9|expanded − native_s1|-0.002189|-0.002316|
|length_512_1024|9|expanded − native_s2|-0.035423|-0.037526|
|monomer|5|expanded − train128|-0.003865|-0.003410|
|monomer|5|native_s2 − native_s1|+0.019507|+0.018539|
|monomer|5|retained − native_s1|+0.006786|+0.009078|
|monomer|5|train128 − retained|+0.006343|+0.005096|
|monomer|5|train128 − native_s1|+0.013129|+0.014175|
|monomer|5|train128 − native_s2|-0.006377|-0.004364|
|monomer|5|expanded − retained|+0.002478|+0.001686|
|monomer|5|expanded − native_s1|+0.009264|+0.010765|
|monomer|5|expanded − native_s2|-0.010242|-0.007775|
|multimer_single_chain|123|expanded − train128|-0.005470|-0.004398|
|multimer_single_chain|123|native_s2 − native_s1|+0.012605|+0.012675|
|multimer_single_chain|123|retained − native_s1|+0.005209|+0.006475|
|multimer_single_chain|123|train128 − retained|+0.007095|+0.005030|
|multimer_single_chain|123|train128 − native_s1|+0.012304|+0.011504|
|multimer_single_chain|123|train128 − native_s2|-0.000301|-0.001170|
|multimer_single_chain|123|expanded − retained|+0.001625|+0.000632|
|multimer_single_chain|123|expanded − native_s1|+0.006834|+0.007106|
|multimer_single_chain|123|expanded − native_s2|-0.005771|-0.005569|

## added_train295: 295 proteins

|Model|AA-lDDT|Cα-lDDT|Zero severe + strict stereo, instances|Both noises, proteins|Severe pairs total|
|---|---:|---:|---:|---:|---:|
|native_s1|0.801504|0.881038|287/590|112/295|14299|
|native_s2|0.812092|0.891652|344/590|138/295|4255|
|retained|0.804582|0.885483|355/590|144/295|7483|
|train128|0.803938|0.884115|369/590|154/295|6796|
|expanded|0.809317|0.889017|443/590|204/295|5796|

Positive quality differences favor the candidate. Intervals resample proteins, conditional on the two locked noises; they do not establish independence from pretraining.

|Candidate − reference|Metric|Mean Δ|95% CI|P01 Δ|P05 Δ|Worst5% Δ mean|Δ < −0.05, proteins|
|---|---|---:|---|---:|---:|---:|---:|
|expanded − train128|AA|+0.005378|[+0.004519, +0.006219]|-0.002420|+0.000367|-0.005190|1/295|
|expanded − train128|Cα|+0.004903|[+0.003835, +0.005922]|-0.003941|-0.000832|-0.008453|1/295|
|native_s2 − native_s1|AA|+0.010588|[+0.008716, +0.012669]|-0.014541|-0.003430|-0.012425|0/295|
|native_s2 − native_s1|Cα|+0.010613|[+0.008330, +0.013298]|-0.012491|-0.003552|-0.010708|0/295|
|retained − native_s1|AA|+0.003079|[+0.002057, +0.004198]|-0.010743|-0.003940|-0.006624|0/295|
|retained − native_s1|Cα|+0.004444|[+0.003246, +0.005748]|-0.010106|-0.003114|-0.006756|0/295|
|train128 − retained|AA|-0.000644|[-0.001068, -0.000236]|-0.011678|-0.005782|-0.010756|0/295|
|train128 − retained|Cα|-0.001368|[-0.001946, -0.000816]|-0.015780|-0.008180|-0.014226|0/295|
|train128 − native_s1|AA|+0.002435|[+0.001349, +0.003660]|-0.012076|-0.006221|-0.009566|0/295|
|train128 − native_s1|Cα|+0.003076|[+0.001766, +0.004611]|-0.013497|-0.005461|-0.009750|0/295|
|train128 − native_s2|AA|-0.008154|[-0.009618, -0.006831]|-0.064600|-0.024138|-0.047963|7/295|
|train128 − native_s2|Cα|-0.007537|[-0.009326, -0.005987]|-0.085981|-0.023948|-0.055291|6/295|
|expanded − retained|AA|+0.004734|[+0.003987, +0.005503]|-0.005163|-0.000596|-0.005752|0/295|
|expanded − retained|Cα|+0.003535|[+0.002674, +0.004434]|-0.005792|-0.001717|-0.008066|1/295|
|expanded − native_s1|AA|+0.007813|[+0.006537, +0.009206]|-0.005358|-0.001540|-0.004558|0/295|
|expanded − native_s1|Cα|+0.007979|[+0.006498, +0.009632]|-0.003760|-0.001652|-0.004258|0/295|
|expanded − native_s2|AA|-0.002775|[-0.004190, -0.001546]|-0.029740|-0.014388|-0.032744|2/295|
|expanded − native_s2|Cα|-0.002634|[-0.004560, -0.001141]|-0.035682|-0.012744|-0.041069|2/295|

|Candidate − reference|New severe collision instances from zero|Lost strict stereo instances|
|---|---:|---:|
|expanded − train128|10|13|
|native_s2 − native_s1|46|44|
|retained − native_s1|17|20|
|train128 − retained|34|17|
|train128 − native_s1|28|16|
|train128 − native_s2|62|37|
|expanded − retained|14|11|
|expanded − native_s1|5|7|
|expanded − native_s2|22|26|

Descriptive length/assembly subsets; overlapping views, not additional independent tests.

|Subset|Proteins|Candidate − reference|Mean AA Δ|Mean Cα Δ|
|---|---:|---|---:|---:|
|length_256_511|48|expanded − train128|+0.001980|+0.001902|
|length_256_511|48|native_s2 − native_s1|+0.005672|+0.005006|
|length_256_511|48|retained − native_s1|+0.000427|+0.001127|
|length_256_511|48|train128 − retained|-0.000518|-0.001226|
|length_256_511|48|train128 − native_s1|-0.000091|-0.000099|
|length_256_511|48|train128 − native_s2|-0.005763|-0.005105|
|length_256_511|48|expanded − retained|+0.001462|+0.000677|
|length_256_511|48|expanded − native_s1|+0.001888|+0.001804|
|length_256_511|48|expanded − native_s2|-0.003784|-0.003203|
|length_50_255|242|expanded − train128|+0.006158|+0.005605|
|length_50_255|242|native_s2 − native_s1|+0.011504|+0.011679|
|length_50_255|242|retained − native_s1|+0.003654|+0.005139|
|length_50_255|242|train128 − retained|-0.000708|-0.001442|
|length_50_255|242|train128 − native_s1|+0.002947|+0.003697|
|length_50_255|242|train128 − native_s2|-0.008557|-0.007983|
|length_50_255|242|expanded − retained|+0.005450|+0.004163|
|length_50_255|242|expanded − native_s1|+0.009104|+0.009301|
|length_50_255|242|expanded − native_s2|-0.002400|-0.002378|
|length_512_1024|5|expanded − train128|+0.000284|-0.000281|
|length_512_1024|5|native_s2 − native_s1|+0.013455|+0.012850|
|length_512_1024|5|retained − native_s1|+0.000666|+0.002681|
|length_512_1024|5|train128 − retained|+0.001237|+0.000858|
|length_512_1024|5|train128 − native_s1|+0.001904|+0.003539|
|length_512_1024|5|train128 − native_s2|-0.011552|-0.009311|
|length_512_1024|5|expanded − retained|+0.001522|+0.000577|
|length_512_1024|5|expanded − native_s1|+0.002188|+0.003258|
|length_512_1024|5|expanded − native_s2|-0.011267|-0.009592|
|monomer|8|expanded − train128|+0.003444|+0.003249|
|monomer|8|native_s2 − native_s1|+0.005285|+0.003519|
|monomer|8|retained − native_s1|+0.000485|+0.000609|
|monomer|8|train128 − retained|-0.000304|-0.000838|
|monomer|8|train128 − native_s1|+0.000180|-0.000229|
|monomer|8|train128 − native_s2|-0.005105|-0.003748|
|monomer|8|expanded − retained|+0.003139|+0.002411|
|monomer|8|expanded − native_s1|+0.003624|+0.003020|
|monomer|8|expanded − native_s2|-0.001661|-0.000499|
|multimer_single_chain|287|expanded − train128|+0.005432|+0.004949|
|multimer_single_chain|287|native_s2 − native_s1|+0.010736|+0.010811|
|multimer_single_chain|287|retained − native_s1|+0.003151|+0.004551|
|multimer_single_chain|287|train128 − retained|-0.000653|-0.001383|
|multimer_single_chain|287|train128 − native_s1|+0.002498|+0.003169|
|multimer_single_chain|287|train128 − native_s2|-0.008239|-0.007642|
|multimer_single_chain|287|expanded − retained|+0.004779|+0.003566|
|multimer_single_chain|287|expanded − native_s1|+0.007930|+0.008117|
|multimer_single_chain|287|expanded − native_s2|-0.002806|-0.002694|

## Matched original-TRAIN32 learning curves

These are training probes, not validation learning curves. The expanded arm exposes each original protein less often at equal total updates.

|Arm|New update|AA-lDDT|Cα-lDDT|Zero severe + strict stereo / 64|Severe pairs|
|---|---:|---:|---:|---:|---:|
|expanded|0|0.804773|0.885653|41/64|394|
|expanded|512|0.805367|0.885849|42/64|382|
|expanded|1024|0.805909|0.886087|41/64|396|
|expanded|2048|0.806617|0.886601|43/64|378|
|train128|0|0.804773|0.885653|41/64|394|
|train128|512|0.807179|0.887278|47/64|330|
|train128|1024|0.808697|0.888009|52/64|209|
|train128|2048|0.811420|0.890676|52/64|166|

## Cost and provenance

|Arm|Training seconds|Allocated peak GiB|Samples per protein, min–max|Clipped updates|
|---|---:|---:|---|---:|
|expanded|6217.4|16.182|19–20|1371|
|train128|4621.7|16.178|64–64|1128|

Complete outputs: **4550** over **455 proteins**. New evaluation prediction NFEs: **2922**; engineering probes: **80**. Independent dense-distance metric maximum absolute discrepancy: **4.44e-16**.

Inference timings in evaluation.json cover diffusion with cached conditioning only. They omit live ESM2 and Pairformer, and are not end-to-end folding speed. Equal updates/exposures are not equal GPU time, FLOPs, or per-protein exposure.

Original128, added295 and new validation32 remain distinct cohorts. Most sources are complete single chains extracted from homooligomers. The scope is supported single-chain prediction; assembly context and pretraining exposure remain limitations.

No model is automatically promoted by this report. Review mean quality, paired tails and newly introduced chemical failures jointly. This experiment does not establish BindCraft utility, binding affinity or a gradient through a changed output function.
