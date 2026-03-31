I'm migrating a Taekwondo tournament data pipeline from Google Apps Script to Python + Streamlit.
I'll give you the full context below — existing logic, data samples, and exactly what to build.

---

## CONTEXT

### What the pipeline does
1. Takes a raw tournament registration CSV
2. Cleans and normalizes it into a "clean" dataset
3. From the clean data, extracts sparring competitors into a separate view
4. Assigns each sparring competitor a "Division" string
5. Displays everything in a Streamlit app with data quality flagging

### Scope for now
Only handle sparring (Olympic Sparring + Grass Root Sparring).
Poomsae, bracket generation, and team/pair grouping will be handled in a later prompt.

---

## INPUT DATA STRUCTURE (raw CSV columns)

Key columns after cleaning:
- Athlete Name (combined first + last)
- Date of Birth
- Gender
- Rank (belt color)
- Dan
- School Name
- Pick Event(s) Below (comma-separated, e.g. "Olympic Sparring, Traditional Poomsae")
- Weight in KG
- Please Confirm your Division Down Below
- World Class division columns (World Class Seniors - Male, World Class Seniors - Female,
  World Class Juniors - Female, World Class Juniors - Male, World Class Cadets - Male,
  World Class Cadets - Female, Youth - Male, Youth - Female, Tiger - Male, Tiger - Female,
  Dragon - Male, Dragon - Female, Ultra (33-45) - Male, Ultra (33-45) - Female,
  Ultra (46+) - Female, Ultra (46+) - Male)
- Partner columns (Sport Pair Partner Name, Freestyle Team Partner Names, etc.) — ignore for now

---

## CLEANING LOGIC (ported from Google Apps Script)

- Drop all empty/blank rows
- Strip all leading/trailing whitespace from every cell
- Combine first name + last name into a single "Athlete Name" column
  (raw data has them split — join with a space)
- Normalize belt rank: strip extra spaces (some entries have "Black " with trailing space)
- Normalize event field: strip whitespace around each comma-separated event
- Age is calculated as: 2026 - birth_year (tournament year is 2026)

---

## SPARRING EXTRACTION LOGIC (ported from Google Apps Script)

A competitor is a sparring competitor if their "Pick Event(s) Below" field contains
either "Olympic Sparring" OR "Grass Root Sparring" (case-insensitive match).

Output columns for the sparring sheet:
- Athlete Name
- School Name
- Pick Event(s) Below
- Weight in KG
- Division (calculated — see logic below)

### Division Assignment Logic

Step 1 — Check the World Class division columns (in this order):
  World Class Seniors - Male, World Class Seniors - Female,
  World Class Juniors - Female, World Class Juniors - Male,
  World Class Cadets - Male, World Class Cadets - Female,
  Youth - Male, Youth - Female, Tiger - Male, Tiger - Female,
  Dragon - Male, Dragon - Female, Ultra (33-45) - Male,
  Ultra (33-45) - Female, Ultra (46+) - Female, Ultra (46+) - Male

  If any of these columns has a non-empty value for this competitor, the division is:
  "{column_header} {cell_value} Black Belt"
  (use the first non-empty column found, then stop)

Step 2 — Fallback (if no World Class column is filled):
  Calculate age from DOB (2026 - birth_year), map to age bracket:
    6-7   → Dragon (6-7)
    8-9   → Tigers (8-9)
    10-11 → Youth (10-11)
    12-14 → Cadet (12-14)
    15-17 → Juniors (15-17)
    18-32 → Senior (17+)
    33-45 → Ultra (33-45)
    46+   → Ultra (46+)

  Division string = "{age_bracket} {gender} {belt_rank}"

---

## DATA QUALITY FLAGS

These should NOT be silently dropped or auto-fixed.
Collect them and display them in a dedicated "⚠️ Data Issues" section in the Streamlit UI.

Flag the following:
1. Negative weight (e.g. -51 kg)
2. Future date of birth (birth year > 2026)
3. Weight/division mismatch: competitor has a World Class division assigned but their
   weight_kg doesn't fall within the weight range stated in that division string
   (parse the kg range from the division string to check)
4. Sparring competitor with no weight entered (empty or 0)
5. Division assigned as fallback but age bracket is "Under 6" (age <= 5) —
   likely a DOB data entry error

Each flagged row should show: Athlete Name, School, issue description, and the raw value
that triggered the flag. Do not exclude flagged athletes from the sparring output —
highlight them but keep them in.

---

## STREAMLIT APP STRUCTURE

Page layout:
1. Sidebar — upload CSV button
2. Main area tabs:
   Tab 1: "📋 Clean Data" — show the full cleaned dataframe
   Tab 2: "🥊 Sparring" — show the sparring dataframe, grouped/sorted by Division
   Tab 3: "⚠️ Data Issues" — show all flagged rows with issue descriptions
3. Each tab should have a download button to export that tab's data as CSV

Styling:
- Highlight flagged athletes in the Sparring tab with a yellow background row
- Show a small summary at the top of the Sparring tab:
  total competitors, breakdown by event type (Olympic Sparring vs Grass Root Sparring)


---

## OUTPUT FILES EXPECTED

- app.py — main Streamlit app
- pipeline.py — all cleaning + sparring extraction logic as pure functions
- requirements.txt — pandas, streamlit, openpyxl

---

## NOTES

- Do not hardcode column indices — find columns dynamically by header name
- The raw CSV uses tab-separated values (TSV), not comma-separated
- Age calculation uses tournament year 2026 (hardcoded is fine)
- Keep all logic in pipeline.py, keep app.py thin (just UI calls)
- Add a short docstring to each function explaining what it does
- Lets do uv instead of typical conda venv or normal venv