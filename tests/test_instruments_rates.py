"""Effective rate, inflation floor, and tenor block behaviour."""

from __future__ import annotations

import numpy as np
import pytest

from src.engines.deterministic import future_value, project_deterministic
from src.engines.monte_carlo import _sample_rate_paths, run_monte_carlo
from src.models.instruments import GoalInputs, Instrument, ProtectionStatus


def _ibond(min_rate: float = 0.02, annual_rate: float = 0.025) -> Instrument:
    return Instrument(
        instrument_id="ibond_test",
        name="iBond Test",
        category="ibond",
        annual_rate=annual_rate,
        tenor_months=36,
        min_deposit_hkd=10_000,
        protection=ProtectionStatus.SOVEREIGN,
        eligible_notes="",
        source="test",
        as_of_date="2026-01-01",
        coupon_type="inflation_linked",
        min_rate=min_rate,
    )


def _td(tenor: int = 6, rate: float = 0.03) -> Instrument:
    return Instrument(
        instrument_id="td_test",
        name="TD Test",
        category="time_deposit",
        annual_rate=rate,
        tenor_months=tenor,
        min_deposit_hkd=10_000,
        protection=ProtectionStatus.DPS_800K,
        eligible_notes="",
        source="test",
        as_of_date="2026-01-01",
    )


def test_effective_rate_uses_inflation_floor():
    inst = _ibond(min_rate=0.02)
    assert inst.effective_annual_rate(0.015) == pytest.approx(0.02)
    assert inst.effective_annual_rate(0.03) == pytest.approx(0.03)


def test_savings_ignore_inflation_for_coupon():
    inst = Instrument(
        instrument_id="sav",
        name="Sav",
        category="savings",
        annual_rate=0.01,
        tenor_months=0,
        min_deposit_hkd=0,
        protection=ProtectionStatus.DPS_800K,
        eligible_notes="",
        source="test",
        as_of_date="2026-01-01",
    )
    assert inst.effective_annual_rate(0.05) == pytest.approx(0.01)


def test_deterministic_ibond_uses_floor():
    inst = _ibond(min_rate=0.04)
    goal = GoalInputs(
        goal_amount=200_000,
        horizon_months=24,
        current_savings=20_000,
        monthly_contribution=3_000,
        annual_inflation=0.015,
    )
    det = project_deterministic(inst, goal)
    assert det.annual_rate == pytest.approx(0.04)
    expected = future_value(
        goal.current_savings,
        goal.monthly_contribution,
        inst.effective_monthly_rate(0.015),
        goal.horizon_months,
    )
    assert det.projected_nominal == pytest.approx(expected)


def test_zero_vol_mc_matches_ibond_deterministic():
    inst = _ibond(min_rate=0.025)
    goal = GoalInputs(
        goal_amount=150_000,
        horizon_months=36,
        current_savings=30_000,
        monthly_contribution=2_500,
        annual_inflation=0.018,
        n_paths=1,
        seed=1,
    )
    det = project_deterministic(inst, goal)
    mc = run_monte_carlo(inst, goal, inflation_history=[0.01, 0.02], zero_volatility=True)
    assert mc.expected_final_balance == pytest.approx(det.projected_nominal, rel=1e-9)


def test_inflation_linked_rates_respect_floor():
    rng = np.random.default_rng(0)
    inst = _ibond(min_rate=0.03)
    rates = _sample_rate_paths(
        rng,
        inst,
        months=24,
        n_paths=200,
        inflation_history=[0.01, 0.015, 0.02, 0.05],
        assumed_inflation=0.02,
        zero_vol=False,
    )
    # Monthly rate from 3% annual ≈ 0.002466; all paths should be >= that floor
    floor_m = (1.0 + 0.03) ** (1.0 / 12.0) - 1.0
    assert np.all(rates >= floor_m - 1e-12)


def test_tenor_holds_rate_constant_within_block():
    rng = np.random.default_rng(42)
    tenor = 6
    inst = _td(tenor=tenor, rate=0.03)
    months = 18
    rates = _sample_rate_paths(
        rng,
        inst,
        months=months,
        n_paths=50,
        inflation_history=[0.01, 0.02, 0.03, 0.025],
        assumed_inflation=0.02,
        zero_vol=False,
    )
    # Within each tenor block, monthly rates are identical per path
    for start in range(0, months, tenor):
        end = min(start + tenor, months)
        block = rates[:, start:end]
        assert np.allclose(block, block[:, :1])
