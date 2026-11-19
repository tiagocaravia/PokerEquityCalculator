"""
Validates the Monte Carlo simulator against the true (exact) equity.

1. Exact: with a flop, turn or river, deals out every possible opponent hand
   and every possible runout (heads-up) to get the true equity. Preflop that's
   ~2.1 billion matchups, so it uses published exact equities instead.
2. Monte Carlo: runs the simulator several times, tracking a running estimate
   and its 95% confidence interval as the number of simulations grows.
3. Checks: does the CI contain the exact answer? Does its width shrink like
   1/sqrt(n)? How many sims do you need for a given precision?
4. Plot: the CI funnel closing in on the exact answer.

Usage (from the project folder):
    python3 validate.py
    python3 validate.py --hole "AS KS" --board "QS JD 2C" --sims 20000 --runs 12
    python3 validate.py --board "QS JD 2C 7H" --save validation.png
    python3 validate.py --hole "AS AD" --board ""        # preflop, vs published equity
"""
import argparse
import math
import random
import time
from itertools import combinations

import numpy as np

from poker.card import parse_card
from poker.deck import Deck
from poker.evaluator import best_hand
from poker.sim import simulate
from convergence import Z_95, checkpoints, running_ci, simulate_values


# Exact heads-up preflop equity vs one random hand (win + tie/2), from full enumeration
# of every board. Only hands where both sources below agree to two decimals are included:
#   https://pailiku.com/matchups  (states "enumerated, not sampled", all 1,712,304 boards)
#   https://pokercoaching.com/blog/best-texas-holdem-starting-hands/
PUBLISHED_PREFLOP = {
    "AA": 0.8520, "KK": 0.8240, "QQ": 0.7993, "JJ": 0.7747, "TT": 0.7501,
    "AKs": 0.6704, "AQs": 0.6621, "AKo": 0.6532,
}


def hand_class(hole_cards):  # e.g. [AH, KH] -> "AKs", [AS, AD] -> "AA"
    hi, lo = sorted(hole_cards, key=lambda c: c.rank_value, reverse=True)
    name = "".join("T" if c.rank == "10" else c.rank for c in (hi, lo))
    if hi.rank == lo.rank:
        return name
    return name + ("s" if hi.suit == lo.suit else "o")


def exact_equity(hole_cards, board):
    """Enumerate every opponent hand and every runout. Heads-up only."""
    known = hole_cards + board
    remaining = [c for c in Deck().cards if c not in known]
    cards_needed = 5 - len(board)

    wins = ties = losses = 0
    for runout in combinations(remaining, cards_needed):
        full_board = board + list(runout)
        my_hand = best_hand(hole_cards + full_board)  # Same for every opponent hand on this runout
        left = [c for c in remaining if c not in runout]
        for opp in combinations(left, 2):
            opp_hand = best_hand(list(opp) + full_board)
            if my_hand > opp_hand:
                wins += 1
            elif my_hand == opp_hand:
                ties += 1
            else:
                losses += 1

    total = wins + ties + losses
    win, tie = wins / total, ties / total
    equity = win + tie / 2
    sigma = math.sqrt(win + tie / 4 - equity ** 2)  # Std dev of a single hand's value (1, 0.5 or 0)
    return {"win": win, "tie": tie, "loss": losses / total, "equity": equity, "sigma": sigma, "total": total}


def monte_carlo_run(hole_cards, board, num_simulations):
    """One heads-up Monte Carlo run. Returns running estimate and 95% CI half-width after each hand."""
    return running_ci(simulate_values(hole_cards, board, 2, num_simulations))


def pct(x):
    return f"{x * 100:6.2f}%"


