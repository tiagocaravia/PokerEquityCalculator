import os
import re
from itertools import combinations

import pandas as pd

from .card import Card
from .deck import Deck

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Data")


def hand_label(c1, c2): # "10J Suited", "22 Offsuit": the label the tables use
    lo, hi = sorted([c1, c2], key=lambda c: Card.RANKS.index(c.rank))
    kind = "Suited" if c1.suit == c2.suit else "Offsuit"
    return f"{lo.rank}{hi.rank} {kind}"


def load_table(num_players): # The preflop table for this many players, with an equity column
    df = pd.read_csv(os.path.join(DATA, f"Standard{num_players}.csv"))
    if "equity%" in df:
        df["equity"] = df["equity%"]
    else:  # older tables: ties approximated
        df["equity"] = df["win%"] + df["tie%"] / num_players
    return df


def load_survivors(num_players): # Playable hands: equity at least the fair share
    df = load_table(num_players)
    return df[df["equity"] >= 100 / num_players]


def build_pool(survivors): # Every two-card combo of the playable hands
    keep = set(survivors["Hand"])
    return [list(pair) for pair in combinations(Deck().cards, 2) if hand_label(*pair) in keep]


def find_hand(text, num_players): # "J10 Suited", "10J suited" or "AA" -> that hand's row, or None
    parts = text.upper().split()
    ranks = re.findall(r"10|[2-9JQKA]", parts[0])
    if len(ranks) != 2:
        return None
    lo, hi = sorted(ranks, key=Card.RANKS.index)
    kind = "Suited" if len(parts) > 1 and parts[1].startswith("S") and lo != hi else "Offsuit"
    match = load_table(num_players).query("Hand == @lo + @hi + ' ' + @kind")
    return None if match.empty else match.drop(columns="equity").iloc[0].to_dict()
