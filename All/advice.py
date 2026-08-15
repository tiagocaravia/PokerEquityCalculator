def get_advice(win_pct, tie_pct, num_players):
 
    advice_lines = []
    
    # Calculate the player's equity and compare it to the table's fair-share baseline
    fair_share = (1.0 / num_players) * 100
    equity = win_pct + (tie_pct / num_players)  # Equity calculated as win percentage plus share of ties
    
    advice_lines.append(f"Your Showdown Equity: {equity:.1f}%")
    advice_lines.append(f"Table Fair-Share Baseline: {fair_share:.1f}%")
    
    if equity > fair_share:
        advice_lines.append("Your equity is above the table fair-share. You have a profitable hand.")
    else:
        advice_lines.append("Your equity is below the table fair-share. You have a losing hand.")
            
    return advice_lines