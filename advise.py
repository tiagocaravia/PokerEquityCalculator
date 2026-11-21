import argparse
import math
import random
import sys

from poker.prompts import NONE_WORDS, again, ask, ask_cards, cards_from, interactive_loop
from poker.decisions import advise_call, advise_preflop
from poker.equity import EquityEstimate, RandomOpponents, RangeOpponents, estimate_equity
from poker.ranges import PREFLOP_ACTIONS, Range, RangeModel, parse_street_action
from poker.tables import build_pool, hand_label, load_survivors, load_table

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


def opponent_models(num_players): # Random hands + hands people play
    models = [RandomOpponents()]
    try:
        models.append(RangeOpponents(build_pool(load_survivors(num_players)), "played"))
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


def build_range(hole, board, num_players, action, pot_before_bet=None, bet=None, street_actions=()): # Their range from their actions
    if not action and not bet and not any(street_actions):
        return None
    rng = Range(hole + board)
    rng.preflop(action or "none", num_players)  # "none": they played some hand
    for cards, text in zip((3, 4), street_actions):  # earlier streets: flop, then turn
        if text and len(board) > cards:
            rng.street_action(board[:cards], *parse_street_action(text))
    if bet and len(board) == 5:
        rng.river_bet(board, pot_before_bet, bet)
    elif bet and board:
        rng.street_action(board, "bet", bet / pot_before_bet)
    return rng


def show_range(rng, hole, board):
    assumption = "  (no read: balanced bluffing)" if len(board) == 5 and "river" in rng.history[-1] else ""
    print(f"Their range after: {' → '.join(rng.history)}{assumption}")
    print("  Most likely: " + ", ".join(f"{name} {share:.0%}" for name, share in rng.top_hands(8)))
    if len(board) == 5:
        cats, beats, ties = rng.breakdown(hole, board)
        print("  Holding:     " + ", ".join(f"{name} {share:.0%}" for name, share in cats if share >= 0.005))
        print(f"  {beats:.0%} of their range beats you, {ties:.0%} ties, {1 - beats - ties:.0%} you beat")
    elif board:
        cats, beats, ties = rng.breakdown(hole, board)
        print("  Holding:     " + ", ".join(f"{name} {share:.0%}" for name, share in cats if share >= 0.005))
        draws = rng.draws(hole, board)
        if any(share >= 0.005 for _, share in draws):
            print("  Drawing:     " + ", ".join(f"{name} {share:.0%}" for name, share in draws if share >= 0.005))
        print(f"  Right now {beats:.0%} of their range is ahead of you (more cards to come)")


def ranged_estimate(rng, hole, board, opponents, num_players, sims): # Equity vs the narrowed range
    if len(board) == 5 and opponents == 1:
        return EquityEstimate(rng.river_equity(hole, board), 0.0, 0, "ranged")
    others = opponent_models(num_players)[-1]
    return estimate_equity(hole, board, opponents, sims, RangeModel(rng, others))


def show_postflop_no_bet(hole, board, opponents, num_players, sims, action="", street_actions=()):
    print(f"\n--- NO BET TO CALL, {opponents} opponent{'s' * (opponents > 1)} ---")
    rng = build_range(hole, board, num_players, action, street_actions=street_actions)
    if rng:
        show_range(rng, hole, board)
    for model in opponent_models(num_players):
        est = estimate_equity(hole, board, opponents, sims, model)
        print(f"Equity vs {est.model:<10} {est}")
    if rng:
        print(f"Equity vs {'ranged':<10} {ranged_estimate(rng, hole, board, opponents, num_players, sims)}")
    print(f"Fair share: {pct(1 / (opponents + 1))}. Checking is free, so there's nothing to fold to.")


