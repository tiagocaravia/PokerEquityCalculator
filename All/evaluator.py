from itertools import combinations
from card import Card

def get_hand_rank(hand): # Evaluates The Rank of a 5 card hand
    ranks = sorted([card.rank_value for card in hand], reverse=True) # Sorts cards by rank value
    suits = [card.suit for card in hand]  # Creates list of suits in hand

    is_flush = len(set(suits)) == 1 # Checks if all cards are suited 
    is_straight = (max(ranks) - min(ranks) == 4) and len(set(ranks)) == 5 # Checks if cards are consecutive uses the indices

    if set(ranks) == {12, 0, 1, 2, 3}:  # Special case for A-2-3-4-5 straight
        is_straight = True
        ranks = [3, 2, 1, 0, -1]  # Treated Ace as low
    
    rank_counts = {} # Counts of each rank in hand
    for r in ranks:
        rank_counts[r] = rank_counts.get(r, 0) + 1

    counts = sorted(rank_counts.values(), reverse=True) # Sorts counts to determine pairs, trips, quads

    if is_straight and is_flush:
        return (8, ranks)  # Straight flush
    if counts == [4, 1]:
        return (7, ranks)  # Four of a kind
    if counts == [3, 2]:
        return (6, ranks)  # Full house
    if is_flush:
        return (5, ranks)  # Flush
    if is_straight:
        return (4, ranks)  # Straight
    if counts == [3, 1, 1]:
        return (3, ranks)  # Three of a kind
    if counts == [2, 2, 1]:
        return (2, ranks)  # Two pair
    if counts == [2, 1, 1, 1]:
        return (1, ranks)  # One pair
    return (0, ranks)  # High card

def best_hand(cards): # Checks which combo of 5 cards from 7 has the best rank
    best = None
    for combo in combinations(cards, 5): # Generates all possible 5 card combos from the 7 cards
        rank = get_hand_rank(combo)
        if best is None or rank > best:
            best = rank # loops through all combos and keeps track of the best one found so far
    return best

