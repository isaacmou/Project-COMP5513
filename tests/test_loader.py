"""CSV loader schema and range validation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.data.loader import load_all_instruments, load_bonds, load_cpi, load_savings


def test_load_curated_data_ok():
    instruments = load_all_instruments()
    assert len(instruments) >= 5
    assert all(i.source and i.as_of_date for i in instruments)
    cpi = load_cpi()
    assert "yoy_inflation" in cpi.columns
    assert len(cpi) > 0


def test_missing_file_raises(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="not found"):
        load_savings(tmp_path)


def test_missing_column_raises(tmp_path: Path):
    path = tmp_path / "savings_rates.csv"
    pd.DataFrame(
        {
            "instrument_id": ["x"],
            "name": ["X"],
            "category": ["savings"],
            # annual_rate missing
            "tenor_months": [0],
            "min_deposit_hkd": [0],
            "protection": ["DPS_800k"],
            "eligible_notes": [""],
            "source": ["test"],
            "as_of_date": ["2026-01-01"],
        }
    ).to_csv(path, index=False)
    with pytest.raises(ValueError, match="missing required columns"):
        load_savings(tmp_path)


def test_bad_annual_rate_raises(tmp_path: Path):
    path = tmp_path / "savings_rates.csv"
    pd.DataFrame(
        {
            "instrument_id": ["x"],
            "name": ["X"],
            "category": ["savings"],
            "annual_rate": [0.5],
            "tenor_months": [0],
            "min_deposit_hkd": [0],
            "protection": ["DPS_800k"],
            "eligible_notes": [""],
            "source": ["test"],
            "as_of_date": ["2026-01-01"],
        }
    ).to_csv(path, index=False)
    with pytest.raises(ValueError, match="annual_rate"):
        load_savings(tmp_path)


def test_bonds_require_coupon_type(tmp_path: Path):
    path = tmp_path / "bonds.csv"
    pd.DataFrame(
        {
            "instrument_id": ["b"],
            "name": ["Bond"],
            "category": ["ibond"],
            "annual_rate": [0.02],
            "tenor_months": [36],
            "min_deposit_hkd": [10000],
            "protection": ["sovereign"],
            "eligible_notes": [""],
            "source": ["test"],
            "as_of_date": ["2026-01-01"],
        }
    ).to_csv(path, index=False)
    with pytest.raises(ValueError, match="coupon_type"):
        load_bonds(tmp_path)
