"""
app.py — Streamlit UI for the AAU tournament data pipeline.
Keeps all display logic here; delegates all data work to pipeline.py.
"""

import json
import html as html_lib
import base64
from datetime import datetime
import streamlit as st
import streamlit.components.v1 as components
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
_logo_col.image("images/AAU_logo.png", width="stretch")

components.html(
    """
    <script>
    (function() {
        const doc = window.parent.document;
        if (doc.getElementById('sidebar-click-outside')) return;

        const marker = doc.createElement('div');
        marker.id = 'sidebar-click-outside';
        marker.style.display = 'none';
        doc.body.appendChild(marker);

        doc.addEventListener('mousedown', function(e) {
            const sidebar = doc.querySelector('[data-testid="stSidebar"]');
            if (!sidebar) return;

            if (sidebar.getAttribute('aria-expanded') !== 'true') return;

            // Ignore clicks inside the sidebar itself
            if (sidebar.contains(e.target)) return;

            // Ignore clicks on popover/dropdown/dialog overlays
            if (e.target.closest('[data-baseweb="popover"]') ||
                e.target.closest('[data-baseweb="select"]') ||
                e.target.closest('[role="listbox"]') ||
                e.target.closest('[role="dialog"]') ||
                e.target.closest('[data-testid="stModal"]')) return;

            // Find the collapse button and click it
            const closeBtn = doc.querySelector('[data-testid="stSidebarCollapseButton"] button')
                          || doc.querySelector('[data-testid="stSidebarCollapseButton"]')
                          || doc.querySelector('button[aria-label="Close sidebar navigation"]')
                          || doc.querySelector('button[aria-label="Collapse sidebar"]');
            if (closeBtn) closeBtn.click();
        });
    })();
    </script>
    """,
    height=0,
    width=0,
)

# ── Sidebar ──────────────────────────────────────────────────────────────────
_pages = ["📊 Reports", "🥊 Sparring", "⚠️ Data Issues", "🎫 Credentials"]

if "nav_goto" in st.session_state:
    st.session_state["nav_page"] = st.session_state.pop("nav_goto")
if "nav_page" not in st.session_state:
    st.session_state["nav_page"] = _pages[0]

with st.sidebar:
    st.header("Upload Data")
    uploaded = st.file_uploader("Registration CSV", type=["csv"])
    if st.button("Try Demo Mode", width="stretch"):
        st.session_state["demo_mode"] = True
        st.rerun()

    st.divider()

    st.markdown(
        """
        <style>
        div[data-testid="stSidebarContent"] .stButton {
            margin-bottom: -15px; /* Pulls the buttons closer together */
        }
        div[data-testid="stSidebarContent"] .nav-btn button {
            width: 100%;
            text-align: left;
            background: transparent;
            border: none;
            border-radius: 6px;
            padding: 10px 14px;
            font-size: 15px;
            color: #d1d1d1;
            cursor: pointer;
            transition: all 0.2s ease-in-out;
        }
        div[data-testid="stSidebarContent"] .nav-btn button:hover {
            background: rgba(255, 255, 255, 0.08); /* softer hover */
            color: #ffffff;
        }
        div[data-testid="stSidebarContent"] .nav-btn-active button {
            background: rgba(76, 175, 80, 0.15) !important;
            border-left: 4px solid #4caf50 !important;
            color: #4caf50 !important;
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
            if st.button(_p, key=f"nav_{_p}", width="stretch"):
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
    issues_df = flag_issues(sparring_df, clean_df)
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
    if btn_col.button("View Issues →"):
        st.session_state["nav_goto"] = "⚠️ Data Issues"
        st.rerun()
    if dismiss_col.button("Dismiss ✕"):
        st.session_state["alert_dismissed"] = True
        st.rerun()


def _open_print_view(title: str, sections: list, flagged_names: set = None):
    """Open a print-friendly view in a new browser tab with full tables."""
    timestamp = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    parts = [f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>{html_lib.escape(title)}</title>
<style>
body {{ font-family: Arial, sans-serif; padding: 30px; color: #222; }}
h1 {{ font-size: 22px; margin-bottom: 2px; }}
.timestamp {{ color: #888; font-size: 12px; margin-bottom: 20px; }}
h2 {{ font-size: 15px; margin-top: 24px; margin-bottom: 6px; color: #333;
      border-bottom: 1px solid #ddd; padding-bottom: 4px; }}
table {{ border-collapse: collapse; width: 100%; margin-bottom: 16px; font-size: 11px; }}
th {{ background: #f0f0f0; padding: 5px 8px; text-align: left; border: 1px solid #ccc; font-weight: 600; }}
td {{ padding: 5px 8px; border: 1px solid #ddd; }}
tr:nth-child(even) {{ background: #fafafa; }}
.flagged {{ background: #fff3cd !important; }}
@media print {{ body {{ padding: 10px; }} .no-print {{ display: none; }} }}
</style></head><body>
<h1>{html_lib.escape(title)}</h1>
<p class="timestamp">{timestamp}</p>"""]

    for section_name, df in sections:
        if section_name:
            parts.append(f"<h2>{html_lib.escape(str(section_name))} — {len(df)} competitor(s)</h2>")
        parts.append("<table><thead><tr>")
        for col in df.columns:
            parts.append(f"<th>{html_lib.escape(str(col))}</th>")
        parts.append("</tr></thead><tbody>")
        for _, row in df.iterrows():
            is_flagged = flagged_names and row.get("Athlete Name") in flagged_names
            cls = ' class="flagged"' if is_flagged else ""
            parts.append(f"<tr{cls}>")
            for val in row:
                parts.append(f"<td>{html_lib.escape(str(val))}</td>")
            parts.append("</tr>")
        parts.append("</tbody></table>")

    parts.append("</body></html>")
    b64 = base64.b64encode("".join(parts).encode("utf-8")).decode("ascii")
    components.html(
        f"""<script>
        var w = window.open('', '_blank');
        if (w) {{
            var bin = atob('{b64}');
            var bytes = new Uint8Array(bin.length);
            for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
            var html = new TextDecoder('utf-8').decode(bytes);
            w.document.write(html);
            w.document.close();
            w.onload = function() {{ w.print(); }};
        }}
        </script>""",
        height=0, width=0,
    )


