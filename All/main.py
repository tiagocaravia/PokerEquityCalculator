from advice import get_advice
from card import Card
from sim import simulate as sim
from visualizer import plot_equity
from iterated_sim import load_survivors, build_pool, simulate_vs_pool, simulate_with_folds 

def parse_card(card_str): # Parses user input into Card objects
    card_str = card_str.strip().upper() # Standardizes input to uppercase and removes extra spaces
    suit_map = {'H': 'Hearts', 'D': 'Diamonds', 'C': 'Clubs', 'S': 'Spades'} # Attributes letter to suit
    rank = card_str[:-1] 
    suit = suit_map.get(card_str[-1]) 
    return Card(rank, suit)

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

def display_results(results): # Displays the results to the user
    print("\n--- RESULTS ---")
    print(f"Win:  {results['win']}%")
    print(f"Tie:  {results['tie']}%")
    print(f"Loss: {results['loss']}%")


def display_pool_results(results):
    print("\n--- VS REALISTIC OPPONENTS (weak hands folded) ---")
    print(f"Win:  {results['win']}%")
    print(f"Tie:  {results['tie']}%")
    print(f"Loss: {results['loss']}%")

def display_fold_results(results):
    print("\n--- VS TABLE WITH FOLDS (weak hands fold, their cards stay dead) ---")
    print(f"Win:  {results['win']}%  ({results['uncontested']}% because everyone folded)")
    print(f"Tie:  {results['tie']}%")
    print(f"Loss: {results['loss']}%")
    print(f"Average opponents left in: {results['avg_opponents']}")
    print(f"Equity: {results['equity']}%  (fair share: {results['fair_share']}%)")

def main(): # Main interaction loop for the user to input their hand, community cards, and get results
    print("=== Poker Equity Calculator ===\n")
    print("Card format: rank + suit (e.g. AS = Ace of Spades, 10H = Ten of Hearts)\n")

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
  
    print("\nCalculating equity...")
    results = sim(hole_cards, community_cards, num_players, num_simulations)
    display_results(results)

    pool = None
    keep = None
    try:
        survivors = load_survivors(num_players)
        keep = set(survivors["Hand"])
        pool = build_pool(survivors)
        pool_results = simulate_vs_pool(hole_cards, community_cards, num_players, num_simulations, pool)
        display_pool_results(pool_results)

        fold_results = simulate_with_folds(hole_cards, community_cards, num_players, num_simulations, keep)
        display_fold_results(fold_results)
    except FileNotFoundError:
        print(f"\nNo Standard{num_players}.csv found. Run the preflop aggregator for "f"{num_players} players to enable realistic opponents.")

    plot_equity(hole_cards, community_cards, num_players, num_simulations, pool, keep)

if __name__ == "__main__":
    main()
