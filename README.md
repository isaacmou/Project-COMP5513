# GoalWise HK

A Monte Carlo savings and investment goal planner for Hong Kong households  
(COMP5513 Financial Computing — group project).

GoalWise HK estimates **not only when** a household might reach a savings goal, but **how likely** it is to get there by a chosen date. It compares local low-risk instruments — savings accounts, time deposits, iBonds, Silver Bonds, and retail Green Bonds — in nominal and inflation-adjusted terms.

## Features

1. **Deterministic goal engine** — time-to-goal, required monthly saving, nominal and real projections  
2. **Monte Carlo engine** — 1,000–10,000 simulated paths with contribution noise, expense shocks, and rate/inflation scenarios  
3. **Instrument comparison** — side-by-side P(success), shortfall, protection status, sources and as-of dates  
4. **Education layer** — short IFEC-style explainers and a clear non-advice disclaimer  

### How rates are modelled

- **Inflation-linked bonds** (iBond / Silver Bond style): coupon = `max(min_rate, inflation)` using the assumed CPI path (deterministic) or bootstrapped historical YoY CPI (Monte Carlo).  
- **Time deposits and bonds with a tenor**: the drawn rate is held constant for each `tenor_months` block, then redrawn at rollover (reinvestment risk).  
- **Savings** (`tenor_months = 0`): rate shocks follow yearly inflation blocks without a lock-in tenor.  

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
- Zero-volatility Monte Carlo converges to the deterministic future value  
- Standard error of the mean &lt; 1% of mean at 10,000 paths  

## Project layout

```
app.py                 Streamlit dashboard
src/
  data/loader.py       Curated CSV loaders
  engines/             Deterministic, Monte Carlo, comparison
  models/              Instrument and goal dataclasses
  education.py         IFEC-style blurbs + disclaimer
data/                  Rate, bond, and CPI seeds (source + as_of_date)
tests/
```

## Data provenance

Rates and CPI figures in `data/` are **curated illustrations** for coursework, each row carrying `source` and `as_of_date`. The loader validates required columns and sensible rate ranges. Replace them with live pulls from bank rate pages, the HKSAR Government Bond Programme, C&SD Composite CPI, and HKMA Open API for production-quality audits.

Deposit Protection Scheme limit displayed in the UI: **HK$800,000** per depositor per bank (from October 2024).

## Disclaimer

Educational analysis only — not personalised investment advice. No personal financial data is stored. Verify current product terms before making decisions.
