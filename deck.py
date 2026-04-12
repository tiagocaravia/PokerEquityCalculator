import random
from card import Card

class Deck: 
    def __init__(self): # Initialize a standard 52-card deck
        self.cards = [Card(rank, suit) for suit in Card.SUITS for rank in Card.RANKS] # Creates cards from 2-Ace of each suit
    
    def shuffle(self): # Uses random library to shuffle the deck
        random.shuffle(self.cards)

    def deal(self, num): # Deals a specified number of card from top of deck
        dealt  = self.cards[:num]
        self.cards = self.cards[num:]
        return dealt
    
    def __repr__(self): # Return Statement for the deck
        return f"Deck of {len(self.cards)} cards"
    
    