"""Load curated Hong Kong rate, bond, and CPI datasets."""

from __future__ import annotations

from pathlib import Path
from typing import List, Sequence

import pandas as pd

from src.models.instruments import Instrument, ProtectionStatus

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

_BASE_INSTRUMENT_COLUMNS = (
    "instrument_id",
    "name",
    "category",
    "annual_rate",
    "tenor_months",
    "min_deposit_hkd",
    "protection",
    "eligible_notes",
    "source",
    "as_of_date",
)
_BOND_EXTRA_COLUMNS = ("coupon_type",)
_CPI_COLUMNS = ("date", "yoy_inflation")


def _protection(value: str) -> ProtectionStatus:
    if value == "DPS_800k":
        return ProtectionStatus.DPS_800K
    return ProtectionStatus.SOVEREIGN


def _require_columns(df: pd.DataFrame, required: Sequence[str], path: Path) -> None:
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"{path.name}: missing required columns: {', '.join(missing)}")


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Data file not found: {path}")
    return pd.read_csv(path)


def _validate_instrument_row(row: pd.Series, path: Path, idx: int) -> None:
    label = f"{path.name} row {idx}"
    instrument_id = str(row.get("instrument_id", "")).strip()
    source = str(row.get("source", "")).strip()
    as_of = str(row.get("as_of_date", "")).strip()
    if not instrument_id:
        raise ValueError(f"{label}: instrument_id must be non-empty")
    if not source:
        raise ValueError(f"{label}: source must be non-empty")
    if not as_of:
        raise ValueError(f"{label}: as_of_date must be non-empty")

    try:
        rate = float(row["annual_rate"])
        tenor = int(row["tenor_months"])
        min_deposit = float(row["min_deposit_hkd"])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}: invalid numeric fields ({exc})") from exc

    if not (0.0 <= rate <= 0.2):
        raise ValueError(f"{label}: annual_rate={rate} out of range [0, 0.2]")
    if tenor < 0:
        raise ValueError(f"{label}: tenor_months must be >= 0")
    if min_deposit < 0:
        raise ValueError(f"{label}: min_deposit_hkd must be >= 0")

    if "min_rate" in row.index and pd.notna(row.get("min_rate")):
        try:
            min_rate = float(row["min_rate"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label}: invalid min_rate ({exc})") from exc
        if not (0.0 <= min_rate <= 0.2):
            raise ValueError(f"{label}: min_rate={min_rate} out of range [0, 0.2]")


def _row_to_instrument(row: pd.Series) -> Instrument:
    return Instrument(
        instrument_id=str(row["instrument_id"]),
        name=str(row["name"]),
        category=str(row["category"]),
        annual_rate=float(row["annual_rate"]),
        tenor_months=int(row["tenor_months"]),
        min_deposit_hkd=float(row["min_deposit_hkd"]),
        protection=_protection(str(row["protection"])),
        eligible_notes=str(row["eligible_notes"]),
        source=str(row["source"]),
        as_of_date=str(row["as_of_date"]),
        coupon_type=str(row["coupon_type"]) if "coupon_type" in row and pd.notna(row.get("coupon_type")) else None,
        min_rate=float(row["min_rate"]) if "min_rate" in row and pd.notna(row.get("min_rate")) else None,
    )


def _read_instruments_csv(path: Path, required_columns: Sequence[str]) -> List[Instrument]:
    df = _read_csv(path)
    _require_columns(df, required_columns, path)
    instruments: List[Instrument] = []
    for idx, row in df.iterrows():
        _validate_instrument_row(row, path, int(idx) + 2)  # +2: header + 1-based
        instruments.append(_row_to_instrument(row))
    return instruments


def load_savings(data_dir: Path | None = None) -> List[Instrument]:
    path = (data_dir or DATA_DIR) / "savings_rates.csv"
    return _read_instruments_csv(path, _BASE_INSTRUMENT_COLUMNS)


def load_time_deposits(data_dir: Path | None = None) -> List[Instrument]:
    path = (data_dir or DATA_DIR) / "time_deposits.csv"
    return _read_instruments_csv(path, _BASE_INSTRUMENT_COLUMNS)


def load_bonds(data_dir: Path | None = None) -> List[Instrument]:
    path = (data_dir or DATA_DIR) / "bonds.csv"
    required = _BASE_INSTRUMENT_COLUMNS + _BOND_EXTRA_COLUMNS
    return _read_instruments_csv(path, required)


def load_all_instruments(data_dir: Path | None = None) -> List[Instrument]:
    return load_savings(data_dir) + load_time_deposits(data_dir) + load_bonds(data_dir)


def load_cpi(data_dir: Path | None = None) -> pd.DataFrame:
    path = (data_dir or DATA_DIR) / "cpi_hk.csv"
    df = _read_csv(path)
    _require_columns(df, _CPI_COLUMNS, path)
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    if df["yoy_inflation"].isna().any():
        raise ValueError(f"{path.name}: yoy_inflation contains missing values")
    return df.sort_values("date").reset_index(drop=True)


def get_mean_inflation(data_dir: Path | None = None) -> float:
    cpi = load_cpi(data_dir)
    return float(cpi["yoy_inflation"].mean())


def get_inflation_history(data_dir: Path | None = None) -> List[float]:
    cpi = load_cpi(data_dir)
    return cpi["yoy_inflation"].astype(float).tolist()
