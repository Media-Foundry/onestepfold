import runpy


def test_oracle_routes_larger_joint_degradation_deeper():
    module = runpy.run_path("scripts/analyze_stage0e_router.py")
    records = [
        {
            "metrics": {
                "c2_s2": {"tm_score_ca": 0.70, "all_atom_lddt": 0.70},
                "c4_s5": {"tm_score_ca": 0.80, "all_atom_lddt": 0.80},
            },
            "labels": {
                "delta_c2s2_vs_c4s5_tm": -0.10,
                "delta_c2s2_vs_c4s5_all_atom_lddt": -0.10,
            },
        },
        {
            "metrics": {
                "c2_s2": {"tm_score_ca": 0.79, "all_atom_lddt": 0.79},
                "c4_s5": {"tm_score_ca": 0.80, "all_atom_lddt": 0.80},
            },
            "labels": {
                "delta_c2s2_vs_c4s5_tm": -0.01,
                "delta_c2s2_vs_c4s5_all_atom_lddt": -0.01,
            },
        },
    ]
    curve = module["oracle_curve"](records)
    all_deep = next(point for point in curve if point["route_deep_fraction"] == 1.0)
    one_deep = next(point for point in curve if point["route_deep_fraction"] == 0.5)
    assert all_deep["catastrophic_joint_risk"] == 0.0
    assert one_deep["catastrophic_joint_risk"] == 0.0
