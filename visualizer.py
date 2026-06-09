import matplotlib.pyplot as plt
from sim import simulate


def build_stages(community_cards):
    stages = [[]]  # Preflop

    if len(community_cards) >= 3:
        stages.append(community_cards[:3])  # Flop

    if len(community_cards) >= 4:
        stages.append(community_cards[:4])  # Turn

    if len(community_cards) >= 5:
        stages.append(community_cards[:5])  # River

    return stages


def plot_equity(hole_cards, community_cards, num_players=2, simulations=10000):

    community_stages = build_stages(community_cards)

    labels = ["Preflop", "Flop", "Turn", "River"]

    streets = []
    equities = []

    fair_share = (1 / num_players) * 100

    for i, community in enumerate(community_stages):

        result = simulate(hole_cards, community, num_players, simulations)
        equity = result["win"] + (result["tie"] / num_players)

        streets.append(labels[i])
        equities.append(equity)

    plt.figure(figsize=(8, 5))

    plt.plot(streets, equities, marker="o", linewidth=2, label="Your Equity")

    # Fair-share baseline
    plt.axhline( y=fair_share, linestyle="--", alpha=0.7, label=f"Fair Share ({fair_share:.1f}%)")

    # Label each point
    for x, y in zip(streets, equities):

        diff = y - fair_share

        plt.text(x, y + 2, f"{y:.1f}%\n({diff:+.1f}%)",ha="center")

    plt.ylim(0, 100)

    plt.title("Equity Progression")
    plt.xlabel("Street")
    plt.ylabel("Equity (%)")

    plt.legend()

    plt.grid(axis="y", linestyle="--", alpha=0.5)

    plt.tight_layout()
    plt.show()