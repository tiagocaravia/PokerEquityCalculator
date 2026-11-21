import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # so "poker" imports work

import joblib

from bots.arena import bb100, play
from bots.explain import animate_training, collect_spots
from bots.ml_agent import MODEL_PATH, Agent, MLAgent
from bots.pool import load
from bots.profiles import TEST_PRESETS
from poker.prompts import again, ask, interactive_loop, yes



def edge(a, b): # Paired edge of a over b on the same hands, bb/100 with 95% CI
    return bb100([x[2] - y[2] for x, y in zip(a, b)])


def train(rounds, hands_per_round, test_hands, session_len, seed, show_plot=True, save=None, animate=None):
    pool = load()
    test_seed = seed + 10_000  # different deals and opponents from training
    print(f"\n=== Training: {rounds} rounds × {hands_per_round:,} hands, "
          f"tested on {test_hands:,} held-out hands each round ===")

    print("Testing the hand-built bots once, for comparison...")
    baselines = {}
    for bot in (Agent("no read", learns=False, mixes=False), Agent("learner", learns=True, mixes=False),
                Agent("oracle", oracle=True, mixes=False)):
        baselines[bot.name] = play(bot, pool, test_hands, session_len, test_seed, TEST_PRESETS)
        m, h = bb100([r[2] for r in baselines[bot.name]])
        print(f"  {bot.name:<10} {m:+7.1f} ± {h:.1f} bb/100")

    bot = MLAgent()
    history = []  # (training hands so far, ml result, edge over learner)
    frames = [{"label": "round 0, the hand-built guidance it starts from", "models": None}]  # for --animate
    print(f"\n  {'round':<6} {'trained on':>11} {'explore':>8}   {'ML bb/100':>15}   {'edge over learner':>19}")
    for r in range(rounds):
        start = time.time()
        bot.explore = max(0.05, 0.30 * 0.6 ** r)  # explore a lot early, less later
        play(bot, pool, hands_per_round, session_len, seed + r)
        bot.train()
        test = play(bot.frozen(), pool, test_hands, session_len, test_seed, TEST_PRESETS)
        m, h = bb100([x[2] for x in test])
        e, eh = edge(test, baselines["learner"])
        trained = (r + 1) * hands_per_round
        history.append((trained, test, (m, h), (e, eh)))
        frames.append({"label": f"round {r + 1}, {trained:,} hands trained", "models": (bot.call_model, bot.bet_model),
                       "trained": trained, "test": (m, h), "edge": (e, eh)})
        print(f"  {r + 1:<6} {trained:>11,} {bot.explore:>8.2f}   {m:>+7.1f} ± {h:<5.1f}   "
              f"{e:>+8.1f} ± {eh:<5.1f}   ({time.time() - start:.0f}s)")

    final = history[-1][1]
    print("\nFinal test, by opponent type (bb/100; 'tricky' was never seen in training)")
    names = ["no read", "learner", "oracle"]
    print(f"  {'':<16}{'ML':>16}" + "".join(f"{n:>16}" for n in names))
    for kind in TEST_PRESETS:
        row = f"  {kind:<16}"
        for results in [final] + [baselines[n] for n in names]:
            m, h = bb100([x[2] for x in results if x[1] == kind])
            row += f"{m:>+9.1f} ± {h:<5.1f}"
        print(row)

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump((bot.call_model, bot.bet_model), MODEL_PATH)
    print(f"\nSaved the trained models to {MODEL_PATH}")

    if animate:
        print("Making the training animation...")
        spots = collect_spots(pool, test_seed + 1)
        animate_training(frames, spots, {n: bb100([r[2] for r in baselines[n]])[0] for n in names}, animate)

    if show_plot:
        plot(history, baselines, save)


def plot(history, baselines, save=None):
    import matplotlib.pyplot as plt
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))
    fig.suptitle("Training the ML bot (gradient-boosted models, reward = profit per hand)",
                 fontsize=13, fontweight="bold")
    x = [t for t, *_ in history]
    m = [r[0] for _, _, r, _ in history]
    h = [r[1] for _, _, r, _ in history]
    ax1.errorbar(x, m, yerr=h, marker="o", capsize=3, color="black", label="ML bot (held-out test)")
    for name, color in (("no read", "tab:blue"), ("learner", "tab:green"), ("oracle", "tab:purple")):
        b, _ = bb100([r[2] for r in baselines[name]])
        ax1.axhline(b, color=color, linestyle="--", label=f"{name} ({b:+.1f})")
    ax1.set_xlabel("Training hands")
    ax1.set_ylabel("Win rate on held-out opponents (bb/100)")
    ax1.set_title("Test win rate as it trains")
    ax1.grid(True, linestyle="--", alpha=0.4)
    ax1.legend(fontsize=9)

    e = [r[0] for *_, r in history]
    eh = [r[1] for *_, r in history]
    ax2.errorbar(x, e, yerr=eh, marker="o", capsize=3, color="black")
    ax2.axhline(0, color="tab:green", linestyle="--", label="hand-built learner")
    ax2.set_xlabel("Training hands")
    ax2.set_ylabel("Edge over hand-built learner (bb/100, 95% CI)")
    ax2.set_title("Does it beat the guidance it started from?")
    ax2.grid(True, linestyle="--", alpha=0.4)
    ax2.legend(fontsize=9)

    fig.tight_layout()
    if save:
        fig.savefig(save, dpi=130)
        print(f"Saved plot to {save}")
    else:
        plt.show()


def interactive():
    print("=== Train the ML bot ===  (enter keeps the value in brackets)\n")
    rounds, hands, test_hands, session_len, seed, show, movie = 5, 20000, 20000, 1000, 1, True, "none"
    while True:
        rounds = ask("Training rounds", rounds, int, lambda n: None if n >= 1 else "At least 1.")
        hands = ask("Hands per round", hands, int, lambda n: None if n >= 1000 else "At least 1,000.")
        test_hands = ask("Test hands per round", test_hands, int, lambda n: None if n >= 1000 else "At least 1,000.")
        session_len = ask("Hands per opponent before switching", session_len, int,
                          lambda n: None if n >= 10 else "At least 10.")
        seed = ask("Random seed", seed, int)
        show = yes("Show the plot? (y/n)", show)
        movie = ask("Save a training animation? (file name like training.gif, or none)", movie)
        train(rounds, hands, test_hands, session_len, seed, show, animate=None if movie == "none" else movie)
        if not again():
            break


def main():
    if len(sys.argv) == 1:
        return interactive_loop(interactive)
    parser = argparse.ArgumentParser(description="Train the ML bot against simulated opponents. "
                                                 "Run with no options to be asked for each input.")
    parser.add_argument("--rounds", type=int, default=5, help="Training rounds")
    parser.add_argument("--hands", type=int, default=20000, help="Training hands per round")
    parser.add_argument("--test-hands", type=int, default=20000, help="Held-out test hands per round")
    parser.add_argument("--session", type=int, default=1000, help="Hands per opponent before a new one")
    parser.add_argument("--seed", type=int, default=1, help="Random seed")
    parser.add_argument("--save", default=None, help="Save the plot to this file instead of showing it")
    parser.add_argument("--no-plot", action="store_true", help="Skip the plot")
    parser.add_argument("--animate", default=None, metavar="FILE.gif", help="Also save an animation of training, one frame per round")
    args = parser.parse_args()
    train(args.rounds, args.hands, args.test_hands, args.session, args.seed, not args.no_plot, args.save, args.animate)


if __name__ == "__main__":
    main()
