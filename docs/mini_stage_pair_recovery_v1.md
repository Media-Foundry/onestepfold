# Native-stage-aligned pair recovery: final versus intermediate supervision

Fixed2026-10-10 under the active model-improvement goal. Previous experiments
remain closed. This new experiment changes where the pretrained suffix starts,
and separately tests a corresponding intermediate label. It does not assume
capacity, data scarcity or the optimizer has been uniquely identified as cause.

Native Mini's pair updates do not read single inside a block. First run the
unadapted WT3->candidate1 path as before, retaining B_inputs/B_s/B_z AND the
candidate's pair after main block13 (zero-based; immediately before blocks14/15).
Student starts from this actual boundary, plus a zero-initialized row/column
edit injection, then runs trainable copies of native pair-only blocks14/15.
No new final LayerNorm/linear residual readout. At initialization this suffix
must reproduce B_z exactly. Final decoder always receives unchanged B_inputs
and B_s, predicted z and actual candidate chemistry. No target state is an input.

Node inputs remain candidate B_inputs/B_s, WT3 mutation row/column, position and
old/new AA. Same128wide node network; left/right start atzero instead of1e-3.
Two native pair blocks are fully trainable, c_s=0/dropout0. Fixed seeds272001/
272003 randomize only the new node branch; native weights and initial function
are identical. All four arms percohort are fresh, never resumed from old runs.
Both objectives at a given seed must have identical initial parameter hashes.

This is a package comparison to the previous appended recovery model, NOT an
isolated test of depth, zero initialization, or LayerNorm removal. The within-
architecture final/hint contrast isolates the declared training objective.
Teacher stage correspondence is explicit: student block14 output matches exact
target C4 block14; final output matches exact block15. Neither teacher state
enters prediction. No teacher forcing, hidden oracle single or held-label fit.

Two losses, same final site scale q from31e3af3c, no recomputation:
 final: mean((pred15-target15)^2)/q.
 hint: .5*[mean((pred15-target15)^2)+mean((pred14-target14)^2)]/q.
Thus hint retains a fixed total coefficient1 but redistributes it across the
two corresponding stages; it is not claimed to preserve identical gradients.
No loss/floor/rank/activation sweep. No structure/ranking/geometry loss orS1
backward. AdamW lr1e-4/wd1e-4/eps1e-8/clip1 and two-candidate accumulation.

Pre-register BOTH cohorts before outcomes: n1=historicalTRAIN1W53T37, n15=the
original15TRAINparents/27sites/513mutants. Four runs each: final/hint x two seeds.
Both receive8208updates. n1 saves/evaluates0/304/1216/4104/8208 (0/32/128/432/864
exposures/candidate), n15 at0/4104/8208 (0/16/32exposures). Same original sorted
site roundrobin/cyclicAA schedule. Terminal only is primary; no winner selection.
Run both cohorts regardless of n1 quality; stop only on integrity/runtime failures.
No extension of previous budgets. n1 compares to981076f4 same site/exposure;
n15 compares to31e3af3c same data/exposure. Different cohort exposures do not
provide an isolated data-size effect.

Reuse old912 B and finaltarget caches. Prepare warm block13/14 for all912
mutants by912 unadapted native last recycles. Reconstruct exact target C4 only
for513TRAIN candidates to obtain block14 training labels:2052 extra native
recycles from cached candidate inputs; all finaltarget s/z must bitwise match
archive. No ESM/MSA preparation/new protein/AA labels. The native MSA update
inside each recycle is retained. Preparation2964recycles is a measured cost,
not a free data read. Save only the needed intermediate pair states, with hashes.
Each candidate's initial student z must match B_z at both seeds, and two-noise
S1 must replay B (1824preparationS1 total, one seed suffices after both z checks).

Implementation gates precede scientific training: cloned weights independent;
initial suffix/function/zero-edit identity; first-step gradients reach native
pair blocks despite zero edit heads; candidate order isolation; source/label/
protocol hashes; no mutation of B/WT/native weights. Dropout0/train-eval numerical
path must preserve the initialization. Native calls forbidden during training.
Targets are read only through training loss; decoder eval reads labels normally.

n1 evaluation only its training site, n15 all48existing sites with train/same-
protein-new/held-protein strata separate. All are development data, not a fresh
confirmation set. At every node decode19AA x2old noises with no NMSE gate.
Terminal fixed next-AA donor residual mismatch retains actual receiver B,
chemistry and noise. No permutation/scaling/postprocessing search. Raw/common/
AA residual metrics, stage14 errors, direction and energy; final structure
response, Spearman, scoreMAE, old-select/new-Exactregret, tail, geometry absolute
and transitions/severity. B, Exact and fixed-single oracle controls unchanged.
No one-protein bootstrap for n1; n15 descriptive parent bootstrap unchanged.

New method still performs the full native candidate last recycle to obtain
fixed B_s and its boundary, then two additional pair blocks. This cost must be
counted; it does not claim the lasttwo native blocks have been safely skipped.
No folding-speed promotion without a separate matching benchmark. MSA/ESM
preparation excluded from this model-only cycle by user instruction.

HIP0..3 independent workers, only HIP_VISIBLE_DEVICES;HIP4 available for preflight,
HIP5 is occupied and untouched. Prepare four shards, then two sequential cohorts
with four workers each. Total65664updates/131328trainingcandidate forwards.
S1:1824 preparation +912 n1 +29184 n15 =31920. n15 eachrun decodes3x1824correct
plus1824terminalmismatch. Each cohort cap6hours; no scientific restart or budget
extension. Persist all failures/seeds/nodes. Native identity error is a blocked
implementation gate, never quietly relaxed into a quality threshold.

Interpretation: whether native stage alignment improves learnability versus
the historical appended model; whether explicit corresponding-stage labels add
benefit versus final-only; whether any training gain survives unseen proteins
and choice/geometry risk. None is implied by a prettier internal loss. Goal
remains reliable mutation-conditioned folding with measured reuse; current
oracle interface and historical negatives are retained.
