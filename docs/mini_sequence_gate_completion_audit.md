# Four-stage gate completion audit — final

2026-09-28. The user confirmed four stages: native hard-input replay, sequence
input-gradient checks, matched S1/S2 optimization, and hard rebuilt sequences with
independent noise. All four are implemented and exercised. This does NOT mean the
model passed all scientific gates or that a smooth binder-design oracle exists.

## Requirement-level evidence

| Requirement | Authoritative evidence | Outcome |
|---|---|---|
| Hard-input forward equivalence |8run reports: native ESM, mixed reference/residue features, original-runner coordinate comparison | All8 native and final-hard replays pass declared tolerances |
| Sequence probabilities reach all modeled input paths | soft_esm.py, soft_sequence_chart.py, differentiable atom-pair preparation and4cycle path; real ESM/native parity and gradient tests | Implemented for a piecewise native-inventory chart; not a global smooth variable-atom graph |
| Gradient numerics | Each run records3directions×5h for both S1/S2, finite/nonzero gradients and repeated gradients; independent auditor recomputes acceptance | Initial100 and9QR4 pass both;8BZN fails S1;194-residue control fails both. Failures retained |
| Matched S1/S2 optimization |4targets×2arms×50updates; cross-loss at0/10/20/30/40/50; saved initial/final logits | All8 complete;7/8 own soft objectives decrease |
| Hard-sequence rebuilding | Native feature regeneration from final sequence plus original-runner replay | All8 complete and pass native replay |
| Independent-noise confirmation |64coordinate artifacts: baseline/final × S1/S2 × seeds103/107 ×8arms |3/8 arms improve their own-sampler hard proxy at both seeds; this is not overall acceptance |
| All-atom geometry | Independent native bond topology/conformer audit: bond RMS error, C–N error, chirality, sub-Angstrom nonbonded clashes | Large chemistry degradation accompanies some proxy gains; reported without hiding failures |
| Atom-inventory boundary behavior | Per-update same-q chart comparisons plus dedicated first-argmax-crossing limit probe | Probability separation falls100-fold while Cα jump stays≈0.184A; global smoothness rejected |
| Artifact integrity | final_audit_v2/acceptance.json;80source artifact hashes; coordinates recompute objective on CPU | All8 runs and80artifacts verified locally; scorer exit0 |
| Tests |12focused tests: native-body equivalence, ESM parity/checkpoint derivatives, chemical path and boundary, detached-gradient detection, geometry chirality, corrupted artifact/loss/acceptance rejection | Pass |
| Reports/plots | reports/mini_sequence_gates_2026-09-28/report.md, optimization_curves.png and full audit JSON | Generated and inspected |
| Compute lifecycle | Workers and boundary process terminal; finalizer stagecomplete/scorer_exit_code0 | No training launched; no remaining inference for this batch |

## Scientific verdict

The implementation goal is complete: the gates can distinguish correct local
plumbing from numerical failures, soft-objective progress from hard-sequence
regression, and contact-proxy gains from chemistry deterioration. The scientific
verdict is rejection of the current map as a reliable globally smooth design oracle.

The current loss is a monomer contact proxy, not an interface/affinity objective.
The input chart uses all20probabilities but rebuilds inventory at argmax changes;
its measured boundary jump is a real limitation. A globally smooth atom-inventory
representation, successful binder design, diffusion LoRA/distillation and recycle
compression have NOT been delivered or claimed by this gate implementation.

Next research decisions should address the soft-input representation and objective
before diffusion correction training. Numerical failures also need targeted
precision/conditioning diagnosis; a failed finite-difference plateau does not by
itself prove an autograd implementation bug. No test thresholds were relaxed to
turn failures into passes, and no frozen temporal test or training targets were used.
