# Read-only alternative-source inventory

While the fixed coordinate-weight ablation trains, inspect whether unsuccessful
source representatives have alternative records under the **unchanged** catalog
admission rules. This is a metadata census, not a new validation set or experiment.

The existing scanner selects one metadata-complete source chain per assembly;
the preparation pipeline then selects one best-resolution record per exact
sequence before native chemistry preflight. Exhausting those representatives
does not prove all alternative experimental records for failed sequences fail.

Use only the frozen 256 catalog shards and unsuccessful representatives from
the completed 783-group expansion and 66-group catalog remainder. Preserve all
source, identity, length, method, date, resolution and assembly rules. Enumerate
alternative PDB/source-chain pairs admitted by the existing scanner; deduplicate
assembly aliases of the same pair. Count exclusions against known PDBs and
accessions, including the full current 455. Do not reuse current groups as new
validation, alter any manifest or read a new model score.

Eight CPU workers, one pass, no model/GPU computation. Record the selected-input
hashes, all catalog hashes, counts and candidate metadata. No fresh sequence
isolation or GT/native preflight is performed in this census, so candidates must
not be described as qualified or independent. Known positive but unselected
groups are counted separately; they may conflict with already selected sources.

Any later validation selection needs a separate locked protocol, complete sequence
isolation against all used proteins, experimental GT/native checks and selection
before prediction. This inventory does not change the running training or the
observed-validation32 comparison, and does not satisfy the larger training-size goal.
