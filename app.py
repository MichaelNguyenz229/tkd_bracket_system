"""
app.py — Streamlit UI for the AAU tournament data pipeline.
Keeps all display logic here; delegates all data work to pipeline.py.
"""

import json
import streamlit as st
import pandas as pd
from pipeline import (
    load_raw_data,
    clean_data,
    extract_sparring,
    assign_division,
    flag_issues,
    seed_competitors,
    SPARRING_DISPLAY_COLS,
    WORLD_CLASS_COLS,
    load_demo_data,
)

st.set_page_config(page_title="AAU Tournament Data Preprocessor", layout="wide")

_title_col, _logo_col = st.columns([5, 1])
_title_col.title("AAU Tournament Data Preprocessor")
_logo_col.image("images/AAU_logo.png", use_container_width=True)

# ── Sidebar ──────────────────────────────────────────────────────────────────
_pages = ["📋 Clean Data", "📊 Reports", "🥊 Sparring", "⚠️ Data Issues"]

if "nav_goto" in st.session_state:
    st.session_state["nav_page"] = st.session_state.pop("nav_goto")
if "nav_page" not in st.session_state:
    st.session_state["nav_page"] = _pages[0]

with st.sidebar:
    st.header("Upload Data")
    uploaded = st.file_uploader("Registration CSV", type=["csv"])
    if st.button("Try Demo Mode", use_container_width=True):
        st.session_state["demo_mode"] = True
        st.rerun()

    st.divider()

    st.markdown(
        """
        <style>
        div[data-testid="stSidebarContent"] .nav-btn button {
            width: 100%;
            text-align: left;
            background: transparent;
            border: none;
            border-radius: 6px;
            padding: 8px 12px;
            font-size: 14px;
            color: #ccc;
            cursor: pointer;
        }
        div[data-testid="stSidebarContent"] .nav-btn button:hover {
            background: #2a2a2a;
            color: #fff;
        }
        div[data-testid="stSidebarContent"] .nav-btn-active button {
            background: #1a3a2a !important;
            border-left: 3px solid #4caf50 !important;
            color: #b7f5c8 !important;
            font-weight: 600 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    for _p in _pages:
        _css_class = "nav-btn-active" if st.session_state["nav_page"] == _p else "nav-btn"
        with st.container():
            st.markdown(f'<div class="{_css_class}">', unsafe_allow_html=True)
            if st.button(_p, key=f"nav_{_p}", use_container_width=True):
                st.session_state["nav_page"] = _p
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

page = st.session_state["nav_page"]

if uploaded is None and not st.session_state.get("demo_mode"):
    st.info("Upload a registration CSV or try Demo Mode using the sidebar.")
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


if st.session_state.get("demo_mode") and uploaded is None:
    clean_df, sparring_df, issues_df = load_demo_data()
else:
    if uploaded is None:
        st.stop()
    st.session_state["demo_mode"] = False
    clean_df, sparring_df, issues_df = process(uploaded.read())

flagged_names = set(issues_df["Athlete Name"].tolist()) if not issues_df.empty else set()

# ── Demo mode banner ──────────────────────────────────────────────────────────
if st.session_state.get("demo_mode"):
    demo_col, exit_col = st.columns([6, 1])
    demo_col.info("👀 Demo Mode — showing sample data. Upload a CSV to use real data.")
    if exit_col.button("Exit Demo"):
        st.session_state["demo_mode"] = False
        st.session_state.pop("alert_dismissed", None)
        st.rerun()


def _issues_alert():
    """Show a warning banner with a link to the Data Issues page and a dismiss option."""
    if issues_df.empty or st.session_state.get("alert_dismissed"):
        return
    warn_col, btn_col, dismiss_col = st.columns([5, 1, 1])
    warn_col.warning(
        f"⚠️ {len(issues_df)} data issue(s) detected across "
        f"{issues_df['Athlete Name'].nunique()} athlete(s)."
    )
    if btn_col.button("View Issues →", type="primary"):
        st.session_state["nav_goto"] = "⚠️ Data Issues"
        st.rerun()
    if dismiss_col.button("Dismiss ✕"):
        st.session_state["alert_dismissed"] = True
        st.rerun()


# ── Page: Clean Data ──────────────────────────────────────────────────────────
if page == "📋 Clean Data":
    _issues_alert()
    st.subheader(f"Clean Data — {len(clean_df)} athletes")

    belt_col1, gender_col1, school_col1 = st.columns([1, 1, 1])
    clean_belt_filter = belt_col1.radio(
        "Belt Type",
        ["All", "Black Belt", "Color Belt"],
        horizontal=True,
        key="clean_belt",
    )
    clean_gender_filter = gender_col1.multiselect(
        "Gender",
        ["Male", "Female"],
        default=["Male", "Female"],
        key="clean_gender",
    )
    clean_group_by = school_col1.selectbox(
        "Group by",
        ["None", "School Name"],
        index=0,
        key="clean_group_by",
    )

    filtered_clean = clean_df.copy()

    if clean_belt_filter == "Black Belt":
        filtered_clean = filtered_clean[filtered_clean["Rank"].str.contains("Black", case=False, na=False)]
    elif clean_belt_filter == "Color Belt":
        filtered_clean = filtered_clean[~filtered_clean["Rank"].str.contains("Black", case=False, na=False)]

    if clean_gender_filter and len(clean_gender_filter) < 2:
        filtered_clean = filtered_clean[
            filtered_clean["Gender"].str.strip().str.lower() == clean_gender_filter[0].lower()
        ]

    filtered_clean = filtered_clean.reset_index(drop=True)

    if clean_group_by == "School Name":
        for school, group in filtered_clean.groupby("School Name", sort=True):
            st.markdown(f"**{school}** — {len(group)} athlete(s)")
            st.dataframe(group.reset_index(drop=True), use_container_width=True)
    else:
        st.dataframe(filtered_clean, use_container_width=True)

    st.download_button(
        "⬇ Download Clean Data CSV",
        filtered_clean.to_csv(index=False),
        "clean_data.csv",
        "text/csv",
    )

# ── Page: Reports ────────────────────────────────────────────────────────────
elif page == "📊 Reports":
    _issues_alert()

    # Build report dataframe: slim columns + computed division for all athletes
    report_df = clean_df.copy()
    wc_cols = [c for c in WORLD_CLASS_COLS if c in report_df.columns]
    report_df["Division"] = report_df.apply(
        lambda row: assign_division(row, wc_cols), axis=1
    )
    # Non-sparring athletes get "—" for division
    sparring_mask = report_df["Pick Event(s) Below"].str.contains(
        r"(?i)(?:olympic sparring|grass root sparring)", regex=True, na=False
    )
    report_df.loc[~sparring_mask, "Division"] = "—"

    report_cols = ["Athlete Name", "Gender", "Age", "Rank", "School Name", "Division", "Pick Event(s) Below"]
    report_cols = [c for c in report_cols if c in report_df.columns]
    report_df = report_df[report_cols].reset_index(drop=True)

    st.subheader(f"Reports — {len(report_df)} athletes")

    rpt_belt_col, rpt_gender_col, rpt_group_col = st.columns([1, 1, 1])
    rpt_belt_filter = rpt_belt_col.radio(
        "Belt Type",
        ["All", "Black Belt", "Color Belt"],
        horizontal=True,
        key="rpt_belt",
    )
    rpt_gender_filter = rpt_gender_col.multiselect(
        "Gender",
        ["Male", "Female"],
        default=["Male", "Female"],
        key="rpt_gender",
    )
    rpt_group_by = rpt_group_col.selectbox(
        "Group by",
        ["None", "School Name", "Event"],
        index=0,
        key="rpt_group_by",
    )

    if rpt_belt_filter == "Black Belt":
        report_df = report_df[report_df["Rank"].str.contains("Black", case=False, na=False)]
    elif rpt_belt_filter == "Color Belt":
        report_df = report_df[~report_df["Rank"].str.contains("Black", case=False, na=False)]

    if rpt_gender_filter and len(rpt_gender_filter) < 2:
        report_df = report_df[
            report_df["Gender"].str.strip().str.lower() == rpt_gender_filter[0].lower()
        ]

    report_df = report_df.reset_index(drop=True)

    visible_cols = st.multiselect(
        "Columns",
        report_df.columns.tolist(),
        default=report_df.columns.tolist(),
        key="rpt_columns",
    )
    if visible_cols:
        report_df = report_df[visible_cols]
    else:
        st.warning("Select at least one column to display.")
        st.stop()

    if rpt_group_by == "None":
        st.dataframe(report_df, use_container_width=True, hide_index=True)
    elif rpt_group_by == "School Name":
        for school, group in report_df.groupby("School Name", sort=True):
            st.markdown(f"**{school}** — {len(group)} athlete(s)")
            st.dataframe(group.reset_index(drop=True), use_container_width=True, hide_index=True)
    elif rpt_group_by == "Event":
        # Explode comma-separated events so each athlete appears under each event
        all_events = set()
        for val in report_df["Pick Event(s) Below"].dropna():
            for e in val.split(","):
                e = e.strip()
                if e:
                    all_events.add(e)
        for event in sorted(all_events):
            mask = report_df["Pick Event(s) Below"].str.contains(
                event, case=False, na=False, regex=False
            )
            group = report_df[mask].reset_index(drop=True)
            if not group.empty:
                st.markdown(f"**{event}** — {len(group)} athlete(s)")
                st.dataframe(group, use_container_width=True, hide_index=True)

    st.download_button(
        "⬇ Download Report CSV",
        report_df.to_csv(index=False),
        "report.csv",
        "text/csv",
    )

# ── Page: Sparring ────────────────────────────────────────────────────────────
elif page == "🥊 Sparring":
    _issues_alert()
    st.subheader("Sparring")
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

    belt_col, gender_col, group_col = st.columns([1, 1, 1])
    belt_filter = belt_col.radio(
        "Belt Type",
        ["All", "Black Belt", "Color Belt"],
        horizontal=True,
    )
    gender_filter = gender_col.multiselect(
        "Gender",
        ["Male", "Female"],
        default=["Male", "Female"],
    )
    group_by = group_col.selectbox(
        "Group by",
        ["None", "Division", "Event Type", "School Name"],
        index=0,
    )

    display_cols = [c for c in SPARRING_DISPLAY_COLS if c in sparring_df.columns]
    display_df = sparring_df[display_cols].sort_values("Division").reset_index(drop=True)

    if belt_filter == "Black Belt":
        display_df = display_df[display_df["Division"].str.endswith("Black Belt", na=False)].reset_index(drop=True)
    elif belt_filter == "Color Belt":
        display_df = display_df[~display_df["Division"].str.endswith("Black Belt", na=False)].reset_index(drop=True)

    if gender_filter and len(gender_filter) < 2:
        pattern = r"\b" + gender_filter[0] + r"\b"
        display_df = display_df[display_df["Division"].str.contains(pattern, regex=True, na=False)].reset_index(drop=True)

    def highlight_flagged(row: pd.Series):
        if row["Athlete Name"] in flagged_names:
            return ["background-color: #7a5c00; color: #ffe08a"] * len(row)
        return [""] * len(row)

    if group_by == "None":
        st.dataframe(
            display_df.style.apply(highlight_flagged, axis=1),
            use_container_width=True,
        )
    elif group_by == "Division":
        for division, group in display_df.groupby("Division", sort=True):
            st.markdown(f"**{division}** — {len(group)} competitor(s)")
            st.dataframe(
                group.reset_index(drop=True).style.apply(highlight_flagged, axis=1),
                use_container_width=True,
            )
    elif group_by == "Event Type":
        for event_label, pat in [("Olympic Sparring", "Olympic Sparring"), ("Grass Root Sparring", "Grass Root Sparring")]:
            mask = display_df["Pick Event(s) Below"].str.contains(pat, case=False, na=False)
            group = display_df[mask].reset_index(drop=True)
            st.markdown(f"**{event_label}** — {len(group)} competitor(s)")
            st.dataframe(
                group.style.apply(highlight_flagged, axis=1),
                use_container_width=True,
            )
    elif group_by == "School Name":
        for school, group in display_df.groupby("School Name", sort=True):
            st.markdown(f"**{school}** — {len(group)} competitor(s)")
            st.dataframe(
                group.reset_index(drop=True).style.apply(highlight_flagged, axis=1),
                use_container_width=True,
            )

    st.download_button(
        "⬇ Download Sparring Data CSV",
        display_df.to_csv(index=False),
        "sparring_data.csv",
        "text/csv",
    )

    # ── Division JSON exports (moved from Brackets tab) ──────────────────
    bb_divisions = sorted(
        d for d in sparring_df["Division"].dropna().unique()
        if str(d).endswith("Black Belt")
    )

    if bb_divisions:
        def _division_to_json(division_name: str) -> dict:
            df = sparring_df[sparring_df["Division"] == division_name]
            names = seed_competitors(df)
            schools = dict(zip(df["Athlete Name"], df["School Name"]))
            return {
                "division": division_name,
                "competitors": [
                    {"id": str(i + 1), "name": name, "school": schools.get(name, ""), "photoUrl": ""}
                    for i, name in enumerate(names)
                ],
            }

        st.divider()
        sel_col, _ = st.columns([1, 2])
        _div_counts = sparring_df[sparring_df["Division"].isin(bb_divisions)].groupby("Division").size()
        _div_labels = {d: f"{d} — {_div_counts.get(d, 0)} competitor(s)" for d in bb_divisions}
        _label_to_div = {v: k for k, v in _div_labels.items()}
        selected_label = sel_col.selectbox("Export Division", list(_div_labels.values()))
        selected_division = _label_to_div[selected_label]

        exp_col1, exp_col2 = st.columns(2)
        exp_col1.download_button(
            "Export This Division (JSON)",
            json.dumps(_division_to_json(selected_division), indent=2),
            f"{selected_division.replace(' ', '_')}.json",
            "application/json",
            use_container_width=True,
        )
        all_data = [_division_to_json(d) for d in bb_divisions]
        exp_col2.download_button(
            "Export All Divisions (JSON)",
            json.dumps(all_data, indent=2),
            "all_divisions.json",
            "application/json",
            use_container_width=True,
        )

        st.divider()
        st.subheader("🚀 Pipeline Architecture Integration")
        if st.button("Sync directly to Bracket Generator", use_container_width=True, type="primary"):
            import os
            from pathlib import Path
            try:
                # Target: tournament-data-pipeline / bracket_generator / public / pipeline_data.json
                pipeline_dir = Path(__file__).resolve().parent.parent / "bracket_generator" / "public"
                pipeline_dir.mkdir(parents=True, exist_ok=True)
                target_file = pipeline_dir / "pipeline_data.json"
                with open(target_file, "w") as f:
                    json.dump(all_data, f, indent=2)
                st.success(f"Successfully synced {len(all_data)} divisions to the Bracket Generator! You can now load it instantly from the other app.")
            except Exception as e:
                st.error(f"Failed to sync to bracket generator: {e}")


# ── Page: Data Issues ─────────────────────────────────────────────────────────
elif page == "⚠️ Data Issues":
    st.subheader("Data Issues")
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
