"""Short IFEC-style education blurbs for the dashboard."""

METRIC_EXPLAINERS = {
    "probability_success": (
        "**Probability of success (nominal)** is the share of simulated household "
        "paths that reach your stated goal amount by the deadline. It is not a "
        "guarantee — real life can fall outside the scenarios we model."
    ),
    "probability_success_real": (
        "**Probability of success (real target)** uses an inflation-adjusted goal: "
        "the future amount that preserves today's purchasing power of your target. "
        "Meeting the nominal dollar figure may still leave you short in real terms."
    ),
    "expected_shortfall": (
        "**Expected shortfall** is the average amount you would still need if you "
        "miss the goal (conditional on missing). A smaller shortfall means even "
        "unsuccessful paths land closer to the target."
    ),
    "nominal_vs_real": (
        "**Nominal** balances are in future Hong Kong dollars. **Real** balances "
        "are deflated by assumed CPI inflation so you can see purchasing power in "
        "today's dollars — important for weddings, tuition, or down payments years away."
    ),
    "monte_carlo": (
        "The **Monte Carlo engine** simulates thousands of possible lives: lumpy "
        "contributions, unexpected expenses, and shifting rates/inflation. Bank "
        "calculators that assume a fixed monthly deposit cannot express this uncertainty. "
        "The **standard error of the proportion** √[p̂(1−p̂)/N] shows sampling "
        "uncertainty in the estimated success probability."
    ),
    "dps": (
        "Eligible **bank deposits** in Hong Kong are protected by the Deposit "
        "Protection Scheme up to **HK$800,000** per depositor per bank (raised from "
        "HK$500,000 from October 2024). **Government retail bonds** carry sovereign "
        "credit rather than DPS coverage — different forms of safety."
    ),
    "eligibility": (
        "**Eligibility filters** hide products you cannot buy under the profile you "
        "set (for example Silver Bonds typically require age 60+, and retail "
        "government bonds are aimed at Hong Kong residents). Filtered views avoid "
        "implying every household can access every instrument."
    ),
}

INSTRUMENT_EXPLAINERS = {
    "savings": (
        "Savings accounts are liquid and DPS-protected (within the limit), but "
        "advertised rates are often low unless bonus criteria are met."
    ),
    "time_deposit": (
        "Time deposits usually pay more than ordinary savings for locking funds "
        "for a tenor. Early withdrawal may forfeit interest. Still DPS-protected "
        "within the scheme limit."
    ),
    "ibond": (
        "iBonds are inflation-linked retail government bonds. Coupons relate to "
        "Hong Kong CPI with a stated minimum in many issues — useful when inflation "
        "uncertainty matters. Subject to subscription windows and allocation."
    ),
    "silver_bond": (
        "Silver Bonds are aimed at senior Hong Kong residents (typically aged 60+). "
        "They often offer inflation-linked coupons with a relatively high minimum "
        "rate. Eligibility rules apply."
    ),
    "green_bond": (
        "Retail Green Bonds fund green projects and may pay fixed or floating "
        "coupons depending on the issue. Like other HKSAR retail bonds, they are "
        "sovereign obligations, not DPS deposits."
    ),
}

DISCLAIMER = (
    "GoalWise HK is an **educational** planner for COMP5513. It provides analysis "
    "and investor-education style explanations, **not** personalised investment advice "
    "and does not execute transactions. Rates are curated illustrations with sources "
    "and as-of dates — always verify current terms with banks and the Government Bond "
    "Programme before deciding. No personal financial data is stored."
)


def explainer_for_category(category: str) -> str:
    return INSTRUMENT_EXPLAINERS.get(category, "Hong Kong low-risk retail instrument.")
