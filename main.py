from advice import get_advice
from card import Card
from sim import simulate as sim
from deck import Deck
from evaluator import detect_threats

def parse_card(card_str):
    card_str = card_str.strip().upper()
    suit_map = {'H': 'Hearts', 'D': 'Diamonds', 'C': 'Clubs', 'S': 'Spades'}
    rank = card_str[:-1]
    suit = suit_map.get(card_str[-1])
    return Card(rank, suit)

def get_cards(prompt, n):
    while True:
        try:
            raw = input(prompt).strip().split()
            if len(raw) != n:
                print(f"Please enter exactly {n} cards.")
                continue    
            return [parse_card(c) for c in raw]
        except (KeyError, ValueError):
            print("Invalid card format. Use RANK followed by SUIT (e.g., 'AH' for Ace of Hearts).")

def display_results(results, advice):
    print("\n--- RESULTS ---")
    print(f"Win:  {results['win']}%")
    print(f"Tie:  {results['tie']}%")
    print(f"Loss: {results['loss']}%")

    print("\n--- BOARD THREATS ---")
    threats = results['threats']
    significant = {t: v for t, v in threats.items()
                   if v >= 10 and t != "No immediate threats detected"}
    if not significant:
        print("No significant threats detected")
    else:
        for threat, pct in sorted(significant.items(), key=lambda x: -x[1]):
            print(f"{threat}: {pct}%")

    print("\n--- ADVICE ---")
    for line in advice:
        print(line)
    
def main():
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
