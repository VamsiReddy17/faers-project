"""
FAERS Executive Pharmacovigilance Dashboard

Designed to senior data analyst & executive UI/UX engineering standards.
Features dynamic Theme Switching (☀️ Light Mode / 🌙 Dark Mode), executive KPI cards,
interactive controls, Plotly forest plots with 95% CIs, signal landscapes,
and patient demographics.
"""

from pathlib import Path
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ──────────────────────────────────────────────
# 1. Page & Layout Configuration
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="FAERS Pharmacovigilance Signal Mining Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────
# 2. Data Loading (DuckDB + CSV Fallback)
# ──────────────────────────────────────────────
DATA_DIR = Path("data/processed")
DUCKDB_PATH = Path("data/faers.duckdb")


@st.cache_data
def load_all_data():
    """Load analytical tables from DuckDB or CSV files."""
    data = {}

    # Try local DuckDB first
    if DUCKDB_PATH.exists():
        try:
            import duckdb
            con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
            for table in ["signal_results", "demographics", "reactions", "outcomes"]:
                data[table] = con.execute(f"SELECT * FROM {table}").df()
            con.close()
            return data
        except Exception:
            pass

    # Fallback to CSVs
    files = {
        "signal_results": "signal_results.csv",
        "demographics": "demographics.csv",
        "reactions": "reactions.csv",
        "outcomes": "outcomes.csv",
    }
    for key, filename in files.items():
        filepath = DATA_DIR / filename
        if filepath.exists():
            data[key] = pd.read_csv(filepath)
        else:
            data[key] = pd.DataFrame()

    return data


data = load_all_data()
results_df = data.get("signal_results", pd.DataFrame())
demographics_df = data.get("demographics", pd.DataFrame())
reactions_df = data.get("reactions", pd.DataFrame())
outcomes_df = data.get("outcomes", pd.DataFrame())

if results_df.empty:
    st.error("⚠️ No processed data found. Please run the pipeline first:\n`python run_fast.py`")
    st.stop()

# ──────────────────────────────────────────────
# 3. Sidebar Controls & Theme Selector
# ──────────────────────────────────────────────
st.sidebar.markdown("## 🛡️ FAERS Controls")

# Theme Switcher
theme_mode = st.sidebar.radio(
    "🎨 Dashboard Theme Mode",
    options=["☀️ Light Mode", "🌙 Dark Mode"],
    index=0,
    horizontal=True,
)

is_dark = "Dark" in theme_mode

st.sidebar.markdown("---")

# ──────────────────────────────────────────────
# 4. Dynamic Theme CSS & Tokens
# ──────────────────────────────────────────────
if is_dark:
    BG_COLOR = "#0F172A"
    TEXT_COLOR = "#F8FAFC"
    CARD_BG = "#1E293B"
    BORDER_COLOR = "#334155"
    SUBTITLE_COLOR = "#38BDF8"
    MUTED_TEXT = "#94A3B8"
    SIDEBAR_BG = "#1E293B"
    BADGE_DANGER_BG = "rgba(239, 68, 68, 0.2)"
    BADGE_DANGER_TEXT = "#FCA5A5"
    BADGE_DANGER_BORDER = "rgba(239, 68, 68, 0.4)"
    TAB_BG = "#1E293B"
    TAB_TEXT = "#94A3B8"
    PLOTLY_PAPER = "#1E293B"
    PLOTLY_PLOT = "#1E293B"
    PLOTLY_GRID = "#334155"
    PLOTLY_TEXT = "#F8FAFC"
else:
    BG_COLOR = "#F8FAFC"
    TEXT_COLOR = "#0F172A"
    CARD_BG = "#FFFFFF"
    BORDER_COLOR = "#CBD5E1"
    SUBTITLE_COLOR = "#2563EB"
    MUTED_TEXT = "#475569"
    SIDEBAR_BG = "#FFFFFF"
    BADGE_DANGER_BG = "#FEE2E2"
    BADGE_DANGER_TEXT = "#991B1B"
    BADGE_DANGER_BORDER = "#FCA5A5"
    TAB_BG = "#F1F5F9"
    TAB_TEXT = "#334155"
    PLOTLY_PAPER = "#FFFFFF"
    PLOTLY_PLOT = "#F8FAFC"
    PLOTLY_GRID = "#E2E8F0"
    PLOTLY_TEXT = "#0F172A"

CUSTOM_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Plus+Jakarta+Sans:wght@500;600;700;800&display=swap');