# ── Credentials HTML builder ─────────────────────────────────────────────────
def _build_credentials_html(df: pd.DataFrame, sparring_df: pd.DataFrame, blank: bool = False) -> str:
    from pathlib import Path
    from pipeline.cleaning import get_birth_year, TOURNAMENT_YEAR

    logo_path = Path(__file__).parent / "images" / "AAU_logo.png"
    logo_b64 = base64.b64encode(logo_path.read_bytes()).decode()
    logo_src = f"data:image/png;base64,{logo_b64}"

    # Build name → division lookup for black belt athletes only
    division_lookup: dict[str, str] = {}
    if "Division" in sparring_df.columns and "Athlete Name" in sparring_df.columns:
        for _, r in sparring_df.iterrows():
            div = str(r.get("Division", ""))
            if div.endswith("Black Belt"):
                division_lookup[str(r.get("Athlete Name", "")).strip()] = div

    df = df.copy().sort_values("School Name", na_position="last").reset_index(drop=True)

    if blank:
        rows_to_iter = [None] * 4
    else:
        rows_to_iter = [row for _, row in df.iterrows()]

    cards = []
    for row in rows_to_iter:
        name       = "" if blank else str(row.get("Athlete Name", "")).strip()
        gender     = "" if blank else str(row.get("Gender", "")).strip()
        rank       = "" if blank else str(row.get("Rank", "")).strip()
        school     = "" if blank else str(row.get("School Name", "")).strip()
        if blank:
            age = ""
        else:
            _by = get_birth_year(row.get("Date of Birth"))
            age = str(TOURNAMENT_YEAR - _by) if _by else "—"

        events_raw = "" if blank else str(row.get("Pick Event(s) Below", ""))
        events = [] if blank else [e.strip() for e in events_raw.split(",") if e.strip() and events_raw != "nan"]
        events_html = "".join(f'<div class="ev">• {html_lib.escape(e)}</div>' for e in events) or '<div class="ev">—</div>'

        is_sparring = any("sparring" in e.lower() for e in events)
        weight_raw  = None if blank else row.get("Weight in KG", "")
        try:
            w = float(weight_raw)
            weight_str = f"{w:.1f} kg" if w > 0 else "—"
        except (TypeError, ValueError):
            weight_str = "—"

        if blank:
            cards.append(f"""
        <div class="card">
          <div class="card-header">
            <img src="{logo_src}" class="logo" alt="AAU Logo">
            <div class="title-block">
              <div class="title-main">AAU District Championship</div>
              <div class="title-sub">Southern Pacific / National Qualifier</div>
            </div>
          </div>
          <div class="card-body">
            <div class="field name-field blank-line">&nbsp;</div>
            <div class="field school-sub blank-full">&nbsp;</div>
            <div class="field field-row">
              <span><span class="lbl">Age:</span> <span class="blank-inline">&nbsp;</span></span>
              <span><span class="lbl">Gender:</span> <span class="blank-inline">&nbsp;</span></span>
            </div>
            <div class="field"><span class="lbl">Belt:</span> <span class="blank-full">&nbsp;</span></div>
            <div class="field"><span class="lbl">Events:</span> <span class="blank-full" style="min-height:36px;display:inline-block;">&nbsp;</span></div>
            <div class="field"><span class="lbl">Division:</span> <span class="blank-full">&nbsp;</span></div>
            <div class="field"><span class="lbl">Weight:</span> <span class="blank-full">&nbsp;</span></div>
          </div>
          <div class="card-footer">ATHLETE</div>
        </div>""")
        else:
            weight_row = f'<div class="field"><span class="lbl">Weight:</span> <span class="val">{weight_str}</span></div>' if is_sparring else ""
            division = division_lookup.get(name, "")
            division_row = f'<div class="field"><span class="lbl">Division:</span> <span class="val">{html_lib.escape(division)}</span></div>' if division else ""

            cards.append(f"""
        <div class="card">
          <div class="card-header">
            <img src="{logo_src}" class="logo" alt="AAU Logo">
            <div class="title-block">
              <div class="title-main">AAU District Championship</div>
              <div class="title-sub">Southern Pacific / National Qualifier</div>
            </div>
          </div>
          <div class="card-body">
            <div class="field name-field">{html_lib.escape(name)}</div>
            <div class="field school-sub">{html_lib.escape(school)}</div>
            <div class="field field-row">
              <span><span class="lbl">Age:</span> <span class="val">{age}</span></span>
              <span><span class="lbl">Gender:</span> <span class="val">{html_lib.escape(gender)}</span></span>
            </div>
            <div class="field"><span class="lbl">Belt:</span> <span class="val">{html_lib.escape(rank)}</span></div>
            <div class="field"><span class="lbl">Events:</span><div class="ev-list">{events_html}</div></div>
            {division_row}
            {weight_row}
          </div>
          <div class="card-footer">ATHLETE</div>
        </div>""")

    pages = []
    for i in range(0, len(cards), 4):
        chunk = cards[i:i+4]
        while len(chunk) < 4:
            chunk.append('<div class="card card-empty"></div>')
        pages.append('<div class="page">' + "".join(chunk) + "</div>")

    num_pages = len(pages)

    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:Arial,sans-serif;background:#eee;}}
