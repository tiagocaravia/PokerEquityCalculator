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

def display_results(results):
    print("\nResults:")
    print(f"Win %: {results['win']:.2f}")
    print(f"Tie %: {results['tie']:.2f}")
    print(f"Loss %: {results['loss']:.2f}")

    print("\nBoard Threats:")
    threats = results['threats']
    if not threats:
        print("No significant threats detected.")
    else:
        significant = {t: v for t, v in threats.items() if v >= 10 and t != "No immediate threats detected"}
        if not significant:
            print("No threats with significant probability.")
        else:
            for threat, prob in significant.items():
                print(f"{threat}: {prob:.2f}%")
    
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
    
    print("\nCalculating equity...")
    results = sim(hole_cards, community_cards, num_players)
    display_results(results)

if __name__ == "__main__":
    main()
