# Calibration source extension v1

The TRAIN structure packet search completed with43 isolated sources (11 at
≤1.5 Å and32 at1.5–2 Å). No connection residuals have been measured. Preserve
this selection and roles; extend only the missing21 high-resolution sources.
Do not reinterpret43 as the originally requested64.

Search the frozen full256-shard catalog mirrored from HPC3 on DiamondHill.
Restrict release≤2021-09-30 (do not use the temporal test), X-ray≤1.5 Å,
model_count1, canonical50–1024-residue chains in author-defined monomers or
sequence-identical homomers without other polymer types. Preserve assembly
composition and source chain. This extends source coverage, not length,
resolution, sequence isolation or backbone completeness tolerances.

Exclude all original historical/reserved references and PDB/accessions, all
43 retained sources, and all379 packet-pool sequences. Among remaining sequence
groups choose one source by resolution, PDB, source chain and assembly ID, then
rank groups using the original calibration SHA salt. Limit discovery to the first
1024 groups. Search against the augmented reference database and all43 retained
sequences, plus all-vs-all new candidates, with the exact previous BLAST contract
and original effective database size. Preserve bidirectional pair evidence.

Materialize eligible sources directly from raw mmCIF using the existing GT
materializer; require exact repeated materialization, complete finite observed
N/CA/C/O, no modified residue or annotated chain break. Disulfides and missing
side-chain atoms remain allowed for this backbone-only task. Keep every source
preflight failure. Select in frozen order, enforcing identity/HSP exclusions,
until21 additions; no source-quality residual or repair-success selection.

Continue alternation in the high-resolution stratum after its existing11 rows.
The final64 must have32 per resolution stratum and32 per role. If still short,
report the shortage without threshold relaxation or residual fitting. Lock all
source coordinates, metadata and panel before running the measurement protocol.
This extension is a calibration source task, not fresh folding validation or a
claim that multimer chains are autonomous monomers.