.controls{{padding:14px 20px;background:#fff;border-bottom:1px solid #ccc;display:flex;align-items:center;gap:16px;}}
.print-btn{{background:#1a3a8f;color:#fff;border:none;padding:10px 22px;font-size:14px;font-weight:700;border-radius:6px;cursor:pointer;}}
.print-btn:hover{{background:#142d70;}}
.info{{color:#555;font-size:13px;}}
.page{{width:8.5in;height:11in;display:grid;grid-template-columns:1fr 1fr;grid-template-rows:1fr 1fr;
       margin:20px auto;background:#fff;box-shadow:0 2px 10px rgba(0,0,0,0.2);}}
.card{{width:4.25in;height:5.5in;border:1px solid #bbb;display:flex;flex-direction:column;overflow:hidden;}}
.card-empty{{background:#f9f9f9;}}
.card-header{{display:flex;align-items:center;padding:10px 12px;border-bottom:3px solid #1a3a8f;gap:12px;}}
.logo{{width:56px;height:56px;object-fit:contain;}}
.title-main{{font-size:18px;font-weight:900;color:#1a3a8f;letter-spacing:0.5px;}}
.title-sub{{font-size:11px;color:#666;text-transform:uppercase;letter-spacing:1px;margin-top:2px;}}
.card-body{{flex:1;padding:12px 16px;display:flex;flex-direction:column;gap:9px;}}
.field{{font-size:13px;border-bottom:1px solid #e8e8e8;padding-bottom:6px;}}
.name-field{{font-size:20px;font-weight:800;color:#111;padding-bottom:2px;border-bottom:none;}}
.school-sub{{font-size:12px;color:#555;border-bottom:2px solid #1a3a8f;padding-bottom:7px;}}
.field-row{{display:flex;gap:24px;}}
.lbl{{font-weight:700;color:#333;}}
.val{{color:#111;}}
.ev-list{{margin-top:3px;padding-left:2px;}}
.ev{{font-size:12px;color:#333;line-height:1.7;}}
.blank-line{{border-bottom:2px solid #1a3a8f!important;min-height:24px;}}
.blank-full{{display:inline-block;width:70%;border-bottom:1px solid #999;}}
.blank-inline{{display:inline-block;width:60px;border-bottom:1px solid #999;}}
.card-footer{{background:#1a3a8f;color:#fff;text-align:center;padding:14px 8px;
              font-size:28px;font-weight:900;text-transform:uppercase;letter-spacing:4px;}}
@media print{{
  *{{-webkit-print-color-adjust:exact;print-color-adjust:exact;}}
  body{{background:#fff;}}
  .controls{{display:none!important;}}
  .page{{width:8.5in;height:11in;margin:0;page-break-after:always;box-shadow:none;}}
  .card{{border:0.5px solid #aaa;}}
}}
</style></head><body>
<div class="controls">
  <button class="print-btn" onclick="window.print()">🖨 Print Credentials</button>
  <span class="info">{"4 blank cards · 1 page" if blank else f"{len(df)} athletes · {num_pages} page(s) · sorted by school"}</span>
</div>
{"".join(pages)}
</body></html>"""


# ── Page: Reports ────────────────────────────────────────────────────────────
if page == "📊 Reports":
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

    _rpt_title_col, _rpt_view_col, _rpt_print_col = st.columns([5.5, 1.5, 1])
    _rpt_title_placeholder = _rpt_title_col.empty()
    with _rpt_view_col:
        with st.popover("⚙️ Columns"):
            visible_cols = st.multiselect(
                "Columns",
                report_df.columns.tolist(),
                default=report_df.columns.tolist(),
                label_visibility="collapsed",
                key="rpt_columns"
            )
    _rpt_print_btn = _rpt_print_col.button("🖨 Print", key="print_report")

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
    _rpt_title_placeholder.subheader(f"Reports — {len(report_df)} athletes")

    if visible_cols:
        report_df = report_df[visible_cols]
    else:
        st.warning("Select at least one column to display.")
        st.stop()



    if rpt_group_by == "None":
        st.dataframe(report_df, width="stretch", hide_index=True)
    elif rpt_group_by == "School Name":
        for school, group in report_df.groupby("School Name", sort=True):
            st.markdown(f"**{school}** — {len(group)} athlete(s)")
            st.dataframe(group.reset_index(drop=True), width="stretch", hide_index=True)
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
                st.dataframe(group, width="stretch", hide_index=True)

    if _rpt_print_btn:
        _sections = []
        if rpt_group_by == "None":
            _sections.append(("", report_df))
        elif rpt_group_by == "School Name":
            for school, group in report_df.groupby("School Name", sort=True):
                _sections.append((school, group.reset_index(drop=True)))
        elif rpt_group_by == "Event":
            _evts = set()
            for val in report_df["Pick Event(s) Below"].dropna():
                for e in val.split(","):
                    if e.strip():
                        _evts.add(e.strip())
            for event in sorted(_evts):
                mask = report_df["Pick Event(s) Below"].str.contains(
                    event, case=False, na=False, regex=False
                )
                group = report_df[mask].reset_index(drop=True)
                if not group.empty:
                    _sections.append((event, group))
        _rpt_subtitle = f" by {rpt_group_by}" if rpt_group_by != "None" else ""
        
        _filters = []
        if rpt_gender_filter and len(rpt_gender_filter) == 1:
            _filters.append(rpt_gender_filter[0])
        if rpt_belt_filter != "All":
            _filters.append(rpt_belt_filter)
        _filter_str = f" ({', '.join(_filters)})" if _filters else ""
        
        _open_print_view(f"Reports{_rpt_subtitle}{_filter_str} — {len(report_df)} athletes", _sections)

# ── Page: Sparring ────────────────────────────────────────────────────────────
elif page == "🥊 Sparring":
    _issues_alert()
    _spr_title_col, _spr_print_col = st.columns([6, 1])
    _spr_title_col.subheader("Sparring")
    _spr_print_btn = _spr_print_col.button("🖨 Print", key="print_sparring")
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
            width="stretch",
        )
    elif group_by == "Division":
        for division, group in display_df.groupby("Division", sort=True):
            st.markdown(f"**{division}** — {len(group)} competitor(s)")
            st.dataframe(
                group.reset_index(drop=True).style.apply(highlight_flagged, axis=1),
                width="stretch",
            )
    elif group_by == "Event Type":
        for event_label, pat in [("Olympic Sparring", "Olympic Sparring"), ("Grass Root Sparring", "Grass Root Sparring")]:
            mask = display_df["Pick Event(s) Below"].str.contains(pat, case=False, na=False)
            group = display_df[mask].reset_index(drop=True)
            st.markdown(f"**{event_label}** — {len(group)} competitor(s)")
            st.dataframe(
                group.style.apply(highlight_flagged, axis=1),
                width="stretch",
            )
    elif group_by == "School Name":
        for school, group in display_df.groupby("School Name", sort=True):
            st.markdown(f"**{school}** — {len(group)} competitor(s)")
            st.dataframe(
                group.reset_index(drop=True).style.apply(highlight_flagged, axis=1),
                width="stretch",
            )

    if _spr_print_btn:
        _sections = []
        if group_by == "None":
            _sections.append(("", display_df))
        elif group_by == "Division":
            for division, group in display_df.groupby("Division", sort=True):
                _sections.append((division, group.reset_index(drop=True)))
        elif group_by == "Event Type":
            for event_label, pat in [("Olympic Sparring", "Olympic Sparring"), ("Grass Root Sparring", "Grass Root Sparring")]:
                mask = display_df["Pick Event(s) Below"].str.contains(pat, case=False, na=False)
                group = display_df[mask].reset_index(drop=True)
                _sections.append((event_label, group))
        elif group_by == "School Name":
            for school, group in display_df.groupby("School Name", sort=True):
                _sections.append((school, group.reset_index(drop=True)))
        _spr_subtitle = f" by {group_by}" if group_by != "None" else ""
        
        _filters = []
        if gender_filter and len(gender_filter) == 1:
            _filters.append(gender_filter[0])
        if belt_filter != "All":
            _filters.append(belt_filter)
        _filter_str = f" ({', '.join(_filters)})" if _filters else ""
        
        _open_print_view(f"Sparring{_spr_subtitle}{_filter_str} — {len(display_df)} competitors", _sections, flagged_names)

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

        all_data = [_division_to_json(d) for d in bb_divisions]

        st.divider()
        st.markdown(
            """
            <style>
            button[kind="primary"] {
                background-color: #2e8b57 !important;
                color: white !important;
                border: none !important;
            }
            button[kind="primary"]:hover {
                background-color: #1f6b40 !important;
                color: white !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Sync directly to Bracket Generator", width="stretch", type="primary"):
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


# ── Page: Credentials ────────────────────────────────────────────────────────
elif page == "🎫 Credentials":
    st.subheader(f"Credentials — {len(clean_df)} athletes")

    # Preview: simple table sorted by school
    preview_df = clean_df[["Athlete Name", "School Name", "Gender", "Rank", "Pick Event(s) Below"]].copy()
    preview_df = preview_df.sort_values("School Name", na_position="last").reset_index(drop=True)
    st.dataframe(preview_df, width="stretch", hide_index=True)

    dl_col1, dl_col2 = st.columns(2)
    with dl_col1:
        cred_html = _build_credentials_html(clean_df, sparring_df, blank=False)
        st.download_button(
            label="🖨 Download Filled Credentials",
            data=cred_html.encode("utf-8"),
            file_name="credentials_filled.html",
            mime="text/html",
            key="dl_creds_filled",
        )
    with dl_col2:
        blank_html = _build_credentials_html(clean_df, sparring_df, blank=True)
        st.download_button(
            label="🖨 Download Blank Credentials",
            data=blank_html.encode("utf-8"),
            file_name="credentials_blank.html",
            mime="text/html",
            key="dl_creds_blank",
        )

# ── Page: Data Issues ─────────────────────────────────────────────────────────
elif page == "⚠️ Data Issues":
    _iss_title_col, _iss_print_col = st.columns([6, 1])
    _iss_title_col.subheader("Data Issues")
    _iss_print_btn = _iss_print_col.button("🖨 Print", key="print_issues")
    if issues_df.empty:
        st.success("No data issues found!")
    else:
        st.warning(f"{len(issues_df)} issue(s) found across {issues_df['Athlete Name'].nunique()} athlete(s)")
        st.dataframe(issues_df, width="stretch")
    if _iss_print_btn and not issues_df.empty:
        _open_print_view(
            f"Data Issues — {len(issues_df)} issue(s)",
            [("", issues_df)],
        )
