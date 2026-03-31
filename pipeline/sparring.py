"""
pipeline/sparring.py — Sparring extraction, division assignment, and data quality flags.

Handles both Olympic Sparring and Grass Root Sparring.
"""

import re
import pandas as pd

from .cleaning import TOURNAMENT_YEAR, WORLD_CLASS_COLS, get_birth_year

SPARRING_DISPLAY_COLS = [
    "Athlete Name",
    "School Name",
    "Pick Event(s) Below",
    "Weight in KG",
    "Division",
]


def _age_bracket(age: int) -> str:
    """Map an integer age to the corresponding TKD tournament age bracket name."""
    if age <= 5:
        return "Under 6"
    elif age <= 7:
        return "Dragon (6-7)"
    elif age <= 9:
        return "Tigers (8-9)"
    elif age <= 11:
        return "Youth (10-11)"
    elif age <= 14:
        return "Cadet (12-14)"
    elif age <= 17:
        return "Juniors (15-17)"
    elif age <= 32:
        return "Senior (17+)"
    elif age <= 45:
        return "Ultra (33-45)"
    else:
        return "Ultra (46+)"


def assign_division(row: pd.Series, world_class_cols: list[str]) -> str:
    """
    Assign a division string to a single sparring competitor row.

    Step 1 — check World Class columns in order; if any has a non-empty value,
    return '{column_header} {cell_value} Black Belt'.

    Step 2 — fallback: calculate age from DOB, map to age bracket, and return
    '{age_bracket} {gender} {belt_rank}'.
    """
    # Step 1: World Class columns
    for col in world_class_cols:
        val = row.get(col, "")
        if isinstance(val, str) and val.strip():
            return f"{col} {val.strip()} Black Belt"

    # Step 2: Fallback via age/gender/belt
    birth_year = get_birth_year(row.get("Date of Birth"))
    if birth_year is None:
        return "Unknown"

    age = TOURNAMENT_YEAR - birth_year
    bracket = _age_bracket(age)
    # Under 6 is an error state — include the actual age so reviewers can see it
    if bracket == "Under 6":
        bracket = f"Under 6 ({age})"
    gender = str(row.get("Gender", "")).strip()
    rank = str(row.get("Rank", "")).strip()

    return f"{bracket} {gender} {rank}"


def extract_sparring(clean_df: pd.DataFrame) -> pd.DataFrame:
    """
    Extract sparring competitors from the cleaned dataset and assign each a Division.

    A competitor qualifies if 'Pick Event(s) Below' contains 'Olympic Sparring'
    or 'Grass Root Sparring' (case-insensitive).

    Returns the full set of clean columns plus a 'Division' column so that
    downstream functions (flagging, display) can access all fields.
    """
    mask = clean_df["Pick Event(s) Below"].apply(
        lambda x: bool(
            re.search(r"(olympic sparring|grass root sparring)", str(x), re.IGNORECASE)
        )
    )
    sparring = clean_df[mask].copy()

    world_class_cols = [c for c in WORLD_CLASS_COLS if c in sparring.columns]
    sparring["Division"] = sparring.apply(
        lambda row: assign_division(row, world_class_cols), axis=1
    )

    return sparring.reset_index(drop=True)


def _parse_weight_range(division: str) -> tuple[float | None, float | None]:
    """
    Parse a weight range from a World Class division string.

    Returns (lower_exclusive, upper_inclusive):
      - 'Over 33 kg & not exceeding 37kg'  → (33.0, 37.0)
      - 'Not exceeding 30 kg'              → (None, 30.0)
      - 'Over 40 kg'                       → (40.0, None)
      - No match                           → (None, None)
    """
    m = re.search(r"[Oo]ver\s+([\d.]+)\s*kg.*?not exceeding\s+([\d.]+)\s*kg", division)
    if m:
        return float(m.group(1)), float(m.group(2))

    m = re.search(r"[Nn]ot exceeding\s+([\d.]+)\s*kg", division)
    if m:
        return None, float(m.group(1))

    m = re.search(r"[Oo]ver\s+([\d.]+)\s*kg", division)
    if m:
        return float(m.group(1)), None

    return None, None


def flag_issues(sparring_df: pd.DataFrame) -> pd.DataFrame:
    """
    Identify data quality issues in the sparring competitor list.

    Flags:
      1. Future date of birth (birth year > TOURNAMENT_YEAR)
      2. No weight entered (empty or 0) for non-World-Class competitors
         (World Class competitors don't rely on the weight field)
      3. Fallback division assigned but age bracket is 'Under 6' (likely DOB error)

    Flagged athletes are NOT removed from the sparring output — they are surfaced
    here for manual review.

    Returns a DataFrame with columns: Athlete Name, School, Issue, Raw Value
    """
    world_class_cols_present = [c for c in WORLD_CLASS_COLS if c in sparring_df.columns]
    flags: list[dict] = []

    for _, row in sparring_df.iterrows():
        name = row.get("Athlete Name", "")
        school = row.get("School Name", "")
        weight_raw = row.get("Weight in KG")
        division = str(row.get("Division", ""))
        dob = row.get("Date of Birth")

        has_world_class = any(
            isinstance(row.get(c, ""), str) and row.get(c, "").strip()
            for c in world_class_cols_present
        )

        # --- Flag 1: Future date of birth ---
        birth_year = get_birth_year(dob)
        if birth_year is not None and birth_year > TOURNAMENT_YEAR:
            flags.append({
                "Athlete Name": name,
                "School": school,
                "Issue": f"Future date of birth (birth year {birth_year})",
                "Raw Value": dob,
            })

        # --- Flag 2: No weight entered (only for non-World-Class competitors) ---
        if not has_world_class:
            no_weight = False
            try:
                if float(weight_raw) == 0:
                    no_weight = True
            except (TypeError, ValueError):
                if pd.isna(weight_raw) or str(weight_raw).strip() == "":
                    no_weight = True

            if no_weight:
                flags.append({
                    "Athlete Name": name,
                    "School": school,
                    "Issue": "No weight entered",
                    "Raw Value": weight_raw,
                })

        # --- Flag 3: Under 6 age bracket (likely DOB error) ---
        if division.startswith("Under 6"):
            flags.append({
                "Athlete Name": name,
                "School": school,
                "Issue": "Age bracket is Under 6 — possible DOB data entry error",
                "Raw Value": dob,
            })

    if flags:
        return pd.DataFrame(flags)
    return pd.DataFrame(columns=["Athlete Name", "School", "Issue", "Raw Value"])
