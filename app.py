"""GoalWise HK — Streamlit dashboard."""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data.loader import get_inflation_history, get_mean_inflation, load_all_instruments
from src.education import DISCLAIMER, METRIC_EXPLAINERS, explainer_for_category
from src.engines.comparison import (
    comparison_to_dataframe,
    compare_instruments,
    what_if_adjustments,
)
from src.engines.deterministic import (
    inflated_target,
    monthly_path_deterministic,
    project_deterministic,
    required_monthly_contribution,
)
from src.engines.monte_carlo import run_monte_carlo
from src.models.instruments import GoalInputs, filter_eligible_instruments

st.set_page_config(
    page_title="GoalWise HK",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Subtle non-generic styling
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Fraunces:opsz,wght@9..144,600;9..144,700&display=swap');
    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
    h1, h2, h3 { font-family: 'Fraunces', serif !important; }
    .block-container { padding-top: 1.5rem; }
    div[data-testid="stMetric"] {
        background: linear-gradient(145deg, #f7faf8 0%, #eef4f1 100%);
        border: 1px solid #d5e3db;
        border-radius: 10px;
        padding: 0.75rem 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def _instruments():
    return load_all_instruments()


@st.cache_data
def _inflation_hist():
    return get_inflation_history()


def format_hkd(x: float) -> str:
    return f"HK${x:,.0f}"


def build_fan_chart(fan: np.ndarray, goal_amount: float, title: str) -> go.Figure:
    months = np.arange(fan.shape[1])
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=np.concatenate([months, months[::-1]]),
            y=np.concatenate([fan[2], fan[0][::-1]]),
            fill="toself",
            fillcolor="rgba(46, 125, 90, 0.18)",
            line=dict(color="rgba(255,255,255,0)"),
            name="10th–90th percentile",
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=months,
            y=fan[1],
            mode="lines",
            name="Median path",
            line=dict(color="#1b5e3b", width=2.5),
        )
    )
    fig.add_hline(
        y=goal_amount,
        line_dash="dash",
        line_color="#c45c26",
        annotation_text="Goal",
    )
    fig.update_layout(
        title=title,
        xaxis_title="Month",
        yaxis_title="Balance (HK$)",
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=40, r=20, t=60, b=40),
        height=420,
    )
    return fig


def build_distribution_hist(finals: np.ndarray, goal_amount: float) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Histogram(
            x=finals,
            nbinsx=40,
            marker_color="#2e7d5a",
            opacity=0.85,
            name="Final balances",
        )
    )
    fig.add_vline(x=goal_amount, line_dash="dash", line_color="#c45c26", annotation_text="Goal")
    fig.update_layout(
        title="Distribution of final balances",
        xaxis_title="Final balance (HK$)",
        yaxis_title="Paths",
        template="plotly_white",
        height=360,
        margin=dict(l=40, r=20, t=50, b=40),
    )
    return fig


