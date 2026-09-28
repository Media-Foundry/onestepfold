# Conditional ESM token-input cut

2026-09-28, declared after complete ESM-output cut: control has mixed deviations
before/after the ESM-output interface. Reuse exactly this target, q, three
original directions, five h and saved ESM-output VJP mu_E. No folding evaluation.

Capture the actual input T to ESM layer0 (including BOS/EOS, embed_scale and
fixed token-dropout scaling) without changing forward. Verify H0 bitwise equal
to archived ESM output and reconstructed T(q0) bitwise equal to captured input.
Compute a_E=mu_E J_H v and nu=grad_T(mu_E dot H); require q VJP reconstructed
through T to agree within original chain tolerance. For archived deltaH:
k=nu dot(Tplus-Tminus)/2h, n_E=mu_E dot deltaH/2h.
Report n_E-a_E=(k-a_E)+(n_E-k), with exact tensors and CPU projection replay.
This isolates pre-Transformer arithmetic and Transformer/last-norm numerical or
linearization deviations for the actual downstream projection. The preceding
unweighted pW vector error is not treated as causal attribution of coordinate
error. Residual R/C contribution can be shown separately as (n-a)-(n_E-a_E),
explicitly retaining small differences in backward accumulation paths.

No whole-model FP64 or model training. A passing local chain is not certification
of the full model. Preserve all prior geometry and derivative failures.
