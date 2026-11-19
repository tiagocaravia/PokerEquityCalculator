import math
import random
from dataclasses import dataclass

from .deck import Deck
from .evaluator import best_hand

Z_95 = 1.96


def key(card):
    return (card.rank, card.suit)


class RandomOpponents:
    name = "random"

    def deal(self, deck, num_opponents):
        hands = random.sample(deck, 2 * num_opponents)
        return [hands[2 * i: 2 * i + 2] for i in range(num_opponents)]


class RangeOpponents:
    def __init__(self, pool, name="range"):
        self.pool = pool  # list of 2-card hands
        self.name = name

    def deal(self, deck, num_opponents):
        live = {key(c) for c in deck}
        available = [h for h in self.pool if key(h[0]) in live and key(h[1]) in live]
        hands = []
        for _ in range(num_opponents):
            if not available:
                raise ValueError("Opponent range has no hands left after removing known cards.")
            hand = random.choice(available)
            hands.append(hand)
            taken = {key(hand[0]), key(hand[1])}
            available = [h for h in available if key(h[0]) not in taken and key(h[1]) not in taken]
        return hands


def pot_share(my_rank, opponent_ranks): # 1 win, 0 loss, 1/k split
    best_opp = max(opponent_ranks)
    if my_rank > best_opp:
        return 1.0
    if my_rank < best_opp:
        return 0.0
    return 1 / (1 + sum(1 for r in opponent_ranks if r == best_opp))


@dataclass
class EquityEstimate:
    equity: float       # 0-1, average share of the pot at showdown
    half_width: float   # 95% CI half-width, 0-1
    sims: int
    model: str

    def __str__(self):
        return f"{self.equity * 100:.1f}% ± {self.half_width * 100:.1f}"


def estimate_equity(hole_cards, board, num_opponents, num_simulations=5000, model=None): # Equity + 95% CI vs a model
    model = model or RandomOpponents()
    known = hole_cards + board
    deck = [c for c in Deck().cards if c not in known]

    cards_needed = 5 - len(board)
    total = total_sq = 0.0
    for _ in range(num_simulations):
        opponents = model.deal(deck, num_opponents)
        used = {key(c) for h in opponents for c in h}
        rest = [c for c in deck if key(c) not in used]
        runout = board + random.sample(rest, cards_needed)
        share = pot_share(best_hand(hole_cards + runout), [best_hand(h + runout) for h in opponents])
        total += share
        total_sq += share * share

    n = num_simulations
    mean = total / n
    var = max(total_sq / n - mean * mean, 0) * n / (n - 1)
    return EquityEstimate(mean, Z_95 * math.sqrt(var / n), n, model.name)
