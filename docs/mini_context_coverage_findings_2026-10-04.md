# Context-replication audit: most expanded TRAIN label energy can be memorized by AA identity

**Read-only audit complete; no new teacher generation or training started.**
This follows the user's review of `f858c875`. It does not reopen the completed
score-head experiment, repair its seeds, or revise any old acceptance result.

The strongest new result is quantitative: six source-AA types occur in only one
expanded training context, and those six contexts carry **99.7143% of the old-noise
label squared energy**. A source/target-AA lookup table has minimum normalized
training MSE **0.0009768478**; the best trained AA-only head obtained **0.0009952100**.
Thus a very small global training loss was available without using any protein
context. This characterizes the data/task and does not establish which internal
algorithm a neural head actually learned.

## Exact categorical lower bound

Use precisely the previous TRAIN labels: for each site, average Exact native
mutant-minus-WT task change over old noises 230201/230211. No held or new-noise
labels enter this calculation. Let y(i,a) be that value and w(i) the source AA.
For a predictor depending only on (w,a), the least-squares optimum is

    table(w,a) = mean of y(i,a) over TRAIN sites with w(i)=w

The reported floor is sum[(table-y)^2]/sum[y^2], matching the previous arm's
global RMS normalization and equal site/candidate weighting. It is an empirical
TRAIN lower bound for unrestricted AA-pair tables, not a new trained model or
a bound on test performance. Singleton source groups can be fit exactly.

| TRAIN arm | Contexts / source types | Context counts by source AA | Singleton contexts | Singleton share of label energy | Exact table floor | Actual AA-only MSE, two seeds |
|---|---:|---|---:|---:|---:|---:|
| Restricted | 10 / 4 | A:5, T:3, N:1, Y:1 | 2 | 5.2611% | 0.69286982 | 0.81224436 / 0.82600768 |
| Expanded | 10 / 8 | A:2, T:2; D/I/L/N/V/Y:1 each | 6 | **99.7143%** | **0.00097685** | 0.00102666 / **0.00099521** |

Expanded 2ED6 V137 alone contributes **89.46%** of label energy; 4HUT I25
contributes another 6.66%. Restricted energy is also concentrated: 2ED6 T90
61.71%, 4HUT A44 32.07%. These are properties of the existing scalar proxy
and global squared-error weighting. They are not reasons to discard those sites
or revise completed training labels.

The expanded table is nearly sufficient for the TRAIN objective. In the
restricted arm, repeated source types have incompatible context-specific
labels, so its table floor is high; the actual AA-only models remain above that
floor. The new audit therefore does not say optimization is solved in every
case, or that data coverage is the only obstacle.

Group means and an independently computed one-hot least-squares projection agree
to numerical precision. The orthogonal energy decomposition is checked; its
largest absolute residual is 1.40e-14. Per-site labels, fitted table outputs,
energies and hashes are in [analysis.json](../reports/mini_context_coverage_2026-10-04/analysis.json).
No floor fitting uses current held proteins.

## What the existing response archive can actually support

The 24-protein/48-site archive retains the common held panel intact: 16 whole
proteins, plus N25 and S34 on two training proteins. Older 50-site rank/stress
cases also retain their regression role; they are not silently reassigned to
student training.

| Source AA | Available archived TRAIN environments after exclusions |
|---|---:|
| A | 5 sites / 5 components |
| T | 3 sites / 3 components |
| D, I, L, N, V, Y | 1 site / component each |
| Other standard types | 0 |

The only repeated types are A and T. Their unchanged held cross-protein support
is just one A site on 2EBE and one T site on 6ZRW. A small 1/2/3-context exercise
could be constructed, but would not provide the broad multi-environment learning
curve requested here. We do not launch it or recruit held proteins into TRAIN
to manufacture a larger curve.

This is a limitation of the **already generated hard-endpoint archive**, not a
claim that the underlying structure collection is too small.

## Concrete next-cohort preparation

Using the existing historical folding TRAIN asset pool, without downloading any
new structures, a sequence/reference-only preflight found **165 candidate
parents in 162 operational isolation components**. All 165 have finite observed
Cα coordinates and at least one observed site for each of A/D/L/T. This checks
the reference mapping; it is not native mutant-chemistry preflight or a quality
test of future predictions.

The existing all-v-all HSP/accession graph was independently reconstructed by
DFS: 204 records, 199 components, eight qualifying directed HSPs plus accession
links. Its complete component mapping matches the archived union-find result.
All 34 prior response-parent components are excluded. This reuses the original
near/domain HSP policy, not a new permissive identity threshold. Twelve earlier
proposal/Chord PDB IDs are also excluded under the existing source rule.

Deterministic hash ordering selects a **prospective**, not yet executed, cohort:

- 32 training parents, nested tiers of 8 / 16 / 32 parents.
- 8 distinct component-isolated confirmation candidates, no response labels yet.
- Every parent supplies one observed A, D, L and T site: 32 / 64 / 128 training
  contexts, with 32 confirmation-candidate contexts.
- Chain lengths 80–192, using the existing three length strata. All four source
  types occur on every parent, so source type alone cannot identify the protein.
- The old 16-protein evaluation panel remains excluded and remains development
  data. The new eight are new to response-method evaluation, not claimed absent
  from folding development, Mini/ESM pretraining or remote homology.

There are no shared graph components across the new train/confirmation split
or with prior response parents. Every selected site matches its sequence AA.
Selection reads sequences, existing provenance/isolation and observed reference
masks only, never a new teacher score, response norm, spectrum or model output.

[Candidate manifest](../reports/mini_context_coverage_2026-10-04/candidate_selection.json),
[all 160 candidate sites](../reports/mini_context_coverage_2026-10-04/candidate_sites.csv),
[isolation audit](../reports/mini_context_coverage_2026-10-04/isolation_audit.json).

The full proposed cohort would require **3080 distinct hard sequences**, or
**3120 C4 calls** including one extra WT replay per parent. Four-noise Exact-only
decoding would require **12320 S1 calls**; retaining additional decoder ablations
would increase that budget. These are accounting estimates, not work performed.

## Scope and decision

The new finding strengthens the user's data-design concern: expanded AA-only
TRAIN fit can be explained by the availability of source-specific labels with
highly concentrated squared energy. It does not prove that collecting more
contexts will restore transfer, or remove limitations of the reference features,
shared encoder, optimization or teacher objective.

The next proposal is recorded in [the learning-curve design](mini_context_replication_design_v1.md).
It separates fixed-update and fixed-exposure comparisons, holds the score models
constant and keeps all seeds. The candidate manifest is ready, but a candidate
inventory is not a completed training protocol or a new positive model result.
No GPU experiment, new C4/S1 call, parameter update, GELU intervention, Δs head,
rank change or blockwise fallback was launched during this audit.

Four focused tests cover the categorical floor, zero-energy handling, exclusion
of held contexts, and deterministic nested component-isolated selection. Old
reports and model checkpoints remain unchanged.
