def get_advice(win_pct, num_players, pot_size, bet_amount):
 
    advice_lines = []
    
    # Calculate the player's equity and compare it to the table's fair-share baseline
    fair_share = (1.0 / num_players) * 100
    equity = win_pct  # Using win_pct directly for a more conservative strategy (can also add tie_pct/num_players for a more aggressive approach)
    
    advice_lines.append(f"Your Showdown Equity: {equity:.1f}%")
    advice_lines.append(f"Table Fair-Share Baseline: {fair_share:.1f}%")
    
    # How to react when facing a bet (Action is on you to Call, Raise, or Fold)
    if bet_amount > 0:
        total_pot_if_called = pot_size + bet_amount
        pot_odds = (bet_amount / total_pot_if_called) * 100
        
        advice_lines.append(f"Pot Odds Threshold Required: {pot_odds:.1f}%")
        advice_lines.append("---")
        
        # Pure EV Decision Gate
        if equity > pot_odds:
            diff = equity - pot_odds
            advice_lines.append("RECOMMENDATION: [ CALL / RAISE ]")
            advice_lines.append(f"Reason: Mathematically profitable (+EV). Your equity exceeds the pot odds by +{diff:.1f}%.")
        else:
            diff = pot_odds - equity
            advice_lines.append("RECOMMENDATION: [ FOLD ]")
            advice_lines.append(f"Reason: Mathematically unprofitable (-EV). Your equity is short of the pot odds by -{diff:.1f}%.")
            
   # How to react when no bet is facing you (Action is on you to Check or Raise)
    else:
        advice_lines.append("---")
        # Pure Value Betting Threshold: Do you win more often than a random hand in this field size?
        if equity > fair_share:
            advice_lines.append("RECOMMENDATION: [ RAISE ]")
            advice_lines.append("Reason: Your equity is above the table fair-share. You have a profitable value-betting opportunity.")
        else:
            advice_lines.append("RECOMMENDATION: [ CHECK ]")
            advice_lines.append("Reason: Your equity is below the table fair-share. Check to realize your hand strength safely.")
            
    return advice_lines