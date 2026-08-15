# Texas Hold'em Monte Carlo Equity Calculator

A high-performance Texas Hold'em equity calculator built in pure Python. The engine leverages a Monte Carlo simulation loop to compute showdown probabilities and translates raw statistics into Expected Value (EV) driven betting advice.

---

## Features

* **Player Scaling** - Scales dynamically for 2-9 players in the pot.
* **Street Specific Advice** - Evaluates Preflop, Flop, Turn, or River states separately depending on the community cards provided.
* **Monte Carlo Simulation** - Simulates 10,000 random board runouts and opponent hand matrices per calculation.
* **Visualizer** - Built a visualizer that analyzes equity based on each street 

---

## Math Element

## 1. True Equity Calculation
Splits ties equally among active players to ensure an accurate financial projection of your pot share:

Showdown Equity = Win% + (Tie% / Number of Players)

## 2. Decision Gateways

* **Facing a Bet:** Advises a Call/Raise if your showdown equity exceeds the pot odds threshold; otherwise, it advises a Fold.
  
  Pot Odds Threshold = (Bet to Call / (Current Pot + Bet to Call)) * 100

* **Checked Pots:** Advises a Value Bet if your equity beats the table's baseline fair share; otherwise, it plays defensively with a Check.
  
  Table Fair Share = (1 / Number of Players) * 100

---
## Examples
  
* ### Example 1: Poor Hand (Seven-Two Offsuit)
* **Input**
* Hole Cards: 7H 2S
* Players: 4
* Community Cards: AH KD QC 9D 3C
* Pot Size: 100
* Bet to Call: 30

<img width="661" height="180" alt="Screenshot 2026-06-09 at 4 20 48 PM" src="https://github.com/user-attachments/assets/d1fd0c57-e352-4330-85f6-4df148540cf8" />

<img width="797" height="494" alt="Screenshot 2026-06-09 at 4 21 07 PM" src="https://github.com/user-attachments/assets/78887fbb-712a-4203-b96f-1341e66a7df0" />

* ### Example 2: Medium Hand (Pair of Nines)
* **Input**
* Hole Cards: 9H 9S
* Players: 4
* Community Cards: AC 8D 3S KH 2C
* Pot Size: 100
* Bet to Call: 25

<img width="647" height="217" alt="Screenshot 2026-06-09 at 4 22 17 PM" src="https://github.com/user-attachments/assets/e6df6904-c6e1-4e53-8548-4540fe8d109d" />

<img width="798" height="500" alt="Screenshot 2026-06-09 at 4 22 34 PM" src="https://github.com/user-attachments/assets/99954045-6c2d-40cd-9609-3fbb93153431" />

### Example 3: Premium Hand (Pair of Aces)
* **Input**
* Hole Cards: AS AH
* Players: 4
* Community Cards: KC 7D 2S 9H 4C
* Pot Size: 100
* Bet to Call: 25

<img width="591" height="184" alt="Screenshot 2026-06-09 at 4 27 40 PM" src="https://github.com/user-attachments/assets/6f6b92bd-ac20-4b9c-a0f7-0d8988d6fae9" />

<img width="794" height="499" alt="Screenshot 2026-06-09 at 4 27 54 PM" src="https://github.com/user-attachments/assets/5b6e2a44-efac-4c52-b23f-4c7e491094b8" />

---

## Installation

```bash
pip install matplotlib
```

## Usage

Run the interface wrapper directly from your terminal:

```bash
python3 main.py

---
