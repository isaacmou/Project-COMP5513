"""Instrument comparison and what-if sensitivity helpers."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import List, Optional, Sequence

import pandas as pd

from src.engines.deterministic import project_deterministic
from src.engines.monte_carlo import run_monte_carlo
from src.models.instruments import GoalInputs, Instrument


@dataclass
class ComparisonRow:
    instrument_id: str
    name: str
    category: str
    annual_rate: float
    protection: str
    projected_nominal: float
    projected_real: float
    required_monthly: float
    time_to_goal_months: Optional[int]
    probability_success: float
    expected_shortfall: float
    expected_final_balance: float
    median_final_balance: float
    source: str
    as_of_date: str
    eligible_notes: str


def compare_instruments(
    instruments: Sequence[Instrument],
    goal: GoalInputs,
    inflation_history: Optional[Sequence[float]] = None,
    run_mc: bool = True,
) -> List[ComparisonRow]:
    rows: List[ComparisonRow] = []
    for inst in instruments:
        det = project_deterministic(inst, goal)
        if run_mc:
            mc = run_monte_carlo(inst, goal, inflation_history=inflation_history)
            p_success = mc.probability_success
            shortfall = mc.expected_shortfall
            expected_final = mc.expected_final_balance
            median_final = mc.median_final_balance
        else:
            p_success = 1.0 if det.meets_goal else 0.0
            shortfall = det.shortfall_nominal
            expected_final = det.projected_nominal
            median_final = det.projected_nominal

        rows.append(
            ComparisonRow(
                instrument_id=inst.instrument_id,
                name=inst.name,
                category=inst.category,
                annual_rate=det.annual_rate,
                protection=inst.protection_label,
                projected_nominal=det.projected_nominal,
                projected_real=det.projected_real,
                required_monthly=det.required_monthly,
                time_to_goal_months=det.time_to_goal_months,
                probability_success=p_success,
                expected_shortfall=shortfall,
                expected_final_balance=expected_final,
                median_final_balance=median_final,
                source=inst.source,
                as_of_date=inst.as_of_date,
                eligible_notes=inst.eligible_notes,
            )
        )

    rows.sort(key=lambda r: (-r.probability_success, -r.expected_final_balance))
    return rows


def comparison_to_dataframe(rows: Sequence[ComparisonRow]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Instrument": r.name,
                "Category": r.category,
                "Annual rate": f"{r.annual_rate:.2%}",
                "P(success)": f"{r.probability_success:.1%}",
                "Expected balance (HK$)": round(r.expected_final_balance, 0),
                "Median balance (HK$)": round(r.median_final_balance, 0),
                "Expected shortfall (HK$)": round(r.expected_shortfall, 0),
                "Deterministic projection (HK$)": round(r.projected_nominal, 0),
                "Real projection (HK$)": round(r.projected_real, 0),
                "Required monthly (HK$)": round(r.required_monthly, 0),
                "Time to goal (months)": r.time_to_goal_months if r.time_to_goal_months is not None else "—",
                "Protection": r.protection,
                "Source": r.source,
                "As of": r.as_of_date,
                "Notes": r.eligible_notes,
            }
            for r in rows
        ]
    )


@dataclass
class WhatIfResult:
    label: str
    description: str
    probability_success: float
    expected_shortfall: float
    expected_final_balance: float
    delta_p_success: float


def what_if_adjustments(
    instrument: Instrument,
    goal: GoalInputs,
    inflation_history: Optional[Sequence[float]] = None,
) -> List[WhatIfResult]:
    """Compare baseline odds vs save-more / extend-deadline adjustments."""
    base_mc = run_monte_carlo(instrument, goal, inflation_history=inflation_history)
    base_p = base_mc.probability_success

    scenarios = [
        (
            "Save 20% more",
            "Increase monthly contribution by 20%",
            replace(goal, monthly_contribution=goal.monthly_contribution * 1.2),
        ),
        (
            "Extend deadline +12 months",
            "Keep the same contribution but give yourself one more year",
            replace(goal, horizon_months=goal.horizon_months + 12),
        ),
        (
            "Save 50% more",
            "Aggressive increase in monthly saving",
            replace(goal, monthly_contribution=goal.monthly_contribution * 1.5),
        ),
    ]

    results: List[WhatIfResult] = [
        WhatIfResult(
            label="Baseline",
            description="Current plan",
            probability_success=base_p,
            expected_shortfall=base_mc.expected_shortfall,
            expected_final_balance=base_mc.expected_final_balance,
            delta_p_success=0.0,
        )
    ]

    for label, desc, g in scenarios:
        mc = run_monte_carlo(instrument, g, inflation_history=inflation_history)
        results.append(
            WhatIfResult(
                label=label,
                description=desc,
                probability_success=mc.probability_success,
                expected_shortfall=mc.expected_shortfall,
                expected_final_balance=mc.expected_final_balance,
                delta_p_success=mc.probability_success - base_p,
            )
        )

    # Rank non-baseline by improvement
    ranked = sorted(results[1:], key=lambda x: -x.delta_p_success)
    return [results[0]] + ranked
