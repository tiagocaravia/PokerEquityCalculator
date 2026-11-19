"""
Turns an equity estimate into advice: PLAY / FOLD / CLOSE preflop, CALL / FOLD / CLOSE facing a bet.

Everything here is plain math on numbers you pass in (no simulation), so bots can call it
directly. The knobs worth tuning before a competition are all in Settings.

Conventions:
    pot      = everything in the middle right now, including the bet you're facing
    to_call  = what it costs you to call
"""
from dataclasses import dataclass, field


@dataclass
class Settings:
    close_margin: float = 0.03       # within 3 equity points of break-even counts as CLOSE
    big_bet_ratio: float = 0.5       # a bet of half the pot (before the bet) or more counts as big
    big_bet_extra_margin: float = 0.05  # widen CLOSE for big bets: bettors' ranges are stronger than our models assume


DEFAULT = Settings()


@dataclass
class Advice:
    action: str                      # PLAY / FOLD / CLOSE, or CALL / FOLD / CLOSE
    equity: float                    # 0-1
    half_width: float                # 95% CI half-width of the equity, 0-1
    break_even: float                # equity needed, 0-1
    ev: float | None = None          # EV of calling, in chips (None when there's no bet)
    ev_half_width: float | None = None
    notes: list = field(default_factory=list)


def required_equity(pot, to_call):
    """Pot odds: the equity you need to break even on a call."""
    return to_call / (pot + to_call)


def ev_call(equity, pot, to_call):
    """Expected chips from calling, compared with folding (worth 0: chips already in are gone)."""
    return equity * (pot + to_call) - to_call


def verdict(equity, half_width, break_even, margin, yes="CALL"):
    """yes if clearly above break-even, FOLD if clearly below, CLOSE if it's within the margin or the CI."""
    band = max(margin, half_width)
    if equity - break_even > band:
        return yes
    if break_even - equity > band:
        return "FOLD"
    return "CLOSE"


def advise_preflop(equity, half_width, num_players, settings=DEFAULT):
    """Preflop with no raise: is the hand playable? Playable means equity >= fair share (1 / players)."""
    fair_share = 1 / num_players
    action = verdict(equity, half_width, fair_share, settings.close_margin, yes="PLAY")
    return Advice(action, equity, half_width, fair_share)


def advise_call(equity, half_width, pot, to_call, settings=DEFAULT):
    """Facing a bet: call or fold, from pot odds and EV."""
    break_even = required_equity(pot, to_call)
    pot_before_bet = pot - to_call
    big = pot_before_bet > 0 and to_call / pot_before_bet >= settings.big_bet_ratio
    margin = settings.close_margin + (settings.big_bet_extra_margin if big else 0)

    advice = Advice(
        action=verdict(equity, half_width, break_even, margin),
        equity=equity,
        half_width=half_width,
        break_even=break_even,
        ev=ev_call(equity, pot, to_call),
        ev_half_width=half_width * (pot + to_call),
    )
    if big:
        advice.notes.append("Big bet: players who bet this much usually hold stronger hands (or bluffs) "
                            "than these models deal them, so the equity here is likely too optimistic.")
    return advice
