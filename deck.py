import random
from card import Card

class Deck:
    def __init__(self):
        self.cards = [Card(rank, suit) for suit in Card.SUITS for rank in Card.RANKS]
    
    def shuffle(self):
        random.shuffle(self.cards)

    def deal(self, num):
        dealt  = self.cards[:num]
        self.cards = self.cards[num:]
        return dealt
    
    def __repr__(self):
        return f"Deck of {len(self.cards)} cards"
    
    