import math
import random
from collections import Counter
from dataclasses import dataclass
from itertools import combinations

from .deck import Deck
from .equity import RandomOpponents, key, pot_share
from .evaluator import best_hand
from .tables import hand_label, load_table

TABLE_SIZES = (3, 5, 7, 9)  # Preflop tables we have
EDGE = 0.03                 # How soft range edges are
CATEGORY = ["High card", "One pair", "Two pair", "Three of a kind", "Straight",
            "Flush", "Full house", "Four of a kind", "Straight flush"]

STREET_ACTIONS = ("check", "bet", "call", "raise")
SIZE_WORDS = {"third": 1 / 3, "half": 0.5, "pot": 1.0}


def parse_street_action(text): # "bet half" -> ("bet", 0.5); "check" -> ("check", None)
    words = text.strip().lower().split()
    if not words or words[0] not in STREET_ACTIONS:
        raise ValueError
    action, size = words[0], None
    if action == "bet":
        size = 0.5
        if len(words) > 1:
            w = words[1]
            if w in SIZE_WORDS:
                size = SIZE_WORDS[w]
            elif w.endswith("%"):
                size = float(w[:-1]) / 100
            elif w.endswith("x"):
                size = float(w[:-1])
            else:
                raise ValueError
    return action, size


def draw_type(combo, board): # Strongest draw the combo adds: flush, straight, gutshot or None
    if len(board) >= 5:
        return None
    cards = combo + board
    for suit in {c.suit for c in combo}:
        if sum(c.suit == suit for c in cards) == 4:
            return "Flush draw"
    mine, theirs = _straight_outs(cards), _straight_outs(board)
    new = mine - theirs
    if _has_straight(_values(cards)) or not new:
        return None
    return "Straight draw" if len(mine) >= 2 else "Gutshot"


def _values(cards):
    vals = {c.rank_value for c in cards}
    return vals | {-1} if 12 in vals else vals  # ace plays low too


def _has_straight(vals):
    return any(all(v + k in vals for k in range(5)) for v in range(-1, 9))


def _straight_outs(cards): # Ranks that would complete a straight
    vals = _values(cards)
    if _has_straight(vals):
        return set()
    outs = set()
    for r in range(13):
        if r not in vals and _has_straight(vals | {r} | ({-1} if r == 12 else set())):
            outs.add(r)
    return outs


PREFLOP_ACTIONS = {
    "none": "play", "check": None,
    "limp": "call", "call": "call",
    "raise": "raise", "open": "raise",
    "raise big": "big", "3bet": "big", "4bet": "big", "allin": "big", "all in": "big",
}


@dataclass
class Tendencies: # How a player plays; defaults = no read
    play_pct: float = 0.45         # plays the top 45% of hands (when we didn't see the action)
    raise_pct: float = 0.20        # opens with the top 20% of hands
    big_raise_pct: float = 0.06    # big raises / 3-bets with the top 6%
    call_pct: float = 0.40         # calls/limps with hands inside the top 40%
    slowplay: float = 0.35         # how often top hands just call preflop
    bluff_share: float | None = None  # share of river bets that are bluffs; None = balanced
    air_cutoff: float = 0.50       # river hands weaker than this are bluff candidates
    medium_bet: float = 0.15       # how often in-between hands bet the river
    flop_bluff: float = 0.40       # missed hands that bet the flop (c-bet bluffs)
    turn_bluff: float = 0.25       # missed hands that bet the turn
    semi_bluff: float = 0.60       # flush / open-ended straight draws that bet
    gutshot_bet: float = 0.30      # gutshots that bet
    early_medium_bet: float = 0.35 # in-between hands that bet the flop/turn
    trap: float = 0.35             # strong hands that check instead of betting
    float_call: float = 0.15       # missed hands that call a bet anyway


NO_READ = Tendencies()


def short_label(a, b): # AKo, AA, JTs
    hi, lo = sorted((a, b), key=lambda c: c.rank_value, reverse=True)
    name = "".join("T" if c.rank == "10" else c.rank for c in (hi, lo))
    return name if hi.rank == lo.rank else name + ("s" if hi.suit == lo.suit else "o")


