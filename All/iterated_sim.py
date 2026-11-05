import os
import pandas as pd
from sim import simulate
import random 
from itertools import combinations
from card import Card
from deck import Deck
from evaluator import best_hand


def load_survivors(num_players):
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Data')
    df = pd.read_csv(os.path.join(data_dir, f'Standard{num_players}.csv'))

    df["equity"] = df["win%"] + df["tie%"] / num_players  # same formula as plot_equity
    cutoff = 100 / num_players

    return df[df["equity"] >= cutoff]


def hand_label(c1, c2):
    lo, hi = sorted([c1, c2], key=lambda c: Card.RANKS.index(c.rank))
    kind = "Suited" if c1.suit == c2.suit else "Offsuit"
    return f"{lo.rank}{hi.rank} {kind}"

def build_pool(survivors):
    keep = set(survivors["Hand"])
    return [list(pair) for pair in combinations(Deck().cards, 2)
            if hand_label(*pair) in keep]    

def remove_dead(pool, known_cards):
    # drop any pool hand that uses a card already in your hand or on the board
    return [h for h in pool if not any(c in known_cards for c in h)]

def deal_opponents(pool, num_opponents):
    hands = []
    for _ in range(num_opponents):
        hand = random.choice(pool)
        hands.append(hand)
        pool = remove_dead(pool, hand)
    return hands

def simulate_vs_pool(hole_cards, community_cards, num_players, num_simulations, pool):
    wins = 0
    ties = 0
    losses = 0

    known_cards = hole_cards + community_cards
    live_pool = remove_dead(pool, known_cards)  # once, since your cards don't change
    base_deck = [c for c in Deck().cards if c not in known_cards]

    for _ in range(num_simulations):
        # opponents first, from the pool
        opponents = deal_opponents(live_pool, num_players - 1)
        opp_cards = [c for h in opponents for c in h]

        # then the rest of the board, from whatever cards are left
        deck = [c for c in base_deck if c not in opp_cards]
        random.shuffle(deck)
        cards_needed = 5 - len(community_cards)
        sim_community = community_cards + deck[:cards_needed]

        my_hand = best_hand(hole_cards + sim_community)
        best_opponent = max(best_hand(opp + sim_community) for opp in opponents)

        if my_hand > best_opponent:
            wins += 1
        elif my_hand == best_opponent:
            ties += 1
        else:
            losses += 1

    return {
        "win": round(wins / num_simulations * 100, 1),
        "tie": round(ties / num_simulations * 100, 1),
        "loss": round(losses / num_simulations * 100, 1),
    }

def simulate_with_folds(hole_cards, community_cards, num_players, num_simulations, keep):
    # keep = set of hand labels that stay in, e.g. set(load_survivors(n)["Hand"])
    wins = ties = losses = uncontested = 0
    equity_total = 0
    opponents_total = 0
    fair_share_total = 0

    known_cards = hole_cards + community_cards
    base_deck = [c for c in Deck().cards if c not in known_cards]
    cards_needed = 5 - len(community_cards)
    num_opponents = num_players - 1

    for _ in range(num_simulations):
        deck = base_deck.copy()
        random.shuffle(deck)

        # every opponent is dealt two random cards; weak hands fold but their cards stay dead
        dealt = [deck[2 * i: 2 * i + 2] for i in range(num_opponents)]
        deck = deck[2 * num_opponents:]
        active = [h for h in dealt if hand_label(*h) in keep]

        opponents_total += len(active)
        fair_share_total += 1 / (len(active) + 1)

        sim_community = community_cards + deck[:cards_needed]

        if not active:  # everyone folded to you
            wins += 1
            uncontested += 1
            equity_total += 1
            continue

        my_hand = best_hand(hole_cards + sim_community)
        opp_hands = [best_hand(h + sim_community) for h in active]
        best_opponent = max(opp_hands)

        if my_hand > best_opponent:
            wins += 1
            equity_total += 1
        elif my_hand == best_opponent:
            ties += 1
            equity_total += 1 / (1 + sum(1 for h in opp_hands if h == best_opponent))
        else:
            losses += 1

    n = num_simulations
    return {
        "win": round(wins / n * 100, 1),
        "tie": round(ties / n * 100, 1),
        "loss": round(losses / n * 100, 1),
        "uncontested": round(uncontested / n * 100, 1),
        "avg_opponents": round(opponents_total / n, 2),
        "equity": round(equity_total / n * 100, 1),
        "fair_share": round(fair_share_total / n * 100, 1),
    }