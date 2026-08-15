from card import Card
from sim import simulate as sim

def AggregatePreflopOdds():
    PreflopEquity = []
    print("=== Preflop Odds Aggregator ===\n")
    num_players = int(input(f"Enter number of players (including you): "))
    num_simulations = input("Enter number of simulations (press enter to skip for standard amount): ")
    for rank1 in Card.RANKS: #Off Suit Sims
        for rank2 in Card.RANKS:
            hole_cards = [Card(rank1, 'Diamonds'), Card(rank2, 'Clubs')]
            if num_simulations:
                num_simulations = int(num_simulations)
            else:
                num_simulations = 10000
            result = sim(hole_cards, num_players=num_players, num_simulations=num_simulations)
            PreflopEquity.append({
                "Hand": f"{hole_cards[0]}, {hole_cards[1]}",
                "win%": result['win'],
                "tie%": result['tie'],
                "loss%": result['loss'],
            })
    for i in range(len(Card.RANKS)): #Suited Sims
        rank1 = Card.RANKS[i]
        for j in range(i + 1, len(Card.RANKS)):
            rank2 = Card.RANKS[j]
            hole_cards = [Card(rank1, 'Diamonds'), Card(rank2, 'Diamonds')]
            if num_simulations:
                num_simulations = int(num_simulations)
            else:
                num_simulations = 10000
            result = sim(hole_cards, num_players=num_players, num_simulations=num_simulations)
            PreflopEquity.append({
                "Hand": f"{hole_cards[0]}, {hole_cards[1]}",
                "win%": result['win'],
                "tie%": result['tie'],
                "loss%": result['loss'],
                })
    return PreflopEquity

print(AggregatePreflopOdds())