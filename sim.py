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

    for _ in range(num_simulations):
        deck = Deck()
        deck.cards = [c for c in deck.cards if c not in known_cards] # Removes Known cards from the deck
        random.shuffle(deck.cards) 

        cards_needed = 5 - len(community_cards) 
        sim_community = community_cards + deck.deal(cards_needed) # Deals remaining cards

        opponents = []
        for _ in range(num_players - 1): # deals 2 hole cards to each opponent
            opponents.append(deck.deal(2))
        
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



                          
