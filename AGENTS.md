# Repository guidance

Before changing the research scope or data contract, read `.agents/memory/project_context.md`
and `.agents/memory/decision_log.md`. Keep the first implementation restricted to fixed
chemical graphs and explicitly approved monosaccharide substitutions. Do not describe a
generated sample distribution as thermodynamic truth without a calibration experiment.

Use `src/fastglycan` for importable code, add focused tests under `tests/`, and record
material research decisions in `.agents/memory/decision_log.md`.

