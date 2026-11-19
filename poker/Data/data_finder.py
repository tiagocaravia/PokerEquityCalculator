import os
import sys
import pandas as pd

script_dir = os.path.dirname(os.path.abspath(__file__))
tables = {}  # Tables already loaded, by player count


def load(num_players):
    if num_players not in tables:
        file_path = os.path.join(script_dir, f'Standard{num_players}.csv')
        tables[num_players] = pd.read_csv(file_path, dtype={"Hand": str})
    return tables[num_players]


def FindHand (hand, num_players=5): # Looks up a hand like "J10 Suited" or "AA Offsuit" in the table for num_players
    df = load(num_players)
    Swaphand = list(hand)
    if Swaphand[2] == " ":
        Swaphand[0], Swaphand[1] = Swaphand[1], Swaphand[0]  # Swap the first two characters
    elif hand.startswith("10"):
        Swaphand[0], Swaphand[1], Swaphand[2] = Swaphand[2], Swaphand[0], Swaphand[1]  # 10 first: 102 -> 210
    else:
        Swaphand[0], Swaphand[1], Swaphand[2] = Swaphand[1], Swaphand[2], Swaphand[0]  # 10 second: J10 -> 10J
    Swaphand = ''.join(Swaphand)  # Convert the list back to a string
    match = df[(df["Hand"] == hand) | (df["Hand"] == Swaphand)]
    if match.empty:
        return None  # Return None if the hand is not found
    return match.iloc[0].to_dict()

if __name__ == "__main__":
    # python3 poker/Data/data_finder.py "J10 Suited" 9
    hand = sys.argv[1] if len(sys.argv) > 1 else "J10 Suited"
    players = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    print(FindHand(hand, players))
