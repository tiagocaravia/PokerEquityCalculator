class Card:
    RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A'] # Card Ranks
    SUITS = ['Hearts', 'Diamonds', 'Clubs', 'Spades'] # Card Suits

    def __init__(self, rank, suit): # Intialize Each Card with a rank and suit
        self.rank = rank 
        self.suit = suit
        self.rank_value = self.RANKS.index(rank) # Index of rank to compare cards

    def __repr__(self): #return statement for each card
        return f"{self.rank} of {self.suit}"

