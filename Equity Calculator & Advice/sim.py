import random 
from itertools import combinations
from card import Card
from deck import Deck
from evaluator import best_hand

def simulate(hole_cards, community_cards = [], num_players = 2, num_simulations = 10000): # Monte Carlo Sim to estimate equity
    wins = 0
    ties = 0
    losses = 0

    known_cards = hole_cards + community_cards # Prevents sim from using cards that are already known to be in play

    base_deck = [c for c in Deck().cards if c not in known_cards]

    for _ in range(num_simulations):
        deck = base_deck.copy()
        random.shuffle(deck)

        cards_needed = 5 - len(community_cards) 
        sim_community = community_cards + deck[:cards_needed] # Deals remaining cards
        deck = deck[cards_needed:]

        opponents = []
        for _ in range(num_players - 1): # deals 2 hole cards to each opponent
            opponents.append(deck[:2])
            deck = deck[2:]
        
        my_hand = best_hand(hole_cards + sim_community) # Evaluates best hand for player
        opponent_hands = [best_hand(opp + sim_community) for opp in opponents] # Evaluates best hand for each opponent
        best_opponent = max(opponent_hands) # Compares Player hand to best opponent

        if my_hand > best_opponent: # Tracks wins, ties, and losses based on best comparison
            wins += 1
        elif my_hand == best_opponent:
            ties += 1
        else:
            losses += 1 

        
    total = num_simulations 
    results = { #Sets results as percentages rounded to 1 decimal place
            "win": round(wins / total * 100, 1),
            "tie": round(ties / total * 100, 1),
            "loss": round(losses / total * 100, 1),
    }
    return results


def convergence_analysis(hole_cards, community_cards=[], num_players=2, num_simulations=10000):
    sample_sizes = [(num_simulations/100), (num_simulations/10), (num_simulations/5), (num_simulations/2)]
    for n in sample_sizes:
        result = simulate(hole_cards, community_cards, num_players, n)
        print(f"n={n:>6}: win={result['win']}%")
