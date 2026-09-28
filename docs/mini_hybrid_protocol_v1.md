# Fixed-graph derivative and hard-mutation pilot — locked v1

2026-09-28, before new candidate results. Preserve pretrained Mini-ESM,C4,S1,K1;
S2 is a diagnostic reference. No diffusion training/recycle changes/FP64 forward
matrix. Prior four targets and noise103/107 are development information.

Three independent questions: segment-local derivative correctness; gradient versus
equal-budget random hard mutation usefulness; preventing known geometry regressions.

Geometry: native bond topology/reference conformers define intraresidue bond lengths
and handedness; peptide C–N ideal1.33A. Nonbonded pairs exclude graph distances1–3
(including1–4pairs). Radii C1.70,N1.55,O1.52,S1.80A as in AlphaFold's published
residue_constants. Clash penalty sums squared penetration beyond1.5A per atom.
Record raw pairs closer than1A, pairs/atom, maximum radius-overlap depth, bond RMSE,
peptide MAE, chirality. These rules differ from the old direct-bond-only clash count;
re-score old artifacts under the new rules, do not compare incompatible counts.
Source: https://github.com/google-deepmind/alphafold/blob/main/alphafold/common/residue_constants.py

Soft proposal objective: previous contact proxy +1×intrinsic bond MSE
+2×peptide MSE +1×clash penalty +.2×chirality penalty. A .01KL trust term to the
initial soft distribution is available during proposals; at the initial point its
derivative is zero. No long soft optimization trajectory in this pilot.

Hard acceptance requires task improvement>1e-4 plus ALL geometry conditions:
bond RMSE≤.25A; peptide MAE≤.15A; chirality≥.99; severe pairs/atom≤.02;
maximum penetration≤2.0A. Additionally no baseline regression beyond.01A bond or
peptide error,.002 severe-pair rate,.05A maximum penetration, or any chirality
fraction decrease. These are conservative experimental limits, not universal
chemical definitions. Invalid baseline structures do not exempt candidates from
absolute constraints. Zero accepted proposals is a valid result. Never trade a
severe geometry failure for better task loss.

Eight distinct single substitutions per arm from the same current hard sequence:
gradient ranks g_p[i,a]−g_p[i,current]; random samples uniformly without replacement
from the same19L substitutions, seed271. Each gets the same native feature/ESM
rebuild and S1 hard evaluations at noise seeds211 and223. Reuse an identical
candidate's prediction if arms overlap, but count its allocated slot in both arms.
Rank/accept using211;223 is confirmation, not selection. Report all candidates,
effective evaluation counts, wall time (including gradient cost), acceptance rate
and retained benefit. This is a bounded one-round hybrid proposal pilot; rebase on
an accepted candidate only in a separately logged subsequent round.

FD segmentation uses fixed chemical chart and identical random tensors:
X→loss; continuous(s_inputs,s,z)→diffusion→loss; q→fresh ESM/features/all4recycles
→diffusion→loss. Positive/negative q must retain argmax/inventory. StartFP32;
coordinate→loss may additionally useFP64 (the complete tested segment), with no
claim of whole-modelFP64. Other FP64 segments only if later justified. Check old
and new losses independently, retain all failures and low-signal uncertainty.

Regression panel: four previous targets; explicitly reject the saved8BZN-S1 and
control-S1 geometry-collapse outcomes under the hard policy. New confirmation
panel: deterministically select two old-development targets not in the four-target
pilot, without looking at new candidate outcomes; length100–220 for this bounded
budget. Exclude exact/near-duplicate sequences to the four development examples.
These are new-to-this-objective development confirmations, not untouched temporal
or homology-independent tests. Lock IDs/sequences before inference. Frozen temporal
test remains untouched. No gate threshold tuning after opening confirmations.
