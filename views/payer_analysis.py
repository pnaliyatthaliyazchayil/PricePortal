"""Payer Analysis — negotiated rate comparison across payers."""
import pandas as pd
import streamlit as st
import plotly.express as px
from views.db import query, PAYER_PQ


def render():
    st.markdown("# 💰 Payer Analysis")
    st.markdown(
        "Comparison of negotiated-rate-to-Medicare ratios across insurance "
        "payers, by state. Payers with ≥100 hospital×code pairs shown."
    )

    payer = query(f"""
        SELECT * FROM '{PAYER_PQ}'
        ORDER BY state, p50_neg_ratio
    """)

    if payer.empty:
        st.warning("No payer data available.")
        return

    # ── State tabs ─────────────────────────────────────────────────
    state_filter = st.radio("State", ["CA", "IN", "Both"], horizontal=True)

    if state_filter != "Both":
        plot_df = payer[payer["state"] == state_filter].copy()
    else:
        plot_df = payer.copy()

    # ── Controls ───────────────────────────────────────────────────
    col_n, col_top = st.columns([1, 1])
    with col_n:
        min_pairs = st.slider(
            "Minimum hospital×code pairs",
            100, 10000, 500, step=100,
        )
    with col_top:
        top_n = st.slider("Show top N payers", 10, 50, 25)

    filtered = plot_df[plot_df["n_pairs"] >= min_pairs].copy()

    if filtered.empty:
        st.warning("No payers meet the minimum pairs threshold.")
        return

    # Take top N by volume within each state
    parts = []
    for state in filtered["state"].unique():
        sub = filtered[filtered["state"] == state].nlargest(top_n, "n_pairs")
        parts.append(sub)
    top = pd.concat(parts, ignore_index=True)
    top = top.sort_values(["state", "p50_neg_ratio"])

    # ── Summary metrics ────────────────────────────────────────────
    m1, m2, m3 = st.columns(3)
    m1.metric("Payers shown", f"{len(top)}")
    m2.metric("Median ratio (across payers)", f"{top.p50_neg_ratio.median():.2f}×")
    m3.metric("Range", f"{top.p50_neg_ratio.min():.2f}× – {top.p50_neg_ratio.max():.2f}×")

    # ── Horizontal bar chart ───────────────────────────────────────
    st.markdown("### Median negotiated ÷ Medicare ratio by payer")

    fig = px.bar(
        top,
        x="p50_neg_ratio",
        y="payer_name",
        color="state",
        orientation="h",
        ccolor_discrete_map={"CA": "#0d9488", "IN": "#d97706"},
        hover_data=["n_pairs", "p25_neg_ratio", "p75_neg_ratio"],
        labels={
            "p50_neg_ratio": "Median neg ÷ Medicare",
            "payer_name": "Payer",
            "state": "State",
            "n_pairs": "# Pairs",
        },
    )
    fig.add_vline(x=1.0, line_dash="dash", line_color="#6b7280",
                  annotation_text="Medicare = 1.0×")
    fig.update_layout(
        height=max(400, len(top) * 22),
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, t=30),
        yaxis=dict(categoryorder="total ascending"),
        font=dict(family="DM Sans"),
    )
    fig.update_xaxes(gridcolor="#e5e7eb")
    st.plotly_chart(fig, use_container_width=True)

    # ── IQR chart ──────────────────────────────────────────────────
    st.markdown("### Negotiated ratio spread (25th–75th percentile)")
    st.caption("Wider bars indicate more price variation for that payer.")

    # Sort by median
    top_sorted = top.sort_values("p50_neg_ratio")

    fig2 = px.bar(
        top_sorted,
        x="payer_name",
        y=[top_sorted["p75_neg_ratio"] - top_sorted["p25_neg_ratio"]],
        base=top_sorted["p25_neg_ratio"],
        color="state",
        color_discrete_map={"CA": "#2563eb", "IN": "#dc2626"},
        labels={"payer_name": "Payer", "value": "Ratio range"},
    )
    fig2.add_hline(y=1.0, line_dash="dash", line_color="#6b7280")
    fig2.update_layout(
        height=400,
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis_tickangle=-45,
        showlegend=True,
        font=dict(family="DM Sans"),
    )
    fig2.update_xaxes(gridcolor="#e5e7eb")
    fig2.update_yaxes(gridcolor="#e5e7eb", title_text="Neg ÷ Medicare ratio")
    st.plotly_chart(fig2, use_container_width=True)

    # ── Data table ─────────────────────────────────────────────────
    with st.expander("Show full payer data table"):
        display = filtered.sort_values(
            ["state", "n_pairs"], ascending=[True, False]
        ).copy()
        display = display.rename(columns={
            "state": "State",
            "payer_name": "Payer",
            "n_pairs": "# Pairs",
            "p50_neg_ratio": "Median ratio",
            "p25_neg_ratio": "25th %ile",
            "p75_neg_ratio": "75th %ile",
        })
        st.dataframe(
            display.style.format({
                "# Pairs": "{:,.0f}",
                "Median ratio": "{:.3f}×",
                "25th %ile": "{:.3f}×",
                "75th %ile": "{:.3f}×",
            }),
            use_container_width=True,
            hide_index=True,
        )
