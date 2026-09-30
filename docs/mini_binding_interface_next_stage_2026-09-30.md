# Next stage: user-specified binding interface

Status: DEFERRED by subsequent user correction: finish C4/S1 folding first.
See mini_folding_mainline_resume_v1.md. No target is required for the active stage.
The text below preserves the earlier interface proposal, not an active request.

Historical status: target-dependent protocol pending. On 2026-09-30 the user chose binding
interface design and will supply a target or complex. No biological target has
been selected by the agent. Required input: PDB ID or local structure path, target
chain(s), design chain if present, and any binding-site or immutable-residue
constraints. A target alone does not specify a binder sequence or scaffold.

This takes priority over further monomer-contact searches and larger training.
The already running HPC3 migration preflight finished; its two reconstruction
shards and new training have NOT been submitted. The source protocols remain
historical, hash-locked plans, not authorization to auto-release those jobs after
this scope decision. DiamondHill remains excluded from new computation after
its kernel-reported hardware memory-corruption incident.

## Verified implementation boundaries

GitNexus onestepfold queries/context and source inspection identified:

- `models/soft_sequence_chart.py:native_sequence_features` constructs one
  proteinChain. `SequenceChart` assumes a single sequence; its reference lookup
  uses residue number and atom name without chain identity. It cannot be used
  unchanged for a target/binder complex.
- `models/soft_esm.py:soft_esm2` accepts one sequence probability array, with one
  BOS/EOS pair. Multi-chain conditioning requires explicit per-chain ESM calls
  and native token mapping, not silent concatenation as one protein.
- `sequence_gate_metrics.py:contact_objective` is explicitly a monomer proxy.
  Its sequence-separation masks and adjacent Cα chain term are unsuitable across
  concatenated chains. Its geometry helper also contains residue-only lookups.
- `interface_decomposition.py` concerns a computational conditioning interface;
  it is not a binding-interface objective.

These findings are integration requirements, not evidence of an error in the
completed single-chain experiments. No production model or objective was changed
for the new task. A new multi-chain implementation should keep existing monomer
experiments replayable.

## Bounded first protocol, to finalize when the structure is provided

1. Resolve biological assembly, chain-instance identities, construct sequences,
   observed masks, disulfides, nonstandard residues and required cofactors.
   Record unsupported chemistry; do not silently remove necessary context.
   Distinguish fixed target sequence from any target-coordinate/template restraint.
2. Establish native hard complex inference and chain/atom mapping. Keep target
   and immutable residues fixed; only design-chain allowed positions receive
   probability variables. Reference chemistry and identity-bound noise must be
   keyed by chain instance, residue and atom name.
3. Verify hard endpoint replay, target-feature invariance and design-gradient
   routing. Keep C4 and use S1 with a matched S2 reference before claiming that
   the monomer-trained update transfers to interfaces. Preserve native pretrained
   weights as a comparison; choose no checkpoint by confirmation results.
4. Lock a task-specific inter-chain objective and hard evaluation budget before
   candidate evaluation. Separate desired interface contacts from steric overlap,
   chain integrity, intrachain geometry and target deformation. Confidence/PAE
   terms require auditing their actual computation and gradient path first.
5. Rebuild every real mutant natively and evaluate a bounded gradient-versus-random
   proposal comparison with separate proposal and confirmation noises. Report all
   candidates and compute costs. A plausible interface or confidence gain is not
   experimental binding or affinity evidence.

If there is no starting complex/binder, choose an initial scaffold and intended
pose as a separate explicit design decision before running mutations. Existing
monomer development cases and confirmation panels are not independent interface
validation. Retain layered evaluation and historical legacy checks; do not revive
an over-idealized connection window as the sole scientific veto.
