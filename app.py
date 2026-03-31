"""
app.py — Streamlit UI for the Taekwondo tournament data pipeline.
Keeps all display logic here; delegates all data work to pipeline.py.
"""

import streamlit as st
import pandas as pd
from pipeline import (
    load_raw_data,
    clean_data,
    extract_sparring,
    flag_issues,
    SPARRING_DISPLAY_COLS,
)

st.set_page_config(page_title="TKD Tournament Pipeline", layout="wide")
st.title("Taekwondo Tournament Pipeline")

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Upload Data")
    uploaded = st.file_uploader("Registration CSV", type=["csv"])

if uploaded is None:
    st.info("Upload a registration CSV using the sidebar to get started.")
    st.stop()

# ── Process data ──────────────────────────────────────────────────────────────
@st.cache_data
def process(file_bytes: bytes):
    """Run the full pipeline on the uploaded file and cache the result."""
    import io
    raw_df = load_raw_data(io.BytesIO(file_bytes))
    clean_df = clean_data(raw_df)
    sparring_df = extract_sparring(clean_df)
    issues_df = flag_issues(sparring_df)
    return clean_df, sparring_df, issues_df


clean_df, sparring_df, issues_df = process(uploaded.read())
flagged_names = set(issues_df["Athlete Name"].tolist()) if not issues_df.empty else set()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📋 Clean Data", "🥊 Sparring", "⚠️ Data Issues"])

# ── Tab 1: Clean Data ─────────────────────────────────────────────────────────
with tab1:
    st.subheader(f"Clean Data — {len(clean_df)} athletes")
    st.dataframe(clean_df, use_container_width=True)
    st.download_button(
        "⬇ Download Clean Data CSV",
        clean_df.to_csv(index=False),
        "clean_data.csv",
        "text/csv",
    )

# ── Tab 2: Sparring ───────────────────────────────────────────────────────────
with tab2:
    total = len(sparring_df)
    olympic_count = sparring_df["Pick Event(s) Below"].str.contains(
        "Olympic Sparring", case=False, na=False
    ).sum()
    grass_count = sparring_df["Pick Event(s) Below"].str.contains(
        "Grass Root Sparring", case=False, na=False
    ).sum()

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Sparring Competitors", total)
    col2.metric("Olympic Sparring", olympic_count)
    col3.metric("Grass Root Sparring", grass_count)

    # Build display DataFrame: required columns only, sorted by Division
    display_cols = [c for c in SPARRING_DISPLAY_COLS if c in sparring_df.columns]
    display_df = sparring_df[display_cols].sort_values("Division").reset_index(drop=True)

    # Highlight flagged athletes in yellow
    def highlight_flagged(row: pd.Series):
        if row["Athlete Name"] in flagged_names:
            return ["background-color: #fff3cd"] * len(row)
        return [""] * len(row)

    st.dataframe(
        display_df.style.apply(highlight_flagged, axis=1),
        use_container_width=True,
    )
    st.download_button(
        "⬇ Download Sparring Data CSV",
        display_df.to_csv(index=False),
        "sparring_data.csv",
        "text/csv",
    )

# ── Tab 3: Data Issues ────────────────────────────────────────────────────────
with tab3:
    if issues_df.empty:
        st.success("No data issues found!")
    else:
        st.warning(f"{len(issues_df)} issue(s) found across {issues_df['Athlete Name'].nunique()} athlete(s)")
        st.dataframe(issues_df, use_container_width=True)
        st.download_button(
            "⬇ Download Issues CSV",
            issues_df.to_csv(index=False),
            "data_issues.csv",
            "text/csv",
        )
