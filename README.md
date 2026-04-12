# Poker Equity Calculator

A Texas Hold'em equity calculator built in Python that uses Monte Carlo simulation to compute hand win probabilities and detect board threats in real time.

## Features
- Calculates win, tie, and loss percentages for any starting hand
- Gives Fold/Call/Raise tips/feedbacks
- Supports 2-9 players
- Accepts known community cards for mid-hand analysis
- Runs 10,000 simulated outcomes per calculation

## How It Works
Given your hole cards and any known community cards, the simulator randomly completes the board and deals opponent hands 10,000 times. Each iteration evaluates all hands using standard poker hand rankings and tracks wins, ties, and losses. It will also give advice based on community cards and equity on whether or not to play certain hands.

## Usage
```bash
python3 main.py
```
Enter your hole cards and community cards using rank + suit notation:
- `AS` = Ace of Spades
- `KH` = King of Hearts  
- `10D` = Ten of Diamonds

## File Structure
- `card.py` — Card class with rank and suit representation
- `deck.py` — Deck class with shuffle and deal methods
- `evaluator.py` — Hand ranking
- `sim.py` — Monte Carlo simulation engine
- `main.py` — CLI interface

## Advice Engine
Given pot size and bet amount, the calculator computes pot odds and recommends whether to fold, call, or raise based on your equity vs required equity.

- **Required equity** = Call Amount / (Pot + Call) × 100
- **Break-even equity** = 1 / Number of Players × 100
- Raise threshold scales relative to required equity with a minimum margin floor (15%)
- Preflop decisions use break-even equity when no bet is present

## Example Output

--- RESULTS ---
Win:  61.3%
Tie:  1.6%
Loss: 37.1%

--- ADVICE ---
Pot size: $50.0
Bet to call: $20.0
Required equity to call: 28.6%
Your equity: 61.3%
Equity margin: +32.7%
Decision: RAISE — equity is 114% above required

## Built With
Python 3 — no external libraries required
