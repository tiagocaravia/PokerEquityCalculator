import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))  # so "poker" imports work

import joblib
import numpy as np
from sklearn.inspection import permutation_importance
from sklearn.tree import DecisionTreeRegressor, plot_tree

from bots.arena import play
from bots.ml_agent import BET_FEATURES, CALL_FEATURES, MODEL_PATH, MLAgent
from bots.pool import load
from bots.profiles import TEST_PRESETS


SHORT = {"equity vs their range": "equity vs range", "equity vs their bet (ranged)": "equity vs bet",
         "guided EV of calling": "guided EV", "guided EV of this action": "guided EV",
         "guided EV of checking": "EV of checking", "bet size (pot)": "bet size",
         "their call rate (read)": "call rate", "bluff share (read)": "bluff share"}  # tree labels


def collect(models, hands, seed): # Real spots the trained bot faces, with a little exploring so every action shows up
    bot = MLAgent("explain", explore=0.15, models=models)
    play(bot, load(), hands, 1000, seed, TEST_PRESETS)
    to_xy = lambda data: np.array([x for x, _ in data])
    return to_xy(bot.call_data), to_xy(bot.bet_data)


def reliance(model, X, names): # How much the model's own predictions change when each input is shuffled
    target = model.predict(X)
    result = permutation_importance(model, X, target, scoring="r2", n_repeats=5, random_state=0)
    order = np.argsort(result.importances_mean)
    return [names[i] for i in order], result.importances_mean[order], result.importances_std[order]


def surrogate(model, X, depth): # A small tree that imitates the model, and how well it does
    target = model.predict(X)
    tree = DecisionTreeRegressor(max_depth=depth, min_samples_leaf=200, random_state=0).fit(X, target)
    return tree, tree.score(X, target)


def explain(hands=20000, seed=99, depth=3, save=None):
    if not os.path.exists(MODEL_PATH):
        sys.exit("No trained model yet. Run: python3 bots/train.py")
    call_model, bet_model = joblib.load(MODEL_PATH)
    print(f"Playing {hands:,} hands with the trained bot to collect spots...")
    X_call, X_bet = collect((call_model, bet_model), hands, seed)
    print(f"  {len(X_call):,} calls and {len(X_bet):,} bet/check decisions")

    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(16, 9))
    grid = fig.add_gridspec(2, 2, height_ratios=[1, 1.5])
    fig.suptitle("What the ML bot relies on", fontsize=13, fontweight="bold")

    for col, (title, model, X, names, note) in enumerate([
            ("Calling model", call_model, X_call, CALL_FEATURES, "calls if above −5bb"),
            ("Betting model", bet_model, X_bet, BET_FEATURES, "picks the highest")]):
        labels, mean, std = reliance(model, X, names)
        used = mean > 0.005  # hide inputs it ignores
        ax = fig.add_subplot(grid[0, col])
        ax.barh(np.array(labels)[used], mean[used], xerr=std[used], color="#2a6f97", capsize=2, height=0.6)
        ax.set_title(f"{title}: inputs it relies on", fontsize=11)
        ax.set_xlabel("Change in its predictions when scrambled (drop in R²)", fontsize=9)
        ax.tick_params(labelsize=9)
        ax.grid(True, axis="x", linestyle="--", alpha=0.4)
        ignored = [l for l, u in zip(labels, used) if not u]
        if ignored:
            ax.text(0.98, 0.04, "ignores: " + ", ".join(ignored), transform=ax.transAxes,
                    ha="right", fontsize=8, color="#666666")
        print(f"\n{title}\n  most relied on: " + ", ".join(f"{l} ({m:.2f})" for l, m in zip(labels[::-1][:4], mean[::-1][:4])))

        tree, fidelity = surrogate(model, X, depth)
        ax = fig.add_subplot(grid[1, col])
        plot_tree(tree, feature_names=[SHORT.get(n, n) for n in names], filled=True, rounded=True, impurity=False,
                  precision=1, fontsize=7, ax=ax, proportion=True, label="root")
        ax.set_title(f"{title} as a {depth}-level tree (value = profit in bb; {note})\n"
                     f"matches the full model with R² = {fidelity:.2f}", fontsize=10)
        print(f"  a {depth}-level tree reproduces it with R² = {fidelity:.2f}")

    fig.tight_layout(rect=(0, 0, 1, 0.96))  # room for the title
    if save:
        fig.savefig(save, dpi=120)
        print(f"\nSaved to {save}")
    else:
        plt.show()


