# Geometry repair outcomes

Development/regression batch only; unchanged thresholds; not a design validation.

Processed 99/99; finite successful repairs 99; pending 0.
Zero severe collisions: 99; absolute geometry pass: 49; preserved: 99; joint: 49.
Structures with newly inverted archived CA centres: 68.

Failures: {"chirality_fraction": 50}
CA transitions: {"corrected": 38, "new_flip": 134, "persistent": 30}

All counts concern repeated mutations/noises of one parent, not independent proteins.
Finite output does not establish minimizer convergence; force RMS is vector magnitude per atom.
CA signed-volume checks do not cover every stereocentre.

| Arm | Candidates | Utility both noises | Full both | Full + preservation both |
|---|---:|---:|---:|---:|
| gradient | 16 | 0 | 0 | 0 |
| random | 16 | 0 | 0 | 0 |
