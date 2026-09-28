# Geometry repair v1 — submitted

The new locked protocol is [mini_geometry_repair_v1.md](mini_geometry_repair_v1.md).
The prior mutation batch remains closed. Code/protocol backup: `70499f76`.

DiamondHill root: `/media/PM982/onestepfold/geometry_repair_v1_20260929`.
OpenMM 8.6.1 and PDBFixer 1.12.0 installed under its isolated `deps/`; original
fold environment unchanged. Downloads were transferred locally after the remote
package connection failed. Four CPU workers, two OpenMM threads each; no folding
or GPU work. Eight focused tests passed.

Lock binds the 99 existing input structures, source files, force-field XMLs and
software versions. First case is already running; detached controller PID39918
waits for that case and then starts the remaining batch without duplicating it.
Each case has a 1800-second ceiling. Completed cases and failures are retained,
not rerun. The controller automatically executes independent coordinate scoring
and produces `exit.json`, `report.json`, per-case reports/coordinates/full PDBs.
The original input root is read-only to these scripts.

At this status snapshot, scientific outcomes are pending. A process returning
finite coordinates is not evidence of geometry acceptance or minimizer convergence.
The recorded `force_rms` is RMS vector magnitude per atom (not RMS per Cartesian
component); `force_tolerance_met` is a conservative diagnostic against10, not an
OpenMM termination code. Energy is never used to rank different sequences.

Reports separate absolute geometry, preservation, and paired task/utility/full
acceptance against the repaired parent. Both confirmation noises are required.
The old thresholds and old failed results remain unchanged. These are already
seen development examples, not independent validation or a differentiable oracle.
