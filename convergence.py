import argparse
import math
import random
import sys

import numpy as np

from poker.prompts import again, ask, ask_cards, cards_from, interactive_loop, yes
from poker.deck import Deck
from poker.sim import play_one_hand

Z_95 = 1.96


def simulate_values(hole_cards, community_cards, num_players, num_simulations): # Pot share per hand
    value = {"win": 1.0, "tie": 1 / num_players, "loss": 0.0}
    known = hole_cards + community_cards
    base_deck = [c for c in Deck().cards if c not in known]
    return np.array([value[play_one_hand(hole_cards, community_cards, num_players, base_deck)]
                     for _ in range(num_simulations)])


def running_ci(values): # Running estimate + 95% CI
    n = np.arange(1, len(values) + 1)
    mean = np.cumsum(values) / n
    mean_sq = np.cumsum(values ** 2) / n
    with np.errstate(invalid="ignore", divide="ignore"):
        sample_var = np.maximum(mean_sq - mean ** 2, 0) * n / (n - 1)  # Unbiased (n-1) variance
        half_width = Z_95 * np.sqrt(sample_var / n)
    return mean, half_width


def checkpoints(num_simulations):
    points, n = [], 100
    while n < num_simulations:
        points.extend(p for p in (n, 2 * n, 5 * n) if p < num_simulations)
        n *= 10
    return points + [num_simulations]


def convergence_report(mean, half_width):
    num_simulations = len(mean)
    sigma = half_width[-1] / Z_95 * math.sqrt(num_simulations)  # Per-hand std dev, from the full run

    print(f"  {'sims':>8}  {'equity':>8}  {'95% CI':>19}  {'± pts':>6}  {'moved':>7}")
    previous = None
    for n in checkpoints(num_simulations):
        m, h = mean[n - 1] * 100, half_width[n - 1] * 100
        moved = "" if previous is None else f"{m - previous:+.2f}"
        print(f"  {n:>8,}  {m:7.2f}%  [{m - h:6.2f}%, {m + h:6.2f}%]  {h:6.2f}  {moved:>7}")
        previous = m

    print(f"\n  Final: {mean[-1] * 100:.2f}% ± {half_width[-1] * 100:.2f} pts (95% CI), per-hand σ ≈ {sigma:.3f}")
    print("  The interval shrinks like 1/√n: 4× the sims gives half the width.")
    print("\n  Sims needed for a 95% CI of:")
    for target in (2, 1, 0.5, 0.1):
        print(f"    ±{target:<4g} pts  →  {math.ceil((Z_95 * sigma * 100 / target) ** 2):>10,}")