def soft_keep(position, cutoff): # 1 inside the cutoff, fading to 0 outside
    return 1 / (1 + math.exp((position - cutoff) / EDGE))


def preflop_percentiles(num_players): # Hand label -> share of combos at least as strong
    size = min(TABLE_SIZES, key=lambda n: abs(n - num_players))
    table = load_table(size).sort_values("equity", ascending=False)
    counts = Counter(hand_label(a, b) for a, b in combinations(Deck().cards, 2))
    percentiles, seen = {}, 0
    for label in table["Hand"]:
        seen += counts[label]
        percentiles[label] = seen / 1326
    return percentiles


class Range:
    def __init__(self, dead_cards):
        dead = {key(c) for c in dead_cards}
        self.combos = [list(c) for c in combinations(Deck().cards, 2)
                       if key(c[0]) not in dead and key(c[1]) not in dead]
        self.weights = [1.0] * len(self.combos)
        self.history = []

    def total(self):
        return sum(self.weights)

    def preflop(self, action, num_players, t=NO_READ): # Narrow by their preflop action
        kind = PREFLOP_ACTIONS.get(action.strip().lower())
        if kind is None:
            return
        pct = preflop_percentiles(num_players)
        for i, (a, b) in enumerate(self.combos):
            p = pct[hand_label(a, b)]
            if kind == "play":
                w = soft_keep(p, t.play_pct)
            elif kind == "raise":
                w = soft_keep(p, t.raise_pct)
            elif kind == "big":
                w = soft_keep(p, t.big_raise_pct)
            else:
                w = soft_keep(p, t.call_pct) * (t.slowplay if p < t.big_raise_pct else 1)
            self.weights[i] *= w
        self.history.append("played a hand preflop" if kind == "play" else f"{action} preflop")

    def strengths(self, board): # Share of all live hands each combo beats or ties on this board
        on_board = {key(b) for b in board}
        is_live = lambda c: key(c[0]) not in on_board and key(c[1]) not in on_board
        rank_of = {i: best_hand(c + board) for i, c in enumerate(self.combos) if is_live(c)}
        ranks = sorted(rank_of.values())
        out = []
        for i in range(len(self.combos)):
            if i not in rank_of:
                out.append(None)
                continue
            r = rank_of[i]
            lo, hi = 0, len(ranks)
            while lo < hi:  # count of ranks <= r
                mid = (lo + hi) // 2
                if ranks[mid] <= r:
                    lo = mid + 1
                else:
                    hi = mid
            out.append(lo / len(ranks))
        return out

    def river_bet(self, board, pot_before, bet, t=NO_READ): # Narrow by a river bet: value + bluffs
        ratio = bet / pot_before
        value_cut = min(0.92, 0.65 + 0.20 * ratio)  # bigger bets, stronger value
        s = self.strengths(board)
        value, air = [0.0] * len(s), [0.0] * len(s)
        for i, x in enumerate(s):
            if x is None:
                self.weights[i] = 0.0
                continue
            value[i] = 1 - soft_keep(x, value_cut)
            air[i] = soft_keep(x, t.air_cutoff)
        value_mass = sum(w * v for w, v in zip(self.weights, value))
        air_mass = sum(w * a for w, a in zip(self.weights, air))

        share = t.bluff_share if t.bluff_share is not None else bet / (pot_before + 2 * bet)  # balanced
        bluff_w = 0.0 if air_mass == 0 else min(1.0, share / (1 - share) * value_mass / air_mass)
        for i in range(len(self.weights)):
            middle = max(0.0, 1 - value[i] - air[i])
            self.weights[i] *= value[i] + bluff_w * air[i] + t.medium_bet * middle
        self.bluff_weight = bluff_w
        self.history.append(f"bet {bet:g} into {pot_before:g} on the river")

    def street_action(self, board, action, size=None, t=NO_READ): # Narrow by a flop/turn action
        size = size or 0.5
        s = self.strengths(board)
        flop = len(board) == 3
        for i, x in enumerate(s):
            if x is None:
                self.weights[i] = 0.0
                continue
            draw = draw_type(self.combos[i], board)
            value_cut = min(0.90, (0.60 if action != "raise" else 0.75) + 0.15 * size)
            value = 1 - soft_keep(x, value_cut)
            air = soft_keep(x, t.air_cutoff) * (0 if draw else 1)
            middle = max(0.0, 1 - value - air) * (0 if draw else 1)
            drawing = {"Flush draw": t.semi_bluff, "Straight draw": t.semi_bluff,
                       "Gutshot": t.gutshot_bet}.get(draw, 0)
            if action == "bet":
                bluff = t.flop_bluff if flop else t.turn_bluff
                w = value + air * bluff + middle * t.early_medium_bet + (1 - value) * drawing
            elif action == "raise":
                w = value + air * 0.1 + middle * 0.05 + (1 - value) * drawing * 0.6
            elif action == "call":
                w = value * 0.6 + middle + air * t.float_call + (1 - value) * (1.0 if draw else 0)
            else:  # check
                w = value * t.trap + middle + air * 0.8 + (1 - value) * (1 - drawing if draw else 0)
            self.weights[i] *= w
        street = "flop" if flop else "turn"
        label = action if action != "bet" else f"bet {size:.0%} pot"
        self.history.append(f"{label} on the {street}")

    def river_equity(self, hole, board): # Exact equity vs this range, heads-up
        mine = best_hand(hole + board)
        blocked = {key(c) for c in hole}
        num = den = 0.0
        for c, w in zip(self.combos, self.weights):
            if w == 0 or key(c[0]) in blocked or key(c[1]) in blocked:
                continue
            num += w * pot_share(mine, [best_hand(c + board)])
            den += w
        return num / den if den else float("nan")

    def breakdown(self, hole, board): # Hand categories, and how many beat you
        mine = best_hand(hole + board)
        blocked = {key(c) for c in hole}
        cats, beats, ties, total = {}, 0.0, 0.0, 0.0
        for c, w in zip(self.combos, self.weights):
            if w == 0 or key(c[0]) in blocked or key(c[1]) in blocked:
                continue
            r = best_hand(c + board)
            cats[CATEGORY[r[0]]] = cats.get(CATEGORY[r[0]], 0) + w
            total += w
            if r > mine:
                beats += w
            elif r == mine:
                ties += w
        cats = sorted(((k, v / total) for k, v in cats.items()), key=lambda kv: -kv[1])
        return cats, beats / total, ties / total

    def draws(self, hole, board): # Share of the range on each kind of draw
        blocked = {key(c) for c in hole}
        out, total = {}, 0.0
        for c, w in zip(self.combos, self.weights):
            if w == 0 or key(c[0]) in blocked or key(c[1]) in blocked:
                continue
            total += w
            d = draw_type(c, board)
            if d:
                out[d] = out.get(d, 0) + w
        return sorted(((k, v / total) for k, v in out.items()), key=lambda kv: -kv[1])

    def top_hands(self, n=6): # Most likely hand types
        types = {}
        for (a, b), w in zip(self.combos, self.weights):
            label = short_label(a, b)
            types[label] = types.get(label, 0) + w
        total = sum(types.values())
        return [(k, v / total) for k, v in sorted(types.items(), key=lambda kv: -kv[1])[:n]]


class RangeModel: # Opponent model: the first opponent comes from the range, any others from `others`
    def __init__(self, rng, others=None, name="ranged"):
        self.rng = rng
        self.others = others or RandomOpponents()
        self.name = name

    def deal(self, deck, num_opponents):
        if getattr(self, "_deck_id", None) != id(deck):  # same deck every trial: filter once
            live = {key(c) for c in deck}
            options = [(c, w) for c, w in zip(self.rng.combos, self.rng.weights)
                       if w > 0 and key(c[0]) in live and key(c[1]) in live]
            self._hands, self._weights = [c for c, _ in options], [w for _, w in options]
            self._deck_id = id(deck)
        first = random.choices(self._hands, weights=self._weights)[0]
        if num_opponents == 1:
            return [first], first
        rest = [c for c in deck if key(c) not in {key(first[0]), key(first[1])}]
        hands, dealt = self.others.deal(rest, num_opponents - 1)
        return [first] + hands, list(first) + dealt
