# Texas Hold'em Monte Carlo Equity Calculator

A poker equity calculator I built in Python. Give it your hole cards, how many players are at the table, and (optionally) the board, and it runs a Monte Carlo sim to estimate how often you win.

---

## What it does

* Win / tie / loss estimates for 2-9 players, from preflop through the river
* Three different ways of modeling your opponents (see below)
* An equity-by-street plot that compares pre-flop, flop, turn, and river equity
* A preflop equity table for all 169 starting hands, which is how the sim decides what a "playable" hand is

---

## Three ways to look at your hand

1. **vs random opponents.** Everyone gets two random cards and stays in. This is the classic equity calculator.
2. **vs realistic opponents.** Everyone still stays in, but each opponent's hand is picked only from hands worth playing. Hands like 7-2 offsuit never shows up in a player's hand.
3. **vs table with folds.** Everyone is dealt random cards, then anyone holding an unplayable hand folds (same criteria as the realistic opponents). Folded cards stay dead (they can't land on the board) and you play whoever is left. If everyone folds, you take the pot.


---

## How "playable" gets decided

The preflop tables are already included in `Data/` as `Standard{n}.csv`, one per table size. Each one has all 169 starting hands simulated against random opponents. `data_collector.py` is what built them, so you only need to run it if you want to rebuild a table.

A hand counts as playable if its equity is at least the table's fair share, which is 1 / number of players. At 9 players that's about 11.1%, and ~75 of the 169 hand types make the cut.

It's a single cut, with no repeated rounds of tightening.

---

## The math

* **Random and realistic modes:** Showdown equity = Win% + (Tie% / Number of Players). This is a quick approximation for split pots.
* **Folds mode:** ties are split exactly among whoever actually tied. The fair share it reports adjusts to how many players are still in (the average of 1 / players left), so it isn't a fixed 1/N.

A few honest caveats: there's no betting in the model, folding only happens preflop based on the starting hand, and "playable" is judged purely by equity against random hands. It's a way to explore equity, not a full poker model (yet).

---

## Example

* **Hole cards:** 7H 2S
* **Players:** 9
* **Simulations:** 3000
* **Community cards:** AH QD 2H 7D 7C

That makes sevens full of twos.

```
--- RESULTS ---
Win:  89.8%
Tie:  1.6%
Loss: 8.6%

--- VS REALISTIC OPPONENTS (weak hands folded) ---
Win:  85.0%
Tie:  0.0%
Loss: 15.0%

--- VS TABLE WITH FOLDS (weak hands fold, their cards stay dead) ---
Win:  93.6%  (2.8% because everyone folded)
Tie:  0.0%
Loss: 6.4%
Average opponents left in: 2.72
Equity: 93.6%  (fair share: 31.3%)
```

Against realistic opponents the loss rate nearly doubles. The hands that beat this one are AA, QQ, or the 7 of spades with an ace or a queen, and those are all playable hands, so they show up far more often than they would from random cards. Ties drop to 0.0% because the only hands that tie are the 7 of spades with a 2, and 7-2 isn't playable.

<img width="899" height="548" alt="Screenshot 2026-11-05 at 7 00 47PM" src="https://github.com/user-attachments/assets/2703776d-ccb4-4f49-b078-4077f39d264b" />

The plot shows the same hand street by street, with all three views. The gray dashed line is the fair share if all 9 players stay in (11.1%). The green dotted line is the fair share when folds shrink the field, and it's the one the green line should be judged against. Here the folds line sits below its own baseline until the turn, then climbs well above it. (The plot comes from a separate run, so its numbers differ slightly from the output above. It's Monte Carlo, so every run wobbles a little.)

---

## Setup

```bash
pip install matplotlib pandas
```

---

## Usage

From the project folder, run:

```bash
python3 All/main.py
```

It will ask for:

* Your hole cards, like `AS KH` (use `10H` for the ten of hearts)
* Number of players, including you
* Number of simulations (press enter for the default of 10,000)
* Community cards, if any (or press enter to skip)

If there's no `Standard{n}.csv` for your player count, it still runs the random-opponent sim and tells you to run `data_collector.py` for the rest.

---

## Convergence

`convergence.py` shows how the estimate settles as the number of simulations grows. It works for any hand, player count and board:

```bash
python3 All/convergence.py --hole "AS KH" --players 6
python3 All/convergence.py --hole "7H 2S" --players 9 --board "AH QD 2H" --save convergence.gif
```

It prints the running equity and its 95% confidence interval at checkpoints (100, 200, 500, 1,000, ...), how far the estimate moved since the last checkpoint, and how many sims you'd need for ±2, ±1, ±0.5 or ±0.1 points. The 95% confidence interval is estimate ± 1.96·σ/√n, so 4× the sims gives half the width.

It also plays an animation: the running estimate draws in with its confidence band shrinking around it, next to a bell curve of where the true equity probably is, which narrows into a spike. Use `--save file.gif` to save it, or `--no-animate` to skip it.

---

## Validation

`validate.py` checks the Monte Carlo sim against the true equity, heads-up against one random hand:

```bash
python3 All/validate.py                                       # AH KH on QH JD 2C
python3 All/validate.py --hole "KS KD" --board ""             # preflop
python3 All/validate.py --hole "7H 2S" --board "AH QD 2H 7D" --save validation.png
```

* **Flop, turn, river:** the true equity comes from enumerating every opponent hand and every runout (about 1.07 million matchups on the flop, about 35 seconds).
* **Preflop:** enumerating would mean about 2.1 billion matchups, so it uses published exact equities instead (AA, KK, QQ, JJ, TT, AKs, AQs, AKo). Only hands where both of these sources agree to two decimals are included:
  * [pailiku.com: Texas Hold'em matchup odds, exact enumerations](https://pailiku.com/matchups)
  * [pokercoaching.com: Best Texas Hold'em starting hands](https://pokercoaching.com/blog/best-texas-holdem-starting-hands/)

It then runs the sim several times and tracks a 95% confidence interval (estimate ± 1.96·σ/√n) as the number of simulations grows. It reports how many runs end with an interval that contains the true value (should be about 95%) and how many simulations you need for a given precision. Against a random hand, 10,000 sims gives roughly ±1 point. The plot shows the interval closing in on the true equity, and the interval width falling as 1/√n (4× the sims gives half the width).

The flop, turn and river checks use the same hand evaluator for both the enumeration and the sim, so they test the sampling and the interval math. The preflop check compares against outside numbers, so it also tests the evaluator.

---

## Project layout

```
PokerEquityCalculator/
├── README.md
├── images/
│   └── equity_example.png # plot used in this README
└── All/
    ├── main.py            # command line interface
    ├── sim.py             # random-opponent simulation
    ├── iterated_sim.py    # realistic-opponent and folds simulations
    ├── visualizer.py      # equity plot
    ├── convergence.py     # running estimate + confidence interval, with animation
    ├── validate.py        # checks the sim against exact equity, with confidence intervals
    ├── data_collector.py  # builds the preflop equity tables
    ├── evaluator.py       # hand ranking
    ├── card.py            # card class
    ├── deck.py            # deck class
    └── Data/              # preflop tables (Standard{n}.csv)
```
