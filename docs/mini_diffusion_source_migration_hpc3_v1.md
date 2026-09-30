# Source preparation recovery on HPC3 after DiamondHill hardware failure

2026-09-30. The original192-worker run terminated with BrokenProcessPool after
kernel-reported hardware memory corruption sent SIGBUS to workers326630 and
326608. Its controller326565 exited1; no training was started. Preserve that
root, logs,192 worker thread records and partial outputs. Do not treat it as an
OOM or a source admission failure. Do not reuse its NEW prepared packets.

Migrate read-only metadata/code and the128 inherited packets (all bound to their
pre-existing hashes) to HPC3. Validate transfer hashes and the available PDB CIF
bytes against per-file SHA256 before rebuilding. Verify native standard-protein
input compatibility on two inherited sequences: identical identities/topology,
integer fields and masks; report floating-feature differences, reject >1e-6.
Torch versions differ (DiamondHill2.12 development ROCm, HPC3 2.7.1 CUDA);
RDKit2026.03.6 and Biotite1.4.0 match. This is a source-only compatibility check,
not folding precision or GPU parity. Keep GPU visibility empty.

After successful preflight, use acd_u, two CPU-only Slurm array tasks,96 workers
per task, each internal thread count1. Rebuild ALL783 ordered eligible candidates
on HPC3, deterministically sharded by order index modulo2. This computes some
extra unused preflights; it does not change candidate order or greedy acceptance.
No early source batch can select candidates based on completion order.

After both tasks complete, apply the SAME frozen global hash order, source rules
and mutual identity/HSP exclusions to choose the first384 qualified additions.
Restore128 inherited packets byte-for-byte. If fewer additions qualify, keep
selection incomplete and report the shortage. Do not reduce denominator or alter
isolation/chemistry rules. Before any feature extraction or training, independently
audit the source mapping and selection; old validation64 remain excluded.

Hardware failure is not evidence that all earlier DiamondHill results were wrong.
It is also not evidence that continuing new compute there is safe. This migration
establishes new source integrity on another host; it does not retroactively certify
every prior floating-point result. Original scientific protocol remains
mini_diffusion_training_expansion_v1.md, with this execution-only amendment.

Scheduler note, before any job ran: acd_u rejected gres=gpu:0 (minimum1 GPU).
CPU-only computation therefore reserves the minimum1 GPU per job; CUDA/ROCm
visibility remains empty. Report this allocation overhead, not GPU compute/NFEs.
The preflight uses4 CPUs; source array uses2×96 CPUs and therefore2 reserved GPUs.