ACTIONS = ["check", "bet ½ pot", "bet ¾ pot", "bet 1¼ pot"]
ACTION_COLORS = ["#c9c9c9", "#9ecae1", "#4292c6", "#08519c"]
BINS = np.linspace(0, 1, 11)  # hand strength buckets


def collect_spots(pool, seed, hands=6000): # A fixed set of spots to replay every round
    bot = MLAgent("spots", explore=0.0)
    bot.spot_log = {"call": [], "bet": []}
    play(bot, pool, hands, 1000, seed, TEST_PRESETS)
    return np.array(bot.spot_log["call"]), np.array(bot.spot_log["bet"])


def policy(models, spots): # What the bot does on the fixed spots: bet choice and call rate, by hand strength
    calls, bets = spots
    call_model, bet_model = models or (None, None)
    flat = bets.reshape(-1, bets.shape[2])
    values = bet_model.predict(flat) if bet_model else flat[:, 3]  # guidance: hand-built EV of each option
    choice = values.reshape(bets.shape[:2]).argmax(axis=1)
    call_value = call_model.predict(calls) if call_model else calls[:, 5]
    called = call_value > -5  # folding loses our 5bb
    bet_bin = np.clip(np.digitize(bets[:, 0, 0], BINS) - 1, 0, 9)
    call_bin = np.clip(np.digitize(calls[:, 0], BINS) - 1, 0, 9)
    bet_share = np.array([[np.mean(choice[bet_bin == b] == a) if np.any(bet_bin == b) else 0
                           for b in range(10)] for a in range(4)])
    call_rate = np.array([called[call_bin == b].mean() if np.any(call_bin == b) else np.nan for b in range(10)])
    return bet_share, call_rate


