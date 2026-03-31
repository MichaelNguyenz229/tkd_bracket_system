"""
pipeline.py — Taekwondo tournament data cleaning and sparring extraction logic.
All functions are pure (no Streamlit imports) so they can be tested independently.
"""

import re
import pandas as pd

TOURNAMENT_YEAR = 2026

WORLD_CLASS_COLS = [
    "World Class Seniors - Male",
    "World Class Seniors - Female",
    "World Class Juniors - Female",
    "World Class Juniors - Male",
    "World Class Cadets - Male",
    "World Class Cadets - Female",
    "Youth - Male",
    "Youth - Female",
    "Tiger - Male",
    "Tiger - Female",
    "Dragon - Male",
    "Dragon - Female",
    "Ultra (33-45) - Male",
    "Ultra (33-45) - Female",
    "Ultra (46+) - Female",
    "Ultra (46+) - Male",
]

CLEAN_COLS = [
    "Athlete Name",
    "Date of Birth",
    "Gender",
    "Rank",
    "Dan",
    "School Name",
    "Pick Event(s) Below",
    "Weight in KG",
    "Please Confirm your Division Down Below",
] + WORLD_CLASS_COLS + [
    "Sport Pair Partner Name",
    "Freestyle Team Partner Name",
    "Freestyle Team Partner Name (2)",
    "Freestyle Pair Partner Name",
    "Freestyle Team Partner Name (3)",
    "Freestyle Team Partner Name (4)",
    "Freestyle Team Partner Name (5)",
    "Freestyle Team Partner Name (6)",
]

SPARRING_DISPLAY_COLS = [
    "Athlete Name",
    "School Name",
    "Pick Event(s) Below",
    "Weight in KG",
    "Division",
]


def load_raw_data(source) -> pd.DataFrame:
    """Load raw tournament CSV into a DataFrame from a file path or file-like object."""
    return pd.read_csv(source)


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and normalize raw tournament registration data.

    - Strips leading/trailing whitespace from all string cells
    - Drops rows with no athlete first name
    - Combines Athlete First Name + Last Name into a single Athlete Name column
    - Renames 'Team Partner Name' to 'Please Confirm your Division Down Below'
      (survey export artifact: that column holds the self-reported division string)
    - Normalizes Rank (strips extra whitespace)
    - Normalizes Pick Event(s) Below (strips whitespace around each comma-separated value)
    - Keeps only the relevant output columns (those that exist in the raw data)
    """
    df = df.copy()

    # Strip all string cells
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)

    # Drop rows with no athlete first name
    df = df.dropna(subset=["Athlete First Name"])
    df = df[df["Athlete First Name"].astype(str).str.strip() != ""]

    # Combine first + last name
    df["Athlete Name"] = (
        df["Athlete First Name"].fillna("").str.strip()
        + " "
        + df["Athlete Last Name"].fillna("").str.strip()
    ).str.strip()

    # The survey exports the main "Please Confirm your Division Down Below" value
    # under the column name "Team Partner Name" (platform artifact). Rename it.
    if "Team Partner Name" in df.columns:
        df = df.rename(columns={"Team Partner Name": "Please Confirm your Division Down Below"})

    # Normalize Rank: strip extra internal whitespace (e.g. "Black " → "Black")
    if "Rank" in df.columns:
        df["Rank"] = df["Rank"].apply(lambda x: " ".join(x.split()) if isinstance(x, str) else x)

    # Normalize events: strip whitespace around each comma-separated event
    if "Pick Event(s) Below" in df.columns:
        df["Pick Event(s) Below"] = df["Pick Event(s) Below"].apply(
            lambda x: ", ".join(e.strip() for e in x.split(",")) if isinstance(x, str) else x
        )

    # Abs-value any negative weights — negative sign is a data entry error
    if "Weight in KG" in df.columns:
        df["Weight in KG"] = pd.to_numeric(df["Weight in KG"], errors="coerce").abs()

    # Keep only columns that exist in this export
    cols_to_keep = [c for c in CLEAN_COLS if c in df.columns]
    return df[cols_to_keep].reset_index(drop=True)


def _get_birth_year(dob_str) -> int | None:
    """Parse a date-of-birth string and return the birth year, or None on failure."""
    try:
        return pd.to_datetime(dob_str).year
    except Exception:
        return None


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
    birth_year = _get_birth_year(row.get("Date of Birth"))
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
    # "Over X kg ... not exceeding Y kg"
    m = re.search(
        r"[Oo]ver\s+([\d.]+)\s*kg.*?not exceeding\s+([\d.]+)\s*kg", division
    )
    if m:
        return float(m.group(1)), float(m.group(2))

    # "Not exceeding X kg"
    m = re.search(r"[Nn]ot exceeding\s+([\d.]+)\s*kg", division)
    if m:
        return None, float(m.group(1))

    # "Over X kg" (open upper bound — last bracket)
    m = re.search(r"[Oo]ver\s+([\d.]+)\s*kg", division)
    if m:
        return float(m.group(1)), None

    return None, None


def flag_issues(sparring_df: pd.DataFrame) -> pd.DataFrame:
    """
    Identify data quality issues in the sparring competitor list.

    Flags:
      1. Future date of birth (birth year > TOURNAMENT_YEAR)
      2. Sparring competitor with no weight entered (empty or 0) AND no World Class
         division (World Class competitors don't rely on the weight field)
      3. Fallback division assigned but age bracket is 'Under 6' (likely DOB error)

    Weight is ignored for World Class competitors — their division already encodes
    the weight category via the World Class column they selected.

    Negative weights are corrected (abs-valued) during cleaning, not flagged here.

    Flagged athletes are NOT removed from the sparring output — they are surfaced
    here for manual review.

    Returns a DataFrame with columns:
      Athlete Name, School, Issue, Raw Value
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
        birth_year = _get_birth_year(dob)
        if birth_year is not None and birth_year > TOURNAMENT_YEAR:
            flags.append(
                {
                    "Athlete Name": name,
                    "School": school,
                    "Issue": f"Future date of birth (birth year {birth_year})",
                    "Raw Value": dob,
                }
            )

        # --- Flag 2: No weight entered (only for non-World-Class competitors) ---
        if not has_world_class:
            no_weight = False
            try:
                w = float(weight_raw)
                if w == 0:
                    no_weight = True
            except (TypeError, ValueError):
                if pd.isna(weight_raw) or str(weight_raw).strip() == "":
                    no_weight = True

            if no_weight:
                flags.append(
                    {
                        "Athlete Name": name,
                        "School": school,
                        "Issue": "No weight entered",
                        "Raw Value": weight_raw,
                    }
                )

        # --- Flag 3: Under 6 age bracket (likely DOB error) ---
        if division.startswith("Under 6"):
            flags.append(
                {
                    "Athlete Name": name,
                    "School": school,
                    "Issue": "Age bracket is Under 6 — possible DOB data entry error",
                    "Raw Value": dob,
                }
            )

    if flags:
        return pd.DataFrame(flags)
    return pd.DataFrame(columns=["Athlete Name", "School", "Issue", "Raw Value"])