def show_facing_bet(hole, board, opponents, num_players, pot_before_bet, bet, stack, sims, action="", street_actions=(),
                    roll=False): # Call/fold report, in bb
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

    rng = build_range(hole, board, num_players, action, pot_before_bet, bet, street_actions)
    if rng:
        show_range(rng, hole, board)
        est = ranged_estimate(rng, hole, board, opponents, num_players, sims)
        rows.append((est, advise_call(est.equity, est.half_width, pot, to_call, bet_in_range=bool(board))))

    print(f"Pot odds: call {fmt_bb(to_call)} to win {fmt_bb(pot)}, so you need {pct(rows[0][1].break_even)} equity\n")
    print(f"  {'vs':<11} {'equity':>13}   {'EV(call)':>18}")
    for est, adv in rows:
        spread = f"± {adv.ev_half_width:<5.2f}" if est.sims else "(exact)"
        print(f"  {est.model:<11} {str(est) if est.sims else pct(est.equity):>13}   {adv.ev:+8.2f} {spread:<8}bb  {adv.action}")

    final = rows[-1][1]  # Ranged, else played, else random
    print(f"\n→ {final.action}  (based on {rows[-1][0].model} opponents)")
    if final.action == "CLOSE":
        print(f"  Close to break-even: call about {final.call_probability:.0%} of the time, so you're hard to exploit.")
        if roll:
            print(f"  Rolled: {'CALL' if random.random() < final.call_probability else 'FOLD'}")
    if rng and len(board) == 5:
        print("  The range assumes they bluff a balanced amount. If they bluff less, fold more; more, call more.")
    elif rng and board:
        print("  The range assumes no-read betting habits (how often they c-bet, semi-bluff and trap).")
    if all_in:
        print("  All-in call: no more betting after this, so pot odds are exact.")
    elif not all_in and len(board) < 5:
        print("  More betting can follow, so this ignores implied odds (what you win later when you hit).")
    for note in final.notes:
        print(f"  Note: {note}")


def run(hole_str, board_str, players, opponents, sims, bet_text="", pot_text="", stack_text="", bb=1.0, action="",
        street_actions=(), roll=False):
    hole, board = cards_from(hole_str), cards_from(board_str)
    if bet_text:
        pot = parse_amount(pot_text, bb)
        bet = parse_bet(bet_text, pot, bb)
        stack = parse_amount(stack_text, bb) if stack_text else None
        if bb != 1:
            print(f"(1bb = {bb:g} chips; amounts below are in big blinds)")
        show_facing_bet(hole, board, opponents, players, pot, bet, stack, sims, action, street_actions, roll)
    elif not board:
        show_preflop(hole, players, sims)
    else:
        show_postflop_no_bet(hole, board, opponents, players, sims, action, street_actions)


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
    bet, pot, stack, bb, action = "", "", "", 1.0, ""
    flop_action, turn_action = "", ""
    street_help = "check, call, raise, bet, bet half, bet pot, bet 75%"
    actions = ", ".join(a for a in PREFLOP_ACTIONS if a not in ("check", "open", "all in"))
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
        action = ask(f"Their preflop action ({actions})", action or "none",
                     check=lambda a: None if a.lower() in PREFLOP_ACTIONS else f"One of: {actions}.")
        action = "" if action.lower() == "none" else action.lower()
        if len(cards_from(board)) >= 4:
            flop_action = ask_street("Their flop action", flop_action, street_help)
        if len(cards_from(board)) == 5:
            turn_action = ask_street("Their turn action", turn_action, street_help)
        bet = ask("Bet you're facing now (none if no bet)", bet or "none")
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
        streets = (flop_action, turn_action) if len(cards_from(board)) >= 4 else ()
        run(hole, board, players, opponents, sims, bet, pot, stack, bb, action, streets)
        if not again():
            break


def ask_street(prompt, current, street_help): # A flop/turn action, or none
    def check(text):
        if text.lower() in NONE_WORDS:
            return None
        try:
            parse_street_action(text)
        except ValueError:
            return f"Try one of: {street_help} (or none)."
        return None
    text = ask(f"{prompt} ({street_help})", current or "none", check=check)
    return "" if text.lower() in NONE_WORDS else text.lower()


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
    parser.add_argument("--action", default="",
                        help="Their preflop action, to narrow their range: " + ", ".join(PREFLOP_ACTIONS))
    parser.add_argument("--flop", default="", help='Their flop action: check, call, raise, "bet half", "bet pot", ...')
    parser.add_argument("--turn", default="", help="Their turn action, same options as --flop")
    parser.add_argument("--sims", type=int, default=5000, help="Simulations per equity estimate")
    parser.add_argument("--roll", action="store_true", help="In CLOSE spots, pick call or fold at the mixed rate")
    args = parser.parse_args()

    for name in ("flop", "turn"):
        text = getattr(args, name)
        if text:
            try:
                parse_street_action(text)
            except ValueError:
                parser.error(f'--{name} must be check, call, raise, or bet with a size like "bet half".')

    if args.action and args.action.lower() not in PREFLOP_ACTIONS:
        parser.error("--action must be one of: " + ", ".join(PREFLOP_ACTIONS))
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
        args.bet or "", args.pot or "", args.stack or "", args.bb, args.action.lower(),
        (args.flop, args.turn), args.roll)


if __name__ == "__main__":
    main()
