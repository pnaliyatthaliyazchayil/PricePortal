"""Wang 2023 Replication — within-hospital cross-price-type correlations."""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from views.db import query, WANG_HOSP_PQ, WANG_SUM_PQ


def render():
    st.markdown("# 📈 Wang 2023 Replication")
    st.markdown(
        "Within-hospital correlations between chargemaster, cash, and "
        "minimum-negotiated prices across CPT/HCPCS codes. Replicates "
        "and extends Wang, Bai & Anderson (*Health Affairs* 2023)."
    )

    # ── Key finding callout ────────────────────────────────────────
    st.error(
        "**Key departure from Wang 2023:** Gross↔Cash correlation is "
        "r = 1.0 within hospital, even among hospitals with a real cash "
        "discount (≥5% off chargemaster). Cash discounts are applied as a "
        "flat per-hospital fraction — not set independently per procedure. "
        "Wang reported r ≈ 0.85."
    )

    # ── State summary table ────────────────────────────────────────
    summary = query(f"SELECT * FROM '{WANG_SUM_PQ}'")

    st.markdown("### Median within-hospital correlations")

    # Pivot for display
    for segment in ["discounters", "all"]:
        seg = summary[summary["segment"] == segment]
        if seg.empty:
            continue

        label = "Discounters only (≥5% cash discount)" if segment == "discounters" else "All hospitals"
        st.markdown(f"**{label}**")

        pivot = seg.pivot(index="pair", columns="state", values="p50")
        pair_labels = {
            "gross_cash": "Gross ↔ Cash",
            "gross_negmin": "Gross ↔ Min negotiated",
            "cash_negmin": "Cash ↔ Min negotiated",
        }
        pivot.index = pivot.index.map(pair_labels)

        # Add Wang's numbers for comparison
        wang_ref = {
            "Gross ↔ Cash": 0.85,
            "Gross ↔ Min negotiated": 0.78,
            "Cash ↔ Min negotiated": 0.83,
        }
        pivot["Wang 2023"] = pivot.index.map(wang_ref)

        st.dataframe(
            pivot.style.format("{:.3f}", na_rep="—"),
            use_container_width=True,
        )

    # ── Per-hospital distributions ─────────────────────────────────
    st.markdown("### Distribution of within-hospital correlations")

    hosp = query(f"""
        SELECT ccn, state, n_codes, median_cash_discount, discounter,
               r_gross_cash, r_gross_negmin, r_cash_negmin
        FROM '{WANG_HOSP_PQ}'
    """)

    segment_filter = st.radio(
        "Hospital segment",
        ["All", "Discounters (≥5%)", "Non-discounters"],
        horizontal=True,
    )
    if segment_filter == "Discounters (≥5%)":
        hosp = hosp[hosp["discounter"] == True]
    elif segment_filter == "Non-discounters":
        hosp = hosp[hosp["discounter"] == False]

    # Box plots of correlation distributions
    pairs = [
        ("r_gross_cash", "Gross ↔ Cash", "#0d9488"),
        ("r_gross_negmin", "Gross ↔ Neg min", "#d97706"),
        ("r_cash_negmin", "Cash ↔ Neg min", "#6366f1"),
    ]

    fig = go.Figure()
    for col, label, color in pairs:
        for state in ["CA", "IN"]:
            vals = hosp[hosp["state"] == state][col].dropna()
            if len(vals) > 0:
                fig.add_trace(go.Box(
                    y=vals,
                    name=f"{state} {label}",
                    marker_color=color,
                    opacity=1.0 if state == "CA" else 0.5,
                    boxmean=True,
                ))

    fig.update_layout(
        height=500,
        yaxis_title="Pearson r (log prices within hospital)",
        yaxis_range=[-0.2, 1.1],
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=30),
        font=dict(family="DM Sans"),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    fig.update_yaxes(gridcolor="#e5e7eb")
    st.plotly_chart(fig, use_container_width=True)

    # ── Cash discount distribution ─────────────────────────────────
    st.markdown("### Cash discount distribution")
    st.caption(
        "Median within-hospital cash discount = (gross − cash) / gross. "
        "Hospitals above the 5% threshold are classified as 'discounters'."
    )

    disc_df = hosp.dropna(subset=["median_cash_discount"]).copy()
    disc_df["discount_pct"] = disc_df["median_cash_discount"] * 100

    fig2 = px.histogram(
        disc_df,
        x="discount_pct",
        color="state",
        nbins=40,
        barmode="overlay",
        color_discrete_map={"CA": "#0d9488", "IN": "#d97706"},
        opacity=0.7,
        labels={"discount_pct": "Cash discount (%)", "state": "State"},
    )
    fig2.add_vline(x=5, line_dash="dash", line_color="#6b7280",
                   annotation_text="5% threshold")
    fig2.update_layout(
        height=400,
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans"),
    )
    fig2.update_xaxes(gridcolor="#e5e7eb")
    fig2.update_yaxes(gridcolor="#e5e7eb", title_text="# Hospitals")
    st.plotly_chart(fig2, use_container_width=True)

    # ── Discounter prevalence ──────────────────────────────────────
    st.markdown("### Discounter prevalence by state")
    disc_stats = disc_df.groupby("state").agg(
        total=("ccn", "count"),
        discounters=("discounter", "sum"),
        median_discount=("median_cash_discount", "median"),
    ).reset_index()
    disc_stats["pct"] = (disc_stats["discounters"] / disc_stats["total"] * 100).round(1)
    disc_stats["median_discount"] = (disc_stats["median_discount"] * 100).round(1)
    disc_stats = disc_stats.rename(columns={
        "state": "State", "total": "Hospitals",
        "discounters": "Discounters", "pct": "% discounters",
        "median_discount": "Median discount (%)",
    })
    st.dataframe(disc_stats, use_container_width=True, hide_index=True)
