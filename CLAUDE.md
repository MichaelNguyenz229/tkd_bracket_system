## PROJECT

Taekwondo tournament data pipeline: raw registration CSV → clean data → event extraction → Streamlit app.

**Runtime:** uv (`~/.local/bin/uv run streamlit run app.py`)
**Data:** `data/` is git-ignored. Raw files are CSV (not TSV).

---

## CURRENT ARCHITECTURE

```
pipeline/
  __init__.py      re-exports public API
  cleaning.py      load_raw_data, clean_data, TOURNAMENT_YEAR, WORLD_CLASS_COLS, CLEAN_COLS
  sparring.py      extract_sparring, assign_division, flag_issues, SPARRING_DISPLAY_COLS
  bracket.py       build_bracket, seed_competitors
app.py             Streamlit UI (4 tabs: Clean Data, Sparring, Data Issues, Brackets)
requirements.txt   pandas, streamlit, openpyxl
```

---

## KEY BUSINESS RULES

- **Tournament year:** 2026 (age = 2026 − birth_year)
- **World Class division:** if any WORLD_CLASS_COLS column is non-empty → `"{col_header} {value} Black Belt"` (first match wins); Weight in KG is ignored entirely for World Class competitors
- **Fallback division:** `"{age_bracket} {gender} {belt_rank}"`; Under 6 gets `f"Under 6 ({age}) {gender} {rank}"`
- **Negative weights:** abs() them silently — no flag
- **Survey artifact:** "Team Partner Name" column in raw CSV actually holds "Please Confirm your Division Down Below" — renamed in clean_data()

### Age brackets (fallback)
| Age | Bracket |
|-----|---------|
| ≤5  | Under 6 |
| 6–7 | Dragon (6-7) |
| 8–9 | Tigers (8-9) |
| 10–11 | Youth (10-11) |
| 12–14 | Cadet (12-14) |
| 15–17 | Juniors (15-17) |
| 18–32 | Senior (17+) |
| 33–45 | Ultra (33-45) |
| 46+ | Ultra (46+) |

### Data quality flags (sparring only)
1. Future DOB (birth year > 2026)
2. No weight entered (empty or 0) — non-World-Class competitors only
3. Under 6 bracket assigned (likely DOB data entry error)

---

## BRACKET RULES

- Brackets are generated for **black belt divisions only** (division string ends with "Black Belt")
- Color belt divisions appear in the Sparring tab but not the Brackets tab

---

## UPCOMING WORK

- Poomsae extraction and division logic
- Demo / freestyle event modules
- Bracket generation improvements
