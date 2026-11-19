import argparse
import math
import sys

from poker.prompts import NONE_WORDS, again, ask, ask_cards, cards_from, interactive_loop
from poker.decisions import advise_call, advise_preflop
from poker.equity import RandomOpponents, RangeOpponents, estimate_equity
from poker.iterated_sim import build_pool, hand_label, load_survivors, load_table

TABLE_SIMS = 10000  # Sims per hand in the tables
BET_WORDS = {"third": 1 / 3, "half": 0.5, "pot": 1.0}


def parse_amount(text, bb): # Amount in big blinds
    text = text.strip().lower()
    if text.endswith("bb"):
        return float(text[:-2])
    return float(text) / bb


def parse_bet(text, pot_before_bet, bb): # Bet size in big blinds
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


def opponent_models(num_players): # Random + realistic ranges
    models = [RandomOpponents()]
    try:
        models.append(RangeOpponents(build_pool(load_survivors(num_players)), "realistic"))
    except FileNotFoundError:
        pass
    return models


def preflop_equity(hole, num_players, sims): # Equity vs random hands
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


def show_facing_bet(hole, board, opponents, num_players, pot_before_bet, bet, stack, sims): # Call/fold report, in bb
    to_call = bet if stack is None else min(bet, stack)
    all_in = stack is not None and to_call >= stack
    # Can only win what you match
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

    final = rows[-1][1]  # Realistic if available
    print(f"\n→ {final.action}  (based on {rows[-1][0].model} opponents)")
    if final.action == "CLOSE":
        print("  Close to break-even: the right answer depends on how this player bets.")
    if all_in:
        print("  All-in call: no more betting after this, so pot odds are exact.")
    elif not all_in and len(board) < 5:
        print("  More betting can follow, so this ignores implied odds (what you win later when you hit).")
    for note in final.notes:
        print(f"  Note: {note}")


def run(hole_str, board_str, players, opponents, sims, bet_text="", pot_text="", stack_text="", bb=1.0):
    hole, board = cards_from(hole_str), cards_from(board_str)
    if bet_text:
        pot = parse_amount(pot_text, bb)
        bet = parse_bet(bet_text, pot, bb)
        stack = parse_amount(stack_text, bb) if stack_text else None
        if bb != 1:
            print(f"(1bb = {bb:g} chips; amounts below are in big blinds)")
        show_facing_bet(hole, board, opponents, players, pot, bet, stack, sims)
    elif not board:
        show_preflop(hole, players, sims)
    else:
        show_postflop_no_bet(hole, board, opponents, players, sims)


def positive(parse): # Parser that rejects zero/negative
    def wrapped(text):
        value = parse(text)
        if value <= 0:
            raise ValueError
        return text
    return wrapped


def interactive():
    print("=== Advice ===  (cards like AS or 10H; enter keeps the value in brackets)")
    print('Amounts are in big blinds unless you give a big blind size. Bets can be "half", "pot", "2x", "75%".\n')
    hole, board, players, postflop_opponents, sims = "AS KH", "", 9, 1, 5000
    bet, pot, stack, bb = "", "", "", 1.0
    while True:
        hole = ask_cards("Your hole cards", hole, [2])
        board = ask_cards("Board (none for preflop)", board, [0, 3, 4, 5], taken=cards_from(hole))
        players = ask("Players dealt in", players, int, lambda n: None if 2 <= n <= 9 else "2 to 9.")
        if board:
            postflop_opponents = ask("Opponents still in the hand", min(postflop_opponents, players - 1), int,
                                     lambda n: None if 1 <= n <= players - 1 else f"1 to {players - 1}.")
            opponents = postflop_opponents
        else:
            opponents = players - 1
        bet = ask("Bet you're facing (none if no bet)", bet or "none")
        bet = "" if bet.lower() in NONE_WORDS else bet
        if bet:
            bb = ask("Big blind in chips (1 if you're typing big blinds)", bb, float,
                     lambda x: None if x > 0 else "Must be positive.")
            pot = ask("Pot before that bet", pot or None, positive(lambda t: parse_amount(t, bb)))
            if not _valid_bet(bet, pot, bb):
                print("  Couldn't read that bet. Try an amount, half, pot, 2x or 75%.")
                bet = ""
                continue
            stack = ask("Your stack (none to skip)", stack or "none")
            stack = "" if stack.lower() in NONE_WORDS else stack
            if stack and not _valid_amount(stack, bb):
                print("  Couldn't read that stack, skipping it.")
                stack = ""
        sims = ask("Simulations", sims, int, lambda n: None if n >= 100 else "At least 100.")
        run(hole, board, players, opponents, sims, bet, pot, stack, bb)
        if not again():
            break


def _valid_amount(text, bb):
    try:
        return parse_amount(text, bb) > 0
    except ValueError:
        return False


def _valid_bet(text, pot_text, bb):
    try:
        return parse_bet(text, parse_amount(pot_text, bb), bb) > 0
    except ValueError:
        return False


def main():
    if len(sys.argv) == 1:
        return interactive_loop(interactive)

    parser = argparse.ArgumentParser(description="PLAY / FOLD / CLOSE advice and pot odds for one spot. "
                                                 "Run with no options to be asked for each input.")
    parser.add_argument("--hole", required=True, help='Your hole cards, e.g. "AS KH"')
    parser.add_argument("--board", default="", help="Community cards so far (0, 3, 4 or 5)")
    parser.add_argument("--players", type=int, default=9, help="Players dealt in (picks the preflop table)")
    parser.add_argument("--opponents", type=int, default=None, help="Opponents still in the hand")
    parser.add_argument("--pot", default=None, help='Pot before the bet you\'re facing, e.g. 12 or "12bb"')
    parser.add_argument("--bet", default=None, help='The bet: an amount, or "third", "half", "pot", "75%%", "2x"')
    parser.add_argument("--stack", default=None, help="Your stack before calling (enables all-in handling)")
    parser.add_argument("--bb", type=float, default=1.0,
                        help="Big blind in chips. Leave out if you're entering amounts in big blinds")
    parser.add_argument("--sims", type=int, default=5000, help="Simulations per equity estimate")
    args = parser.parse_args()

    try:
        hole, board = cards_from(args.hole), cards_from(args.board)
    except ValueError:
        parser.error("Invalid card. Use RANK + SUIT, e.g. AH or 10S.")
    cards = hole + board
    if len(hole) != 2 or len(board) not in (0, 3, 4, 5):
        parser.error("Need exactly 2 hole cards and 0, 3, 4 or 5 board cards.")
    if len({(c.rank, c.suit) for c in cards}) != len(cards):
        parser.error("Duplicate card.")
    opponents = args.opponents or (args.players - 1 if not board else 1)
    if not 2 <= args.players <= 9 or not 1 <= opponents <= args.players - 1:
        parser.error("Players must be 2-9, and opponents between 1 and players - 1.")
    if args.bet:
        if args.bb <= 0:
            parser.error("--bb must be positive.")
        if args.pot is None or not _valid_amount(args.pot, args.bb):
            parser.error("Facing a bet needs a positive --pot (the pot before the bet).")
        if not _valid_bet(args.bet, args.pot, args.bb):
            parser.error("Couldn't read --bet.")
        if args.stack and not _valid_amount(args.stack, args.bb):
            parser.error("--stack must be positive.")
    run(args.hole, args.board, args.players, opponents, args.sims,
        args.bet or "", args.pot or "", args.stack or "", args.bb)


if __name__ == "__main__":
    main()
