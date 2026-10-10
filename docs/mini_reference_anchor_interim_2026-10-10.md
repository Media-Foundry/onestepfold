# Reference-anchor trial: first fixed checkpoint, no terminal decision

Seed272001 has completed the pre-specified32-update checkpoint and all1,824
candidate/noise S1 outputs. Training continues to128. The second seed is still
running. This is an interim latent comparison, not a selected checkpoint,
completed functional assessment, independent confirmation or promotion.

The comparison uses the already closed unanchored AdamW272001 checkpoint32:
same initialization, training data, candidate exposures, objective and optimizer.
The anchor branch adds reference work, so computation and wall time differ.
The residual target remains target_C4_pair minus unadapted candidate pair; zero
correction has NMSE1. Values below are site-normalized then protein weighted.

| Panel | Old AdamW AA residual NMSE | Anchored AA residual NMSE | Parents improving |
|---|---:|---:|---:|
| TRAIN |0.996782|0.956188|14/15|
| Same-protein new site |0.999969|0.990952|2/3|
| New-protein development |0.999279|0.986352|6/9|

Descriptive protein-paired bootstrap intervals for anchored-minus-control AA
NMSE are[-0.06361,-0.02119] on TRAIN and[-0.02352,-0.00151] on the nine-protein
development panel. The three-protein new-site interval crosses zero. These are
the original fixed resampling rules, not new thresholds; repeated development
use and a single interim seed limit interpretation.

The learning signal is stronger than the unanchored same-budget checkpoint,
but recovery remains small: about4.38% of TRAIN and1.36% of new-protein AA
residual NMSE relative to zero correction. This does not resolve the large
oracle gap. On new proteins the predicted AA energy ratio is0.02316 and cosine
0.11075, versus0.000155 and0.04262 in the control. Producing more AA variation
is not sufficient; final decoded structure, regret and geometry remain required.

The predicted common-energy fraction decreases from0.9893 to0.5582 on TRAIN,
and0.9907 to0.5163 on new proteins. Some reduction follows directly from the
reference subtraction; it must not be treated as independent evidence of
correct response recovery. The AA error comparison above measures a different
quantity. The training graph, not a post-hoc substitution, generated this state.

Evidence: `reports/mini_reference_anchor_training_2026-10-10/interim_32_seed272001`.
Evaluation SHA256:
`c6c6fbf28675ad5f7bc27ec79619b514e57e4057ae33d82ee061a57bd0c4babc`.
Remote checkpoint hash was independently checked against the saved evaluation:
`76c83765f301da161c9c2e71f1500f592c3da6218377ed46a2e69701e896db41`.
The local comparison recomputes aggregation and intervals from saved moments.
Full checkpoint re-forward and coordinate scoring are still pending in the
locked controller. Hash equality alone is not a tensor or geometry replay.

No training, evaluation rule, budget, source or checkpoint-selection policy was
changed in response to these numbers. The primary result remains128 for both
seeds, evaluated against unadapted, matched control, oracle-pair and fixed wrong
AA assignment. Do not infer useful folding acceleration from this interim gain.
