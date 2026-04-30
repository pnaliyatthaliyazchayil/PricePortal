"""ZIP Map — geographic price variation with community risk overlay."""

import streamlit as st
import plotly.express as px
from views.db import query, CHANG_PQ


def render():
    st.markdown("# 🗺️ ZIP-Level Price Map")
    st.markdown(
        "Hospital ZIP-level median price-to-Medicare ratios overlaid "
        "with community socioeconomic indicators. Based on the "
        "Chang & Psek (2024) extension analysis."
    )

    # ── Load panel ─────────────────────────────────────────────────
    panel = query(f"""
        SELECT state, zip, n_hospitals, gross_ratio, cash_ratio,
               neg_min_ratio, median_income, poverty_rate,
               total_pop, poverty_rate_pct
        FROM '{CHANG_PQ}'
        WHERE gross_ratio IS NOT NULL OR cash_ratio IS NOT NULL
    """)

    if panel.empty:
        st.warning("No ZIP panel data available.")
        return

    # ── Controls ───────────────────────────────────────────────────
    col_ratio, col_state = st.columns([2, 1])
    with col_ratio:
        ratio_col = st.selectbox(
            "Price ratio to display",
            ["gross_ratio", "cash_ratio", "neg_min_ratio"],
            format_func=lambda x: {
                "gross_ratio": "Chargemaster ÷ Medicare",
                "cash_ratio": "Cash ÷ Medicare",
                "neg_min_ratio": "Min negotiated ÷ Medicare",
            }[x],
        )
    with col_state:
        state_filter = st.radio("State", ["Both", "CA", "IN"], horizontal=True)

    if state_filter != "Both":
        panel = panel[panel["state"] == state_filter]

    plot_df = panel.dropna(subset=[ratio_col]).copy()

    if plot_df.empty:
        st.warning("No data for this combination.")
        return

    # ── Summary metrics ────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("ZIPs", f"{len(plot_df)}")
    m2.metric("Median ratio", f"{plot_df[ratio_col].median():.2f}×")
    m3.metric("Median income", f"${plot_df.median_income.median():,.0f}")
    m4.metric("Median poverty", f"{plot_df.poverty_rate_pct.median():.1f}%")

    # ── Scatter: ratio vs income ───────────────────────────────────
    st.markdown("### Price ratio vs median household income")
    st.caption(
        "Each dot is a hospital ZIP. Chang & Psek (2024) found "
        "socioeconomic gradients at HSA level; we test at ZIP resolution."
    )

    ratio_labels = {
        "gross_ratio": "Gross ÷ Medicare",
        "cash_ratio": "Cash ÷ Medicare",
        "neg_min_ratio": "Min neg ÷ Medicare",
    }

    fig = px.scatter(
        plot_df,
        x="median_income",
        y=ratio_col,
        color="state",
        size="n_hospitals",
        hover_data=["zip", "poverty_rate_pct", "total_pop"],
        color_discrete_map={"CA": "#2563eb", "IN": "#dc2626"},
        opacity=0.65,
        labels={
            "median_income": "Median household income ($)",
            ratio_col: ratio_labels[ratio_col],
            "state": "State",
            "n_hospitals": "# Hospitals in ZIP",
        },
    )
    fig.update_layout(
        height=500,
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans"),
    )
    fig.update_xaxes(gridcolor="#e5e7eb", tickformat="$,.0f")
    fig.update_yaxes(gridcolor="#e5e7eb")
    st.plotly_chart(fig, use_container_width=True)

    # ── Scatter: ratio vs poverty rate ─────────────────────────────
    st.markdown("### Price ratio vs poverty rate")

    fig2 = px.scatter(
        plot_df,
        x="poverty_rate_pct",
        y=ratio_col,
        color="state",
        size="n_hospitals",
        hover_data=["zip", "median_income", "total_pop"],
        color_discrete_map={"CA": "#2563eb", "IN": "#dc2626"},
        opacity=0.65,
        labels={
            "poverty_rate_pct": "Poverty rate (%)",
            ratio_col: ratio_labels[ratio_col],
            "state": "State",
        },
    )
    fig2.update_layout(
        height=500,
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans"),
    )
    fig2.update_xaxes(gridcolor="#e5e7eb")
    fig2.update_yaxes(gridcolor="#e5e7eb")
    st.plotly_chart(fig2, use_container_width=True)

    # ── Regression results callout ─────────────────────────────────
    st.markdown("### Regression highlights (from Chang & Psek extension)")
    r1, r2 = st.columns(2)
    with r1:
        st.info(
            "**Pooled cash ratio:**\n\n"
            "log(median_income) β = −1.70 (p = 0.036)\n\n"
            "Wealthier ZIPs → lower cash-to-Medicare ratios."
        )
    with r2:
        st.info(
            "**Negotiated rates show no gradient:**\n\n"
            "neg_min_ratio: all coefficients NS\n\n"
            "Negotiated rates are set by hospital–payer contracts, "
            "not local demographics."
        )

    # ── Data table ─────────────────────────────────────────────────
    with st.expander("Show ZIP-level data table"):
        display = plot_df[[
            "zip", "state", "n_hospitals", ratio_col,
            "median_income", "poverty_rate_pct", "total_pop"
        ]].sort_values(ratio_col, ascending=False).copy()
        display = display.rename(columns={
            "zip": "ZIP",
            "state": "State",
            "n_hospitals": "# Hospitals",
            ratio_col: "Ratio",
            "median_income": "Median income",
            "poverty_rate_pct": "Poverty %",
            "total_pop": "Population",
        })
        st.dataframe(
            display.style.format({
                "Ratio": "{:.2f}×",
                "Median income": "${:,.0f}",
                "Poverty %": "{:.1f}%",
                "Population": "{:,.0f}",
            }, na_rep="—"),
            use_container_width=True,
            hide_index=True,
        )
