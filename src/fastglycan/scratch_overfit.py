"""Quality-aware summaries for a bounded scratch-core TRAIN-only diagnostic."""

import statistics

from fastglycan.capacity_c import summarize_rows as summarize_capacity


SMOOTH_WEIGHT = 10.0
MIN_LDDT = 0.90


def summarize_rows(rows):
    """Require both historical geometry and every protein/noise lDDT >= 0.90."""
    summary = summarize_capacity(rows)
    values = [r["quality"]["all_atom_lddt"] for r in rows]
    if not all(0 <= v <= 1 for v in values):
        raise ValueError("invalid all-atom lDDT")
    by_group = {}
    conditions = {}
    for row in rows:
        by_group.setdefault(row["group_id"], []).append(row["quality"]["all_atom_lddt"])
    for noise in (12345, 54321):
        scores = [r["quality"]["all_atom_lddt"] for r in rows if r["noise"] == noise]
        conditions[str(noise)] = {
            "mean": statistics.mean(scores),
            "median": statistics.median(scores),
            "minimum": min(scores),
            "below_0_7": sum(v < 0.7 for v in scores),
            "below_0_9": sum(v < MIN_LDDT for v in scores),
        }
    means = [statistics.mean(v) for v in by_group.values()]
    historical = summary["joint_capacity_pass"]
    summary.update(
        historical_geometry_pass=historical,
        quality_conditions=conditions,
        paired_protein_quality={
            "mean": statistics.mean(means),
            "median": statistics.median(means),
            "minimum": min(means),
            "below_0_7": sum(v < 0.7 for v in means),
        },
        minimum_protein_noise_lddt=min(values),
        selection_score=max(summary["selection_score"], MIN_LDDT / max(min(values), 1e-9)),
        joint_capacity_pass=historical and min(values) >= MIN_LDDT,
    )
    return summary
