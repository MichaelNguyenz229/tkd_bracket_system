"""
pipeline/bracket.py — Single-elimination bracket generation for sparring divisions.
"""

import math
import pandas as pd


def build_bracket(competitors: list[str]) -> list[list[str | None]]:
    """
    Build a single-elimination bracket from an ordered list of competitor names.

    Seeds competitors into a power-of-2 bracket size, inserting BYE slots where
    needed. Returns a list of rounds, where each round is a flat list of names/BYEs.
    Round 0 is the first round (all slots), round 1 is the next, etc.

    Example with 3 competitors → bracket size 4:
      Round 0: ['Alice', 'BYE', 'Bob', 'Charlie']
      Round 1: ['Alice', winner(Bob/Charlie)]
      Round 2: [champion]
    """
    n = len(competitors)
    if n < 2:
        return [competitors[:]]

    size = 2 ** math.ceil(math.log2(n))
    byes_needed = size - n

    # Build seeded first round: top seeds get the BYEs
    # Interleave BYEs so they're distributed across the bracket
    slots: list[str | None] = []
    bye_count = 0
    for i, name in enumerate(competitors):
        slots.append(name)
        if bye_count < byes_needed:
            slots.append(None)  # BYE
            bye_count += 1

    # Pad to full size if needed
    while len(slots) < size:
        slots.append(None)

    rounds: list[list[str | None]] = [slots]

    # Generate subsequent rounds (winners TBD — show as "TBD")
    current = slots
    while len(current) > 1:
        next_round: list[str | None] = []
        for i in range(0, len(current), 2):
            a = current[i]
            b = current[i + 1] if i + 1 < len(current) else None
            if a is None and b is None:
                next_round.append(None)
            elif a is None:
                next_round.append(b)   # auto-advance on BYE
            elif b is None:
                next_round.append(a)   # auto-advance on BYE
            else:
                next_round.append("TBD")
        rounds.append(next_round)
        current = next_round

    return rounds


def seed_competitors(division_df: pd.DataFrame) -> list[str]:
    """
    Return competitors sorted by weight ascending (lightest = seed 1).
    Competitors with missing/zero weight are placed at the end.
    """
    df = division_df.copy()

    def _weight(val):
        try:
            w = float(val)
            return w if w > 0 else float("inf")
        except (TypeError, ValueError):
            return float("inf")

    df["_sort_weight"] = df["Weight in KG"].apply(_weight)
    df = df.sort_values("_sort_weight")
    return df["Athlete Name"].tolist()
