# AAU Tournament Data Preprocessor

A Streamlit web app that takes raw AAU Taekwondo tournament registration CSVs and turns them into clean, filtered, and bracket-ready views for tournament organizers.

---

## What it does

1. **Ingests** a raw registration CSV exported from the survey platform
2. **Cleans** the data — combines names, normalizes ranks and events, fixes negative weights, renames mislabeled columns
3. **Extracts** sparring competitors and assigns each one a division string
4. **Flags** data quality issues (missing weights, future DOBs, Under 6 bracket errors)
5. **Displays** everything across four views with filters and download buttons
6. **Generates** single-elimination brackets for black belt divisions

---

## Running the app

```bash
~/.local/bin/uv run streamlit run app.py
```

A demo mode is available on the upload screen — no data required to explore the app.

---

## Project structure

```
pipeline/
  __init__.py      re-exports public API
  cleaning.py      load_raw_data, clean_data — shared by all event modules
  sparring.py      extract_sparring, assign_division, flag_issues
  bracket.py       build_bracket, seed_competitors
  demo.py          load_demo_data — generates fake tournament data for demo mode
app.py             Streamlit UI (sidebar nav: Clean Data, Sparring, Data Issues, Brackets)
images/
  AAU_logo.png
requirements.txt
```

---

## The four views

### 📋 Clean Data
Full cleaned athlete roster. Filterable by belt type, gender, and groupable by school.

### 🥊 Sparring
Sparring competitors only (Olympic Sparring + Grass Root Sparring). Shows metrics at the top, filterable by belt type and gender, groupable by division, event type, or school. Flagged athletes are highlighted in yellow.

### ⚠️ Data Issues
All athletes with data quality problems and a description of each issue. An alert banner with a "View Issues →" shortcut appears on all other pages when issues exist and can be dismissed.

### 🏆 Brackets
Single-elimination brackets for black belt divisions only. Each competitor card shows name and school. Seeding is by weight (lightest first). Color belt divisions are excluded.

---

## Division assignment logic

**Step 1 — World Class check:** if any of the 16 World Class columns is non-empty, the division is `"{column_header} {cell_value} Black Belt"` (first match wins). Weight in KG is ignored for these competitors.

**Step 2 — Fallback:** age bracket (2026 − birth year) + gender + belt rank. Under 6 gets `"Under 6 ({age}) {gender} {rank}"`.

| Age | Bracket |
|-----|---------|
| ≤5 | Under 6 |
| 6–7 | Dragon (6-7) |
| 8–9 | Tigers (8-9) |
| 10–11 | Youth (10-11) |
| 12–14 | Cadet (12-14) |
| 15–17 | Juniors (15-17) |
| 18–32 | Senior (17+) |
| 33–45 | Ultra (33-45) |
| 46+ | Ultra (46+) |

---

## Data quality flags

| Flag | Condition |
|------|-----------|
| Future DOB | Birth year > 2026 |
| No weight | Weight empty or 0 — non-World-Class competitors only |
| Under 6 bracket | Age ≤ 5 — likely a DOB entry error |

---

## Upcoming

- Poomsae extraction and division logic
- Demo / freestyle event modules
