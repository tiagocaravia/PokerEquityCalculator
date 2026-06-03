# Texas Hold'em Monte Carlo Equity Calculator

A high-performance Texas Hold'em equity calculator built in pure Python. The engine leverages a Monte Carlo simulation loop to compute showdown probabilities and translates raw statistics into Expected Value (EV) driven betting advice.

---

## Features

* **Player Scaling** - Scales dynamically for 2-9 players in the pot.
* **Street Specific Advice** - Evaluates Preflop, Flop, Turn, or River states separately depending on the community cards provided.
* **Monte Carlo Simulation** - Simulates 10,000 random board runouts and opponent hand matrices per calculation.
* **Zero Dependencies** - Built entirely within the Python standard library with no external installation requirements.

---

## The Math Behind the Advice

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

* **Conclusion:** I stripped out the subjective patches to keep the codebase clean, testable, and deterministic. The engine provides unadulterated, objective EV data. This means the strategic limitations listed above must be audited and accounted for by the human user during live play.

---

## Future Plans

* ### Visualizer
* Implement visual graphs using libraries like Matplotlib to cleanly chart Equity vs. Pot Odds Thresholds and map equity shifts across different streets. Also visual how accurate the win% becomes as N (numer of tests) becomes greater and greater. 
  
* ### Algorithmic Adjustments for Equity Realization (R)
* Workshop a mathematically sound approach devoid of arbitrary constants to account for position and opponent profiles. The goal is to dynamically compute an Equity Realization factor ($R$) as a function of player aggression metrics, relative position, and board texture coordination.

* * ### Front End
* In order to do this I'll need to familiarise myself with HTML/CSS to make a pretty front end where inputting values is easy and doesn't require terminal to run. I'd also use this as a place to display the visualizer.

---

## Usage

Run the interface wrapper directly from your terminal:

```bash
python3 main.py
