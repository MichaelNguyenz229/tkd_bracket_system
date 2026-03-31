"""
pipeline/demo.py — Generates a realistic fake tournament dataset for demo mode.

Produces a clean_df, sparring_df, and issues_df that exercise all app features:
multiple divisions, both event types, World Class competitors, color belts,
multiple schools, and a couple of intentional data issues.
"""

import pandas as pd
from .cleaning import TOURNAMENT_YEAR, WORLD_CLASS_COLS
from .sparring import extract_sparring, flag_issues, assign_division

_SCHOOLS = [
    "Tigers ATA",
    "Dragon TKD Academy",
    "Elite Martial Arts",
    "AAU Champions Club",
    "Riverside TKD",
    "Apex Taekwondo",
]

_RANKS = ["White", "Yellow", "Green", "Blue", "Red", "Black"]

def _make_clean_df() -> pd.DataFrame:
    rows = [
        # ── World Class Black Belt competitors ────────────────────────────────
        {"Athlete Name": "James Park",      "Date of Birth": "1998-03-12", "Gender": "Male",   "Rank": "Black", "Dan": "2", "School Name": "Tigers ATA",          "Pick Event(s) Below": "Olympic Sparring",           "Weight in KG": 68.0,  "World Class Seniors - Male":   "Over 63 kg & not exceeding 68kg"},
        {"Athlete Name": "Kevin Tran",       "Date of Birth": "2000-07-04", "Gender": "Male",   "Rank": "Black", "Dan": "1", "School Name": "Dragon TKD Academy",   "Pick Event(s) Below": "Olympic Sparring",           "Weight in KG": 54.0,  "World Class Seniors - Male":   "Not exceeding 54kg"},
        {"Athlete Name": "Marcus Lee",       "Date of Birth": "1997-11-19", "Gender": "Male",   "Rank": "Black", "Dan": "3", "School Name": "Elite Martial Arts",   "Pick Event(s) Below": "Olympic Sparring",           "Weight in KG": 74.0,  "World Class Seniors - Male":   "Over 68 kg & not exceeding 74kg"},
        {"Athlete Name": "Daniel Kim",       "Date of Birth": "1999-05-30", "Gender": "Male",   "Rank": "Black", "Dan": "1", "School Name": "AAU Champions Club",   "Pick Event(s) Below": "Olympic Sparring",           "Weight in KG": 80.0,  "World Class Seniors - Male":   "Over 74 kg & not exceeding 80kg"},
        {"Athlete Name": "Sofia Reyes",      "Date of Birth": "2001-02-14", "Gender": "Female", "Rank": "Black", "Dan": "1", "School Name": "Riverside TKD",        "Pick Event(s) Below": "Olympic Sparring",           "Weight in KG": 57.0,  "World Class Seniors - Female": "Over 53 kg & not exceeding 57kg"},
        {"Athlete Name": "Aisha Patel",      "Date of Birth": "1999-08-22", "Gender": "Female", "Rank": "Black", "Dan": "2", "School Name": "Apex Taekwondo",       "Pick Event(s) Below": "Olympic Sparring",           "Weight in KG": 62.0,  "World Class Seniors - Female": "Over 57 kg & not exceeding 62kg"},
        {"Athlete Name": "Mia Nguyen",       "Date of Birth": "2000-12-01", "Gender": "Female", "Rank": "Black", "Dan": "1", "School Name": "Tigers ATA",           "Pick Event(s) Below": "Olympic Sparring",           "Weight in KG": 49.0,  "World Class Seniors - Female": "Not exceeding 49kg"},
        {"Athlete Name": "Elena Vasquez",    "Date of Birth": "1998-04-17", "Gender": "Female", "Rank": "Black", "Dan": "2", "School Name": "Dragon TKD Academy",   "Pick Event(s) Below": "Olympic Sparring",           "Weight in KG": 53.0,  "World Class Seniors - Female": "Over 49 kg & not exceeding 53kg"},

        # ── World Class Juniors ───────────────────────────────────────────────
        {"Athlete Name": "Liam Cho",         "Date of Birth": "2009-06-10", "Gender": "Male",   "Rank": "Black", "Dan": "1", "School Name": "Elite Martial Arts",   "Pick Event(s) Below": "Olympic Sparring",           "Weight in KG": 45.0,  "World Class Juniors - Male":   "Not exceeding 45kg"},
        {"Athlete Name": "Noah Yun",         "Date of Birth": "2010-03-25", "Gender": "Male",   "Rank": "Black", "Dan": "1", "School Name": "AAU Champions Club",   "Pick Event(s) Below": "Olympic Sparring",           "Weight in KG": 51.0,  "World Class Juniors - Male":   "Over 45 kg & not exceeding 51kg"},
        {"Athlete Name": "Ethan Bae",        "Date of Birth": "2009-09-14", "Gender": "Male",   "Rank": "Black", "Dan": "1", "School Name": "Riverside TKD",        "Pick Event(s) Below": "Olympic Sparring",           "Weight in KG": 55.0,  "World Class Juniors - Male":   "Over 51 kg & not exceeding 55kg"},
        {"Athlete Name": "Lily Shin",        "Date of Birth": "2010-01-08", "Gender": "Female", "Rank": "Black", "Dan": "1", "School Name": "Apex Taekwondo",       "Pick Event(s) Below": "Olympic Sparring",           "Weight in KG": 42.0,  "World Class Juniors - Female": "Not exceeding 42kg"},
        {"Athlete Name": "Grace Oh",         "Date of Birth": "2009-11-20", "Gender": "Female", "Rank": "Black", "Dan": "1", "School Name": "Tigers ATA",           "Pick Event(s) Below": "Olympic Sparring",           "Weight in KG": 47.0,  "World Class Juniors - Female": "Over 42 kg & not exceeding 47kg"},

        # ── Fallback Black Belt (age-bracket) ─────────────────────────────────
        {"Athlete Name": "Ryan Choi",        "Date of Birth": "2012-07-03", "Gender": "Male",   "Rank": "Black", "Dan": "1", "School Name": "Dragon TKD Academy",   "Pick Event(s) Below": "Grass Root Sparring",        "Weight in KG": 38.0},
        {"Athlete Name": "Tyler Kang",       "Date of Birth": "2013-02-18", "Gender": "Male",   "Rank": "Black", "Dan": "1", "School Name": "Elite Martial Arts",   "Pick Event(s) Below": "Grass Root Sparring",        "Weight in KG": 41.0},
        {"Athlete Name": "Hannah Moon",      "Date of Birth": "2012-10-05", "Gender": "Female", "Rank": "Black", "Dan": "1", "School Name": "AAU Champions Club",   "Pick Event(s) Below": "Grass Root Sparring",        "Weight in KG": 36.0},
        {"Athlete Name": "Claire Jung",      "Date of Birth": "2013-05-22", "Gender": "Female", "Rank": "Black", "Dan": "1", "School Name": "Riverside TKD",        "Pick Event(s) Below": "Grass Root Sparring",        "Weight in KG": 39.0},

        # ── Color Belt competitors ─────────────────────────────────────────────
        {"Athlete Name": "Tommy Nguyen",     "Date of Birth": "2014-04-11", "Gender": "Male",   "Rank": "Blue",  "Dan": "",  "School Name": "Apex Taekwondo",       "Pick Event(s) Below": "Grass Root Sparring",        "Weight in KG": 32.0},
        {"Athlete Name": "Jason Wu",         "Date of Birth": "2015-08-30", "Gender": "Male",   "Rank": "Green", "Dan": "",  "School Name": "Tigers ATA",           "Pick Event(s) Below": "Grass Root Sparring",        "Weight in KG": 28.0},
        {"Athlete Name": "Amy Chen",         "Date of Birth": "2014-12-19", "Gender": "Female", "Rank": "Red",   "Dan": "",  "School Name": "Dragon TKD Academy",   "Pick Event(s) Below": "Grass Root Sparring",        "Weight in KG": 30.0},
        {"Athlete Name": "Sara Kim",         "Date of Birth": "2015-03-07", "Gender": "Female", "Rank": "Blue",  "Dan": "",  "School Name": "Elite Martial Arts",   "Pick Event(s) Below": "Grass Root Sparring",        "Weight in KG": 27.0},
        {"Athlete Name": "Chris Hong",       "Date of Birth": "2016-06-14", "Gender": "Male",   "Rank": "Yellow","Dan": "",  "School Name": "AAU Champions Club",   "Pick Event(s) Below": "Grass Root Sparring",        "Weight in KG": 24.0},
        {"Athlete Name": "Emma Park",        "Date of Birth": "2016-09-02", "Gender": "Female", "Rank": "Yellow","Dan": "",  "School Name": "Riverside TKD",        "Pick Event(s) Below": "Grass Root Sparring",        "Weight in KG": 22.0},

        # ── Athletes in multiple events ───────────────────────────────────────
        {"Athlete Name": "Alex Santos",      "Date of Birth": "2003-01-15", "Gender": "Male",   "Rank": "Black", "Dan": "1", "School Name": "Apex Taekwondo",       "Pick Event(s) Below": "Olympic Sparring, Traditional Poomsae", "Weight in KG": 60.0, "World Class Seniors - Male": "Over 58 kg & not exceeding 63kg"},
        {"Athlete Name": "Diana Lopez",      "Date of Birth": "2004-07-28", "Gender": "Female", "Rank": "Black", "Dan": "1", "School Name": "Tigers ATA",           "Pick Event(s) Below": "Olympic Sparring, Traditional Poomsae", "Weight in KG": 46.0, "World Class Seniors - Female": "Over 42 kg & not exceeding 46kg"},

        # ── Intentional data issues ───────────────────────────────────────────
        # Issue 1: no weight entered (non-WC competitor)
        {"Athlete Name": "Sam Rivers",       "Date of Birth": "2013-03-10", "Gender": "Male",   "Rank": "Black", "Dan": "1", "School Name": "Dragon TKD Academy",   "Pick Event(s) Below": "Grass Root Sparring",        "Weight in KG": None},
        # Issue 2: future date of birth
        {"Athlete Name": "Zoe Future",       "Date of Birth": "2028-05-01", "Gender": "Female", "Rank": "Red",   "Dan": "",  "School Name": "Elite Martial Arts",   "Pick Event(s) Below": "Grass Root Sparring",        "Weight in KG": 25.0},
    ]

    # Fill missing World Class cols with empty string
    for row in rows:
        for col in WORLD_CLASS_COLS:
            row.setdefault(col, "")
        row.setdefault("Dan", "")
        row.setdefault("Please Confirm your Division Down Below", "")
        row.setdefault("Sport Pair Partner Name", "")
        row.setdefault("Freestyle Team Partner Name", "")
        row.setdefault("Freestyle Team Partner Name (2)", "")
        row.setdefault("Freestyle Pair Partner Name", "")
        row.setdefault("Freestyle Team Partner Name (3)", "")
        row.setdefault("Freestyle Team Partner Name (4)", "")
        row.setdefault("Freestyle Team Partner Name (5)", "")
        row.setdefault("Freestyle Team Partner Name (6)", "")

    return pd.DataFrame(rows).reset_index(drop=True)


def load_demo_data() -> tuple:
    """
    Return (clean_df, sparring_df, issues_df) populated with realistic fake data.
    Exercises all app features: World Class + fallback divisions, both event types,
    color belts, multiple schools, and intentional data issues.
    """
    clean_df = _make_clean_df()
    sparring_df = extract_sparring(clean_df)
    issues_df = flag_issues(sparring_df)
    return clean_df, sparring_df, issues_df
