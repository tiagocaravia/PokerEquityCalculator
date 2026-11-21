import random
from dataclasses import dataclass, replace

AIR = 0.5  # hands weaker than this (share of hands beaten) count as missed / bluffs


@dataclass
class Profile: # How an opponent plays the river; strength = share of hands it beats
    name: str
    value_cut: float   # bets for value at or above this strength
    bluff: float       # bets this often with missed hands
    medium_bet: float  # bets this often with in-between hands
    bet_size: float    # bet as a fraction of the pot
    call_cut: float    # calls a bet at or above this strength

    def bets(self, strength, u): # Bet or check; u is a random number in [0, 1)
        if strength >= self.value_cut:
            return True
        if strength < AIR:
            return u < self.bluff
        return u < self.medium_bet

    def calls(self, strength, bet_ratio=0.75): # Call or fold; bigger bets need stronger hands
        return strength >= min(0.98, self.call_cut + 0.15 * (bet_ratio - 0.75))


PRESETS = {
    "nit":             Profile("nit", value_cut=0.85, bluff=0.05, medium_bet=0.05, bet_size=0.75, call_cut=0.70),
    "regular":         Profile("regular", value_cut=0.75, bluff=0.30, medium_bet=0.10, bet_size=0.75, call_cut=0.45),
    "calling station": Profile("calling station", value_cut=0.70, bluff=0.05, medium_bet=0.20, bet_size=0.5, call_cut=0.20),
    "maniac":          Profile("maniac", value_cut=0.65, bluff=0.70, medium_bet=0.50, bet_size=1.2, call_cut=0.35),
}

HELD_OUT = {  # only used for testing, never for training
    "tricky":          Profile("tricky", value_cut=0.82, bluff=0.45, medium_bet=0.02, bet_size=1.5, call_cut=0.55),
}


def random_profile(rng, presets=PRESETS): # A preset with every number nudged, so no two opponents are identical
    base = rng.choice(list(presets.values()))
    jitter = lambda x, spread, lo, hi: min(hi, max(lo, x + rng.uniform(-spread, spread)))
    return replace(
        base,
        value_cut=jitter(base.value_cut, 0.05, 0.55, 0.95),
        bluff=jitter(base.bluff, 0.10, 0.0, 1.0),
        medium_bet=jitter(base.medium_bet, 0.05, 0.0, 1.0),
        bet_size=jitter(base.bet_size, 0.15, 0.33, 2.0),
        call_cut=jitter(base.call_cut, 0.07, 0.05, 0.95),
    )
