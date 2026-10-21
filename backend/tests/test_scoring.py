import pytest

from app.scoring import compute_score


def test_zero_floor_and_max():
    assert compute_score(1, 0, 0)["score"] == 0.0
    assert compute_score(5, 4, 14)["score"] == 100.0


def test_caps_apply():
    assert compute_score(5, 99, 999)["score"] == 100.0


def test_known_value_and_breakdown_sums_to_score():
    r = compute_score(4, 2, 7)  # sev .75*50=37.5 ; sim .5*30=15 ; age .5*20=10
    assert r["score"] == 62.5
    assert r["level"] == "high"
    assert round(sum(c["points"] for c in r["components"]), 1) == r["score"]


def test_custom_weights_are_normalised():
    r = compute_score(5, 0, 0, weights={"severity": 2, "similar_reports": 1, "unresolved_age": 1})
    assert r["score"] == 50.0  # 0.5 weight on a maxed severity


def test_more_similar_reports_never_lowers_score():
    assert compute_score(3, 3, 5)["score"] > compute_score(3, 1, 5)["score"]


@pytest.mark.parametrize("args", [(0, 0, 0), (6, 0, 0), (3, -1, 0), (3, 0, -1)])
def test_invalid_inputs(args):
    with pytest.raises(ValueError):
        compute_score(*args)
