# GoalWise HK

A Monte Carlo savings and investment goal planner for Hong Kong households  
(COMP5513 Financial Computing — group project).

GoalWise HK estimates **not only when** a household might reach a savings goal, but **how likely** it is to get there by a chosen date. It compares five curated low-risk instruments — HSBC Everyday Global Savings, a 24-month HKD time deposit, an iBond, a Silver Bond, and a retail Green Bond — in nominal and inflation-adjusted terms.

繁體中文系統與方法說明：[系統與方法說明.md](系統與方法說明.md)

## Features

1. **Deterministic goal engine** — time-to-goal, required monthly saving, nominal and real projections  
2. **Monte Carlo engine** — 1,000–10,000 simulated paths with contribution noise, expense shocks, and rate/inflation scenarios  
3. **Instrument comparison** — side-by-side P(success), shortfall, protection status, sources and as-of dates  
4. **Education layer** — short IFEC-style explainers and a clear non-advice disclaimer  

### How rates are modelled

- **Inflation-linked bonds** (iBond / Silver Bond in this build): coupon = `max(min_rate, inflation)` using the assumed CPI path (deterministic) or bootstrapped historical YoY CPI (Monte Carlo). The curated Green Bond uses a fixed/floating illustrative rate.  
- **Time deposits and bonds with a tenor**: the drawn rate is held constant for each `tenor_months` block, then redrawn at rollover (reinvestment risk).  
- **Savings** (`tenor_months = 0`): rate shocks follow yearly inflation blocks without a lock-in tenor.  

### Compounding convention

- **Live engine** (deterministic + Monte Carlo + UI): monthly rate = `(1 + annual)^(1/12) − 1` (effective monthly compounding). Real purchasing power uses the matching monthly inflation factor.
- **Progress-report Table 4 benchmark**: independently calculated with nominal monthly `r = annual/12` and inflation `π/12`. Reproduced in `tests/test_report_benchmark.py` via `nominal_monthly_rate` / `nominal_real_value` helpers — those helpers are for auditability, not the live path.  

## Quick start

```bash
# Windows (recommended)
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\streamlit.exe run app.py

# If Activate.ps1 is blocked by PowerShell execution policy, skip activate
# and use the full paths above. Or allow scripts for your user:
#   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Open the URL Streamlit prints (usually http://localhost:8501).

## Tests

```bash
pytest -q
```

KPIs covered in tests:

- Closed-form annuity / accumulation math  
- Progress-report Table 4 known-answer benchmark (`r = annual/12`)  
- Zero-volatility Monte Carlo converges to the deterministic future value  
- Standard error of the mean &lt; 1% of mean at 10,000 paths  
- Binomial SE of success proportion √[p̂(1−p̂)/N]  
- Inflation-adjusted (real-target) success probability  
- Eligibility filters (age / HK residency)  

## Project layout

```
app.py                 Streamlit dashboard
src/
  data/loader.py       Curated CSV loaders
  engines/             Deterministic, Monte Carlo, comparison
  models/              Instrument and goal dataclasses
  education.py         IFEC-style blurbs + disclaimer
data/                  Rate, bond, and CPI seeds (source + as_of_date)
docs/                  Data dictionary and meeting log
results/               Fixed-seed MC export and pytest evidence
scripts/               Evidence export helpers
tests/
```

## Evidence artefacts

```bash
pytest -q | tee results/pytest_output.txt
py -3 scripts/export_fixed_seed_results.py
```

See [`docs/data_dictionary.md`](docs/data_dictionary.md) for column definitions and eligibility rules.

## Data provenance

Rates and CPI figures in `data/` are **curated illustrations** for coursework, each row carrying `source` and `as_of_date`. The loader validates required columns and sensible rate ranges. Replace them with live pulls from bank rate pages, the HKSAR Government Bond Programme, C&SD Composite CPI, and HKMA Open API for production-quality audits.

Deposit Protection Scheme limit displayed in the UI: **HK$800,000** per depositor per bank (from October 2024).

## Disclaimer

Educational analysis only — not personalised investment advice. No personal financial data is stored. Verify current product terms before making decisions.
