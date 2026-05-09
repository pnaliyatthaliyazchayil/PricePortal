"""Overview page — headline stats + state comparison."""

import streamlit as st
import plotly.graph_objects as go
from views.db import query, get_con, RATIOS_SUM_PQ, COMPLIANCE_PQ, CROSSWALK_PQ

def render():
    st.write("DEBUG: render() called")
    st.write("DEBUG: about to query COMPLIANCE_PQ")
    comp = query(f"SELECT * FROM '{COMPLIANCE_PQ}'")
    st.write("DEBUG: query returned, rows:", len(comp))
    st.markdown("# Hospital Price Transparency Explorer")
    st.markdown(
        "Comparing **chargemaster**, **cash**, **negotiated**, and "
        "**Medicare-allowable** prices across **528 hospitals** in "
        "California and Indiana."
    )

    # ── Headline metrics ───────────────────────────────────────────
    comp = query(f"SELECT * FROM '{COMPLIANCE_PQ}'")
    ca = comp[comp["state"] == "CA"].iloc[0]
    in_ = comp[comp["state"] == "IN"].iloc[0]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total hospitals", f"{int(ca.n_universe + in_.n_universe)}")
    col2.metric("With gross prices", f"{int(ca.n_gross + in_.n_gross)}")
    col3.metric("With negotiated", f"{int(ca.n_neg + in_.n_neg)}")

    from views.db import RATIOS_PQ_PARTS
    total_rows = sum(
    query(f"SELECT COUNT(*) as n FROM '{p}'").iloc[0].n
    for p in RATIOS_PQ_PARTS
    )
    col4.metric("Hospital × code pairs", f"{int(total_rows):,}")

    # ── State compliance bars ──────────────────────────────────────
    st.markdown("### Compliance with CMS §180 MRF rule")
    c1, c2 = st.columns(2)

    with c1:
        st.markdown(f"**California** — {int(ca.n_universe)} hospitals")
        st.progress(ca.pct_gross / 100, text=f"Gross prices: {ca.pct_gross:.1f}%")
        st.progress(ca.pct_neg / 100, text=f"Negotiated rates: {ca.pct_neg:.1f}%")

    with c2:
        st.markdown(f"**Indiana** — {int(in_.n_universe)} hospitals")
        st.progress(in_.pct_gross / 100, text=f"Gross prices: {in_.pct_gross:.1f}%")
        st.progress(in_.pct_neg / 100, text=f"Negotiated rates: {in_.pct_neg:.1f}%")

    # ── Price-to-Medicare ratios by state ──────────────────────────
    st.markdown("### Median price-to-Medicare ratio by state")
    st.caption("How many times Medicare's rate does each hospital charge?")

    summary = query(f"""
        SELECT * FROM '{RATIOS_SUM_PQ}'
        ORDER BY state, price_type
    """)

    price_order = ["gross", "cash", "neg_min", "neg_median"]
    price_labels = {
        "gross": "Chargemaster",
        "cash": "Cash / self-pay",
        "neg_min": "Min negotiated",
        "neg_median": "Median negotiated",
    }
    colors = {"CA": "#0d9488", "IN": "#d97706"}

    fig = go.Figure()
    for state in ["CA", "IN"]:
        sub = summary[summary["state"] == state].set_index("price_type")
        sub = sub.reindex(price_order)
        fig.add_trace(go.Bar(
            name=state,
            x=[price_labels[p] for p in price_order],
            y=sub["p50"].values,
            marker_color=colors[state],
            text=[f"{v:.2f}×" for v in sub["p50"].values],
            textposition="outside",
        ))

    fig.add_hline(y=1.0, line_dash="dash", line_color="#6b7280",
                  annotation_text="Medicare = 1.0×",
                  annotation_position="bottom right")
    fig.update_layout(
        barmode="group",
        height=420,
        margin=dict(t=40, b=60),
        yaxis_title="Median ratio to Medicare",
        legend=dict(orientation="h", yanchor="bottom", y=1.02,
                    xanchor="right", x=1),
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="DM Sans"),
    )
    fig.update_yaxes(gridcolor="#e5e7eb")
    st.plotly_chart(fig, use_container_width=True)

    # ── Ratio distribution table ───────────────────────────────────
    st.markdown("### Full distribution")
    display = summary.copy()
    display["price_type"] = display["price_type"].map(price_labels)
    display = display.rename(columns={
        "state": "State", "price_type": "Price type",
        "n_pairs": "N pairs", "p25": "25th %ile",
        "p50": "Median", "p75": "75th %ile", "mean": "Mean",
    })
    st.dataframe(
        display.style.format({
            "N pairs": "{:,.0f}",
            "25th %ile": "{:.2f}×",
            "Median": "{:.2f}×",
            "75th %ile": "{:.2f}×",
            "Mean": "{:.2f}×",
        }),
        use_container_width=True,
        hide_index=True,
    )

    # ── Key findings callout ───────────────────────────────────────
    st.markdown("---")
    f1, f2, f3 = st.columns(3)
    with f1:
        st.info(
            "**CA charges ~2× IN relative to Medicare**\n\n"
            "Median gross ratio: CA 3.87× vs IN 1.81×. "
            "The gap persists across all price types."
        )
    with f2:
        st.info(
            "**IN cash sits *below* Medicare**\n\n"
            "IN median cash ratio is 0.76× — hospitals price "
            "cash below the Medicare benchmark, consistent with "
            "HEA 1004 repricing."
        )
    with f3:
        st.info(
            "**Cash is a flat discount off gross**\n\n"
            "Within-hospital gross↔cash correlation is r=1.0 "
            "even among real discounters — a departure from "
            "Wang 2023."
        )
