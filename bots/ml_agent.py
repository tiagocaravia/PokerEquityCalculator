import math
import os

os.environ.setdefault("OMP_NUM_THREADS", "1")  # one thread: much faster for one-spot predictions

from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor

from poker.decisions import advise_call
from poker.ranges import EDGE

from .pool import COMBOS
from .profiles import AIR

MEDIUM = 0.15  # no-read guess: how often in-between hands bet the river
BET_SIZES = (0.5, 0.75, 1.25)  # pot fractions the ML bot can bet
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache", "ml_model.joblib")
CALL_FEATURES = ["hand strength", "equity vs their range", "equity vs their bet (ranged)", "bet size (pot)",
                 "pot odds needed", "guided EV of calling", "bluff share (read)", "their bets seen",
                 "their call rate (read)", "hands of evidence"]
BET_FEATURES = ["hand strength", "equity vs their range", "bet size (pot)", "guided EV of this action",
                "guided EV of checking", "their call rate (read)", "our bets they answered",
                "bluff share (read)", "hands of evidence"]

# CONFLICT[i] marks every hand that shares a card with hand i
_onehot = np.zeros((len(COMBOS), 52), dtype=np.float32)
_onehot[np.arange(len(COMBOS)), COMBOS[:, 0]] = 1
_onehot[np.arange(len(COMBOS)), COMBOS[:, 1]] = 1
CONFLICT = (_onehot @ _onehot.T) > 0


def soft_keep(x, cut): # numpy version of poker.ranges.soft_keep
    return 1 / (1 + np.exp(np.clip((x - cut) / EDGE, -50, 50)))


@dataclass
class Spot: # What the bot can see
    pool: object
    board: int     # board index in the pool
    mine: int      # our hand (combo index)
    pot: float

    def their_range(self): # Hands they could hold: played preflop, not using our cards or the board's
        live = self.pool.rank[self.board] >= 0
        return np.where(live & ~CONFLICT[self.mine], self.pool.played, 0.0)

    def strengths(self):
        return np.nan_to_num(self.pool.strength[self.board], nan=0.0)

    def share_beaten(self, weights): # Our equity vs a weighted range of their hands
        ranks = self.pool.rank[self.board]
        mine = ranks[self.mine]
        total = weights.sum()
        if total == 0:
            return 0.5
        return float((weights[ranks < mine].sum() + 0.5 * weights[ranks == mine].sum()) / total)


class Agent: # The hand-built bot: the ML bot's guidance, and the baselines
    def __init__(self, name, learns=True, mixes=True, oracle=False, prior_weight=8, bet_size=0.75):
        self.name = name
        self.learns = learns
        self.mixes = mixes
        self.oracle = oracle
        self.k = prior_weight    # how many hands' worth of trust the no-read assumption gets
        self.bet_size = bet_size

    def new_opponent(self, profile): # Forget everything; the oracle peeks at the real profile
        self.truth = profile if self.oracle else None
        self.bets_seen = self.bluffs_seen = 0
        self.calls = self.folds = 0

    # --- reads ---
    def bluff_share(self, bet_ratio): # Share of their bets we think are bluffs
        balanced = bet_ratio / (1 + 2 * bet_ratio)
        if not self.learns:
            return balanced
        return (self.bluffs_seen + self.k * balanced) / (self.bets_seen + self.k)

    def call_rate(self): # How often we think they call our bet
        balanced = 1 / (1 + self.bet_size)
        if not self.learns:
            return balanced
        return (self.calls + self.k * balanced) / (self.calls + self.folds + self.k)

    def evidence(self):
        return (self.bets_seen + self.calls + self.folds) if self.learns else 0

    # --- facing their bet ---
    def betting_range(self, spot, bet_ratio): # Their range after they bet: value + bluffs (+ a few in-between)
        base, s = spot.their_range(), spot.strengths()
        if self.truth:
            p = self.truth
            bets = np.where(s >= p.value_cut, 1.0, np.where(s < AIR, p.bluff, p.medium_bet))
            return base * bets
        value = 1 - soft_keep(s, min(0.92, 0.65 + 0.20 * bet_ratio))
        air = soft_keep(s, AIR)
        middle = np.clip(1 - value - air, 0, None)
        q = self.bluff_share(bet_ratio)
        value_mass = (base * (value + MEDIUM * middle)).sum()
        air_mass = (base * air).sum()
        bluff_w = 0.0 if air_mass == 0 else min(1.0, q / (1 - q) * value_mass / air_mass)
        return base * (value + bluff_w * air + MEDIUM * middle)

    def equity_vs_bet(self, spot, bet):
        equity = spot.share_beaten(self.betting_range(spot, bet / spot.pot))
        n = 0 if self.truth else self.evidence()
        half_width = 0.0 if self.truth else 1.96 * math.sqrt(max(equity * (1 - equity), 1e-9) / (self.k + n))
        return equity, half_width

    def respond(self, spot, bet, rng): # Call (True) or fold (False)
        equity, half_width = self.equity_vs_bet(spot, bet)
        advice = advise_call(equity, half_width, spot.pot + bet, bet, bet_in_range=True)
        if self.mixes:
            return rng.random() < advice.call_probability
        return equity >= advice.break_even

    def saw_their_bet(self, their_strength): # Showdown after we called
        self.bets_seen += 1
        self.bluffs_seen += their_strength < AIR

    # --- our bet ---
    def bet_evs(self, spot, bet): # (EV of betting, EV of checking) in bb, from what we know about them
        base, s = spot.their_range(), spot.strengths()
        ranks = spot.pool.rank[spot.board]
        mine = ranks[spot.mine]
        total = base.sum()
        if self.truth:
            calls = s >= self.truth.call_cut
        else:  # they call with their strongest hands, as many as their call rate says
            order = np.argsort(-s)
            share = np.cumsum(base[order]) / total
            calls = np.zeros(len(s), dtype=bool)
            calls[order[share <= self.call_rate()]] = True
        fold = base[~calls].sum() / total
        win = base[calls & (ranks < mine)].sum() / total
        lose = base[calls & (ranks > mine)].sum() / total
        pot = spot.pot
        ev_bet = fold * pot / 2 + (win - lose) * (pot / 2 + bet)
        ev_check = spot.share_beaten(base) * pot - pot / 2
        return ev_bet, ev_check

    def wants_to_bet(self, spot): # Bet size, or None to check
        bet = self.bet_size * spot.pot
        ev_bet, ev_check = self.bet_evs(spot, bet)
        return bet if ev_bet > ev_check else None

    def finish_hand(self, net): # Told how much the hand won or lost; the ML bot learns from this
        pass

    def saw_response(self, called):
        if called:
            self.calls += 1
        else:
            self.folds += 1


