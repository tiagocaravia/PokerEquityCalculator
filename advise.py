"""
Advice for one spot: is the hand playable, and should you call a bet?

    Preflop, no bet:   PLAY / FOLD / CLOSE   (equity vs the fair share, 1 / players)
    Facing a bet:      CALL / FOLD / CLOSE   (equity vs pot odds, plus the EV of calling)

CLOSE means the equity is within a few points of break-even (or within the confidence
interval), so the answer depends on who you're up against. That's the part the bots
section will learn to handle.

Amounts are in big blinds unless you pass --bb (the big blind in chips), in which case
plain numbers are chips and get converted. "2.5bb" always means big blinds.

Usage (from the project folder):
    python3 advise.py                                           # asks you questions
    python3 advise.py --hole "AS 10S" --players 9               # preflop: playable?
    python3 advise.py --hole "KH KD" --board "KS 9H 4H 7C 2H" --pot 10 --bet pot --stack 40
    python3 advise.py --hole "QH JH" --board "10H 4C 2H" --opponents 2 --pot 60 --bet 20 --bb 2
"""
import argparse
import math

from poker.card import parse_card
from poker.decisions import advise_call, advise_preflop
from poker.equity import RandomOpponents, RangeOpponents, estimate_equity
from poker.iterated_sim import build_pool, hand_label, load_survivors, load_table

TABLE_SIMS = 10000  # Sims per hand used to build the preflop tables
BET_WORDS = {"third": 1 / 3, "half": 0.5, "pot": 1.0}


def parse_cards(text):
    cards = [parse_card(c) for c in text.split()]
    if any(c.suit is None or c.rank not in c.RANKS for c in cards):
        raise ValueError("Invalid card. Use RANK + SUIT, e.g. AH or 10S.")
    return cards


def parse_amount(text, bb):
    """An amount in big blinds. "2.5bb" is big blinds; a plain number is chips, divided by the big blind."""
    text = text.strip().lower()
    if text.endswith("bb"):
        return float(text[:-2])
    return float(text) / bb


def parse_bet(text, pot_before_bet, bb):
    """An amount ("50", "2.5bb"), a fraction of the pot ("third", "half", "pot", "75%") or a multiple ("2x")."""
    text = text.strip().lower()
    if text in BET_WORDS:
        return BET_WORDS[text] * pot_before_bet
    if text.endswith("%"):
        return float(text[:-1]) / 100 * pot_before_bet
    if text.endswith("x"):
        return float(text[:-1]) * pot_before_bet
    return parse_amount(text, bb)


def fmt_bb(x):
    return f"{x:g}bb" if x == round(x, 2) else f"{x:.2f}bb"


def pct(x):
    return f"{x * 100:.1f}%"


def opponent_models(num_players):
    """Random hands, plus the realistic (playable-only) range when there's a table for this table size."""
    models = [RandomOpponents()]
    try:
        models.append(RangeOpponents(build_pool(load_survivors(num_players)), "realistic"))
    except FileNotFoundError:
        pass
    return models


def preflop_equity(hole, num_players, sims):
    """Equity vs random hands. From the preflop table when there is one, so it matches 'playable'."""
    try:
        table = load_table(num_players)
        row = table[table["Hand"] == hand_label(*hole)].iloc[0]
        equity = row["equity"] / 100
        half_width = 1.96 * math.sqrt(equity * (1 - equity) / TABLE_SIMS)
        return equity, half_width, f"Standard{num_players}.csv"
    except FileNotFoundError:
        est = estimate_equity(hole, [], num_players - 1, sims)
        return est.equity, est.half_width, f"{sims:,} sims"


def show_preflop(hole, num_players, sims):
    equity, hw, source = preflop_equity(hole, num_players, sims)
    advice = advise_preflop(equity, hw, num_players)
    print(f"\n--- PREFLOP, {num_players} players ---")
    print(f"Equity vs random hands: {pct(equity)} ± {hw * 100:.1f}  ({source})")
    print(f"Fair share (1 / {num_players}): {pct(advice.break_even)}")
    print(f"\n→ {advice.action}")
    if advice.action == "CLOSE":
        print("  Near the cutoff: depends on position and who's at the table.")


def show_postflop_no_bet(hole, board, opponents, num_players, sims):
    print(f"\n--- NO BET TO CALL, {opponents} opponent{'s' * (opponents > 1)} ---")
    for model in opponent_models(num_players):
        est = estimate_equity(hole, board, opponents, sims, model)
        print(f"Equity vs {est.model:<10} {est}")
    print(f"Fair share: {pct(1 / (opponents + 1))}. Checking is free, so there's nothing to fold to.")