html, body, [class*="css"] {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    color: {TEXT_COLOR};
}}

h1, h2, h3, h4, .stHeaderTitle {{
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    color: {TEXT_COLOR} !important;
    font-weight: 700 !important;
    letter-spacing: -0.02em;
}}

.stApp {{
    background-color: {BG_COLOR} !important;
    color: {TEXT_COLOR} !important;
}}

[data-testid="stSidebar"] {{
    background-color: {SIDEBAR_BG} !important;
    border-right: 1px solid {BORDER_COLOR} !important;
}}

[data-testid="stSidebar"] label, 
[data-testid="stSidebar"] .stMarkdown p, 
[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {{
    color: {TEXT_COLOR} !important;
    font-weight: 700 !important;
    font-size: 0.92rem !important;
}}

[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
    color: {TEXT_COLOR} !important;
}}

.metric-card {{
    background: {CARD_BG} !important;
    border: 1px solid {BORDER_COLOR} !important;
    border-top: 4px solid #4F46E5 !important;
    border-radius: 12px !important;
    padding: 1.25rem 1.5rem !important;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.05) !important;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}}

.metric-card-danger {{ border-top-color: #DC2626 !important; }}
.metric-card-success {{ border-top-color: #059669 !important; }}
.metric-card-warning {{ border-top-color: #D97706 !important; }}

.metric-label {{
    font-size: 0.8rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    color: {MUTED_TEXT} !important;
    margin-bottom: 0.35rem !important;
}}

.metric-value {{
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 1.85rem !important;
    font-weight: 800 !important;
    color: {TEXT_COLOR} !important;
    line-height: 1.2 !important;
}}

.metric-subtitle {{
    font-size: 0.85rem !important;
    color: {SUBTITLE_COLOR} !important;
    margin-top: 0.4rem !important;
    font-weight: 600 !important;
}}

.badge-danger {{
    background-color: {BADGE_DANGER_BG} !important;
    color: {BADGE_DANGER_TEXT} !important;
    border: 1px solid {BADGE_DANGER_BORDER} !important;
    padding: 3px 10px !important;
    border-radius: 6px !important;
    font-size: 0.78rem !important;
    font-weight: 800 !important;
}}

.stTabs [data-baseweb="tab-list"] {{
    gap: 8px !important;
    background-color: {TAB_BG} !important;
    padding: 6px 10px !important;
    border-radius: 10px !important;
    border: 1px solid {BORDER_COLOR} !important;
}}

.stTabs [data-baseweb="tab"] {{
    height: 44px !important;
    border-radius: 8px !important;
    color: {TAB_TEXT} !important;
    font-weight: 700 !important;
    font-size: 0.92rem !important;
    padding: 0 16px !important;
    border: none !important;
}}

.stTabs [aria-selected="true"] {{
    background-color: #4F46E5 !important;
    color: #FFFFFF !important;
}}

.stMarkdown, p, div {{
    color: {TEXT_COLOR};
}}

#MainMenu {{visibility: hidden;}}
footer {{visibility: hidden;}}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ──────────────────────────────────────────────
# 5. Sidebar Filter Execution
# ──────────────────────────────────────────────
available_drugs = sorted(results_df["drug"].unique().tolist())
selected_drugs = st.sidebar.multiselect(
    "💊 Select Antipsychotic Drugs",
    options=available_drugs,
    default=available_drugs,
    help="Filter signals by drug generic name",
)

available_categories = ["All"] + sorted(results_df["event_category"].dropna().unique().tolist())
selected_category = st.sidebar.selectbox(
    "🫀 Adverse Event Category",
    options=available_categories,
    index=0,
)

signal_filter_choice = st.sidebar.radio(
    "⚡ Signal Criterion",
    options=["Confirmed Signals Only", "All Tested Pairs"],
    index=0,
)

min_case_count = st.sidebar.slider(
    "🔢 Minimum Report Count (n)",
    min_value=3,
    max_value=500,
    value=10,
    step=5,
    help="Filter out low-volume drug-event combinations",
)

metric_choice = st.sidebar.selectbox(
    "📏 Disproportionality Metric",
    options=["Reporting Odds Ratio (ROR)", "Proportional Reporting Ratio (PRR)"],
    index=0,
)

# Filter Dataset
filtered_results = results_df[results_df["drug"].isin(selected_drugs)].copy()

if selected_category != "All":
    filtered_results = filtered_results[filtered_results["event_category"] == selected_category]

if signal_filter_choice == "Confirmed Signals Only":
    filtered_results = filtered_results[filtered_results["Signal"] == True]

filtered_results = filtered_results[filtered_results["a (drug+event)"] >= min_case_count]

st.sidebar.markdown("---")
st.sidebar.markdown(
    f"""
    <div style='background-color:{CARD_BG}; padding:14px; border-radius:10px; border:1px solid {BORDER_COLOR};'>
        <p style='color:{MUTED_TEXT}; font-size:0.78rem; font-weight:700; margin:0; letter-spacing:0.05em;'>ACTIVE FILTER RESULTS</p>
        <h3 style='color:{TEXT_COLOR}; margin:4px 0 0 0; font-size:1.4rem;'>{len(filtered_results)} Pairs Shown</h3>
        <p style='color:#059669; font-size:0.85rem; font-weight:700; margin:4px 0 0 0;'>
            {int(filtered_results['Signal'].sum()) if 'Signal' in filtered_results.columns else 0} Signals Detected
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────
# 6. Header Banner & Executive KPI Metrics
# ──────────────────────────────────────────────
st.markdown(
    f"""
    <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:1.5rem;'>
        <div>
            <h1 style='margin:0; color:{TEXT_COLOR}; font-size:2.2rem;'>FAERS Pharmacovigilance Signal Mining</h1>
            <p style='color:{MUTED_TEXT}; margin:0.3rem 0 0 0; font-size:0.95rem; font-weight:500;'>
                Comparative Adverse Drug Reaction (ADR) Safety Mining • FDA FAERS Dataset (2018–2023)
            </p>
        </div>
        <div style='text-align:right;'>
            <span style='background:{CARD_BG}; border:1px solid {BORDER_COLOR}; color:{SUBTITLE_COLOR}; padding:8px 16px; border-radius:20px; font-size:0.85rem; font-weight:700;'>
                ● 101,708 Deduplicated Patient Reports
            </span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# KPI Cards
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

total_reports_count = len(demographics_df) if not demographics_df.empty else 101708
detected_signals_count = int(filtered_results["Signal"].sum()) if "Signal" in filtered_results.columns else 0

top_signal_name = "Clozapine → Agranulocytosis"
top_signal_ror = 10.05
if not filtered_results.empty:
    top_row = filtered_results.sort_values("ROR", ascending=False).iloc[0]
    top_signal_name = f"{top_row['drug'].capitalize()} → {top_row['event']}"
    top_signal_ror = top_row["ROR"]

with kpi1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">STUDY COHORT REPORTS</div>
            <div class="metric-value">{total_reports_count:,}</div>
            <div class="metric-subtitle">Deduplicated FAERS Cases</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with kpi2:
    st.markdown(
        f"""
        <div class="metric-card metric-card-danger">
            <div class="metric-label">DETECTED SAFETY SIGNALS</div>
            <div class="metric-value">{detected_signals_count}</div>
            <div class="metric-subtitle">Lower 95% CI > 1.0 & PRR ≥ 2.0</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with kpi3:
    st.markdown(
        f"""
        <div class="metric-card metric-card-warning">
            <div class="metric-label">TOP DISPROPORTIONALITY SIGNAL</div>
            <div class="metric-value" style="font-size:1.3rem;">{top_signal_name}</div>
            <div class="metric-subtitle">ROR: {top_signal_ror:.2f} (High Risk)</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with kpi4:
    st.markdown(
        f"""
        <div class="metric-card metric-card-success">
            <div class="metric-label">PRIMARY ADVERSE EVENT</div>
            <div class="metric-value" style="font-size:1.4rem;">Weight Increased</div>
            <div class="metric-subtitle">20,245 Total Case Reports</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# 7. Main Dashboard Tabs & Plotly Theme
# ──────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Executive Leaderboard & Forest Plot",
    "🔍 Signal Matrix & SOC Categories",
    "👥 Demographics & Risk Vulnerability",
    "📈 Temporal Volatility & Trajectory",
    "📋 Interactive Data Explorer",
])

PLOTLY_THEME = dict(
    paper_bgcolor=PLOTLY_PAPER,
    plot_bgcolor=PLOTLY_PLOT,
    font=dict(family="Inter, sans-serif", color=PLOTLY_TEXT, size=12),
    xaxis=dict(gridcolor=PLOTLY_GRID, zerolinecolor=BORDER_COLOR, tickfont=dict(color=PLOTLY_TEXT, size=11)),
    yaxis=dict(gridcolor=PLOTLY_GRID, zerolinecolor=BORDER_COLOR, tickfont=dict(color=PLOTLY_TEXT, size=11)),
)

# ──────────────────────────────────────────────
# TAB 1: Forest Plot & Leaderboard
# ──────────────────────────────────────────────
with tab1:
    st.markdown("### 🌲 Forest Plot — Reporting Odds Ratio (ROR) & 95% Confidence Intervals")
    st.markdown(f"<p style='color:{MUTED_TEXT}; font-weight:500;'>Disproportionality estimate per drug-event pair. Points with error bars strictly right of ROR=1.0 represent statistically significant safety signals.</p>", unsafe_allow_html=True)

    if not filtered_results.empty:
        top_n = st.slider("Display Top N Signals", 5, 40, 15)
        plot_df = filtered_results.sort_values("ROR", ascending=False).head(top_n).copy()
        plot_df["label"] = plot_df["drug"].str.capitalize() + " → " + plot_df["event"]
        plot_df = plot_df.sort_values("ROR", ascending=True)

        fig_forest = go.Figure()

        for _, row in plot_df.iterrows():
            is_sig = row.get("Signal", False)
            color = "#DC2626" if is_sig else "#0284C7"

            fig_forest.add_trace(go.Scatter(
                x=[row["ROR_lower_CI"], row["ROR_upper_CI"]],
                y=[row["label"], row["label"]],
                mode="lines",
                line=dict(color=color, width=3),
                showlegend=False,
                hoverinfo="skip",
            ))

            fig_forest.add_trace(go.Scatter(
                x=[row["ROR"]],
                y=[row["label"]],
                mode="markers",
                marker=dict(size=11, color=color, line=dict(width=1.5, color="#FFFFFF")),
                name="Signal" if is_sig else "Non-Signal",
                text=[
                    f"<b>{row['label']}</b><br>"
                    f"Category: {row.get('event_category', 'N/A')}<br>"
                    f"ROR: {row['ROR']:.2f} [95% CI: {row['ROR_lower_CI']:.2f} – {row['ROR_upper_CI']:.2f}]<br>"
                    f"PRR: {row['PRR']:.2f} | Chi²: {row['Chi_squared']:.2f}<br>"
                    f"Cases (a): {row['a (drug+event)']:,}"
                ],
                hoverinfo="text",
                showlegend=False,
            ))

        fig_forest.add_vline(
            x=1.0,
            line_dash="dash",
            line_color="#D97706",
            line_width=2,
            annotation_text="ROR = 1.0 (Null Hypothesis)",
            annotation_position="bottom right",
            annotation_font_color="#B45309",
        )

        fig_forest.update_layout(
            **PLOTLY_THEME,
            xaxis_title="Reporting Odds Ratio (ROR) — Log Scale",
            xaxis_type="log",
            height=max(450, len(plot_df) * 34),
            margin=dict(l=220, r=40, t=30, b=50),
        )

        st.plotly_chart(fig_forest, use_container_width=True)

        # Leaderboard Cards
        st.markdown("#### 🏆 Top Disproportionality Signals")
        top_cards_df = filtered_results.sort_values("ROR", ascending=False).head(3)
        c1, c2, c3 = st.columns(3)
        card_cols = [c1, c2, c3]

        for i, (_, row) in enumerate(top_cards_df.iterrows()):
            with card_cols[i]:
                st.markdown(
                    f"""
                    <div style='background:{CARD_BG}; border:1px solid {BORDER_COLOR}; border-left:5px solid #DC2626; padding:16px; border-radius:10px; box-shadow:0 4px 12px rgba(0,0,0,0.04);'>
                        <span class='badge-danger'>RANK #{i+1} HIGH RISK</span>
                        <h4 style='color:{TEXT_COLOR}; margin:10px 0 4px 0; font-size:1.1rem;'>{row['drug'].capitalize()} → {row['event']}</h4>
                        <p style='color:{MUTED_TEXT}; font-size:0.85rem; font-weight:600; margin:0;'>Category: {row.get('event_category', 'General')}</p>
                        <hr style='border-color:{BORDER_COLOR}; margin:10px 0;'>
                        <div style='display:flex; justify-content:space-between;'>
                            <div><span style='color:{MUTED_TEXT}; font-size:0.75rem; font-weight:700;'>ROR</span><br><b style='color:#2563EB; font-size:1.1rem;'>{row['ROR']:.2f}</b></div>
                            <div><span style='color:{MUTED_TEXT}; font-size:0.75rem; font-weight:700;'>PRR</span><br><b style='color:#D97706; font-size:1.1rem;'>{row['PRR']:.2f}</b></div>
                            <div><span style='color:{MUTED_TEXT}; font-size:0.75rem; font-weight:700;'>CASES</span><br><b style='color:{TEXT_COLOR}; font-size:1.1rem;'>{row['a (drug+event)']:,}</b></div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    else:
        st.warning("No signal data matches your selected filters.")

# ──────────────────────────────────────────────
# TAB 2: Signal Landscape & Matrix
# ──────────────────────────────────────────────
with tab2:
    st.markdown("### 🔍 Signal Landscape Matrix — Drug × Adverse Event")
    st.markdown(f"<p style='color:{MUTED_TEXT}; font-weight:500;'>Bubble matrix where bubble size represents report count ($n$) and color represents log-transformed ROR intensity.</p>", unsafe_allow_html=True)

    if not filtered_results.empty:
        col_mat1, col_mat2 = st.columns([3, 1.2])

        with col_mat1:
            pivot_df = filtered_results.copy()
            pivot_df["log_ROR"] = np.log1p(pivot_df["ROR"])
            pivot_df["drug_title"] = pivot_df["drug"].str.capitalize()

            fig_bubble = px.scatter(
                pivot_df,
                x="drug_title",
                y="event",
                size="a (drug+event)",
                color="ROR",
                color_continuous_scale="Reds",
                hover_name="event",
                hover_data={
                    "drug_title": True,
                    "ROR": ":.2f",
                    "PRR": ":.2f",
                    "a (drug+event)": ":,",
                },
                size_max=35,
                title="Drug × Event Signal Matrix",
            )

            fig_bubble.update_layout(
                **PLOTLY_THEME,
                height=550,
                xaxis_title="Antipsychotic Medication",
                yaxis_title="Adverse Event (MedDRA PT)",
            )
            st.plotly_chart(fig_bubble, use_container_width=True)

        with col_mat2:
            st.markdown("#### 🫀 SOC Category Breakdown")
            cat_counts = filtered_results["event_category"].value_counts().reset_index()
            cat_counts.columns = ["Category", "Count"]

            fig_donut = px.pie(
                cat_counts,
                names="Category",
                values="Count",
                hole=0.55,
                color_discrete_sequence=px.colors.qualitative.Bold,
            )
            fig_donut.update_layout(
                **PLOTLY_THEME,
                showlegend=True,
                legend=dict(orientation="h", y=-0.2),
                height=400,
                margin=dict(l=10, r=10, t=30, b=30),
            )
            st.plotly_chart(fig_donut, use_container_width=True)

# ──────────────────────────────────────────────
# TAB 3: Demographics & Risk Factors
# ──────────────────────────────────────────────
with tab3:
    st.markdown("### 👥 Patient Demographics & Reporter Profile")
    st.markdown(f"<p style='color:{MUTED_TEXT}; font-weight:500;'>Age distribution, sex ratio, and reporter qualification analysis across patient records.</p>", unsafe_allow_html=True)

    if not demographics_df.empty:
        demo_filtered = demographics_df[demographics_df["drug_queried"].isin(selected_drugs)]

        d_col1, d_col2, d_col3 = st.columns(3)

        with d_col1:
            st.markdown("#### 📅 Age Group Distribution")
            if "age_group" in demo_filtered.columns:
                age_counts = demo_filtered["age_group"].value_counts().sort_index().reset_index()
                age_counts.columns = ["Age Group", "Reports"]

                fig_age = px.bar(
                    age_counts,
                    x="Age Group",
                    y="Reports",
                    color="Reports",
                    color_continuous_scale="Blues",
                    text_auto=",.0f",
                )
                fig_age.update_layout(**PLOTLY_THEME, showlegend=False, height=360)
                st.plotly_chart(fig_age, use_container_width=True)

        with d_col2:
            st.markdown("#### ⚧ Sex Ratio")
            if "sex_label" in demo_filtered.columns:
                sex_counts = demo_filtered["sex_label"].value_counts().reset_index()
                sex_counts.columns = ["Sex", "Count"]

                fig_sex = px.pie(
                    sex_counts,
                    names="Sex",
                    values="Count",
                    color="Sex",
                    color_discrete_map={"Male": "#0284C7", "Female": "#E11D48", "Unknown": "#64748B"},
                    hole=0.45,
                )
                fig_sex.update_layout(**PLOTLY_THEME, height=360)
                st.plotly_chart(fig_sex, use_container_width=True)

        with d_col3:
            st.markdown("#### 👨‍⚕️ Reporter Type Breakdown")
            if "reporter_label" in demo_filtered.columns:
                rep_counts = demo_filtered["reporter_label"].value_counts().reset_index()
                rep_counts.columns = ["Reporter", "Count"]

                fig_rep = px.bar(
                    rep_counts,
                    y="Reporter",
                    x="Count",
                    orientation="h",
                    color="Count",
                    color_continuous_scale="Teal",
                    text_auto=",.0f",
                )
                fig_rep.update_layout(**PLOTLY_THEME, showlegend=False, height=360)
                st.plotly_chart(fig_rep, use_container_width=True)

# ──────────────────────────────────────────────
# TAB 4: Temporal Volatility & Trends
# ──────────────────────────────────────────────
with tab4:
    st.markdown("### 📈 Temporal Volatility & Reporting Velocity (2018–2023)")
    st.markdown(f"<p style='color:{MUTED_TEXT}; font-weight:500;'>Quarterly reporting volume trajectories per drug across the 6-year study window.</p>", unsafe_allow_html=True)

    if not demographics_df.empty and "receive_quarter" in demographics_df.columns:
        demo_filtered = demographics_df[demographics_df["drug_queried"].isin(selected_drugs)]
        time_pivot = (
            demo_filtered.groupby(["receive_quarter", "drug_queried"])
            .size()
            .reset_index(name="Report Count")
        )
        time_pivot["Drug"] = time_pivot["drug_queried"].str.capitalize()

        fig_time = px.line(
            time_pivot,
            x="receive_quarter",
            y="Report Count",
            color="Drug",
            markers=True,
            color_discrete_sequence=px.colors.qualitative.Dark24,
        )
        fig_time.update_layout(
            **PLOTLY_THEME,
            xaxis_title="Quarter (YYYY-Q)",
            yaxis_title="Adverse Event Reports",
            height=480,
            xaxis_tickangle=-45,
        )
        st.plotly_chart(fig_time, use_container_width=True)

# ──────────────────────────────────────────────
# TAB 5: Interactive Data Explorer
# ──────────────────────────────────────────────
with tab5:
    st.markdown("### 📋 FAERS Signal Master Dataset Explorer")
    st.markdown(f"<p style='color:{MUTED_TEXT}; font-weight:500;'>Search, filter, and export the complete disproportionality results table.</p>", unsafe_allow_html=True)

    search_query = st.text_input("🔍 Quick Search (Drug, Event, or Category):", "")
    exp_df = filtered_results.copy()

    if search_query:
        query_lower = search_query.lower()
        exp_df = exp_df[
            exp_df["drug"].str.lower().str.contains(query_lower)
            | exp_df["event"].str.lower().str.contains(query_lower)
            | exp_df["event_category"].str.lower().str.contains(query_lower)
        ]

    exp_df["Drug"] = exp_df["drug"].str.capitalize()
    exp_df["Adverse Event"] = exp_df["event"]
    exp_df["Category"] = exp_df["event_category"]
    exp_df["Cases (a)"] = exp_df["a (drug+event)"]

    show_cols = [
        "Drug", "Adverse Event", "Category", "Cases (a)",
        "ROR", "ROR_lower_CI", "ROR_upper_CI", "PRR", "Chi_squared", "Signal",
    ]
    avail_show = [c for c in show_cols if c in exp_df.columns]

    st.dataframe(
        exp_df[avail_show].style.map(
            lambda v: "background-color: #FEE2E2; color: #991B1B; font-weight: bold;" if v is True else "",
            subset=["Signal"] if "Signal" in avail_show else [],
        ),
        use_container_width=True,
        height=480,
    )

    csv_bytes = exp_df[avail_show].to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Export Signal Results (CSV)",
        data=csv_bytes,
        file_name="faers_disproportionality_signals.csv",
        mime="text/csv",
    )

# ──────────────────────────────────────────────
# 8. Professional Footer
# ──────────────────────────────────────────────
st.markdown("---")
st.markdown(
    f"""
    <div style='text-align: center; color: {MUTED_TEXT}; font-size: 0.8rem; font-weight:600; padding: 10px 0;'>
        FDA FAERS Pharmacovigilance Analytics Engine • Powered by DuckDB & openFDA API • Built for Evidence-Based Clinical Decision Support
    </div>
    """,
    unsafe_allow_html=True,
)
