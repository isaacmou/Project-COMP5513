"""Monte Carlo validation: zero-vol converges to closed form; SE shrinks with paths."""

from __future__ import annotations

import numpy as np
import pytest

from src.engines.deterministic import future_value, inflated_target
from src.engines.monte_carlo import proportion_standard_error, run_monte_carlo
from src.models.instruments import GoalInputs, Instrument, ProtectionStatus


def _inst(rate: float = 0.03) -> Instrument:
    return Instrument(
        instrument_id="mc_test",
        name="MC Test",
        category="savings",
        annual_rate=rate,
        tenor_months=0,
        min_deposit_hkd=0,
        protection=ProtectionStatus.DPS_800K,
        eligible_notes="",
        source="test",
        as_of_date="2026-01-01",
    )


def _goal(n_paths: int = 5_000) -> GoalInputs:
    return GoalInputs(
        goal_amount=200_000,
        horizon_months=36,
        current_savings=40_000,
        monthly_contribution=4_000,
        annual_inflation=0.02,
        contribution_volatility=0.2,
        expense_shock_prob=0.05,
        expense_shock_mean=3_000,
        expense_shock_std=1_000,
        n_paths=n_paths,
        seed=123,
    )


def test_zero_volatility_matches_closed_form():
    inst = _inst(0.036)
    goal = _goal(n_paths=1)
    closed = future_value(
        goal.current_savings,
        goal.monthly_contribution,
        inst.monthly_rate,
        goal.horizon_months,
    )
    mc = run_monte_carlo(inst, goal, inflation_history=[0.02, 0.015, 0.025], zero_volatility=True)
    assert mc.expected_final_balance == pytest.approx(closed, rel=1e-9)
    assert mc.probability_success in (0.0, 1.0)


def test_standard_error_below_one_percent_of_mean():
    inst = _inst(0.03)
    goal = _goal(n_paths=10_000)
    mc = run_monte_carlo(inst, goal, inflation_history=[0.01, 0.02, 0.018, 0.022])
    assert mc.expected_final_balance > 0
    assert mc.std_error_of_mean < 0.01 * mc.expected_final_balance


def test_fan_chart_shape():
    goal = _goal(n_paths=2_000)
    mc = run_monte_carlo(_inst(), goal, inflation_history=[0.02])
    assert mc.fan_chart.shape == (3, goal.horizon_months + 1)
    # p10 <= p50 <= p90
    assert np.all(mc.fan_chart[0] <= mc.fan_chart[1] + 1e-6)
    assert np.all(mc.fan_chart[1] <= mc.fan_chart[2] + 1e-6)


def test_more_paths_tighter_se():
    inst = _inst()
    g_small = _goal(n_paths=500)
    g_large = _goal(n_paths=8_000)
    hist = [0.015, 0.02, 0.025]
    se_small = run_monte_carlo(inst, g_small, inflation_history=hist).std_error_of_mean
    se_large = run_monte_carlo(inst, g_large, inflation_history=hist).std_error_of_mean
    assert se_large < se_small


def test_proportion_standard_error_formula():
    assert proportion_standard_error(0.5, 10_000) == pytest.approx(0.005, rel=1e-12)
    assert proportion_standard_error(0.0, 1_000) == 0.0
    assert proportion_standard_error(1.0, 1_000) == 0.0


def test_real_success_uses_inflated_goal():
    inst = _inst(0.03)
    goal = _goal(n_paths=3_000)
    hist = [0.01, 0.02, 0.018, 0.022]
    mc = run_monte_carlo(inst, goal, inflation_history=hist)
    expected_inflated = inflated_target(goal.goal_amount, goal.annual_inflation, goal.horizon_months)
    assert mc.inflated_goal == pytest.approx(expected_inflated)
    assert mc.probability_success_real <= mc.probability_success + 1e-12
    assert mc.std_error_of_proportion == pytest.approx(
        proportion_standard_error(mc.probability_success, mc.n_paths)
    )
    assert mc.std_error_of_proportion_real == pytest.approx(
        proportion_standard_error(mc.probability_success_real, mc.n_paths)
    )
    assert mc.seed == goal.seed


def test_zero_inflation_real_matches_nominal_success():
    inst = _inst(0.03)
    goal = GoalInputs(
        goal_amount=200_000,
        horizon_months=36,
        current_savings=40_000,
        monthly_contribution=4_000,
        annual_inflation=0.0,
        contribution_volatility=0.1,
        expense_shock_prob=0.02,
        n_paths=2_000,
        seed=11,
    )
    mc = run_monte_carlo(inst, goal, inflation_history=[0.0])
    assert mc.inflated_goal == pytest.approx(goal.goal_amount)
    assert mc.probability_success_real == pytest.approx(mc.probability_success)
