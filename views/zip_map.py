"""ZIP Map — geographic price variation with community risk overlay."""

from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.express as px
from views.db import query, CHANG_PQ

CENTROIDS_CSV = Path(__file__).parent.parent / "data" / "zip_centroids.csv"

RATIO_LABELS = {
    "gross_ratio": "Chargemaster ÷ Medicare",
    "cash_ratio": "Cash ÷ Medicare",
    "neg_min_ratio": "Min negotiated ÷ Medicare",
}
SHORT_LABELS = {
    "gross_ratio": "Gross ÷ Medicare",
    "cash_ratio": "Cash ÷ Medicare",
    "neg_min_ratio": "Min neg ÷ Medicare",
}
STATE_VIEWS = {
    "Both": dict(center=dict(lat=37.5, lon=-104.0), zoom=3.4),
    "CA":   dict(center=dict(lat=37.0, lon=-119.5), zoom=4.6),
    "IN":   dict(center=dict(lat=39.9, lon=-86.3),  zoom=5.6),
}


@st.cache_data
def _load_centroids() -> pd.DataFrame:
    return pd.read_csv(CENTROIDS_CSV, dtype={"zip": str})


def render():
    st.markdown("# 🗺️ ZIP-Level Price Map")
    st.markdown(
        "Hospital ZIP-level median price-to-Medicare ratios across CA + IN, "
        "with the underlying socioeconomic gradients from the Chang & Psek "
        "(2024) extension analysis."
    )

    # ── Load panel + centroids ─────────────────────────────────────
    panel = query(f"""
        SELECT state, zip, n_hospitals, gross_ratio, cash_ratio,
               neg_min_ratio, median_income, poverty_rate,
               total_pop, poverty_rate_pct
        FROM '{CHANG_PQ}'
        WHERE gross_ratio IS NOT NULL OR cash_ratio IS NOT NULL
           OR neg_min_ratio IS NOT NULL
    """)
    if panel.empty:
        st.warning("No ZIP panel data available.")
        return
    panel["zip"] = panel["zip"].astype(str)

    centroids = _load_centroids()
    panel = panel.merge(centroids, on="zip", how="left")

    # ── Controls ───────────────────────────────────────────────────
    col_ratio, col_state = st.columns([2, 1])
    with col_ratio:
        ratio_col = st.selectbox(
            "Price ratio to display",
            list(RATIO_LABELS.keys()),
            format_func=lambda x: RATIO_LABELS[x],
        )
    with col_state:
        state_filter = st.radio("State", ["Both", "CA", "IN"], horizontal=True)

    view = panel.copy()
    if state_filter != "Both":
        view = view[view["state"] == state_filter]
    view = view.dropna(subset=[ratio_col, "lat", "lon"]).copy()

    if view.empty:
        st.warning("No data for this combination.")
        return

    # ── Summary metrics ────────────────────────────────────────────
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("ZIPs", f"{len(view)}")
    m2.metric("Median ratio", f"{view[ratio_col].median():.2f}×")
    m3.metric("Median income", f"${view.median_income.median():,.0f}")
    m4.metric("Median poverty", f"{view.poverty_rate_pct.median():.1f}%")

    # ── ZIP bubble map ─────────────────────────────────────────────
    st.markdown(f"### {RATIO_LABELS[ratio_col]} by hospital ZIP")
    st.caption(
        "One bubble per ZIP; bubble size = number of hospitals in that ZIP, "
        "color = price-to-Medicare ratio. Color scale clipped at the "
        "5th–95th percentile so a few extreme ZIPs don't flatten the gradient."
    )

    lo = float(view[ratio_col].quantile(0.05))
    hi = float(view[ratio_col].quantile(0.95))
    if hi <= lo:
        lo, hi = float(view[ratio_col].min()), float(view[ratio_col].max())

    map_view = STATE_VIEWS[state_filter]
    fig = px.scatter_mapbox(
        view,
        lat="lat",
        lon="lon",
        size="n_hospitals",
        color=ratio_col,
        color_continuous_scale="RdYlBu_r",
        range_color=(lo, hi),
        size_max=22,
        hover_name="zip",
        hover_data={
            "state": True,
            "n_hospitals": True,
            ratio_col: ":.2f",
            "median_income": ":,.0f",
            "poverty_rate_pct": ":.1f",
            "lat": False,
            "lon": False,
        },
        labels={
            ratio_col: SHORT_LABELS[ratio_col],
            "n_hospitals": "# Hospitals",
            "median_income": "Median income",
            "poverty_rate_pct": "Poverty %",
            "state": "State",
        },
        zoom=map_view["zoom"],
        center=map_view["center"],
    )
    fig.update_layout(
        mapbox_style="open-street-map",
        height=560,
        margin=dict(l=0, r=0, t=10, b=0),
        font=dict(family="DM Sans"),
        coloraxis_colorbar=dict(
            title=SHORT_LABELS[ratio_col],
            ticksuffix="×",
        ),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── Socioeconomic gradients ────────────────────────────────────
    st.markdown("---")
    st.markdown("## Socioeconomic gradients")
    st.caption(
        "Each dot is a hospital ZIP. Chang & Psek (2024) found "
        "socioeconomic gradients at HSA level; we test at ZIP resolution."
    )

    gcol1, gcol2 = st.columns(2)

    with gcol1:
        st.markdown("**Ratio vs median household income**")
        fig_inc = px.scatter(
            view,
            x="median_income",
            y=ratio_col,
            color="state",
            size="n_hospitals",
            hover_data=["zip", "poverty_rate_pct", "total_pop"],
            color_discrete_map={"CA": "#2563eb", "IN": "#dc2626"},
            opacity=0.65,
            labels={
                "median_income": "Median household income ($)",
                ratio_col: SHORT_LABELS[ratio_col],
                "state": "State",
                "n_hospitals": "# Hospitals",
            },
        )
        fig_inc.update_layout(
            height=380,
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="DM Sans"),
            margin=dict(t=10, b=0),
        )
        fig_inc.update_xaxes(gridcolor="#e5e7eb", tickformat="$,.0f")
        fig_inc.update_yaxes(gridcolor="#e5e7eb")
        st.plotly_chart(fig_inc, use_container_width=True)

    with gcol2:
        st.markdown("**Ratio vs poverty rate**")
        fig_pov = px.scatter(
            view,
            x="poverty_rate_pct",
            y=ratio_col,
            color="state",
            size="n_hospitals",
            hover_data=["zip", "median_income", "total_pop"],
            color_discrete_map={"CA": "#2563eb", "IN": "#dc2626"},
            opacity=0.65,
            labels={
                "poverty_rate_pct": "Poverty rate (%)",
                ratio_col: SHORT_LABELS[ratio_col],
                "state": "State",
            },
        )
        fig_pov.update_layout(
            height=380,
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="DM Sans"),
            margin=dict(t=10, b=0),
        )
        fig_pov.update_xaxes(gridcolor="#e5e7eb")
        fig_pov.update_yaxes(gridcolor="#e5e7eb")
        st.plotly_chart(fig_pov, use_container_width=True)

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
        display = view[[
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