def plot(runs, exact, num_simulations, hole_str, board_str, save_path=None):
    import matplotlib.pyplot as plt

    mu, sigma = exact["equity"] * 100, exact["sigma"] * 100
    n = np.arange(1, num_simulations + 1)
    start = 30  # Below this the CI isn't meaningful
    x = n[start - 1:]
    theory = Z_95 * sigma / np.sqrt(x)

    main_mean, main_hw = runs[0][0][start - 1:] * 100, runs[0][1][start - 1:] * 100

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.8), gridspec_kw={"width_ratios": [1.5, 1]})
    fig.suptitle(f"Monte Carlo vs {exact['source']}  ·  {hole_str} {board_str}  ·  heads-up",
                 fontsize=13, fontweight="bold")

    # Left: the funnel
    band_label = "Theoretical 95% band" + ("" if exact["sigma_exact"] else " (σ from all runs)")
    ax1.fill_between(x, mu - theory, mu + theory, color="#d9d9d9", alpha=0.6, label=band_label)
    for mean, _ in runs[1:]:
        ax1.plot(x, mean[start - 1:] * 100, color="#7f7f7f", alpha=0.35, linewidth=0.8)
    ax1.plot([], [], color="#7f7f7f", alpha=0.6, linewidth=0.8, label=f"Other runs ({len(runs) - 1})")
    ax1.fill_between(x, main_mean - main_hw, main_mean + main_hw, color="#1f77b4", alpha=0.18,
                     label="Highlighted run's 95% CI")
    ax1.plot(x, main_mean, color="#1f77b4", linewidth=1.6, label="Highlighted run's estimate")
    ax1.axhline(mu, color="#d62728", linewidth=1.6, linestyle="--", label=f"True equity, {exact['source']} ({mu:.2f}%)")

    ax1.set_xscale("log")
    ax1.set_xlim(start, num_simulations)
    spread = Z_95 * sigma / math.sqrt(start) * 1.3
    ax1.set_ylim(mu - spread, mu + spread)
    ax1.set_xlabel("Number of simulations (log scale)")
    ax1.set_ylabel("Equity (%)")
    ax1.set_title("The interval closes in on the exact answer")
    ax1.grid(True, which="both", linestyle="--", alpha=0.35)
    ax1.legend(fontsize=8, loc="upper right")

    # Right: CI width on log-log, slope -1/2
    ax2.loglog(x, theory, color="#d62728", linestyle="--", linewidth=1.6, label=r"Theory: $1.96\,\sigma/\sqrt{n}$")
    ax2.loglog(x, main_hw, color="#1f77b4", linewidth=1.6, label="Highlighted run's CI half-width")
    for target in (1.0, 0.5):
        needed = (Z_95 * sigma / target) ** 2
        ax2.axhline(target, color="#7f7f7f", linewidth=0.8, linestyle=":")
        if needed <= num_simulations:
            ax2.plot(needed, target, "o", color="#2ca02c", zorder=5)
        ax2.annotate(f"±{target:g}% needs ~{math.ceil(needed):,} sims", (start * 1.2, target),
                     textcoords="offset points", xytext=(0, 4), fontsize=8, color="#555555")
    ax2.set_xlim(start, num_simulations)
    ax2.set_xlabel("Number of simulations (log scale)")
    ax2.set_ylabel("95% CI half-width (percentage points)")
    ax2.set_title("4× the sims → half the width")
    ax2.grid(True, which="both", linestyle="--", alpha=0.35)
    ax2.legend(fontsize=8, loc="upper right")

    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150)
        print(f"\nSaved plot to {save_path}")
    else:
        plt.show()


