class Card:
    RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A'] # Card Ranks
    SUITS = ['Hearts', 'Diamonds', 'Clubs', 'Spades'] # Card Suits

    def __init__(self, rank, suit): # Intialize Each Card with a rank and suit
        self.rank = rank 
        self.suit = suit
        self.rank_value = self.RANKS.index(rank) # Index of rank to compare cards

    def __repr__(self): #return statement for each card
        return f"{self.rank} of {self.suit}"

    def __eq__(self, other):
        return self.rank == other.rank and self.suit == other.suit


def parse_card(card_str): # Parses user input into Card objects
    card_str = card_str.strip().upper() # Standardizes input to uppercase and removes extra spaces
    suit_map = {'H': 'Hearts', 'D': 'Diamonds', 'C': 'Clubs', 'S': 'Spades'} # Attributes letter to suit
    rank = card_str[:-1] 
    suit = suit_map.get(card_str[-1]) 
    return Card(rank, suit)
