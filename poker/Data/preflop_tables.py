import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))  # so "poker" imports work

import pandas as pd

from poker.card import Card
from poker.equity import estimate_equity
from poker.prompts import again, ask, interactive_loop
from poker.tables import DATA, find_hand


def build(num_players, sims): # Equity of all 169 starting hands vs random hands
    rows = []
    for i, low in enumerate(Card.RANKS):
        for high in Card.RANKS[i:]:
            for suited in ([False, True] if low != high else [False]):
                hole = [Card(low, "Diamonds"), Card(high, "Diamonds" if suited else "Clubs")]
                est = estimate_equity(hole, [], num_players - 1, sims)
                rows.append({"Hand": f"{low}{high} {'Suited' if suited else 'Offsuit'}",
                             "win%": round(est.win * 100, 1), "tie%": round(est.tie * 100, 1),
                             "loss%": round(est.loss * 100, 1), "equity%": round(est.equity * 100, 2)})
        print(f"  {len(rows)}/169 hands", flush=True)
    path = os.path.join(DATA, f"Standard{num_players}.csv")
    pd.DataFrame(rows).to_csv(path, index=False)
    print(f"Saved to {path}")


def show(hand, num_players): # One hand's row
    row = find_hand(hand, num_players)
    print(row if row else f"No hand called {hand!r}. Try e.g. \"J10 Suited\" or \"AA\".")


def interactive():
    print("=== Preflop tables ===  (enter keeps the value in brackets)\n")
    mode, players, sims, hand = "find", 9, 10000, "J10 Suited"
    while True:
        mode = ask("Build a table or find a hand? (build/find)", mode,
                   check=lambda m: None if m in ("build", "find") else "Type build or find.")
        players = ask("Players", players, int, lambda n: None if 2 <= n <= 9 else "2 to 9.")
        try:
            if mode == "build":
                sims = ask("Simulations per hand", sims, int, lambda n: None if n >= 100 else "At least 100.")
                build(players, sims)
            else:
                hand = ask("Hand", hand)
                show(hand, players)
        except FileNotFoundError:
            print(f"  No table for {players} players yet; build it first.")
        if not again():
            break


def main():
    if len(sys.argv) == 1:
        return interactive_loop(interactive)
    parser = argparse.ArgumentParser(description="Build the preflop equity tables, or look up a hand. "
                                                 "Run with no options to be asked.")
    parser.add_argument("--build", type=int, metavar="PLAYERS", help="Build the table for this many players")
    parser.add_argument("--sims", type=int, default=10000, help="Simulations per hand when building")
    parser.add_argument("--find", metavar="HAND", help='Look up a hand, e.g. "J10 Suited" or "AA"')
    parser.add_argument("--players", type=int, default=9, help="Table to look in (with --find)")
    args = parser.parse_args()
    if args.build:
        build(args.build, args.sims)
    elif args.find:
        show(args.find, args.players)
    else:
        parser.error("Use --build PLAYERS or --find HAND (or no options to be asked).")


if __name__ == "__main__":
    main()
