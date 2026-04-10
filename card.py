class Card:
    RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    SUITS = ['Hearts', 'Diamonds', 'Clubs', 'Spades']

    def __init__(self, rank, suit):
        self.rank = rank
        self.suit = suit
        self.rank_value = self.RANKS.index(rank)

    def __repr__(self):
        return f"{self.rank} of {self.suit}"

