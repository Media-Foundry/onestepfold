# Connection penalty onset intervention v1

2026-09-30. Bounded development experiment after the independent64 calibration
64ccaf4b. No new model inference, training, sequence design, independent32 reuse,
or change to chemical acceptance thresholds. Keep the eight historical sources
and two cached C1/S1 noises; retain3CR6 unsupported source slots.28 supported
solves,32 planned slots, comparing original vs calibrated connection onset.

Both arms start at exactly the original zero-parameter residue chart built from
the same raw Mini prediction. No fitted initialization. Keep raw position anchors,
reference chemistry, topology, raw-selected cis/trans targets, tail top16 term,
all regularization and fixed180-iteration three-stage L-BFGS budget unchanged.
CPU FP64, two single-thread workers,900s per-case external ceiling, final iterate.

For raw-selected trans connections, change each of the five continuous connection
penalty onset widths from the original half-tolerance to the pooled q95 in the
CALIBRATION half of independent64, separately for following-Pro/other. Load the
locked fitted_windows.json, not per-protein GT or held-out values. Retain the old
denominator/curvature: relu(abs(residual)/old_scale - new_onset/old_scale)^2.
This tests a dead zone change, not simultaneous weakening of the outside penalty.
Raw-selected cis connections keep all five original onsets; rare-cis calibration
is unsupported. Branch targets remain identical across arms, including known
errors. Do not interpret this experiment as repairing cis/trans classification.

The subclass replaces only the connection objective term. Validate original-onset
replay, shared buffers, local FP64 derivative, and unchanged nonconnection terms.
Hash inputs/code/calibration before running. Verify baseline output against the
previous zero-start run, independent pose replay and metric recomputation. Keep
all failed/timeout/missing and unsupported cases visible; no retry with changed
settings, best iterate selection or parameter sweep.

Report paired experimental AA/Cα-lDDT and raw-relative displacement, old connection
gate and maxima, original objective vs new objective, clash/penetration, strict
checked chirality, all old absolute geometry conditions and raw-selected branch
errors against GT (diagnostic only). The empirical onset is NOT a new gate. Keep
the old joint-pass result, even if many structures now fail that narrow window.
Do not erase a lost old pass by introducing a new pass label.

The development question is whether independently motivated onset widths retain
more experimental accuracy while avoiding additional severe collisions, checked
chirality failure or structural-budget failure. Only if paired mean AA and CA
both improve AND the count satisfying zero severe pairs, strict checked chirality
and structural budgets does not decline, consider a further bounded confirmation.
This screening rule is not deployment acceptance or proof of valid chemistry;
bond/peptide/max-penetration tradeoffs and old gate failures remain explicit.
Otherwise close this version without tuning the same panel. The fourteen inputs
are two noises of seven supported proteins, not fourteen independent proteins.
