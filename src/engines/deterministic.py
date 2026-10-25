"""Deterministic goal engine: closed-form accumulation and annuity formulas."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, log
from typing import Optional

import numpy as np

from src.models.instruments import GoalInputs, Instrument


def future_value(
    principal: float,
    monthly_contribution: float,
    monthly_rate: float,
    months: int,
) -> float:
    """Closed-form future value of principal plus ordinary annuity contributions.

    Contributions are assumed at month-end; interest compounds monthly.
    """
    if months < 0:
        raise ValueError("months must be non-negative")
    if months == 0:
        return float(principal)

    p = float(principal)
    c = float(monthly_contribution)
    r = float(monthly_rate)
    n = int(months)

    if abs(r) < 1e-15:
        return p + c * n

    growth = (1.0 + r) ** n
    return p * growth + c * (growth - 1.0) / r


def required_monthly_contribution(
    goal_amount: float,
    principal: float,
    monthly_rate: float,
    months: int,
) -> float:
    """Monthly contribution needed to reach goal_amount in `months`."""
    if months <= 0:
        return float("inf") if principal < goal_amount else 0.0

    r = float(monthly_rate)
    n = int(months)
    target = float(goal_amount)
    p = float(principal)

    if abs(r) < 1e-15:
        return max(0.0, (target - p) / n)

    growth = (1.0 + r) ** n
    fv_principal = p * growth
    if fv_principal >= target:
        return 0.0
    return (target - fv_principal) * r / (growth - 1.0)


def time_to_goal_months(
    goal_amount: float,
    principal: float,
    monthly_contribution: float,
    monthly_rate: float,
    max_months: int = 600,
) -> Optional[int]:
    """Smallest number of months to reach the goal, or None if unreachable in max_months."""
    goal = float(goal_amount)
    p = float(principal)
    c = float(monthly_contribution)
    r = float(monthly_rate)

    if p >= goal:
        return 0
    if c <= 0 and (r <= 0 or p <= 0):
        return None

    # Closed form when r > 0: solve p*(1+r)^n + c*((1+r)^n - 1)/r >= goal
    if r > 1e-15 and c > 0:
        # (1+r)^n >= (goal*r + c) / (p*r + c)
        numerator = goal * r + c
        denominator = p * r + c
        if denominator <= 0 or numerator / denominator <= 0:
            return None
        n = log(numerator / denominator) / log(1.0 + r)
        months = int(ceil(n - 1e-12))
        if months < 0:
            months = 0
        if months > max_months:
            return None
        return months

    if abs(r) < 1e-15:
        if c <= 0:
            return None
        months = int(ceil((goal - p) / c))
        return months if months <= max_months else None

    # Fallback iterative for edge cases
    balance = p
    for m in range(1, max_months + 1):
        balance = balance * (1.0 + r) + c
        if balance >= goal:
            return m
    return None


def real_value(nominal: float, annual_inflation: float, months: int) -> float:
    """Deflate nominal amount to today's purchasing power."""
    if months <= 0:
        return float(nominal)
    monthly_inf = (1.0 + annual_inflation) ** (1.0 / 12.0) - 1.0
    return float(nominal) / ((1.0 + monthly_inf) ** months)


@dataclass(frozen=True)
class DeterministicResult:
    instrument_id: str
    instrument_name: str
    annual_rate: float
    months: int
    projected_nominal: float
    projected_real: float
    required_monthly: float
    time_to_goal_months: Optional[int]
    shortfall_nominal: float
    meets_goal: bool
    protection_label: str
    source: str
    as_of_date: str


def project_deterministic(
    instrument: Instrument,
    goal: GoalInputs,
) -> DeterministicResult:
    months = goal.horizon_months
    eff_annual = instrument.effective_annual_rate(goal.annual_inflation)
    r_m = instrument.effective_monthly_rate(goal.annual_inflation)
    projected = future_value(
        goal.current_savings,
        goal.monthly_contribution,
        r_m,
        months,
    )
    projected_real = real_value(projected, goal.annual_inflation, months)
    req = required_monthly_contribution(
        goal.goal_amount,
        goal.current_savings,
        r_m,
        months,
    )
    ttm = time_to_goal_months(
        goal.goal_amount,
        goal.current_savings,
        goal.monthly_contribution,
        r_m,
    )
    shortfall = max(0.0, goal.goal_amount - projected)
    return DeterministicResult(
        instrument_id=instrument.instrument_id,
        instrument_name=instrument.name,
        annual_rate=eff_annual,
        months=months,
        projected_nominal=projected,
        projected_real=projected_real,
        required_monthly=req,
        time_to_goal_months=ttm,
        shortfall_nominal=shortfall,
        meets_goal=projected >= goal.goal_amount,
        protection_label=instrument.protection_label,
        source=instrument.source,
        as_of_date=instrument.as_of_date,
    )


def monthly_path_deterministic(
    principal: float,
    monthly_contribution: float,
    monthly_rate: float,
    months: int,
) -> np.ndarray:
    """Return month-end balances for charting (length months+1 including t0)."""
    balances = np.empty(months + 1, dtype=float)
    balances[0] = principal
    bal = float(principal)
    for t in range(1, months + 1):
        bal = bal * (1.0 + monthly_rate) + monthly_contribution
        balances[t] = bal
    return balances
