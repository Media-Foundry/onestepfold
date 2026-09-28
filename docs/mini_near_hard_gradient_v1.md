# Near-hard full ERC gradient gate

Locked before outcomes. Eight arms:8BZN/control × alpha1e-4/1e-3 × S1/S2.
Frozen MiniESM/C4/K1, FP32, native fixed chemical graph, identity-keyed noise211,
no dropout/augmentation. No source-combination expansion, model/loss change,
smoothing, training, hard mutation search or temporal-test use.

Exact onehot is replay/geometry baseline only, not a random central-difference
point. Define intended p by the established alpha interpolation in FP64, then
q=log(p) cast to FP32. The actual model receives softmax(q),temperature1; record
rounding error and actual non-native mass. Main derivatives are with respect to
logits q, never labelled probability derivatives. Every perturbation must preserve
the native argmax and regenerate ESM, all probability-dependent inputs, full4cycle
conditioning and diffusion caches. No cached ESM or conditioning in this gate.
Pack s_inputs/s/z identically for baseline/gradient/FD paths, retaining autograd.

Original directions:torch CUDA seed731,three Gaussian Lx20 directions, subtract
per-residue mean then normalize global L2 to1. Original logits h=.3,.1,.03,.01,.003;
5%relative+1e-6 absolute; each direction needs two adjacent passing h; finite,
nonzero and exactly repeatable gradient. Keep original old contact proxy and new
geometry objective, including .01KL(p||p0) in the new sequence objective. p0 is
the actual softmax(q0) and detached. No change to chemistry rules.

Record AD, FD, numerator,L+/L−,actual probability delta,coordinate delta,geometry,
and linearized-coordinate response (plus direct KL directional derivative).
Save all +/- coordinates and probabilities, directions and gradients. Compare
same-sampler hard baseline and near-hard chemistry under existing absolute AND
nonregression limits, reporting failures separately from FD status.

Original pass/fail remains authoritative for that numerical gate. Additional
conservative signal annotation only: an informative row must also pass relative
error alone, have nonzero numerator/probability/coordinate response, and have
relative tolerance contribution larger than the absolute contribution, i.e.
max(|AD|,|FD|)>2e-5. Informative direction requires adjacent informative rows;
otherwise an original pass is labelled low-signal/absolute-tolerance-assisted.
This diagnostic crossover is not a universal signal-to-noise bound or relaxed
acceptance threshold. Retain all actual magnitudes, including resolved small ones.

Require/record same-layout grad/no_grad coordinate replay and repeated gradient.
Do not hide replay differences or certify the oracle if these differ. Measure
soft token embedding, ESM output, projected ESM and s_inputs changes relative to
hard on the already required baseline forwards; no layer/alpha expansion.

Use all8DiamondHillGCD for the independent arms, bounded30minutes per arm. Stop
at this diagnostic batch. Any source repair retains failed artifacts and is
recorded as an implementation correction, never a scientific threshold change.
