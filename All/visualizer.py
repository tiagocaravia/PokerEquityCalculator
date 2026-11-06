import matplotlib.pyplot as plt
from sim import simulate
from iterated_sim import simulate_vs_pool, simulate_with_folds


def build_stages(community_cards): # Determines street by street stages based on the number of community cards available
    stages = [[]]  # Preflop, no community cards

    if len(community_cards) >= 3:
        stages.append(community_cards[:3])  # Flop

    if len(community_cards) >= 4:
        stages.append(community_cards[:4])  # Turn

    if len(community_cards) >= 5:
        stages.append(community_cards[:5])  # River

    return stages


def stage_equity(result, num_players): # Equity formula for the random and pool sims
    return result["win"] + (result["tie"] / num_players)


def plot_equity(hole_cards, community_cards, num_players=2, simulations=10000, pool=None, keep=None):

    community_stages = build_stages(community_cards)
    street_names = ["Preflop", "Flop", "Turn", "River"]

    streets = street_names[:len(community_stages)]
    xs = list(range(len(streets)))
    left, right = -0.3, len(xs) - 0.7  # plot edges

    fair_share = (1 / num_players) * 100

    series = {"vs random opponents": []}  # line name -> equity at each street
    if pool is not None:
        series["vs realistic opponents"] = []
    if keep is not None:
        series["vs table with folds"] = []
    fold_fair_share = []

    for community in community_stages:
        series["vs random opponents"].append(
            stage_equity(simulate(hole_cards, community, num_players, simulations), num_players))
        if pool is not None:
            series["vs realistic opponents"].append(
                stage_equity(simulate_vs_pool(hole_cards, community, num_players, simulations, pool), num_players))
        if keep is not None:
            r = simulate_with_folds(hole_cards, community, num_players, simulations, keep)
            series["vs table with folds"].append(r["equity"])
            fold_fair_share.append(r["fair_share"])

    plt.figure(figsize=(9, 5.5))

    colors = {}
    for name, values in series.items():
        line, = plt.plot(xs, values, marker="o", linewidth=2, label=name)
        colors[name] = line.get_color()

    plt.axhline(y=fair_share, linestyle="--", alpha=0.7, color="gray",
                label=f"Fair share if all {num_players} stay in ({fair_share:.1f}%)")

    if keep is not None:
        # Stretch the dotted line to both edges, like the gray one, by repeating the first and last values
        fx = [left] + xs + [right]
        fy = [fold_fair_share[0]] + fold_fair_share + [fold_fair_share[-1]]
        plt.plot(fx, fy, linestyle=":", linewidth=2, marker="s", markersize=5,
                 markevery=list(range(1, len(fx) - 1)),  # markers only on the real street points
                 color=colors["vs table with folds"], label="Fair share with folds")

    for i in xs: # Label points: highest above, lowest below, anything in the middle to the right
        ranked = sorted(series, key=lambda name: series[name][i], reverse=True)
        for position, name in enumerate(ranked):
            y = series[name][i]
            if position == 0:
                offset, ha, va = (0, 8), "center", "bottom"
            elif position == len(ranked) - 1:
                offset, ha, va = (0, -8), "center", "top"
            else:
                offset, ha, va = (10, 0), "left", "center"
            plt.annotate(f"{y:.1f}%", (i, y), textcoords="offset points", xytext=offset,
                         ha=ha, va=va, color=colors[name],
                         bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.8))

    plt.xticks(xs, streets)
    plt.xlim(left, right)
    plt.ylim(-10, 100) # Extra room below zero so labels under low points aren't cut off
    plt.yticks(range(0, 101, 20))

    plt.title("Equity Progression")
    plt.xlabel("Street")
    plt.ylabel("Equity (%)")

    plt.legend(fontsize=8)
    plt.grid(axis="y", linestyle="--", alpha=0.5)
    plt.tight_layout()
    plt.show()