def main() -> None:
    st.title("GoalWise HK")
    st.subheader("Monte Carlo savings & investment goal planner for Hong Kong households")
    st.info(DISCLAIMER)

    instruments = _instruments()
    hist = _inflation_hist()
    default_inflation = get_mean_inflation()

    with st.sidebar:
        st.header("Your goal")
        goal_amount = st.number_input(
            "Goal amount (HK$)",
            min_value=10_000.0,
            max_value=10_000_000.0,
            value=400_000.0,
            step=10_000.0,
        )
        years = st.slider(
            "Deadline (years)",
            min_value=1.0,
            max_value=15.0,
            value=4.0,
            step=0.5,
            format="%.1f",
        )
        current = st.number_input(
            "Current savings (HK$)",
            min_value=0.0,
            max_value=5_000_000.0,
            value=50_000.0,
            step=5_000.0,
        )
        monthly = st.number_input(
            "Planned monthly saving (HK$)",
            min_value=0.0,
            max_value=200_000.0,
            value=6_000.0,
            step=500.0,
        )
        # Use percent points (0–6) so Streamlit sprintf format stays valid.
        # format="%.1%" is rejected by newer Streamlit (unexpected placeholder).
        inflation_pct = st.slider(
            "Assumed annual inflation (%)",
            min_value=0.0,
            max_value=6.0,
            value=float(round(default_inflation * 100.0, 1)),
            step=0.1,
            format="%.1f%%",
        )
        inflation = inflation_pct / 100.0
        st.caption(f"Historical mean CPI (curated series): {default_inflation:.1%}")

        st.header("Eligibility")
        hk_resident = st.checkbox("Hong Kong resident", value=True)
        age = st.number_input(
            "Age (years)",
            min_value=18,
            max_value=100,
            value=35,
            step=1,
            help="Silver Bonds typically require age 60+. Used to filter instruments. iBond and Green Bond require HK residency.",
        )
        st.caption(METRIC_EXPLAINERS["eligibility"])

        st.header("Uncertainty")
        n_paths = st.select_slider(
            "Monte Carlo paths",
            options=[1_000, 2_500, 5_000, 10_000],
            value=5_000,
        )
        contrib_vol = st.slider(
            "Contribution variability",
            0.0,
            0.4,
            0.15,
            0.05,
            format="%.2f",
        )
        shock_prob = st.slider(
            "Monthly expense-shock probability",
            0.0,
            0.15,
            0.05,
            0.01,
            format="%.2f",
        )

        eligible = filter_eligible_instruments(
            instruments,
            age=int(age),
            hk_resident=bool(hk_resident),
        )
        if not eligible:
            st.error("No instruments match the current eligibility profile.")
            return

        names = [i.name for i in eligible]
        selected_name = st.selectbox(
            "Focus instrument",
            names,
            index=min(5, len(names) - 1),
        )
        run = st.button("Run planner", type="primary", use_container_width=True)

    goal = GoalInputs(
        goal_amount=goal_amount,
        horizon_months=int(round(years * 12)),
        current_savings=current,
        monthly_contribution=monthly,
        annual_inflation=inflation,
        contribution_volatility=contrib_vol,
        expense_shock_prob=shock_prob,
        expense_shock_mean=5_000.0,
        expense_shock_std=2_000.0,
        n_paths=int(n_paths),
        seed=42,
    )
    focus = next(i for i in eligible if i.name == selected_name)
    excluded = [i.name for i in instruments if i not in eligible]

    if not run and "ran" not in st.session_state:
        st.markdown("### How it works")
        st.write(
            "Enter a Hong Kong dollar goal, deadline, and saving pattern. "
            "GoalWise compares HSBC Everyday Global Savings, a 24-month HKD time deposit, "
            "an iBond, a Silver Bond, and a retail Green Bond — then estimates **how likely** you are to make it."
        )
        cols = st.columns(3)
        cols[0].markdown(METRIC_EXPLAINERS["probability_success"])
        cols[1].markdown(METRIC_EXPLAINERS["probability_success_real"])
        cols[2].markdown(METRIC_EXPLAINERS["dps"])
        st.markdown(METRIC_EXPLAINERS["monte_carlo"])
        with st.expander("Curated instruments in this build (eligibility-filtered)"):
            rows = [
                {
                    "Name": i.name,
                    "Category": i.category,
                    "Rate": f"{i.annual_rate:.2%}",
                    "Protection": i.protection.value,
                    "As of": i.as_of_date,
                    "Source": i.source,
                }
                for i in eligible
            ]
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
            if excluded:
                st.caption("Excluded by eligibility: " + ", ".join(excluded))
        return

    st.session_state["ran"] = True

    with st.spinner("Running deterministic baseline and Monte Carlo simulations…"):
        det = project_deterministic(focus, goal)
        mc = run_monte_carlo(focus, goal, inflation_history=hist)
        # Use fewer paths for full comparison for responsiveness
        cmp_goal = replace(goal, n_paths=min(goal.n_paths, 2_500))
        comparison = compare_instruments(eligible, cmp_goal, inflation_history=hist)
        what_ifs = what_if_adjustments(focus, cmp_goal, inflation_history=hist)

    future_goal = inflated_target(goal.goal_amount, goal.annual_inflation, goal.horizon_months)
    req_real = required_monthly_contribution(
        future_goal,
        goal.current_savings,
        focus.effective_monthly_rate(goal.annual_inflation),
        goal.horizon_months,
    )

    st.markdown(f"### Results — {focus.name}")
    st.caption(
        f"Assumptions: {goal.horizon_months} months · "
        f"rate {focus.annual_rate:.2%} (as of {focus.as_of_date}) · "
        f"inflation {goal.annual_inflation:.1%} · {mc.n_paths:,} paths · "
        f"seed {mc.seed} · source: {focus.source}"
    )
    if excluded:
        st.caption("Excluded by eligibility: " + ", ".join(excluded))

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        "P(success) nominal",
        f"{mc.probability_success:.1%}",
        help=f"SE = {mc.std_error_of_proportion:.2%} (binomial)",
    )
    m2.metric(
        "P(success) real target",
        f"{mc.probability_success_real:.1%}",
        help=f"SE = {mc.std_error_of_proportion_real:.2%} · inflated goal {format_hkd(mc.inflated_goal)}",
    )
    m3.metric("Expected shortfall (if miss)", format_hkd(mc.expected_shortfall))
    m4.metric("Expected final balance", format_hkd(mc.expected_final_balance))

    s1, s2, s3 = st.columns(3)
    s1.metric("Binomial SE (nominal P)", f"{mc.std_error_of_proportion:.2%}")
    s2.metric("Binomial SE (real P)", f"{mc.std_error_of_proportion_real:.2%}")
    s3.metric("Deterministic projection", format_hkd(det.projected_nominal))

    st.markdown(METRIC_EXPLAINERS["probability_success"])
    st.markdown(METRIC_EXPLAINERS["probability_success_real"])
    st.markdown(METRIC_EXPLAINERS["nominal_vs_real"])

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(
            build_fan_chart(mc.fan_chart, goal.goal_amount, "Probability fan chart"),
            use_container_width=True,
        )
    with c2:
        st.plotly_chart(
            build_distribution_hist(mc.final_balances, goal.goal_amount),
            use_container_width=True,
        )

    det_path = monthly_path_deterministic(
        goal.current_savings,
        goal.monthly_contribution,
        focus.effective_monthly_rate(goal.annual_inflation),
        goal.horizon_months,
    )
    fig_det = go.Figure()
    fig_det.add_trace(
        go.Scatter(
            x=np.arange(len(det_path)),
            y=det_path,
            name="Deterministic",
            line=dict(color="#1b5e3b", width=2),
        )
    )
    fig_det.add_trace(
        go.Scatter(
            x=np.arange(mc.fan_chart.shape[1]),
            y=mc.fan_chart[1],
            name="MC median",
            line=dict(color="#5b8c6a", width=2, dash="dot"),
        )
    )
    fig_det.add_hline(y=goal.goal_amount, line_dash="dash", line_color="#c45c26")
    fig_det.update_layout(
        title="Deterministic path vs Monte Carlo median",
        xaxis_title="Month",
        yaxis_title="Balance (HK$)",
        template="plotly_white",
        height=360,
    )
    st.plotly_chart(fig_det, use_container_width=True)

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Real (CPI-deflated) projection", format_hkd(det.projected_real))
    r2.metric("Required monthly (nominal goal)", format_hkd(det.required_monthly))
    r3.metric("Required monthly (real goal)", format_hkd(req_real))
    ttm = det.time_to_goal_months
    r4.metric("Time to goal (deterministic)", f"{ttm} mo" if ttm is not None else "Unreachable")
    st.caption(
        f"Inflated goal preserving today's purchasing power: {format_hkd(future_goal)} "
        f"(assumed inflation {goal.annual_inflation:.1%})."
    )

    st.markdown(f"**Protection:** {focus.protection_label}")
    st.markdown(explainer_for_category(focus.category))
    st.markdown(METRIC_EXPLAINERS["dps"])

    st.markdown("### Instrument comparison")
    st.caption(
        "Side-by-side outcomes for the five curated instruments "
        f"(eligibility-filtered). Comparison uses {cmp_goal.n_paths:,} paths for speed "
        f"(seed {cmp_goal.seed})."
    )
    st.dataframe(comparison_to_dataframe(comparison), use_container_width=True, hide_index=True)

    # Bar chart of success probabilities
    fig_bar = go.Figure(
        go.Bar(
            x=[r.name for r in comparison],
            y=[r.probability_success for r in comparison],
            marker_color="#2e7d5a",
            text=[f"{r.probability_success:.0%}" for r in comparison],
            textposition="outside",
        )
    )
    fig_bar.update_layout(
        title="Probability of success by instrument",
        yaxis_title="P(success)",
        yaxis_tickformat=".0%",
        template="plotly_white",
        height=400,
        xaxis_tickangle=-25,
        margin=dict(b=120),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("### What improves the odds most?")
    st.caption(f"Sensitivities for the focus instrument: **{focus.name}**")
    wi_df = pd.DataFrame(
        [
            {
                "Scenario": w.label,
                "Description": w.description,
                "P(success)": f"{w.probability_success:.1%}",
                "Δ vs baseline": f"{w.delta_p_success:+.1%}",
                "Expected shortfall": format_hkd(w.expected_shortfall),
                "Expected balance": format_hkd(w.expected_final_balance),
            }
            for w in what_ifs
        ]
    )
    st.dataframe(wi_df, use_container_width=True, hide_index=True)
    best = max(what_ifs[1:], key=lambda w: w.delta_p_success)
    st.success(
        f"Largest improvement among tested levers: **{best.label}** "
        f"({best.delta_p_success:+.1%} probability of success). "
        "Switching instruments is reflected in the comparison table above."
    )

    with st.expander("Learn more — education layer"):
        for key in (
            "monte_carlo",
            "probability_success",
            "probability_success_real",
            "nominal_vs_real",
            "expected_shortfall",
            "eligibility",
            "dps",
        ):
            st.markdown(METRIC_EXPLAINERS[key])
        st.markdown("#### Instrument types")
        for cat in ("savings", "time_deposit", "ibond", "silver_bond", "green_bond"):
            st.markdown(f"**{cat.replace('_', ' ').title()}** — {explainer_for_category(cat)}")


if __name__ == "__main__":
    main()