def new_model():
    return HistGradientBoostingRegressor(max_iter=200, learning_rate=0.08, max_leaf_nodes=31,
                                         min_samples_leaf=80, l2_regularization=1.0)


class MLAgent(Agent): # Hand-built reads + ranging as features; two GBMs predict each action's profit

    def __init__(self, name="ml", explore=0.1, models=None):
        super().__init__(name, learns=True, mixes=False)
        self.explore = explore  # chance of trying a random action, to keep learning
        self.call_model, self.bet_model = models or (None, None)
        self.call_data, self.bet_data = [], []  # (features, profit) from finished hands
        self.pending = None
        self.rng = np.random.default_rng(7)
        self.spot_log = None  # set to {"call": [], "bet": []} to record every spot it decides

    # --- features (the guidance) ---
    def call_features(self, spot, bet):
        equity, _ = self.equity_vs_bet(spot, bet)
        ratio = bet / spot.pot
        break_even = bet / (spot.pot + 2 * bet)
        guided_ev = equity * (spot.pot + 2 * bet) - bet - spot.pot / 2  # hand-built EV of calling, as profit
        return [float(spot.pool.strength[spot.board, spot.mine]), spot.share_beaten(spot.their_range()),
                equity, ratio, break_even, guided_ev, self.bluff_share(ratio), self.bets_seen,
                self.call_rate(), self.evidence()]

    def bet_features(self, spot, size, evs):
        ev_bet, ev_check = evs
        return [float(spot.pool.strength[spot.board, spot.mine]), spot.share_beaten(spot.their_range()),
                size, ev_bet if size else ev_check, ev_check, self.call_rate(), self.calls + self.folds,
                self.bluff_share(0.75), self.evidence()]

    # --- decisions ---
    def respond(self, spot, bet, rng):
        x = self.call_features(spot, bet)
        if self.spot_log is not None:
            self.spot_log["call"].append(x)
        if self.call_model is None:
            call = super().respond(spot, bet, rng)  # no model yet: follow the guidance
        else:
            call = self.call_model.predict([x])[0] > -spot.pot / 2  # folding loses exactly our half of the pot
        if self.rng.random() < self.explore:
            call = self.rng.random() < 0.5
        self.pending = ("call", x) if call else None  # folds have a known result; nothing to learn
        return call

    def wants_to_bet(self, spot):
        options = [0.0] + list(BET_SIZES)
        rows = []
        for size in options:
            evs = self.bet_evs(spot, max(size, 0.01) * spot.pot)
            rows.append(self.bet_features(spot, size, evs))
        if self.spot_log is not None:
            self.spot_log["bet"].append(rows)
        if self.rng.random() < self.explore:
            choice = int(self.rng.integers(len(options)))
        elif self.bet_model is None:  # no model yet: hand-built choice among the sizes
            choice = int(np.argmax([r[3] for r in rows]))
        else:
            choice = int(np.argmax(self.bet_model.predict(rows)))
        self.pending = ("bet", rows[choice])
        size = options[choice]
        return size * spot.pot if size else None

    def finish_hand(self, net):
        if self.pending:
            kind, x = self.pending
            (self.call_data if kind == "call" else self.bet_data).append((x, net))
        self.pending = None

    # --- training ---
    def train(self):
        for kind in ("call", "bet"):
            data = self.call_data if kind == "call" else self.bet_data
            if len(data) < 500:
                continue
            X = np.array([x for x, _ in data])
            y = np.array([net for _, net in data])
            model = new_model().fit(X, y)
            if kind == "call":
                self.call_model = model
            else:
                self.bet_model = model

    def frozen(self, name="ml"): # A copy that only plays (no exploring, no data collection)
        bot = MLAgent(name, explore=0.0, models=(self.call_model, self.bet_model))
        bot.finish_hand = lambda net: None
        return bot


def lineup(): # The hand-built bot versions the arena compares
    return [
        Agent("no read", learns=False, mixes=False),
        Agent("no read + mixing", learns=False, mixes=True),
        Agent("learner", learns=True, mixes=True),
        Agent("learner, no mixing", learns=True, mixes=False),
        Agent("oracle", oracle=True, mixes=False),
    ]