def main():
    parser = argparse.ArgumentParser(description="Validate the Monte Carlo simulator against the exact equity (heads-up).")
    parser.add_argument("--hole", default="AH KH", help='Your hole cards, e.g. "AH KH"')
    parser.add_argument("--board", default="QH JD 2C",
                        help='3-5 community cards, or "" for preflop (uses published equities: '
                             + ", ".join(PUBLISHED_PREFLOP) + ")")
    parser.add_argument("--sims", type=int, default=20000, help="Simulations per Monte Carlo run")
    parser.add_argument("--runs", type=int, default=12, help="Number of independent Monte Carlo runs")
    parser.add_argument("--seed", type=int, default=None, help="Random seed, for reproducible runs")
    parser.add_argument("--save", default=None, help="Save the plot to this file instead of showing it")
    parser.add_argument("--no-plot", action="store_true", help="Skip the plot")
    args = parser.parse_args()

    hole = [parse_card(c) for c in args.hole.split()]
    board = [parse_card(c) for c in args.board.split()]
    if len(hole) != 2 or len(board) not in (0, 3, 4, 5):
        parser.error("Need exactly 2 hole cards and 0 (preflop) or 3-5 board cards.")
    if any(c.suit is None or c.rank not in c.RANKS for c in hole + board):
        parser.error("Invalid card. Use RANK + SUIT, e.g. AH or 10S.")
    if len({(c.rank, c.suit) for c in hole + board}) != len(hole + board):
        parser.error("Duplicate card.")
    if args.seed is not None:
        random.seed(args.seed)

    hole_str = args.hole.upper()
    board_str = f"on {args.board.upper()}" if board else "preflop"
    print(f"=== Validation: {hole_str} {board_str}, heads-up vs a random hand ===\n")

    # 1. The true equity
    if board:
        print("Enumerating every opponent hand and runout...", flush=True)
        t = time.time()
        exact = exact_equity(hole, board)
        exact.update(source="exact enumeration", sigma_exact=True)
        print(f"  {exact['total']:,} matchups in {time.time() - t:.1f}s")
        print(f"  Win {pct(exact['win'])}   Tie {pct(exact['tie'])}   Loss {pct(exact['loss'])}")
        print(f"  Exact equity: {exact['equity'] * 100:.3f}%   (per-hand std dev σ = {exact['sigma']:.3f})")
    else:
        cls = hand_class(hole)
        if cls not in PUBLISHED_PREFLOP:
            parser.error(f"No published preflop equity for {cls}. Available: {', '.join(PUBLISHED_PREFLOP)}")
        exact = {"equity": PUBLISHED_PREFLOP[cls], "source": "published exact equity", "sigma_exact": False}
        print(f"Preflop is ~2.1 billion matchups to enumerate, so using the published exact equity for {cls}:")
        print(f"  {exact['equity'] * 100:.2f}%   (rounded to 2 decimals, so good to ±0.005 pts)")

    # 2. Repeated runs with running CI
    print(f"\nRunning {args.runs} independent Monte Carlo runs of {args.sims:,} sims...", flush=True)
    t = time.time()
    runs = [monte_carlo_run(hole, board, args.sims) for _ in range(args.runs)]
    print(f"  done in {time.time() - t:.1f}s")

    if not exact["sigma_exact"]:
        # Published tables don't split win/tie, so estimate σ by pooling every run's final variance
        final_vars = [(h[-1] / Z_95) ** 2 * args.sims for _, h in runs]
        exact["sigma"] = math.sqrt(sum(final_vars) / len(final_vars))
        print(f"  Per-hand std dev σ ≈ {exact['sigma']:.3f} (estimated from all {args.runs * args.sims:,} hands)")

    # 3. The simulator as hand_analysis.py calls it
    print(f"\nRunning simulate() as hand_analysis.py does ({args.sims:,} sims)...", flush=True)
    r = simulate(hole, board, 2, args.sims)
    sim_equity = r["win"] + r["tie"] / 2
    se = exact["sigma"] * 100 / math.sqrt(args.sims)
    z = (sim_equity - exact["equity"] * 100) / se
    verdict = "OK" if abs(z) < Z_95 else "outside 95% range (expected about 1 time in 20)"
    print(f"  simulate() equity: {sim_equity:.2f}%   off by {sim_equity - exact['equity'] * 100:+.2f} pts"
          f"   z = {z:+.2f}   {verdict}")

    mean, hw = runs[0]
    print("\n  First run, step by step:")
    print(f"  {'sims':>8}  {'estimate':>9}  {'95% CI':>19}  {'± pts':>6}  contains exact?")
    for n in checkpoints(args.sims):
        m, h = mean[n - 1], hw[n - 1]
        hit = "yes" if abs(m - exact["equity"]) <= h else "NO"
        print(f"  {n:>8,}  {pct(m):>9}  [{pct(m - h)}, {pct(m + h)}]  {h * 100:6.2f}  {hit}")

    covered = sum(abs(m[-1] - exact["equity"]) <= h[-1] for m, h in runs)
    print(f"\n  Coverage: {covered}/{args.runs} final CIs contain the exact equity "
          f"({covered / args.runs:.0%}; should be near 95%)")

    final_hw = np.array([h[-1] for _, h in runs]) * 100
    theory_hw = Z_95 * exact["sigma"] * 100 / math.sqrt(args.sims)
    print(f"  Final CI half-width: ±{final_hw.mean():.3f} pts on average (theory ±{theory_hw:.3f})")

    print("\n  Sims needed for a 95% CI of:")
    for target in (2, 1, 0.5, 0.1):
        print(f"    ±{target:<4g} pts  →  {math.ceil((Z_95 * exact['sigma'] * 100 / target) ** 2):>10,}")

    if not args.no_plot:
        plot(runs, exact, args.sims, hole_str, board_str, args.save)


if __name__ == "__main__":
    main()
