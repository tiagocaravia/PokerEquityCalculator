# Poker Equity Calculator

A Texas Hold'em equity calculator built in Python that uses Monte Carlo simulation to compute hand win probabilities and detect board threats in real time.

## Features
- Calculates win, tie, and loss percentages for any starting hand
- Supports 2-9 players
- Accepts known community cards for mid-hand analysis
- Detects board threats including flush draws, straight draws, and paired boards
- Runs 10,000 simulated outcomes per calculation

## How It Works
Given your hole cards and any known community cards, the simulator randomly completes the board and deals opponent hands 10,000 times. Each iteration evaluates all hands using standard poker hand rankings and tracks wins, ties, and losses. Board threats are detected and aggregated across all simulations to show how often dangerous board textures appear.

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
- `evaluator.py` — Hand ranking and board threat detection
- `sim.py` — Monte Carlo simulation engine
- `main.py` — CLI interface

## Example Output
Win %: 87.1
Tie %: 1.0
Loss %: 11.9
Board Threats:
Straight Draw on Board: 22.5%
Flush Draw on Board: Hearts: 8.6%
Paired Board: 38.2%

## Built With
Python 3 — no external libraries required
