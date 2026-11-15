"""Export a fixed-seed Monte Carlo snapshot for report evidence."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.loader import get_inflation_history, load_all_instruments
from src.engines.deterministic import (
    inflated_target,
    project_deterministic,
    required_monthly_contribution,
)
from src.engines.monte_carlo import run_monte_carlo
from src.models.instruments import GoalInputs

OUT_DIR = ROOT / "results"


def main() -> None:
    instruments = load_all_instruments()
    hist = get_inflation_history()
    # Align with mid-semester report cash-flow case; live engine uses effective monthly rates
    goal = GoalInputs(
        goal_amount=400_000.0,
        horizon_months=48,
        current_savings=50_000.0,
        monthly_contribution=6_500.0,
        annual_inflation=0.02,
        contribution_volatility=0.15,
        expense_shock_prob=0.05,
        expense_shock_mean=5_000.0,
        expense_shock_std=2_000.0,
        n_paths=5_000,
        seed=42,
    )
    focus = next(
        (i for i in instruments if i.category == "time_deposit"),
        instruments[0],
    )
    det = project_deterministic(focus, goal)
    mc = run_monte_carlo(focus, goal, inflation_history=hist)

    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "configuration": {
            "instrument_id": focus.instrument_id,
            "instrument_name": focus.name,
            "goal_amount": goal.goal_amount,
            "horizon_months": goal.horizon_months,
            "current_savings": goal.current_savings,
            "monthly_contribution": goal.monthly_contribution,
            "annual_inflation": goal.annual_inflation,
            "n_paths": goal.n_paths,
            "seed": goal.seed,
            "contribution_volatility": goal.contribution_volatility,
            "expense_shock_prob": goal.expense_shock_prob,
        },
        "deterministic": {
            "projected_nominal": round(det.projected_nominal, 2),
            "projected_real": round(det.projected_real, 2),
            "required_monthly": round(det.required_monthly, 2),
            "required_monthly_real_goal": round(
                required_monthly_contribution(
                    inflated_target(
                        goal.goal_amount, goal.annual_inflation, goal.horizon_months
                    ),
                    goal.current_savings,
                    focus.effective_monthly_rate(goal.annual_inflation),
                    goal.horizon_months,
                ),
                2,
            ),
            "inflated_goal": round(
                inflated_target(goal.goal_amount, goal.annual_inflation, goal.horizon_months),
                2,
            ),
            "annual_rate_used": det.annual_rate,
            "compounding": "effective_monthly_(1+r)**(1/12)-1",
        },
        "monte_carlo": {
            "n_paths": mc.n_paths,
            "seed": mc.seed,
            "probability_success": mc.probability_success,
            "probability_success_real": mc.probability_success_real,
            "std_error_of_proportion": mc.std_error_of_proportion,
            "std_error_of_proportion_real": mc.std_error_of_proportion_real,
            "std_error_of_mean": mc.std_error_of_mean,
            "expected_final_balance": round(mc.expected_final_balance, 2),
            "median_final_balance": round(mc.median_final_balance, 2),
            "expected_shortfall": round(mc.expected_shortfall, 2),
            "expected_shortfall_real": round(mc.expected_shortfall_real, 2),
            "inflated_goal": round(mc.inflated_goal, 2),
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / "fixed_seed_monte_carlo.json"
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
