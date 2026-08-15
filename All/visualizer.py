import matplotlib.pyplot as plt
from sim import simulate


def build_stages(community_cards): # Detemines/Builds street by street predictions based on the number of community cards available
    stages = [[]]  # Preflop, no community cards

    if len(community_cards) >= 3:
        stages.append(community_cards[:3])  # Flop, the first three community cards

    if len(community_cards) >= 4:
        stages.append(community_cards[:4])  # Turn, the first four community cards

    if len(community_cards) >= 5:
        stages.append(community_cards[:5])  # River, all five community cards

    return stages


def plot_equity(hole_cards, community_cards, num_players=2, simulations=10000):

    community_stages = build_stages(community_cards) 

    labels = ["Preflop", "Flop", "Turn", "River"]

    streets = [] 
    equities = []

    fair_share = (1 / num_players) * 100

    for i, community in enumerate(community_stages): # Simulate equity for each stage of the hand, starting with preflop and adding community cards as we go

        result = simulate(hole_cards, community, num_players, simulations)
        equity = result["win"] + (result["tie"] / num_players)

        streets.append(labels[i])
        equities.append(equity)

    plt.figure(figsize=(8, 5)) # Set the figure size for better visibility

    plt.plot(streets, equities, marker="o", linewidth=2, label="Your Equity") # Plot the equity progression with markers and a label for the legend

    # Fair-share baseline
    plt.axhline( y=fair_share, linestyle="--", alpha=0.7, label=f"Fair Share ({fair_share:.1f}%)") # Add a dashed line to indicate the fair share baseline, with a label for the legend

    # Label each point
    for x, y in zip(streets, equities):

        diff = y - fair_share # Calculate the difference from the fair share baseline

        plt.text(x, y + 2, f"{y:.1f}%\n({diff:+.1f}%)",ha="center") # Add text labels above each point showing the equity percentage and the difference from the fair share baseline, with a small vertical offset for better visibility

    plt.ylim(0, 100) # Set the y-axis to 0-100% 

    plt.title("Equity Progression") # Set the title of the plot
    plt.xlabel("Street") # Set the x-axis label
    plt.ylabel("Equity (%)") # Set the y-axis label

    plt.legend() 

    plt.grid(axis="y", linestyle="--", alpha=0.5)

    plt.tight_layout()
    plt.show() # Display the plot