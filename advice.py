
def get_advice(equity, num_players, pot_size, bet_amount):
    
    advice = []
    break_even = round(1 / num_players * 100, 1)

    if bet_amount == 0:
        margin = equity - break_even

        strong_threshold = break_even * 0.5
        slight_threshold = break_even * 0.2
        weak_threshold = break_even * -0.2

        advice.append(f"Break-even equity at this table: {break_even}%")
        advice.append(f"Your equity: {equity}%")
        advice.append(f"Equity margin: {margin:+.1f}%")

        if margin >= strong_threshold:
            advice.append(f"Decision: BET/RAISE \n equity is {round(margin/break_even*100)}% above break-even \n Play Aggressive")
        elif margin >= slight_threshold:
            advice.append(f"Decision: BET \nsolid edge of {margin:+.1f}% \n Get Rid of Weaker Hands")
        elif margin > weak_threshold:
            advice.append(f"Decision: CHECK \n Very Close to Break Even \n Play Cautious")
        else:
            advice.append(f"Decision: FOLD \n equity is {round(abs(margin/break_even*100))}% below break-even \n Avoid Playing")

    else:
        total_pot_after_bet = pot_size + bet_amount
        required_equity = round((bet_amount / total_pot_after_bet) * 100, 1)
        margin = equity - required_equity
        strong_threshold = max(required_equity * 0.5, 15) #Ensure a minimum threshold for strong hands
        
        advice.append(f"Pot size: ${pot_size}")
        advice.append(f"Bet to call: ${bet_amount}")
        advice.append(f"Required equity to call: {required_equity}%")
        advice.append(f"Your equity: {equity}%")
        advice.append(f"Equity margin: {margin:+.1f}%")

        if margin >= strong_threshold:
            advice.append(f"Decision: RAISE \n equity is {round(margin/required_equity*100)}% above required \n Play Aggresive")
        elif margin >= 0:
            if bet_amount <= 0.5 * pot_size:
                advice.append(f"Decision: CALL \n equity is {round(margin/required_equity*100)}% above required \n Pot is reasonable to call")
            else:
                advice.append(f"Decision: CALL Cautiously \n equity is {round(margin/required_equity*100)}% above required \n Still at edge but pot is large, check for threat of stronger hands")
        else:
            advice.append(f"Decision: FOLD \n equity is {round(abs(margin/required_equity*100))}% below required \n Avoid Playing")

    return advice 

