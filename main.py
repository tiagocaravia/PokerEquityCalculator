from advice import get_advice
from card import Card
from sim import simulate as sim

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

def display_results(results, advice): # Displays the results and advice to the user
    print("\n--- RESULTS ---")
    print(f"Win:  {results['win']}%")
    print(f"Tie:  {results['tie']}%")
    print(f"Loss: {results['loss']}%")

    print("\n--- ADVICE ---")
    for line in advice:
        print(line)
    
def main(): # Main interaction loop for the user to input their hand, community cards, and get results
    print("=== Poker Equity Calculator ===\n")
    print("Card format: rank + suit (e.g. AS = Ace of Spades, 10H = Ten of Hearts)\n")

    hole_cards = get_cards("Enter your 2 hole cards (e.g. AS KH): ", 2)
    
    num_players = int(input("Enter number of players (including you): "))

    community_input = input("Enter community cards if any (or press enter to skip): ").strip()
    if community_input:
        community_cards = [parse_card(c) for c in community_input.split()]
    else:
        community_cards = []
    
    pot_size = float(input("Current pot size (0 if preflop): $"))
    bet_amount = float(input("Bet amount to call (0 if no bet): $"))
    
    print("\nCalculating equity...")
    results = sim(hole_cards, community_cards, num_players)
    advice = get_advice(results['win'], num_players, pot_size, bet_amount)
    display_results(results, advice)

if __name__ == "__main__":
    main()
