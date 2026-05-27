def get_poker_advice(sim_results, community_cards, current_pot, bet_to_call, num_players=2):
    """
    Translates Monte Carlo results into mathematically sound poker advice.
    sim_results: dict -> The output from your simulate() function
    community_cards: list -> The current community cards in play
    current_pot: float -> The total money in the pot BEFORE you call
    bet_to_call: float -> How much it costs you to stay in (0 if checking/betting first)
    num_players: int -> Number of active players in the hand
    """
    # 1. Calculate True Equity from your simulation dict
    win_pct = sim_results["win"]
    tie_pct = sim_results["tie"]
    equity = (win_pct + (tie_pct / 2)) / 100.0  # Convert to a 0.0 - 1.0 decimal

    # 2. Determine the current street based on number of community cards
    num_cards = len(community_cards)
    if num_cards == 0:
        street = "Preflop"
    elif num_cards == 3:
        street = "Flop"
    elif num_cards == 4:
        street = "Turn"
    elif num_cards == 5:
        street = "River"
    else:
        street = "Unknown"

    # 3. Apply the Equity Realization Tax (Adjust for the "No-Fold" simulation artifact)
    # This prevents you from over-calling when there are future cards left to be dealt.
    if street == "Preflop":
        adjusted_equity = equity - 0.08
    elif street == "Flop":
        adjusted_equity = equity - 0.05
    elif street == "Turn":
        adjusted_equity = equity - 0.02
    else:  # River
        adjusted_equity = equity  # 100% accurate on the river

    # 4. Scenario A: Facing a Bet (bet_to_call > 0)
    if bet_to_call > 0:
        # Calculate Pot Odds Threshold
        total_pot_if_called = current_pot + bet_to_call
        pot_odds = bet_to_call / total_pot_if_called

        # Calculate Minimum Defense Frequency (MDF) to counter big bluffers
        # Opponent's bet size is the bet_to_call. The pot before their bet was (current_pot - bet_to_call)
        pot_before_bet = max(0.1, current_pot - bet_to_call) 
        mdf = pot_before_bet / (pot_before_bet + bet_to_call)

        # Basic EV call check
        if adjusted_equity >= pot_odds:
            # If our equity is massively dominating, consider raising
            if adjusted_equity > (pot_odds + 0.20):
                return {"action": "RAISE", "reason": f"High adjusted equity ({adjusted_equity*100:.1f}%) cleanly beats Pot Odds ({pot_odds*100:.1f}%)."}
            else:
                return {"action": "CALL", "reason": f"Adjusted equity ({adjusted_equity*100:.1f}%) justifies a profitable call based on Pot Odds."}
        
        # EXPLOITATIVE ANTI-BLUFF LAYER (Heads-Up Only)
        # If pot odds say fold, check if MDF demands we protect ourselves against a big bluffer
        elif num_players == 2 and street != "Preflop":
            # If our raw equity is in the top tier of what we could have, or if the opponent is over-betting
            # We use a proxy: if raw equity is still reasonably close to a coinflip but pot odds failed
            if equity > 0.40 and mdf < 0.55: 
                return {"action": "CALL (Bluff Catcher)", "reason": f"Pure odds say fold, but in a 2-player game, the opponent's large bet size requires you to defend to prevent being bluffed out."}
        
        return {"action": "FOLD", "reason": f"Adjusted equity ({adjusted_equity*100:.1f}%) is too low to match Pot Odds ({pot_odds*100:.1f}%)."}

    # 5. Scenario B: Action is on You / Checking or Betting (bet_to_call == 0)
    else:
        # Value betting threshold
        if num_players == 2:
            value_threshold = 0.52 # Need >50% equity against 1 player
        else:
            value_threshold = 1.0 / num_players + 0.05 # Dynamic multi-way threshold
            
        if adjusted_equity >= value_threshold:
            return {"action": "BET / RAISE", "reason": f"Your equity is high enough ({equity*100:.1f}%) to bet for value against {num_players-1} opponents."}
        else:
            return {"action": "CHECK", "reason": f"Equity ({equity*100:.1f}%) isn't strong enough to value bet. Check to see the next card or showdown free."}