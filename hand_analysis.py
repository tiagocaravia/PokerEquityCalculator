from poker.card import parse_card
from poker.equity import FoldingOpponents, estimate_equity
from poker.prompts import again, interactive_loop
from poker.tables import load_survivors
from poker.visualizer import build_stages, plot_equity

def get_cards(prompt, n): #input loop to get valid card input
    while True:
        try:
            raw = input(prompt).strip().split()
            if len(raw) != n:
                print(f"Please enter exactly {n} cards.")
                continue    
            return [parse_card(c) for c in raw]
        except (KeyError, ValueError):
            print("Invalid card format. Use RANK followed by SUIT (e.g., 'AH' for Ace of Hearts).")

def show(title, est, average): # One view's results
    print(f"\n--- {title} ---")
    folded = f"  ({est.uncontested * 100:.1f}% because everyone folded)" if est.uncontested else ""
    print(f"Win:  {est.win * 100:.1f}%{folded}")
    print(f"Tie:  {est.tie * 100:.1f}%")
    print(f"Loss: {est.loss * 100:.1f}%")
    if est.model == "real table":
        print(f"Average opponents left in: {est.opponents_left:.2f}")
    print(f"Equity: {est}  (an average hand here: {average * 100:.1f}%)")


def equity_by_street(hole, board, num_players, sims, keep): # Both views at every street so far
    streets = []
    for community in build_stages(board):
        street = {"random": estimate_equity(hole, community, num_players - 1, sims), "average": 1 / num_players}
        if keep:
            table = FoldingOpponents(keep)
            street["table"] = estimate_equity(hole, community, num_players - 1, sims, table)
            street["table average"] = estimate_equity(None, community, num_players - 1, sims, table).equity
        streets.append(street)
    return streets


def analyze(): # One hand: inputs, results, plot
    hole_cards = get_cards("Enter your 2 hole cards (e.g. AS KH): ", 2)
    
    num_players = int(input("Enter number of players (including you): "))

    num_simulations = input("Enter number of simulations (press enter to skip for standard amount): ")
    if num_simulations:
        num_simulations = int(num_simulations)
    else:
        num_simulations = 10000

    community_input = input("Enter community cards if any (or press enter to skip): ").strip()
    if community_input:
        community_cards = [parse_card(c) for c in community_input.split()]
    else:
        community_cards = []

    try:
        keep = set(load_survivors(num_players)["Hand"])
    except FileNotFoundError:
        keep = None
        print(f"\nNo Standard{num_players}.csv found. Run poker/Data/preflop_tables.py for "
              f"{num_players} players to see results at a real table.")

    print("\nCalculating equity...")
    streets = equity_by_street(hole_cards, community_cards, num_players, num_simulations, keep)
    now = streets[-1]
    show("VS RANDOM HANDS (nobody folds)", now["random"], now["average"])
    if keep:
        show("AT A REAL TABLE (weak hands fold, their cards stay dead)", now["table"], now["table average"])

    plot_equity(streets, num_players)


def main(): # Main interaction loop for the user to input their hand, community cards, and get results
    print("=== Poker Equity Calculator ===\n")
    print("Card format: rank + suit (e.g. AS = Ace of Spades, 10H = Ten of Hearts)\n")
    while True:
        analyze()
        if not again():
            break
        print()

if __name__ == "__main__":
    interactive_loop(main)
