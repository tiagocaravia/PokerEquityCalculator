from itertools import combinations
from card import Card

def get_hand_rank(hand):
    ranks = sorted([card.rank_value for card in hand], reverse=True)
    suits = [card.suit for card in hand] 

    is_flush = len(set(suits)) == 1
    is_straight = (max(ranks) - min(ranks) == 4) and len(set(ranks)) == 5

    if set(ranks) == {12, 0, 1, 2, 3}:  # Special case for A-2-3-4-5 straight
        is_straight = True
        ranks = [3, 2, 1, 0, -1]  # Treat Ace as low
    
    rank_counts = {}
    for r in ranks:
        rank_counts[r] = rank_counts.get(r, 0) + 1

    counts = sorted(rank_counts.values(), reverse=True)

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

def best_hand(cards):
    best = None
    for combo in combinations(cards, 5):
        rank = get_hand_rank(combo)
        if best is None or rank > best:
            best = rank
    return best


def detect_threats (community_cards):
    threats = []

    suit_counts = {}
    for card in community_cards:
        suit_counts[card.suit] = suit_counts.get(card.suit, 0) + 1
    for suit, count in suit_counts.items():
        if count >= 4:
            threats.append(f"Flush on Board: {suit}")
        elif count == 3:
            threats.append(f"Flush Draw on Board: {suit}")
    

    rank_values = sorted(set([card.rank_value for card in community_cards]))
    consequtive = 1
    max_consequtive = 1
    for i in range(1, len(rank_values)):
        if rank_values[i] == rank_values[i-1] + 1:
            consequtive += 1
            max_consequtive = max(max_consequtive, consequtive)
        else:
            consequtive = 1
    
    if max_consequtive >= 4:
        threats.append("Straight on Board")
    if max_consequtive >= 3:
        threats.append("Straight Draw on Board")
    
    rank_counts = {}
    for card in community_cards:
        rank_counts[card.rank_value] = rank_counts.get(card.rank_value, 0) + 1

    pairs = [r for r, count in rank_counts.items() if count >= 2]
    if pairs:
        pair_ranks = [Card.Ranks[r] for r in pairs]
        threats.append(f"Pairs on Board: {', '.join(pair_ranks)}")
    
    return threats if threats else ["No immediate threats detected"]

