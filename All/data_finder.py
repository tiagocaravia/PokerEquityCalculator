import csv
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, 'Standard5.csv')

with open(file_path, 'r', newline='') as file:
    reader = csv.reader(file)
    data = list(reader)


def FindHand (hand):
    Swaphand = list(hand)
    Swaphand[0], Swaphand[1] = Swaphand[1], Swaphand[0]  # Swap the first two characters
    Swaphand = ''.join(Swaphand)  # Convert the list back to a string
    for row in data[1:]:  # Skip the header row
        if row[0] == hand or row[0] == Swaphand:
            win_percentage = float(row[1])
            tie_percentage = float(row[2])
            loss_percentage = float(row[3])
            
            return {
                "Hand": hand,
                "win%": win_percentage,
                "tie%": tie_percentage,
                "loss%": loss_percentage
            }
    return None  # Return None if the hand is not found


