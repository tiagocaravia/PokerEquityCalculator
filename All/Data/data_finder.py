import os
import pandas as pd
script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, 'Standard5.csv')

df = pd.read_csv(file_path, dtype={"Hand": str})


def FindHand (hand):
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

print(FindHand("J10 Suited"))
