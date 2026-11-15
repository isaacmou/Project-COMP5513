"""Reproduce mid-semester progress report Table 4 (nominal monthly r = annual/12).

The live engine compounds with effective monthly rates
``(1 + annual)**(1/12) - 1``. Report Table 4 was calculated independently with
``r = annual/12`` and monthly inflation ``π/12``. These tests lock those
published figures so the analytical benchmark stays auditable.
"""

from __future__ import annotations

import pytest

from src.engines.deterministic import (
    future_value,
    nominal_monthly_rate,
    nominal_real_value,
    required_monthly_contribution,
)


# Report Table 4 configuration
P = 50_000.0
C = 6_500.0
N = 48
ANNUAL_RETURN = 0.02
ANNUAL_INFLATION = 0.02
GOAL = 400_000.0


def test_known_answer_goal_case():
    r = nominal_monthly_rate(ANNUAL_RETURN)
    fv = future_value(P, C, r, N)
    assert fv == pytest.approx(378_698.98, abs=0.01)
    assert (GOAL - fv) == pytest.approx(21_301.02, abs=0.01)


def test_inflation_adjustment_nominal_convention():
    r = nominal_monthly_rate(ANNUAL_RETURN)
    fv = future_value(P, C, r, N)
    real_fv = nominal_real_value(fv, ANNUAL_INFLATION, N)
    assert real_fv == pytest.approx(349_606.50, abs=0.01)


def test_required_saving_nominal_goal():
    r = nominal_monthly_rate(ANNUAL_RETURN)
    req = required_monthly_contribution(GOAL, P, r, N)
    assert req == pytest.approx(6_926.63, abs=0.01)
    assert (req - C) == pytest.approx(426.63, abs=0.01)


def test_required_saving_real_goal():
    # Future target that preserves HK$400,000 purchasing power under π/12
    future_target = GOAL * ((1.0 + ANNUAL_INFLATION / 12.0) ** N)
    assert future_target == pytest.approx(433_285.97, abs=0.01)
    r = nominal_monthly_rate(ANNUAL_RETURN)
    req = required_monthly_contribution(future_target, P, r, N)
    assert req == pytest.approx(7_593.29, abs=0.01)


def test_return_sensitivity():
    expected = {
        0.00: 362_000.00,
        0.02: 378_698.98,
        0.04: 396_397.34,
    }
    for annual, fv_expected in expected.items():
        r = nominal_monthly_rate(annual)
        fv = future_value(P, C, r, N)
        assert fv == pytest.approx(fv_expected, abs=0.01)
