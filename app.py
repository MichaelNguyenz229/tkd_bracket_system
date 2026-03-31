"""
app.py — Streamlit UI for the Taekwondo tournament data pipeline.
Keeps all display logic here; delegates all data work to pipeline.py.
"""

import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from pipeline import (
    load_raw_data,
    clean_data,
    extract_sparring,
    flag_issues,
    build_bracket,
    seed_competitors,
    SPARRING_DISPLAY_COLS,
)

st.set_page_config(page_title="AAU Tournament Data Prepocessor", layout="wide")
st.title("AAU Tournament Data Prepocessor")

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

# ── Bracket HTML renderer ─────────────────────────────────────────────────────
def _render_bracket_html(rounds: list, flagged_names: set, school_map: dict | None = None) -> tuple[str, int]:
    """Render a tournament bracket as a positioned HTML string with connector lines."""
    SLOT_H  = 64   # vertical space per first-round slot
    BOX_H   = 52   # height of each competitor box (taller to fit name + school)
    BOX_W   = 190  # width of each competitor box
    COL_GAP = 60   # gap between columns (where connector lines live)
    LABEL_H = 32   # space reserved at top for round labels

    num_rounds  = len(rounds)
    total_slots = len(rounds[0])
    canvas_h = LABEL_H + total_slots * SLOT_H + 20
    canvas_w = num_rounds * (BOX_W + COL_GAP) + 20

    round_labels = ["Round 1", "Quarterfinals", "Semifinals", "Finals", "Champion"]
    while len(round_labels) < num_rounds:
        round_labels.insert(0, f"Round {num_rounds - len(round_labels) + 1}")
    labels = round_labels[-num_rounds:]

    p = [
        f'<div style="position:relative;width:{canvas_w}px;height:{canvas_h}px;'
        f'font-family:sans-serif;background:transparent;">'
    ]

    # Round labels
    for r_idx, label in enumerate(labels):
        x = r_idx * (BOX_W + COL_GAP)
        p.append(
            f'<div style="position:absolute;left:{x}px;top:0;width:{BOX_W}px;'
            f'text-align:center;color:#aaa;font-size:11px;font-weight:700;'
            f'text-transform:uppercase;letter-spacing:1px;">{label}</div>'
        )

    # Competitor boxes
    for r_idx, round_slots in enumerate(rounds):
        span = 2 ** r_idx
        x = r_idx * (BOX_W + COL_GAP)
        for s_idx, slot in enumerate(round_slots):
            cy  = LABEL_H + (s_idx * span + (span - 1) / 2) * SLOT_H + SLOT_H / 2
            top = cy - BOX_H / 2
            if slot is None:
                p.append(
                    f'<div style="position:absolute;left:{x}px;top:{top:.1f}px;'
                    f'width:{BOX_W}px;height:{BOX_H}px;border:1px dashed #444;'
                    f'border-radius:6px;display:flex;align-items:center;padding:0 12px;'
                    f'color:#555;font-size:12px;box-sizing:border-box;">BYE</div>'
                )
            elif slot == "TBD":
                p.append(
                    f'<div style="position:absolute;left:{x}px;top:{top:.1f}px;'
                    f'width:{BOX_W}px;height:{BOX_H}px;border:1px solid #555;'
                    f'border-radius:6px;display:flex;align-items:center;padding:0 12px;'
                    f'color:#999;background:#2a2a2a;font-size:13px;box-sizing:border-box;">TBD</div>'
                )
            else:
                is_flagged = slot in flagged_names
                bg     = "#7a5c00" if is_flagged else "#1a4d2e"
                color  = "#ffe08a" if is_flagged else "#b7f5c8"
                border = "#f0ad4e" if is_flagged else "#4caf50"
                school = (school_map or {}).get(slot, "")
                school_html = (
                    f'<div style="font-size:10px;color:#aaa;margin-top:2px;'
                    f'overflow:hidden;white-space:nowrap;text-overflow:ellipsis;">{school}</div>'
                    if school else ""
                )
                p.append(
                    f'<div style="position:absolute;left:{x}px;top:{top:.1f}px;'
                    f'width:{BOX_W}px;height:{BOX_H}px;border:1px solid {border};'
                    f'border-radius:6px;display:flex;flex-direction:column;justify-content:center;'
                    f'padding:0 12px;background:{bg};box-sizing:border-box;overflow:hidden;">'
                    f'<div style="font-weight:500;font-size:13px;color:{color};'
                    f'overflow:hidden;white-space:nowrap;text-overflow:ellipsis;">{slot}</div>'
                    f'{school_html}'
                    f'</div>'
                )

    # Connector lines
    LINE = "#555"
    for r_idx in range(num_rounds - 1):
        span    = 2 ** r_idx
        x_right = r_idx * (BOX_W + COL_GAP) + BOX_W
        x_next  = (r_idx + 1) * (BOX_W + COL_GAP)
        x_mid   = (x_right + x_next) / 2
        slots   = rounds[r_idx]

        for i in range(0, len(slots), 2):
            a = slots[i]
            b = slots[i + 1] if i + 1 < len(slots) else None
            cy_a    = LABEL_H + (i * span + (span - 1) / 2) * SLOT_H + SLOT_H / 2
            cy_b    = LABEL_H + ((i + 1) * span + (span - 1) / 2) * SLOT_H + SLOT_H / 2
            cy_next = (cy_a + cy_b) / 2

            if a is None and b is None:
                continue
            elif a is None or b is None:
                active_cy = cy_a if b is None else cy_b
                p.append(
                    f'<div style="position:absolute;left:{x_right}px;top:{active_cy:.1f}px;'
                    f'width:{x_next - x_right}px;height:1px;background:{LINE};"></div>'
                )
            else:
                # horizontal from a to midpoint
                p.append(
                    f'<div style="position:absolute;left:{x_right}px;top:{cy_a:.1f}px;'
                    f'width:{x_mid - x_right:.1f}px;height:1px;background:{LINE};"></div>'
                )
                # horizontal from b to midpoint
                p.append(
                    f'<div style="position:absolute;left:{x_right}px;top:{cy_b:.1f}px;'
                    f'width:{x_mid - x_right:.1f}px;height:1px;background:{LINE};"></div>'
                )
                # vertical connector
                v_top = min(cy_a, cy_b)
                v_h   = abs(cy_b - cy_a)
                p.append(
                    f'<div style="position:absolute;left:{x_mid:.1f}px;top:{v_top:.1f}px;'
                    f'width:1px;height:{v_h:.1f}px;background:{LINE};"></div>'
                )
                # horizontal from midpoint to next round
                p.append(
                    f'<div style="position:absolute;left:{x_mid:.1f}px;top:{cy_next:.1f}px;'
                    f'width:{x_next - x_mid:.1f}px;height:1px;background:{LINE};"></div>'
                )

    p.append("</div>")
    return "".join(p), canvas_h


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs(["📋 Clean Data", "🥊 Sparring", "⚠️ Data Issues", "🏆 Brackets"])

