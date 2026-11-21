from dataclasses import dataclass, field


@dataclass
class Settings:
    close_margin: float = 0.03          # CLOSE band: ±3 points
    big_bet_ratio: float = 0.5          # big bet: half pot or more
    big_bet_extra_margin: float = 0.05  # wider CLOSE band for big bets


DEFAULT = Settings()


@dataclass
class Advice:
    action: str                      # PLAY / FOLD / CLOSE, or CALL / FOLD / CLOSE
    equity: float                    # 0-1
    half_width: float                # 95% CI half-width of the equity, 0-1
    break_even: float                # equity needed, 0-1
    ev: float | None = None          # EV of calling (same units as pot)
    ev_half_width: float | None = None
    call_probability: float = 1.0    # how often to take the yes action; mixed in CLOSE spots
    notes: list = field(default_factory=list)


def required_equity(pot, to_call): # Pot odds
    return to_call / (pot + to_call)


def ev_call(equity, pot, to_call): # EV of calling vs folding
    return equity * (pot + to_call) - to_call


def mix_probability(equity, half_width, break_even, margin): # Chance of the yes action
    band = max(margin, half_width)
    return min(1.0, max(0.0, 0.5 + (equity - break_even) / (2 * band)))


def verdict(equity, half_width, break_even, margin, yes="CALL"): # Above, below or close
    band = max(margin, half_width)
    if equity - break_even > band:
        return yes
    if break_even - equity > band:
        return "FOLD"
    return "CLOSE"


def advise_preflop(equity, half_width, num_players, settings=DEFAULT): # Playable?
    fair_share = 1 / num_players
    action = verdict(equity, half_width, fair_share, settings.close_margin, yes="PLAY")
    return Advice(action, equity, half_width, fair_share)


def advise_call(equity, half_width, pot, to_call, settings=DEFAULT, bet_in_range=False): # Call or fold? (pot includes the bet)
    break_even = required_equity(pot, to_call)
    pot_before_bet = pot - to_call
    # bet_in_range: the opponent model already accounts for this bet, so no big-bet adjustment
    big = not bet_in_range and pot_before_bet > 0 and to_call / pot_before_bet >= settings.big_bet_ratio
    margin = settings.close_margin + (settings.big_bet_extra_margin if big else 0)

    advice = Advice(
        action=verdict(equity, half_width, break_even, margin),
        equity=equity,
        half_width=half_width,
        break_even=break_even,
        ev=ev_call(equity, pot, to_call),
        ev_half_width=half_width * (pot + to_call),
        call_probability=mix_probability(equity, half_width, break_even, margin),
    )
    if big:
        advice.notes.append("Big bet: players who bet this much usually hold stronger hands (or bluffs) "
                            "than these models deal them, so the equity here is likely too optimistic.")
    return advice
