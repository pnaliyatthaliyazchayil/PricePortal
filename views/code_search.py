"""CPT / Code Search — compare prices for a procedure across hospitals."""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from views.db import query, get_con, CROSSWALK_PQ


# Common target CPT codes for quick access
TARGET_CODES = {
    "99281": "ED visit level 1",
    "99282": "ED visit level 2",
    "99283": "ED visit level 3",
    "99284": "ED visit level 4",
    "99285": "ED visit level 5",
    "99291": "Critical care (first hour)",
    "99292": "Critical care (add'l 30 min)",
    "59400": "Vaginal delivery (global)",
    "59409": "Vaginal delivery only",
    "59410": "Vaginal delivery + postpartum",
    "59510": "C-section (global)",
    "59514": "C-section only",
    "59515": "C-section + postpartum",
}


def render():
    st.markdown("# 🔍 CPT / Code Search")
    st.markdown(
        "Search for a CPT or HCPCS code to compare prices across hospitals."
    )

    # ── Code selection ─────────────────────────────────────────────
    col_quick, col_custom = st.columns([2, 2])

    with col_quick:
        quick_pick = st.selectbox(
            "Common procedures",
            [""] + [f"{k} — {v}" for k, v in TARGET_CODES.items()],
            index=0,
        )

    with col_custom:
        custom_code = st.text_input(
            "Or enter a CPT/HCPCS code",
            placeholder="e.g., 99285",
        )

    # Determine which code to use
    if custom_code.strip():
        code = custom_code.strip().upper()
    elif quick_pick:
        code = quick_pick.split(" — ")[0]
    else:
        st.info("Select a common procedure or enter a code above.")
        return

    # ── State filter ───────────────────────────────────────────────
    state_filter = st.radio(
        "State", ["Both", "CA", "IN"], horizontal=True
    )
    state_clause = ""
    if state_filter != "Both":
        state_clause = f"AND r.state = '{state_filter}'"

    # ── Query ──────────────────────────────────────────────────────
    df = query(f"""
        SELECT r.ccn, x.name, x.city, r.state, x.county,
               x.hospital_type, x.ownership,
               r.gross, r.cash, r.neg_min, r.neg_median,
               r.medicare_allowable, r.gross_ratio, r.cash_ratio,
               r.neg_min_ratio, r.neg_median_ratio, r.neg_n_payers
        FROM ratios r
        JOIN '{CROSSWALK_PQ}' x ON r.ccn = x.ccn
        WHERE r.code = '{code}' {state_clause}
        ORDER BY r.gross_ratio DESC NULLS LAST
    """)

    if df.empty:
        st.warning(f"No hospitals found with code **{code}**.")
        return

    # ── Summary metrics ────────────────────────────────────────────
    medicare = df["medicare_allowable"].iloc[0]
    st.markdown(f"### Code {code}")
    st.caption(
        f"Medicare allowable: **${medicare:,.2f}**  ·  "
        f"**{len(df)}** hospitals report this code"
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        "Median gross",
        f"${df.gross.median():,.0f}" if df.gross.notna().any() else "—",
        f"{df.gross_ratio.median():.1f}× Medicare" if df.gross_ratio.notna().any() else None,
    )
    m2.metric(
        "Median cash",
        f"${df.cash.median():,.0f}" if df.cash.notna().any() else "—",
        f"{df.cash_ratio.median():.1f}× Medicare" if df.cash_ratio.notna().any() else None,
    )
    m3.metric(
        "Median neg (min)",
        f"${df.neg_min.median():,.0f}" if df.neg_min.notna().any() else "—",
        f"{df.neg_min_ratio.median():.1f}× Medicare" if df.neg_min_ratio.notna().any() else None,
    )
    m4.metric(
        "Price range (gross)",
        f"${df.gross.min():,.0f} – ${df.gross.max():,.0f}" if df.gross.notna().any() else "—",
    )

    # ── Distribution chart ─────────────────────────────────────────
    st.markdown("### Price distribution by state")

    fig = go.Figure()
    colors = {"CA": "#2563eb", "IN": "#dc2626"}

    for state in ["CA", "IN"]:
        if state_filter != "Both" and state != state_filter:
            continue
        sub = df[df["state"] == state]
        if sub.gross.notna().any():
            fig.add_trace(go.Box(
                y=sub["gross"].dropna(),
                name=f"{state} Gross",
                marker_color=colors[state],
                boxmean=True,
            ))
        if sub.cash.notna().any():
            fig.add_trace(go.Box(
                y=sub["cash"].dropna(),
                name=f"{state} Cash",
                marker_color=colors[state],
                opacity=0.6,
                boxmean=True,
            ))
        if sub.neg_min.notna().any():
            fig.add_trace(go.Box(
                y=sub["neg_min"].dropna(),
                name=f"{state} Neg min",
                marker_color=colors[state],
                opacity=0.3,
                boxmean=True,
            ))

    fig.add_hline(y=medicare, line_dash="dash", line_color="#6b7280",
                  annotation_text=f"Medicare ${medicare:,.0f}")
    fig.update_layout(
        height=450,
        yaxis_title="Price ($)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=30),
        font=dict(family="DM Sans"),
    )
    fig.update_yaxes(gridcolor="#e5e7eb")
    st.plotly_chart(fig, use_container_width=True)

    # ── Scatter: gross vs negotiated ───────────────────────────────
    scatter_df = df.dropna(subset=["gross", "neg_min"])
    if len(scatter_df) > 5:
        st.markdown("### Gross charge vs minimum negotiated rate")
        fig2 = px.scatter(
            scatter_df,
            x="gross", y="neg_min",
            color="state",
            hover_data=["name", "city"],
            color_discrete_map=colors,
            opacity=0.6,
        )
        # 45-degree line
        max_val = max(scatter_df.gross.max(), scatter_df.neg_min.max())
        fig2.add_trace(go.Scatter(
            x=[0, max_val], y=[0, max_val],
            mode="lines", line=dict(dash="dash", color="#9ca3af"),
            name="Equal", showlegend=False,
        ))
        fig2.update_layout(
            height=450,
            xaxis_title="Gross charge ($)",
            yaxis_title="Min negotiated ($)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="DM Sans"),
        )
        fig2.update_xaxes(gridcolor="#e5e7eb")
        fig2.update_yaxes(gridcolor="#e5e7eb")
        st.plotly_chart(fig2, use_container_width=True)

    # ── Hospital table ─────────────────────────────────────────────
    st.markdown("### Hospital-level detail")

    display = df[[
        "name", "city", "state", "gross", "cash", "neg_min",
        "neg_median", "medicare_allowable", "gross_ratio",
        "cash_ratio", "neg_min_ratio", "neg_n_payers"
    ]].copy()
    display = display.rename(columns={
        "name": "Hospital",
        "city": "City",
        "state": "State",
        "gross": "Gross ($)",
        "cash": "Cash ($)",
        "neg_min": "Neg min ($)",
        "neg_median": "Neg med ($)",
        "medicare_allowable": "Medicare ($)",
        "gross_ratio": "Gross ratio",
        "cash_ratio": "Cash ratio",
        "neg_min_ratio": "Neg min ratio",
        "neg_n_payers": "# Payers",
    })
    st.dataframe(
        display.style.format({
            "Gross ($)": "${:,.0f}",
            "Cash ($)": "${:,.0f}",
            "Neg min ($)": "${:,.0f}",
            "Neg med ($)": "${:,.0f}",
            "Medicare ($)": "${:,.2f}",
            "Gross ratio": "{:.2f}×",
            "Cash ratio": "{:.2f}×",
            "Neg min ratio": "{:.2f}×",
            "# Payers": "{:.0f}",
        }, na_rep="—"),
        use_container_width=True,
        hide_index=True,
        height=400,
    )
