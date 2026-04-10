import random 
from itertools import combinations
from card import Card
from deck import Deck
from evaluator import best_hand, detect_threats

def simulate(hole_cards, community_cards = [], num_players = 2, num_simulations = 10000):
    wins = 0
    ties = 0
    losses = 0
    threat_counts = {}

    known_cards = hole_cards + community_cards

    for _ in range(num_simulations):
        deck = Deck()
        deck.cards = [c for c in deck.cards if c not in known_cards]
        random.shuffle(deck.cards)

        cards_needed = 5 - len(community_cards)
        sim_community = community_cards + deck.deal(cards_needed)

        opponents = []
        for _ in range(num_players - 1):
            opponents.append(deck.deal(2))
        
        my_hand = best_hand(hole_cards + sim_community)
        opponent_hands = [best_hand(opp + sim_community) for opp in opponents]
        best_opponent = max(opponent_hands)

        if my_hand > best_opponent:
            wins += 1
        elif my_hand == best_opponent:
            ties += 1
        else:
            losses += 1

        threats = detect_threats(sim_community)
        for threat in threats:
            if threat.startswith("Pairs on Board") or threat.startswith("Paired Board"):
                key = "Paired Board"
            else:
                key = threat
            threat_counts[key] = threat_counts.get(key, 0) + 1
        
    total = num_simulations
    results = {
            "win": round(wins / total * 100, 1),
            "tie": round(ties / total * 100, 1),
            "loss": round(losses / total * 100, 1),
            "threats": {t: round(c / total * 100, 1) for t, c in threat_counts.items()}
    }
    return results



                          
