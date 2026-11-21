# GoalWise HK — Data dictionary

Curated illustration datasets under `data/`. Every instrument and CPI row carries provenance fields so results can be tied to a fixed snapshot.

## Common instrument columns

| Column | Type | Description |
|--------|------|-------------|
| `instrument_id` | string | Stable unique key |
| `name` | string | Display name |
| `category` | string | `savings`, `time_deposit`, `ibond`, `silver_bond`, or `green_bond` |
| `annual_rate` | float | Advertised / illustrative annual rate (decimal, e.g. `0.03` = 3%) |
| `tenor_months` | int | Lock-in tenor in months; `0` = no lock (savings) |
| `min_deposit_hkd` | float | Minimum subscription / deposit (HK$) |
| `protection` | string | `DPS_800k` or `sovereign` |
| `eligible_notes` | string | Human-readable eligibility / caveats |
| `source` | string | Publisher or programme name |
| `as_of_date` | string | Snapshot date (`YYYY-MM-DD`) |

### Bonds-only extra columns (`data/bonds.csv`)

| Column | Type | Description |
|--------|------|-------------|
| `coupon_type` | string | `inflation_linked`, `inflation_linked_min`, or `fixed_or_floating` |
| `min_rate` | float | Coupon floor for inflation-linked issues (decimal) |

### Curated instruments in this build

| File | Instrument |
|------|------------|
| `savings_rates.csv` | HSBC Everyday Global Savings |
| `time_deposits.csv` | Major Bank HKD Time Deposit 24M |
| `bonds.csv` | iBond; Silver Bond; Retail Green Bond (illustrative) |

### Eligibility rules applied in the UI

| Category | HK resident | Minimum age |
|----------|-------------|-------------|
| `savings`, `time_deposit` | not required | none |
| `ibond`, `green_bond` | required | none |
| `silver_bond` | required | 60 |

## CPI series (`data/cpi_hk.csv`)

| Column | Type | Description |
|--------|------|-------------|
| `date` | date | Period start |
| `cpi_index` | float | Illustrative index level |
| `yoy_inflation` | float | Year-on-year inflation (decimal) |
| `source` | string | Series attribution |
| `as_of_date` | string | Retrieval / snapshot date |

**Notes**

- Series: illustrative Composite CPI–style path for coursework (not a live C&SD pull).
- Frequency: semi-annual sample points in the curated file.
- Transformation: `yoy_inflation` used directly for Monte Carlo bootstrap; mean used as UI default inflation.
- Missing-value rule: loader rejects any null `yoy_inflation`.

## Authoritative sources (for production refresh)

| Dataset | Authoritative source |
|---------|----------------------|
| Deposit rates | Published bank rate pages |
| Retail bond terms | [Hong Kong Government Bonds programme](https://www.hkgb.gov.hk) |
| Composite CPI | [Census and Statistics Department](https://www.censtatd.gov.hk) |
| Monetary context | [HKMA Open API](https://api.hkma.gov.hk) |

Rates in this repository are **curated illustrations**. Replace with live pulls and keep raw downloads separate from cleaned CSVs for audit-quality work.
