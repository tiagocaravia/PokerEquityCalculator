import matplotlib.pyplot as plt


def build_stages(community_cards): # Determines street by street stages based on the number of community cards available
    stages = [[]]  # Preflop, no community cards

    if len(community_cards) >= 3:
        stages.append(community_cards[:3])  # Flop

    if len(community_cards) >= 4:
        stages.append(community_cards[:4])  # Turn

    if len(community_cards) >= 5:
        stages.append(community_cards[:5])  # River

    return stages


def plot_equity(streets, num_players): # Equity by street; streets come from hand_analysis.equity_by_street
    names = ["Preflop", "Flop", "Turn", "River"][:len(streets)]
    xs = list(range(len(names)))
    left, right = -0.3, len(xs) - 0.7  # plot edges

    fair_share = (1 / num_players) * 100  # what an average hand wins when nobody folds
    has_table = "table" in streets[0]

    series = {"vs random hands (nobody folds)": [s["random"].equity * 100 for s in streets]}
    if has_table:
        series["at a real table (weak hands fold)"] = [s["table"].equity * 100 for s in streets]
        fold_average = [s["table average"] * 100 for s in streets]  # what an average hand wins at that table

    plt.figure(figsize=(9, 5.5))

    colors = {}
    for name, values in series.items():
        line, = plt.plot(xs, values, marker="o", linewidth=2, label=name)
        colors[name] = line.get_color()

    plt.axhline(y=fair_share, linestyle="--", alpha=0.7, color=colors["vs random hands (nobody folds)"],
                label=f"Average hand, nobody folds ({fair_share:.1f}%)")

    if has_table:
        # Stretch the dotted line to both edges, like the dashed one, by repeating the first and last values
        fx = [left] + xs + [right]
        fy = [fold_average[0]] + fold_average + [fold_average[-1]]
        plt.plot(fx, fy, linestyle=":", linewidth=2, marker="s", markersize=5,
                 markevery=list(range(1, len(fx) - 1)),  # markers only on the real street points
                 color=colors["at a real table (weak hands fold)"], label="Average hand at a real table")

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

    plt.xticks(xs, names)
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