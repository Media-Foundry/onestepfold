import pytest
from fastglycan.pair_candidate_fit import candidate_pair, expected_exposures, validate_fit_site, FIT_NODES
from fastglycan.reference_editor_multiref import multiref_update


CHOICES = list('ACDEFGHIKLMNPQRSVWY')


def test_single_context_schedule_matches_original_site_visit_subsequence():
    site = dict(candidates=CHOICES)
    sites = {f's{i}': site for i in range(27)}
    run = dict(updates=8208, train_site_keys=list(sites))
    for visit in range(304):
        _, historical = multiref_update(run, sites, visit * 27)
        assert candidate_pair(CHOICES, visit) == historical
    for step, count in zip(FIT_NODES, (0, 32, 128, 432, 864)):
        assert expected_exposures(CHOICES, step) == dict.fromkeys(CHOICES, count)


def test_site_and_normalization_contract_rejects_leakage():
    site = dict(site_key='p3_s37', role_n15='train', parent_index=3,
                position_zero_based=36, original_aa='T', pdb_id='1W53', candidates=CHOICES)
    validate_fit_site(site, ['p3_s37'], 31.323820267027703)
    for patch in ({'role_n15': 'held'}, {'site_key': 'p3_s84'}, {'original_aa': 'A'},
                  {'candidates': CHOICES[:-1] + [CHOICES[0]]}):
        with pytest.raises(ValueError):
            validate_fit_site(dict(site, **patch), ['p3_s37'], 31.323820267027703)
    with pytest.raises(ValueError):
        validate_fit_site(site, ['p4_s2'], 31.323820267027703)
    with pytest.raises(ValueError):
        validate_fit_site(site, ['p3_s37'], 1.)


def test_no_silent_budget_extension_or_duplicate_candidate():
    for step in (-1, 8208):
        with pytest.raises(ValueError):
            candidate_pair(CHOICES, step)
    with pytest.raises(ValueError):
        candidate_pair(CHOICES[:-1] + [CHOICES[0]], 0)
