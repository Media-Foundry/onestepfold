# Data protocol

Reference ensembles are stored as one JSON object per line. The checked-in
example is synthetic and exists only to exercise the loader and audit command.
Real records must include:

- a stable glycan/scaffold identifier and the exact sequence notation;
- one representative per conformational cluster, with population `weight`;
- the simulation temperature, solvent, force field, protocol and replica count;
- an effective sample size estimate, not just the raw saved-frame count;
- a topology hash and common-atom mapping metadata for any paired edit.

Do not mix alpha/beta reducing-end variants or different simulation protocols in
one ensemble without an explicit condition identifier.

