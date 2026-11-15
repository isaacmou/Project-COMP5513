"""Eligibility filters for age- and residency-restricted instruments."""

from __future__ import annotations

from src.data.loader import load_all_instruments
from src.models.instruments import (
    Instrument,
    ProtectionStatus,
    filter_eligible_instruments,
)


def _silver() -> Instrument:
    return Instrument(
        instrument_id="silver",
        name="Silver",
        category="silver_bond",
        annual_rate=0.04,
        tenor_months=36,
        min_deposit_hkd=10_000,
        protection=ProtectionStatus.SOVEREIGN,
        eligible_notes="Aged 60+",
        source="test",
        as_of_date="2026-01-01",
        coupon_type="inflation_linked_min",
        min_rate=0.04,
    )


def _savings() -> Instrument:
    return Instrument(
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


def test_silver_bond_requires_age_60():
    silver = _silver()
    assert silver.min_age == 60
    assert not silver.is_eligible(age=35, hk_resident=True)
    assert silver.is_eligible(age=60, hk_resident=True)
    assert not silver.is_eligible(age=65, hk_resident=False)


def test_retail_bonds_require_hk_resident():
    instruments = load_all_instruments()
    bonds = [i for i in instruments if i.category in ("ibond", "green_bond", "silver_bond")]
    assert bonds
    for bond in bonds:
        assert bond.requires_hk_resident
        assert not bond.is_eligible(age=70, hk_resident=False)


def test_filter_excludes_silver_for_young_user():
    instruments = [_savings(), _silver()]
    filtered = filter_eligible_instruments(instruments, age=40, hk_resident=True)
    assert [i.instrument_id for i in filtered] == ["sav"]


def test_filter_keeps_silver_for_senior_resident():
    instruments = [_savings(), _silver()]
    filtered = filter_eligible_instruments(instruments, age=62, hk_resident=True)
    assert {i.instrument_id for i in filtered} == {"sav", "silver"}
