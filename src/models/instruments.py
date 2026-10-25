"""Instrument and goal input data models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ProtectionStatus(str, Enum):
    DPS_800K = "DPS_800k"
    SOVEREIGN = "sovereign"


@dataclass(frozen=True)
class Instrument:
    instrument_id: str
    name: str
    category: str
    annual_rate: float
    tenor_months: int
    min_deposit_hkd: float
    protection: ProtectionStatus
    eligible_notes: str
    source: str
    as_of_date: str
    coupon_type: Optional[str] = None
    min_rate: Optional[float] = None

    @property
    def monthly_rate(self) -> float:
        return (1.0 + self.annual_rate) ** (1.0 / 12.0) - 1.0

    def effective_annual_rate(self, inflation: float) -> float:
        """Coupon / yield used for projections given assumed inflation.

        Inflation-linked retail bonds (iBond / Silver Bond style) pay
        max(min_rate, inflation). Other instruments use the advertised annual_rate.
        """
        linked = self.coupon_type in ("inflation_linked", "inflation_linked_min")
        if linked and self.min_rate is not None:
            return max(float(self.min_rate), float(inflation))
        return float(self.annual_rate)

    def effective_monthly_rate(self, inflation: float) -> float:
        annual = self.effective_annual_rate(inflation)
        return (1.0 + annual) ** (1.0 / 12.0) - 1.0

    @property
    def is_deposit(self) -> bool:
        return self.protection == ProtectionStatus.DPS_800K

    @property
    def is_inflation_linked(self) -> bool:
        return self.coupon_type in ("inflation_linked", "inflation_linked_min")

    @property
    def protection_label(self) -> str:
        if self.protection == ProtectionStatus.DPS_800K:
            return "Deposit Protection Scheme (up to HK$800,000 per depositor per bank)"
        return "Hong Kong SAR Government (sovereign)"


@dataclass(frozen=True)
class GoalInputs:
    goal_amount: float
    horizon_months: int
    current_savings: float
    monthly_contribution: float
    annual_inflation: float = 0.02
    contribution_volatility: float = 0.15
    expense_shock_prob: float = 0.05
    expense_shock_mean: float = 5000.0
    expense_shock_std: float = 2000.0
    n_paths: int = 10_000
    seed: int = 42
