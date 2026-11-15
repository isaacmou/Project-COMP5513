"""Vectorised Monte Carlo goal simulator."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np

from src.engines.deterministic import future_value
from src.models.instruments import GoalInputs, Instrument


@dataclass(frozen=True)
class MonteCarloResult:
    instrument_id: str
    instrument_name: str
    n_paths: int
    probability_success: float
    probability_success_real: float
    expected_final_balance: float
    median_final_balance: float
    expected_shortfall: float
    expected_shortfall_real: float
    final_balances: np.ndarray
    fan_chart: np.ndarray  # shape (3, months+1) for p10, p50, p90
    std_error_of_mean: float
    std_error_of_proportion: float
    std_error_of_proportion_real: float
    inflated_goal: float
    seed: int
    zero_vol_mean: Optional[float] = None


def proportion_standard_error(p_hat: float, n: int) -> float:
    """Binomial SE of a success proportion: √[p̂(1−p̂)/N]."""
    if n <= 0:
        return 0.0
    p = min(1.0, max(0.0, float(p_hat)))
    return float(np.sqrt(p * (1.0 - p) / n))


def _sample_contributions(
    rng: np.random.Generator,
    base: float,
    volatility: float,
    n_paths: int,
    months: int,
    zero_vol: bool,
) -> np.ndarray:
    """Monthly contributions: lognormal-ish noise around base, clipped at 0."""
    if zero_vol or volatility <= 0 or base <= 0:
        return np.full((n_paths, months), base, dtype=float)
    # Multiplicative noise each month; mean ≈ base
    noise = rng.lognormal(mean=-0.5 * volatility**2, sigma=volatility, size=(n_paths, months))
    return np.maximum(0.0, base * noise)


def _sample_expense_shocks(
    rng: np.random.Generator,
    n_paths: int,
    months: int,
    prob: float,
    mean: float,
    std: float,
    zero_vol: bool,
) -> np.ndarray:
    if zero_vol or prob <= 0 or mean <= 0:
        return np.zeros((n_paths, months), dtype=float)
    occur = rng.random((n_paths, months)) < prob
    shocks = rng.normal(loc=mean, scale=max(std, 1.0), size=(n_paths, months))
    shocks = np.maximum(0.0, shocks)
    return occur * shocks


def _annual_to_monthly(annual: np.ndarray | float) -> np.ndarray | float:
    return (1.0 + annual) ** (1.0 / 12.0) - 1.0


def _expand_blocks_to_months(
    block_annual: np.ndarray,
    block_len: int,
    months: int,
) -> np.ndarray:
    """Repeat each column of annual rates for `block_len` months; trim to `months`."""
    monthly = np.repeat(block_annual, block_len, axis=1)[:, :months]
    return _annual_to_monthly(monthly)


def _sample_rate_paths(
    rng: np.random.Generator,
    instrument: Instrument,
    months: int,
    n_paths: int,
    inflation_history: Sequence[float],
    assumed_inflation: float,
    zero_vol: bool,
) -> np.ndarray:
    """Monthly effective rates with inflation-linked floors and tenor rollovers."""
    if months <= 0:
        return np.zeros((n_paths, 0), dtype=float)

    base_annual = instrument.effective_annual_rate(assumed_inflation)
    base_m = _annual_to_monthly(base_annual)

    if zero_vol:
        return np.full((n_paths, months), base_m, dtype=float)

    hist = np.asarray(inflation_history, dtype=float) if inflation_history else np.array([])
    tenor = int(instrument.tenor_months) if instrument.tenor_months and instrument.tenor_months > 0 else 0
    block_len = tenor if tenor > 0 else 12
    n_blocks = max(1, (months + block_len - 1) // block_len)

    if instrument.is_inflation_linked and instrument.min_rate is not None:
        floor = float(instrument.min_rate)
        if len(hist) == 0:
            annual_blocks = np.full((n_paths, n_blocks), max(floor, assumed_inflation), dtype=float)
        else:
            idx = rng.integers(0, len(hist), size=(n_paths, n_blocks))
            annual_blocks = np.maximum(floor, hist[idx])
        return _expand_blocks_to_months(annual_blocks, block_len, months)

    # Fixed / floating / deposits: base ± half inflation delta, with tenor or yearly blocks
    if len(hist) == 0:
        return np.full((n_paths, months), base_m, dtype=float)

    mean_inf = float(hist.mean())
    idx = rng.integers(0, len(hist), size=(n_paths, n_blocks))
    drawn = hist[idx]
    annual_blocks = instrument.annual_rate + 0.5 * (drawn - mean_inf)
    annual_blocks = np.clip(annual_blocks, 0.0, 0.15)
    return _expand_blocks_to_months(annual_blocks, block_len, months)


def run_monte_carlo(
    instrument: Instrument,
    goal: GoalInputs,
    inflation_history: Optional[Sequence[float]] = None,
    zero_volatility: bool = False,
    store_paths_for_fan: bool = True,
) -> MonteCarloResult:
    """Simulate n_paths household saving paths for one instrument."""
    rng = np.random.default_rng(goal.seed)
    n_paths = 1 if zero_volatility else goal.n_paths
    months = goal.horizon_months
    hist = list(inflation_history or [])

    contributions = _sample_contributions(
        rng,
        goal.monthly_contribution,
        goal.contribution_volatility,
        n_paths,
        months,
        zero_volatility,
    )
    shocks = _sample_expense_shocks(
        rng,
        n_paths,
        months,
        goal.expense_shock_prob,
        goal.expense_shock_mean,
        goal.expense_shock_std,
        zero_volatility,
    )
    rates = _sample_rate_paths(
        rng,
        instrument,
        months,
        n_paths,
        hist,
        goal.annual_inflation,
        zero_volatility,
    )

    balances = np.empty((n_paths, months + 1), dtype=float)
    balances[:, 0] = goal.current_savings
    for t in range(months):
        balances[:, t + 1] = (
            balances[:, t] * (1.0 + rates[:, t]) + contributions[:, t] - shocks[:, t]
        )
        balances[:, t + 1] = np.maximum(0.0, balances[:, t + 1])

    finals = balances[:, -1]
    success = finals >= goal.goal_amount
    p_success = float(success.mean())
    mean_final = float(finals.mean())
    median_final = float(np.median(finals))
    shortfalls = np.maximum(0.0, goal.goal_amount - finals)
    # Expected shortfall conditional on missing
    if (~success).any():
        expected_shortfall = float(shortfalls[~success].mean())
    else:
        expected_shortfall = 0.0

    # Inflation-adjusted success: meet a future target that preserves today's purchasing power
    if months > 0:
        monthly_inf = (1.0 + goal.annual_inflation) ** (1.0 / 12.0) - 1.0
        inflated_goal = float(goal.goal_amount) * ((1.0 + monthly_inf) ** months)
    else:
        inflated_goal = float(goal.goal_amount)
    success_real = finals >= inflated_goal
    p_success_real = float(success_real.mean())
    shortfalls_real = np.maximum(0.0, inflated_goal - finals)
    if (~success_real).any():
        expected_shortfall_real = float(shortfalls_real[~success_real].mean())
    else:
        expected_shortfall_real = 0.0

    se = float(finals.std(ddof=1) / np.sqrt(n_paths)) if n_paths > 1 else 0.0
    se_p = proportion_standard_error(p_success, n_paths)
    se_p_real = proportion_standard_error(p_success_real, n_paths)

    if store_paths_for_fan and months >= 0:
        fan = np.vstack(
            [
                np.percentile(balances, 10, axis=0),
                np.percentile(balances, 50, axis=0),
                np.percentile(balances, 90, axis=0),
            ]
        )
    else:
        fan = np.zeros((3, months + 1))

    zero_vol_mean = None
    if zero_volatility:
        zero_vol_mean = mean_final
    else:
        # Closed-form reference using inflation-aware effective rate
        r_m = instrument.effective_monthly_rate(goal.annual_inflation)
        zero_vol_mean = future_value(
            goal.current_savings,
            goal.monthly_contribution,
            r_m,
            months,
        )

    return MonteCarloResult(
        instrument_id=instrument.instrument_id,
        instrument_name=instrument.name,
        n_paths=n_paths,
        probability_success=p_success,
        probability_success_real=p_success_real,
        expected_final_balance=mean_final,
        median_final_balance=median_final,
        expected_shortfall=expected_shortfall,
        expected_shortfall_real=expected_shortfall_real,
        final_balances=finals,
        fan_chart=fan,
        std_error_of_mean=se,
        std_error_of_proportion=se_p,
        std_error_of_proportion_real=se_p_real,
        inflated_goal=inflated_goal,
        seed=int(goal.seed),
        zero_vol_mean=zero_vol_mean,
    )


def real_balances(nominal_finals: np.ndarray, annual_inflation: float, months: int) -> np.ndarray:
    if months <= 0:
        return nominal_finals.copy()
    monthly_inf = (1.0 + annual_inflation) ** (1.0 / 12.0) - 1.0
    factor = (1.0 + monthly_inf) ** months
    return nominal_finals / factor