def animate(mean, half_width, title, save_path=None, frames=120):
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation

    num_simulations = len(mean)
    start = min(30, num_simulations // 10)  # Below this the CI isn't meaningful
    mean_pct, hw_pct = mean * 100, half_width * 100
    final = mean_pct[-1]

    # Log-spaced points, fast to redraw
    idx = np.unique(np.geomspace(start, num_simulations, 800).astype(int)) - 1
    xs = idx + 1
    frame_ends = np.unique(np.geomspace(start, num_simulations, frames).astype(int))
    frame_ends = np.concatenate([frame_ends, [num_simulations] * 25])  # Hold the last frame

    spread = max(hw_pct[start - 1] * 1.25, 1.0)
    lo, hi = max(final - spread, 0), min(final + spread, 100)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.6), gridspec_kw={"width_ratios": [1.6, 1]})
    fig.suptitle(title, fontsize=13, fontweight="bold")

    # Left: running estimate with its CI band
    ax1.set_xscale("log")
    ax1.set_xlim(start, num_simulations)
    ax1.set_ylim(lo, hi)
    ax1.set_xlabel("Number of simulations (log scale)")
    ax1.set_ylabel("Equity (%)")
    ax1.set_title("Running estimate and 95% confidence interval")
    ax1.grid(True, which="both", linestyle="--", alpha=0.35)
    ax1.axhline(final, color="#d62728", linestyle="--", linewidth=1.2, alpha=0.5,
                label=f"Final estimate ({final:.2f}%)")
    line, = ax1.plot([], [], color="#1f77b4", linewidth=1.8, label="Running estimate")
    head, = ax1.plot([], [], "o", color="#1f77b4", markersize=6)
    band = [ax1.fill_between([], [], [], color="#1f77b4", alpha=0.2)]
    ax1.fill_between([], [], [], color="#1f77b4", alpha=0.2, label="95% CI")  # Legend entry
    ax1.legend(fontsize=8, loc="upper right")
    readout = ax1.text(0.02, 0.04, "", transform=ax1.transAxes, fontsize=11, family="monospace",
                       bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#cccccc"))

    # Right: bell curve of the estimate
    grid = np.linspace(lo, hi, 600)
    ax2.set_xlim(lo, hi)
    ax2.set_ylim(0, 1.25)
    ax2.set_yticks([])
    ax2.set_xlabel("Equity (%)")
    ax2.set_title("Where the true equity probably is")
    ax2.grid(True, axis="x", linestyle="--", alpha=0.35)
    curve, = ax2.plot([], [], color="#1f77b4", linewidth=2)
    shade = [ax2.fill_between([], [], [], color="#1f77b4", alpha=0.25)]
    centre = ax2.axvline(final, color="#1f77b4", linewidth=1, alpha=0.6)
    width_text = ax2.text(0.5, 0.95, "", transform=ax2.transAxes, ha="center", va="top", fontsize=10)

    def draw(frame):
        n = frame_ends[frame]
        shown = idx[xs <= n]
        m, h = mean_pct[shown], hw_pct[shown]
        line.set_data(shown + 1, m)
        head.set_data([n], [mean_pct[n - 1]])
        band[0].remove()
        band[0] = ax1.fill_between(shown + 1, m - h, m + h, color="#1f77b4", alpha=0.2, linewidth=0)

        est, hw = mean_pct[n - 1], hw_pct[n - 1]
        readout.set_text(f"n = {n:>7,}   {est:6.2f}% ± {hw:.2f}")

        se = max(hw / Z_95, 1e-9)
        y = np.exp(-0.5 * ((grid - est) / se) ** 2)
        curve.set_data(grid, y)
        shade[0].remove()
        inside = np.abs(grid - est) <= hw
        shade[0] = ax2.fill_between(grid[inside], 0, y[inside], color="#1f77b4", alpha=0.25, linewidth=0)
        centre.set_xdata([est, est])
        width_text.set_text(f"95% CI: {est - hw:.2f}% to {est + hw:.2f}%")
        return line, head, band[0], readout, curve, shade[0], centre, width_text

    fig.tight_layout()
    anim = FuncAnimation(fig, draw, frames=len(frame_ends), interval=50, blit=False)
    if save_path:
        anim.save(save_path, writer="pillow", fps=20, dpi=80)
        print(f"\nSaved animation to {save_path}")
    else:
        plt.show()
    return anim


def run(hole_str, board_str, players, sims, animate_it=True, save=None):
    hole, board = cards_from(hole_str), cards_from(board_str)
    where = f"on {board_str.upper()}" if board else "preflop"
    title = f"{hole_str.upper()} {where}  ·  {players} players  ·  {sims:,} sims"
    print(f"\n=== Convergence: {title} ===\n")

    values = simulate_values(hole, board, players, sims)
    mean, half_width = running_ci(values)
    convergence_report(mean, half_width)

    if animate_it:
        animate(mean, half_width, title, save)


def interactive():
    print("=== Convergence ===  (cards like AS or 10H; enter keeps the value in brackets)\n")
    hole, board, players, sims, show = "AS KH", "", 2, 20000, True
    while True:
        hole = ask_cards("Your hole cards", hole, [2])
        board = ask_cards("Board (none for preflop)", board, [0, 3, 4, 5], taken=cards_from(hole))
        players = ask("Players, including you", players, int, lambda n: None if 2 <= n <= 9 else "2 to 9.")
        sims = ask("Simulations", sims, int, lambda n: None if n >= 100 else "At least 100.")
        show = yes("Show the animation? (y/n)", show)
        run(hole, board, players, sims, show)
        if not again():
            break


def main():
    if len(sys.argv) == 1:
        return interactive_loop(interactive)

    parser = argparse.ArgumentParser(description="Convergence analysis and animation for the Monte Carlo sim. "
                                                 "Run with no options to be asked for each input.")
    parser.add_argument("--hole", default="AS KH", help='Your hole cards, e.g. "AS KH"')
    parser.add_argument("--players", type=int, default=2, help="Number of players, including you")
    parser.add_argument("--board", default="", help='0, 3, 4 or 5 community cards, e.g. "QH JD 2C"')
    parser.add_argument("--sims", type=int, default=20000, help="Number of simulations")
    parser.add_argument("--seed", type=int, default=None, help="Random seed, for reproducible runs")
    parser.add_argument("--save", default=None, help="Save the animation as a .gif instead of showing it")
    parser.add_argument("--no-animate", action="store_true", help="Just print the report")
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
    if not 2 <= args.players <= 9:
        parser.error("Players must be between 2 and 9.")
    if args.sims < 100:
        parser.error("Use at least 100 sims.")
    if args.seed is not None:
        random.seed(args.seed)
    run(args.hole, args.board, args.players, args.sims, not args.no_animate, args.save)


if __name__ == "__main__":
    main()
