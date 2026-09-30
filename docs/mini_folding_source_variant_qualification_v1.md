# Alternate source qualification v1

Freeze before new HSP searches or native preflight. This is source preparation
only; the running TRAIN423 ablation and its 455-target evaluation remain unchanged.
No folding, ESM extraction, model selection or final validation panel is authorized
by this source protocol.

Use exactly the inventoried 234 alternative PDB/source-chain records for 113 exact
sequence groups. Existing catalog rules remain: canonical 50–1024-residue construct
sequence, X-ray ≤2.5 Å, release ≤2021-09-30, one model, author-supported monomer or
homooligomer without other polymer components, required SIFTS mapping. Preserve
experimental source context. No new crawl, crop or score-based filtering.

Group order: SHA256(`folding-alternate-source-v1:20260930:` + group ID).
Within each group: increasing resolution, PDB ID, source chain and assembly ID.
Complete sequence isolation against the union of the archived historical references
and all current 455 proteins, plus new/new pair searches. Retain all existing PDB
and accession exclusions. Use the same hash/version-checked BLAST programs,
effective database size, scoring/masking settings, full target cap and HSP rules:
aligned non-gap residues ≥50 and either E≤1e−5, or E≤0.001 with shorter coverage
≥0.70 and identity ≥0.30. Search warnings stop release; no-hit is not acceptance
when statistics fail. Independently reparse every HSP alignment string.

Only reference-isolated groups enter native qualification. Eight single-thread CPU
workers, hidden GPU, separate attempt directories. Reuse unchanged
`qualify_adapter_source`: double GT materialization, complete finite N/CA/C/O,
continuous unmodified backbone, no unsupported covalent/disulfide connection or
observed SG proximity, ≥90% observed native heavy atoms, exact identity mapping,
masked missing GT and native reference replay. Do not use Mini prediction quality.
Before new sources, requalify the current shortest and longest accepted sources
and require exact GT-array/metadata replay. This separates runtime failures from
unsupported new experimental sources; it adds no folding computation.

Try each group's variants in the locked order, stopping after the first passing
record. Record every visited failure and the chosen variant; at most 234 attempts.
Keep process output in group order, regardless of completion order. Then greedily
reserve all mutually isolated qualifying groups under the same PDB/accession/HSP
conflict rules. No fixed validation count is claimed; report the actual shortage
or surplus before any future panel protocol. Reservations have role
`reserved_source`, not TRAIN or evaluated validation.

Audit GT/mask/native atom correspondence and rehash input CIFs, code, searches and
saved packets. Save all outcomes, rejected conflicts, selected source rows and
packet manifest. This establishes source support under this implementation, not
absence from Mini/ESM pretraining. A later locked panel and model comparison are
still required for independent folding confirmation.
