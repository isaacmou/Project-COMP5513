"""Tests for instrument comparison and data loading."""

from __future__ import annotations

from src.data.loader import get_inflation_history, load_all_instruments
from src.engines.comparison import compare_instruments, what_if_adjustments
from src.models.instruments import GoalInputs


def test_load_instruments():
    instruments = load_all_instruments()
    assert len(instruments) >= 5
    assert all(i.source and i.as_of_date for i in instruments)


def test_compare_ranks_by_success():
    instruments = load_all_instruments()[:4]
    goal = GoalInputs(
        goal_amount=300_000,
        horizon_months=48,
        current_savings=50_000,
        monthly_contribution=5_000,
        n_paths=1_500,
        seed=7,
    )
    hist = get_inflation_history()
    rows = compare_instruments(instruments, goal, inflation_history=hist)
    assert len(rows) == 4
    probs = [r.probability_success for r in rows]
    assert probs == sorted(probs, reverse=True)


def test_what_if_returns_baseline_and_scenarios():
    inst = load_all_instruments()[0]
    goal = GoalInputs(
        goal_amount=250_000,
        horizon_months=36,
        current_savings=30_000,
        monthly_contribution=4_500,
        n_paths=1_200,
        seed=9,
    )
    results = what_if_adjustments(inst, goal, inflation_history=get_inflation_history())
    assert results[0].label == "Baseline"
    assert len(results) == 4
