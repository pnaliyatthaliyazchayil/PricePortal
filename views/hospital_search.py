"""Hospital Search — look up any hospital and see its price profile."""

import streamlit as st
import plotly.graph_objects as go
from views.db import query, get_con, CROSSWALK_PQ, WANG_HOSP_PQ


def render():
    st.markdown("# 🏥 Hospital Search")
    st.markdown("Search by name, city, or CCN to see a hospital's price profile.")

    # ── Search controls ────────────────────────────────────────────
    col_state, col_search = st.columns([1, 3])
    with col_state:
        state_filter = st.selectbox("State", ["All", "CA", "IN"])
    with col_search:
        search_term = st.text_input(
            "Search hospital name or city",
            placeholder="e.g., Kaiser, Stanford, Indianapolis..."
        )

    # ── Hospital list ──────────────────────────────────────────────
    where = []
    if state_filter != "All":
        where.append(f"state = '{state_filter}'")
    if search_term:
        safe = search_term.replace("'", "''")
        where.append(
            f"(LOWER(name) LIKE '%{safe.lower()}%' "
            f"OR LOWER(city) LIKE '%{safe.lower()}%' "
            f"OR ccn = '{safe}')"
        )

    where_clause = "WHERE " + " AND ".join(where) if where else ""

    hospitals = query(f"""
        SELECT ccn, name, city, state, zip, county,
               hospital_type, ownership, has_ed
        FROM '{CROSSWALK_PQ}'
        {where_clause}
        ORDER BY state, name
        LIMIT 200
    """)

    if hospitals.empty:
        st.warning("No hospitals found. Try a broader search.")
        return

    st.markdown(f"**{len(hospitals)}** hospitals found")

    # Hospital selector
    hospitals["label"] = (
        hospitals["name"] + " — " + hospitals["city"]
        + ", " + hospitals["state"]
    )
    selected_label = st.selectbox(
        "Select a hospital",
        hospitals["label"].tolist(),
        label_visibility="collapsed",
    )
    selected = hospitals[hospitals["label"] == selected_label].iloc[0]

    # ── Hospital detail card ───────────────────────────────────────
    st.markdown("---")
    st.markdown(f"## {selected['name']}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("CCN", selected.ccn)
    c2.metric("Location", f"{selected.city}, {selected.state} {selected.zip}")
    c3.metric("Type", selected.hospital_type)
    c4.metric("Emergency dept", selected.has_ed)

    st.caption(f"**Ownership:** {selected.ownership}  ·  **County:** {selected.county}")

    # ── Price ratios for this hospital ─────────────────────────────
    from views.db import RATIOS_PQ_PARTS
    ratios = query(f"""
        SELECT code, gross, cash, neg_min, neg_median,
               medicare_allowable, gross_ratio, cash_ratio,
               neg_min_ratio, neg_median_ratio, neg_n_payers
        FROM ({' UNION ALL '.join(f"SELECT * FROM '{p}'" for p in RATIOS_PQ_PARTS)})
        WHERE ccn = '{selected.ccn}'
        ORDER BY gross_ratio DESC NULLS LAST
    """)

    if ratios.empty:
        st.warning("No price data available for this hospital.")
        return

    # Summary metrics
    st.markdown("### Price summary")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        "Median gross ratio",
        f"{ratios.gross_ratio.median():.2f}×" if ratios.gross_ratio.notna().any() else "N/A",
    )
    m2.metric(
        "Median cash ratio",
        f"{ratios.cash_ratio.median():.2f}×" if ratios.cash_ratio.notna().any() else "N/A",
    )
    m3.metric(
        "Median neg (min) ratio",
        f"{ratios.neg_min_ratio.median():.2f}×" if ratios.neg_min_ratio.notna().any() else "N/A",
    )
    m4.metric("CPT/HCPCS codes", f"{len(ratios):,}")

    # Wang correlation for this hospital
    wang = query(f"""
        SELECT median_cash_discount, discounter,
               r_gross_cash, r_gross_negmin, r_cash_negmin
        FROM '{WANG_HOSP_PQ}'
        WHERE ccn = '{selected.ccn}'
    """)
    if not wang.empty:
        w = wang.iloc[0]
        st.markdown("### Within-hospital price correlations")
        wc1, wc2, wc3, wc4 = st.columns(4)
        wc1.metric(
            "Cash discount",
            f"{w.median_cash_discount:.0%}" if w.median_cash_discount == w.median_cash_discount else "N/A"
        )
        wc2.metric("Gross ↔ Cash r", f"{w.r_gross_cash:.3f}" if w.r_gross_cash == w.r_gross_cash else "N/A")
        wc3.metric("Gross ↔ Neg min r", f"{w.r_gross_negmin:.3f}" if w.r_gross_negmin == w.r_gross_negmin else "N/A")
        wc4.metric("Cash ↔ Neg min r", f"{w.r_cash_negmin:.3f}" if w.r_cash_negmin == w.r_cash_negmin else "N/A")

    # ── Four-price-type chart ──────────────────────────────────────
    st.markdown("### Price distribution across codes")

    # Box plot of the four ratio types
    fig = go.Figure()
    ratio_cols = [
        ("gross_ratio", "Chargemaster", "#ef4444"),
        ("cash_ratio", "Cash", "#f59e0b"),
        ("neg_min_ratio", "Min negotiated", "#10b981"),
        ("neg_median_ratio", "Median negotiated", "#3b82f6"),
    ]
    for col, label, color in ratio_cols:
        vals = ratios[col].dropna()
        # Cap at 99th percentile for display
        if len(vals) > 10:
            cap = vals.quantile(0.99)
            vals = vals[vals <= cap]
        if len(vals) > 0:
            fig.add_trace(go.Box(
                y=vals, name=label, marker_color=color,
                boxmean=True,
            ))

    fig.add_hline(y=1.0, line_dash="dash", line_color="#6b7280",
                  annotation_text="Medicare = 1.0×")
    fig.update_layout(
        height=400,
        yaxis_title="Ratio to Medicare",
        showlegend=False,
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=30),
        font=dict(family="DM Sans"),
    )
    fig.update_yaxes(gridcolor="#e5e7eb")
    st.plotly_chart(fig, use_container_width=True)

    # ── Code-level table ───────────────────────────────────────────
    st.markdown("### All codes for this hospital")

    display = ratios.copy()
    display = display.rename(columns={
        "code": "CPT/HCPCS",
        "gross": "Gross ($)",
        "cash": "Cash ($)",
        "neg_min": "Neg min ($)",
        "neg_median": "Neg median ($)",
        "medicare_allowable": "Medicare ($)",
        "gross_ratio": "Gross ratio",
        "cash_ratio": "Cash ratio",
        "neg_min_ratio": "Neg min ratio",
        "neg_median_ratio": "Neg med ratio",
        "neg_n_payers": "# Payers",
    })
    st.dataframe(
        display.style.format({
            "Gross ($)": "${:,.0f}",
            "Cash ($)": "${:,.0f}",
            "Neg min ($)": "${:,.0f}",
            "Neg median ($)": "${:,.0f}",
            "Medicare ($)": "${:,.2f}",
            "Gross ratio": "{:.2f}×",
            "Cash ratio": "{:.2f}×",
            "Neg min ratio": "{:.2f}×",
            "Neg med ratio": "{:.2f}×",
            "# Payers": "{:.0f}",
        }, na_rep="—"),
        use_container_width=True,
        hide_index=True,
        height=400,
    )
