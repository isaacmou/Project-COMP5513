"""Unit tests for closed-form deterministic goal engine."""

from __future__ import annotations

import math

import numpy as np
import pytest

from src.engines.deterministic import (
    future_value,
    project_deterministic,
    real_value,
    required_monthly_contribution,
    time_to_goal_months,
)
from src.models.instruments import GoalInputs, Instrument, ProtectionStatus


def _inst(rate: float = 0.06) -> Instrument:
    return Instrument(
        instrument_id="test",
        name="Test",
        category="savings",
        annual_rate=rate,
        tenor_months=0,
        min_deposit_hkd=0,
        protection=ProtectionStatus.DPS_800K,
        eligible_notes="",
        source="test",
        as_of_date="2026-01-01",
    )


def test_future_value_zero_rate():
    assert future_value(1000, 100, 0.0, 10) == pytest.approx(2000.0)


def test_future_value_matches_manual_loop():
    principal, c, r, n = 10_000.0, 2_000.0, 0.005, 24
    fv = future_value(principal, c, r, n)
    bal = principal
    for _ in range(n):
        bal = bal * (1 + r) + c
    assert fv == pytest.approx(bal, rel=1e-12)


def test_required_contribution_reaches_goal():
    goal, p, r, n = 100_000.0, 20_000.0, 0.004, 36
    c = required_monthly_contribution(goal, p, r, n)
    assert future_value(p, c, r, n) == pytest.approx(goal, rel=1e-9)


def test_required_contribution_zero_when_principal_enough():
    c = required_monthly_contribution(50_000, 60_000, 0.003, 12)
    assert c == pytest.approx(0.0)


def test_time_to_goal_closed_form():
    months = time_to_goal_months(50_000, 10_000, 1_500, 0.004)
    assert months is not None
    assert future_value(10_000, 1_500, 0.004, months) >= 50_000
    if months > 0:
        assert future_value(10_000, 1_500, 0.004, months - 1) < 50_000


def test_time_to_goal_already_there():
    assert time_to_goal_months(10_000, 10_000, 0, 0.01) == 0


def test_real_value_deflation():
    # 2% annual over 12 months ≈ divide by 1.02
    assert real_value(102_000, 0.02, 12) == pytest.approx(100_000, rel=1e-9)


def test_project_deterministic_fields():
    goal = GoalInputs(
        goal_amount=400_000,
        horizon_months=48,
        current_savings=50_000,
        monthly_contribution=6_000,
        annual_inflation=0.02,
    )
    result = project_deterministic(_inst(0.03), goal)
    assert result.projected_nominal > result.projected_real
    assert result.required_monthly >= 0
    assert result.months == 48