def show_facing_bet(hole, board, opponents, num_players, pot_before_bet, bet, stack, sims):
    """All amounts in big blinds. stack = your stack before calling (None if unknown)."""
    to_call = bet if stack is None else min(bet, stack)
    all_in = stack is not None and to_call >= stack
    # If you can't cover the whole bet you can only win the part you match
    pot = pot_before_bet + to_call

    print(f"\n--- FACING A BET: {fmt_bb(bet)} into {fmt_bb(pot_before_bet)} "
          f"({bet / pot_before_bet:.0%} pot), {opponents} opponent{'s' * (opponents > 1)} ---")
    if stack is not None:
        if all_in:
            print(f"Calling puts you all in for {fmt_bb(to_call)}"
                  + (f" (you can only win the {fmt_bb(to_call)} of their bet you match)" if to_call < bet else ""))
        else:
            behind = stack - to_call
            print(f"Stack: {fmt_bb(stack)}, {fmt_bb(behind)} behind after calling "
                  f"(stack-to-pot ratio {behind / (pot + to_call):.1f})")

    rows = []
    for model in opponent_models(num_players):
        est = estimate_equity(hole, board, opponents, sims, model)
        rows.append((est, advise_call(est.equity, est.half_width, pot, to_call)))

    print(f"Pot odds: call {fmt_bb(to_call)} to win {fmt_bb(pot)}, so you need {pct(rows[0][1].break_even)} equity\n")
    print(f"  {'vs':<11} {'equity':>13}   {'EV(call)':>18}")
    for est, adv in rows:
        print(f"  {est.model:<11} {str(est):>13}   {adv.ev:+8.2f} ± {adv.ev_half_width:<5.2f}bb  {adv.action}")

    final = rows[-1][1]  # Realistic opponents when we have a table, otherwise random
    print(f"\n→ {final.action}  (based on {rows[-1][0].model} opponents)")
    if final.action == "CLOSE":
        print("  Close to break-even: the right answer depends on how this player bets.")
    if all_in:
        print("  All-in call: no more betting after this, so pot odds are exact.")
    elif not all_in and len(board) < 5:
        print("  More betting can follow, so this ignores implied odds (what you win later when you hit).")
    for note in final.notes:
        print(f"  Note: {note}")


def main():
    parser = argparse.ArgumentParser(description="PLAY / FOLD / CLOSE advice and pot odds for one spot.")
    parser.add_argument("--hole", help='Your hole cards, e.g. "AS KH"')
    parser.add_argument("--board", default="", help="Community cards so far (0, 3, 4 or 5)")
    parser.add_argument("--players", type=int, default=None, help="Players dealt in (picks the preflop table)")
    parser.add_argument("--opponents", type=int, default=None, help="Opponents still in the hand")
    parser.add_argument("--pot", default=None, help='Pot before the bet you\'re facing, e.g. 12 or "12bb"')
    parser.add_argument("--bet", default=None, help='The bet: an amount, or "third", "half", "pot", "75%%", "2x"')
    parser.add_argument("--stack", default=None, help="Your stack before calling (enables all-in handling)")
    parser.add_argument("--bb", type=float, default=1.0,
                        help="Big blind in chips. Leave out if you're entering amounts in big blinds")
    parser.add_argument("--sims", type=int, default=5000, help="Simulations per equity estimate")
    args = parser.parse_args()

    interactive = args.hole is None
    if interactive:
        print("=== Advice ===  (card format: AS = ace of spades, 10H = ten of hearts)\n")
        args.hole = input("Your hole cards: ")
        args.board = input("Board so far (enter for preflop): ")

    hole, board = parse_cards(args.hole), parse_cards(args.board)
    cards = hole + board
    if len(hole) != 2 or len(board) not in (0, 3, 4, 5):
        parser.error("Need exactly 2 hole cards and 0, 3, 4 or 5 board cards.")
    if len({(c.rank, c.suit) for c in cards}) != len(cards):
        parser.error("Duplicate card.")

    if interactive:
        args.players = int(input("Players dealt in: ") or 9)
        if board:
            args.opponents = int(input("Opponents still in the hand (enter for 1): ") or 1)
        bet_text = input("Bet you're facing (enter for none): ").strip()
        if bet_text:
            args.bb = float(input("Big blind in chips (enter if you're using big blinds): ") or 1)
            args.pot = input("Pot before that bet: ")
            args.bet = bet_text
            args.stack = input("Your stack (enter to skip): ").strip() or None

    num_players = args.players or 9
    opponents = args.opponents or (num_players - 1 if not board else 1)
    if not 2 <= num_players <= 9 or not 1 <= opponents <= num_players - 1:
        parser.error("Players must be 2-9, and opponents between 1 and players - 1.")

    if args.bet:
        if args.bb <= 0:
            parser.error("--bb must be positive.")
        if args.pot is None:
            parser.error("Facing a bet needs --pot (the pot before the bet).")
        pot = parse_amount(args.pot, args.bb)
        if pot <= 0:
            parser.error("--pot must be positive.")
        bet = parse_bet(args.bet, pot, args.bb)
        stack = parse_amount(args.stack, args.bb) if args.stack else None
        if bet <= 0 or (stack is not None and stack <= 0):
            parser.error("The bet and stack must be positive.")
        if args.bb != 1:
            print(f"(1bb = {args.bb:g} chips; amounts below are in big blinds)")
        show_facing_bet(hole, board, opponents, num_players, pot, bet, stack, args.sims)
    elif not board:
        show_preflop(hole, num_players, args.sims)
    else:
        show_postflop_no_bet(hole, board, opponents, num_players, args.sims)


if __name__ == "__main__":
    main()
