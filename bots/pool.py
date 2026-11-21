import os
import time
from itertools import combinations

import numpy as np

from poker.deck import Deck
from poker.evaluator import best_hand
from poker.iterated_sim import hand_label
from poker.ranges import preflop_percentiles, soft_keep

CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache", "river_boards.npz")
CARDS = Deck().cards
COMBOS = np.array(list(combinations(range(52), 2)))  # all 1,326 two-card hands, as card ids
PLAY_PCT = 0.45  # players reach the river with roughly their top 45% of hands


class Pool:
    def __init__(self, boards, strength, rank, played):
        self.boards = boards        # (B, 5) card ids
        self.strength = strength    # (B, 1326) share of live hands each hand beats or ties; nan if it uses a board card
        self.rank = rank            # (B, 1326) showdown order, higher wins; -1 if it uses a board card
        self.played = played        # (1326,) how likely each hand is to be played preflop

    def deal(self, rng): # A board plus two disjoint played hands
        b = rng.integers(len(self.boards))
        live = self.rank[b] >= 0
        weights = np.where(live, self.played, 0.0)
        weights /= weights.sum()
        while True:
            a, c = rng.choice(len(COMBOS), size=2, p=weights)
            if not set(COMBOS[a]) & set(COMBOS[c]):
                return b, a, c


def played_weights():
    pct = preflop_percentiles(9)
    return np.array([soft_keep(pct[hand_label(CARDS[i], CARDS[j])], PLAY_PCT) for i, j in COMBOS])


def build(num_boards=1000, seed=1):
    rng = np.random.default_rng(seed)
    boards = np.zeros((num_boards, 5), dtype=np.int8)
    strength = np.full((num_boards, len(COMBOS)), np.nan, dtype=np.float32)
    rank = np.full((num_boards, len(COMBOS)), -1, dtype=np.int16)
    start = time.time()
    for b in range(num_boards):
        board = rng.choice(52, size=5, replace=False)
        boards[b] = board
        cards = [CARDS[i] for i in board]
        live = [k for k, (i, j) in enumerate(COMBOS) if i not in board and j not in board]
        ranks = [best_hand([CARDS[COMBOS[k][0]], CARDS[COMBOS[k][1]]] + cards) for k in live]
        ranks = [(r[0], tuple(r[1])) for r in ranks]  # hashable
        order = {r: n for n, r in enumerate(sorted(set(ranks)))}  # dense showdown order
        dense = np.array([order[r] for r in ranks])
        sorted_dense = np.sort(dense)
        below = np.searchsorted(sorted_dense, dense, side="left")
        equal = np.searchsorted(sorted_dense, dense, side="right") - below
        strength[b, live] = (below + 0.5 * equal) / len(live)
        rank[b, live] = dense
        if (b + 1) % 100 == 0:
            print(f"  {b + 1}/{num_boards} boards ({time.time() - start:.0f}s)", flush=True)
    return Pool(boards, strength, rank, played_weights())


def load():
    if not os.path.exists(CACHE):
        print("First run: scoring every hand on 1,000 real river boards (about 45 seconds, then it's cached)...")
        pool = build()
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        np.savez_compressed(CACHE, boards=pool.boards, strength=pool.strength, rank=pool.rank, played=pool.played)
        return pool
    data = np.load(CACHE)
    return Pool(data["boards"], data["strength"], data["rank"], data["played"])
