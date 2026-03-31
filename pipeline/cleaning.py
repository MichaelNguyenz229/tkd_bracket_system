"""
pipeline/cleaning.py — Shared data loading and cleaning logic.

Used by all event modules (sparring, poomsae, demos, etc.).
"""

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
    - Abs-values negative weights (data entry errors)
    - Keeps only the relevant output columns (those that exist in the raw data)
    """
    df = df.copy()

    # Drop any fully duplicate columns (same name appearing more than once)
    df = df.loc[:, ~df.columns.duplicated()]

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
    # under the column name "Team Partner Name" (platform artifact). Rename it,
    # but only if the target column doesn't already exist (some exports have both).
    if "Team Partner Name" in df.columns and "Please Confirm your Division Down Below" not in df.columns:
        df = df.rename(columns={"Team Partner Name": "Please Confirm your Division Down Below"})
    elif "Team Partner Name" in df.columns and "Please Confirm your Division Down Below" in df.columns:
        df = df.drop(columns=["Team Partner Name"])

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


def get_birth_year(dob_str) -> int | None:
    """Parse a date-of-birth string and return the birth year, or None on failure."""
    try:
        return pd.to_datetime(dob_str).year
    except Exception:
        return None
