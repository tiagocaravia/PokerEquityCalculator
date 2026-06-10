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

## System Limitations and Strategic Trade-offs

* ## Architectural Decision History
* During development, I identified a core limitation: a Monte Carlo simulation calculates "hot-and-cold" showdown equity, assuming all players check to the river. It cannot natively account for human aggression, betting leverage, or positional disadvantages on early streets.
  
* ### The Proposed Solution
* To solve this, I designed a heuristic layer to simulate real-world betting pressure:
* * **Equity Realization Taxes:** Artificially slashing Pre-Flop equity by 8%, Flop equity by 5%, and Turn equity by 2% to protect the user from future betting rounds.
* * **Crowd & Position Penalties:** Hiking the required calling threshold by 3% for every active player left to act behind the user.
  
* #### Why I Ultimately Omitted This Solution
* 1. **Introduction of Magic Numbers:** Implementing these fixes required hardcoded, arbitrary constants. This degraded the mathematical integrity of the engine, turning a deterministic simulator into a subjective guessing tool.
* 2. **Strategic Context-Blindness:** Static taxes assume a fixed opponent profile. A 5% penalty safely defends against a hyper-aggressive bluffer, but it results in massive under-realization and highly unprofitable over-folding against passive players.

---

## Future Plans
  
* ### Algorithmic Adjustments for Equity Realization (R)
* Workshop a mathematically sound approach devoid of arbitrary constants to account for position and opponent profiles. The goal is to dynamically compute an Equity Realization factor ($R$) as a function of player aggression metrics, relative position, and board texture coordination.

* ### Front End
* In order to do this I'll need to familiarise myself with HTML/CSS to make a pretty front end where inputting values is easy and doesn't require terminal to run. I'd also use this as a place to display the visualizer.

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
