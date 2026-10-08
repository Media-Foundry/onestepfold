# Mini LoRA paired distributed training infrastructure

2026-10-08, user explicitly requests faster training and authorizes HIP0–5.
This is an execution amendment to the locked Mini LoRA experiment, not a new
loss/model/data sweep. The existing immutable serial execution is preserved.

## Preserve the update

The locked update contains two candidates. Each of two DDP ranks computes one
candidate's unscaled structure loss. DDP averages the two gradients; global clip1
and one AdamW step follow. No LR scaling, larger global batch, extra exposure or
mixed precision. Only655360 LoRA parameters belong to DDP;the135.22M frozen native
model remains an external runtime. Same candidate order,noise,objective,8208total
updates and32exposures/candidate/site. Torchrun launches processes, NCCL/RCCL
synchronizes gradients. Native runner is initialized as single-device before the
explicit process group, preventing its own distributed initialization from
interfering. Each process selects one device using HIP_VISIBLE_DEVICES only.

This follows PyTorch's [DDP gradient-averaging contract](https://docs.pytorch.org/docs/stable/generated/torch.nn.parallel.DistributedDataParallel.html).
Weight/update arithmetic equivalence is separately measured, not inferred merely
from using DDP. Normal floating-point reduction differences remain possible.

## Resource layout

Seed272001 uses HIP0,2;seed272003 uses HIP1,3. HIP4,5 evaluate disjoint candidate
shards from immutable checkpoints. Four training devices are the useful maximum
for two simultaneous two-candidate updates without changing the scientific batch.
The evaluation cards are idle between available evaluation jobs;this is not six
cards continuously performing training or a claimed6× speedup.

A process-scoped opt-in authorizes exactly the latest user-requested HIP0–5 and
checks ordinal→PCI mapping. Legacy default policy remains unchanged. In this host's
enumeration HIP4/5 correspond to management6/7;the latest explicit HIP authorization
is recorded as the resource basis. HIP6/7 are not selected. No CUDA/ROCR selector.

## Native benchmark

On spare HIP2/3, checkpoint0, four successive paired updates compared serial versus
DDP gradients and AdamW-updated parameters. Maximum parameter difference0;
maximum gradient difference1.821688e-44;fixed gate rtol1e-5/atol1e-7 passed.
Two serial and two parallel runs each54updates,covering all27training sites twice:

| Mode | Trial seconds | Total updates |
|---|---|---:|
| Serial |56.1314,49.5882|108|
| Paired DDP |33.5885,24.8036|108|

Combined throughput ratio1.8105×;averages0.979s versus0.541s/update. This is a small
native-training benchmark with other original workers still active,not an isolated
whole-experiment or inference speed claim. Model load excluded. All benchmark
updates discarded. Rank0 benchmark peak20.69GB includes serial comparison bank;
not a normal training peak. HIP4/5 each reproduce T37A/two-noise zero-checkpoint
coordinates bitwise before serving as evaluation devices.

## Fixed checkpoint handoff

Each original worker completes checkpoint4104 and its evaluation/exposure manifests.
The controller verifies hashes, stops that exact process group, preserves its full
files, and resumes from4104 with LoRA and AdamW state. Any few updates executed
between checkpoint and interception are recorded as discarded;not silently counted
as extra scientific exposure. The old controller is stopped by exact command/PID,
not broad process matching. The other old worker continues until its own4104.
The new controller records handoff provenance and watches both continuations.

New atomic latest checkpoints every128steps preserve optimizer state and support
manual explicit continuation. History is trimmed only in the NEW continuation to
the resumed checkpoint;original history remains untouched. After completion,
replica hashes must agree and the merged history must have precisely steps1..8208
and32exposures for each of513variants. The final report distinguishes original
serial segment,DDP segment,per-rank native counts,and separate evaluation counts.
No intermediate-quality-driven handoff or winner selection.

## Evaluation

Two eval workers each produce456candidates with both fixed noises. Merge requires
912unique labels and checkpoint/hash agreement. Original checkpoint0/4104
coordinates and manifests are linked into a compatibility audit layout;new8208
coordinates,history and checkpoint are independently scored with the original
coordinate auditor. Original C4/reference/disabled baselines remain unchanged.
The two seeds are evaluated in completion order. CPU scoring can overlap GPU work;
final numeric replay/timing is serial after training/evaluation complete.

No oracle target final conditioning,new teachers,input preparation or scientific
promotion is introduced by this infrastructure. Existing development status and
quality gates remain in force. Numerical training trajectory after handoff is
identified as distributed rather than retroactively calling it an uninterrupted
serial run.