def animate_training(frames, spots, baselines, path): # One frame per round: results, decisions, what it relies on
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation

    calls, bets = spots
    sample = np.random.default_rng(0).choice(len(bets), min(2000, len(bets)), replace=False)
    for f in frames:
        f["policy"] = policy(f["models"], spots)
        if f["models"]:
            f["call_rel"] = reliance(f["models"][0], calls, CALL_FEATURES)
            f["bet_rel"] = reliance(f["models"][1], bets[sample].reshape(-1, bets.shape[2]), BET_FEATURES)
    guide_calls = frames[0]["policy"][1]
    rel_max = max(max(f[k][1].max() for k in ("call_rel", "bet_rel")) for f in frames if f["models"]) * 1.1
    trained = [f["trained"] for f in frames[1:]]
    ylo = min([b for b in baselines.values()] + [f["test"][0] - f["test"][1] for f in frames[1:]]) - 5
    yhi = max([b for b in baselines.values()] + [f["test"][0] + f["test"][1] for f in frames[1:]]) + 5
    centers = (BINS[:-1] + BINS[1:]) / 2

    fig, axes = plt.subplots(2, 3, figsize=(17, 8.5), gridspec_kw={"width_ratios": [1.1, 1, 1]})
    (ax_win, ax_bet, ax_bet_rel), (ax_edge, ax_call, ax_call_rel) = axes

    def draw(i):
        f = frames[i]
        for ax in axes.flat:
            ax.clear()
        fig.suptitle(f"Training the ML bot: {f['label']}", fontsize=14, fontweight="bold")
        done = frames[1:i + 1]

        for name, color in (("no read", "tab:blue"), ("learner", "tab:green"), ("oracle", "tab:purple")):
            ax_win.axhline(baselines[name], color=color, linestyle="--", linewidth=2, label=name)
        if done:
            ax_win.errorbar([d["trained"] for d in done], [d["test"][0] for d in done],
                            yerr=[d["test"][1] for d in done], color="black", marker="o", capsize=3, label="ML bot")
        ax_win.set(xlim=(0, max(trained) * 1.05), ylim=(ylo, yhi), xlabel="Training hands",
                   ylabel="bb/100 on held-out test", title="Win rate on opponents it hasn't seen")
        ax_win.legend(fontsize=8, loc="lower right")
        ax_win.grid(True, linestyle="--", alpha=0.4)

        ax_edge.axhline(0, color="tab:green", linestyle="--", linewidth=2)
        if done:
            ax_edge.errorbar([d["trained"] for d in done], [d["edge"][0] for d in done],
                             yerr=[d["edge"][1] for d in done], color="black", marker="o", capsize=3)
        edges = [d["edge"][0] + d["edge"][1] for d in frames[1:]] + [5]
        ax_edge.set(xlim=(0, max(trained) * 1.05), ylim=(min(-10, min(d["edge"][0] - d["edge"][1] for d in frames[1:]) - 2),
                    max(edges) + 3), xlabel="Training hands", ylabel="bb/100 (95% CI)",
                    title="Edge over the hand-built learner it started from")
        ax_edge.grid(True, linestyle="--", alpha=0.4)

        bet_share, call_rate = f["policy"]
        bottom = np.zeros(10)
        for a in range(4):
            ax_bet.bar(centers, bet_share[a], width=0.09, bottom=bottom, color=ACTION_COLORS[a], label=ACTIONS[a])
            bottom += bet_share[a]
        ax_bet.set(xlim=(0, 1), ylim=(0, 1), xlabel="Hand strength (share of hands it beats)",
                   ylabel="Share of spots", title="When it acts first: what it does")
        ax_bet.legend(fontsize=7, loc="upper left", ncol=2)

        ax_call.plot(centers, guide_calls, color="tab:green", linestyle="--", marker=".", label="hand-built guidance")
        ax_call.plot(centers, call_rate, color="black", marker="o", label="ML bot")
        ax_call.set(xlim=(0, 1), ylim=(-0.03, 1.03), xlabel="Hand strength (share of hands it beats)",
                    ylabel="Share of bets it calls", title="Facing a bet: how often it calls")
        ax_call.legend(fontsize=8, loc="upper left")
        ax_call.grid(True, linestyle="--", alpha=0.4)

        for ax, key, title in ((ax_bet_rel, "bet_rel", "Betting model relies on"),
                               (ax_call_rel, "call_rel", "Calling model relies on")):
            ax.set_title(title)
            if not f["models"]:
                ax.text(0.5, 0.5, "no model yet:\nfollowing the hand-built guidance", ha="center", va="center",
                        transform=ax.transAxes, color="#666666")
                ax.set_xticks([]), ax.set_yticks([])
                continue
            labels, mean, _ = f[key]
            ax.barh([SHORT.get(l, l) for l in labels[-5:]], mean[-5:], color="#2a6f97")
            ax.set_xlim(0, rel_max)
            ax.set_xlabel("drop in R² when scrambled", fontsize=8)
            ax.tick_params(labelsize=8)
        fig.tight_layout(rect=(0, 0, 1, 0.95))

    order = list(range(len(frames))) + [len(frames) - 1] * 2  # hold the last frame
    anim = FuncAnimation(fig, draw, frames=order, interval=1300)
    anim.save(path, writer="pillow", fps=0.8, dpi=80)
    plt.close(fig)
    print(f"Saved training animation to {path}")


def main():
    parser = argparse.ArgumentParser(description="Show which inputs the trained ML bot relies on, and its logic as a small tree.")
    parser.add_argument("--hands", type=int, default=20000, help="Hands to play to collect spots")
    parser.add_argument("--depth", type=int, default=3, help="Depth of the imitation tree")
    parser.add_argument("--save", default=None, help="Save the figure to this file instead of showing it")
    args = parser.parse_args()
    explain(args.hands, depth=args.depth, save=args.save)


if __name__ == "__main__":
    main()