# ── Tab 1: Clean Data ─────────────────────────────────────────────────────────
with tab1:
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
    group_by_school = school_col1.checkbox("Group by School Name")

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

    if group_by_school:
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

    # Filters + group-by (3 columns)
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

    # Gender filter: use \bMale\b / \bFemale\b to avoid "Female" matching "Male"
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
        for event_label, pattern in [("Olympic Sparring", "Olympic Sparring"), ("Grass Root Sparring", "Grass Root Sparring")]:
            mask = display_df["Pick Event(s) Below"].str.contains(pattern, case=False, na=False)
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

# ── Tab 4: Brackets ───────────────────────────────────────────────────────────
with tab4:
    # Color belt divisions don't get brackets — black belt only
    divisions = sorted(
        d for d in sparring_df["Division"].dropna().unique()
        if str(d).endswith("Black Belt")
    )

    if not divisions:
        st.info("No sparring divisions found.")
    else:
        selected_division = st.selectbox("Select Division", divisions)

        div_df = sparring_df[sparring_df["Division"] == selected_division]
        seeded = seed_competitors(div_df)
        school_map = dict(zip(div_df["Athlete Name"], div_df["School Name"]))
        n = len(seeded)

        st.markdown(f"**{selected_division}** — {n} competitor(s)")

        if n < 2:
            st.warning("Need at least 2 competitors to generate a bracket.")
            if n == 1:
                st.write(f"🏆 {seeded[0]} — sole competitor")
        else:
            rounds = build_bracket(seeded)
            html, height = _render_bracket_html(rounds, flagged_names, school_map)
            components.html(html, height=height + 20, scrolling=True)
