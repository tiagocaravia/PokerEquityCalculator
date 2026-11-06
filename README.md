# Texas Hold'em Monte Carlo Equity Calculator

A poker equity calculator I built in pure Python. Give it your hole cards, how many players are at the table, and (optionally) the board, and it runs a Monte Carlo sim to estimate how often you win. It's not fast. It's just simple, readable, and a fun way to poke at how poker equity actually works.

---

## What it does

* Win / tie / loss estimates for 2-9 players, from preflop through the river
* Three different ways of modeling your opponents (see below)
* An equity-by-street plot that compares all three
* A preflop equity table for all 169 starting hands, which is how the sim decides what a "playable" hand is

---

## Three ways to look at your hand

1. **vs random opponents.** Everyone gets two random cards and stays in. This is the classic equity calculator.
2. **vs realistic opponents.** Everyone still stays in, but each opponent's hand is picked only from hands worth playing. Junk like 7-2 offsuit never shows up.
3. **vs table with folds.** Everyone is dealt random cards, then anyone holding an unplayable hand folds. Folded cards stay dead (they can't land on the board) and you play whoever is left. If everyone folds, you take the pot.

The gaps between these are the interesting part. A hand can look great against random cards and a lot worse against people who only play good hands, and the field shrinking changes things again.

---

## How "playable" gets decided

The preflop tables are already included in `Data/` as `Standard{n}.csv`, one per table size. Each one has all 169 starting hands simulated against random opponents. `data_collector.py` is what built them, so you only need to run it if you want to rebuild a table.

A hand counts as playable if its equity is at least the table's fair share, which is 1 / number of players. At 9 players that's about 11.1%, and 81 of the 169 hand types make the cut (roughly 38% of all two-card combos).

It's a single cut, with no repeated rounds of tightening.

---

## The math

* **Random and realistic modes:** Showdown equity = Win% + (Tie% / Number of Players). This is a quick approximation for split pots.
* **Folds mode:** ties are split exactly among whoever actually tied. The fair share it reports adjusts to how many players are still in (the average of 1 / players left), so it isn't a fixed 1/N.

A few honest caveats: there's no betting in the model, folding only happens preflop based on the starting hand, and "playable" is judged purely by equity against random hands. It's a way to explore equity, not a full poker model.

---

## Example

* **Hole cards:** 7H 2S
* **Players:** 9
* **Simulations:** 3000
* **Community cards:** AH QD 2H 7D 7C

That makes sevens full of twos.

```
--- RESULTS ---
Win:  89.2%
Tie:  1.3%
Loss: 9.5%

--- VS REALISTIC OPPONENTS (weak hands folded) ---
Win:  82.7%
Tie:  0.0%
Loss: 17.3%

--- VS TABLE WITH FOLDS (weak hands fold, their cards stay dead) ---
Win:  92.0%  (1.8% because everyone folded)
Tie:  0.0%
Loss: 8.0%
Average opponents left in: 3.04
Equity: 92.0%  (fair share: 28.4%)
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
    ├── data_collector.py  # builds the preflop equity tables
    ├── evaluator.py       # hand ranking
    ├── card.py            # card class
    ├── deck.py            # deck class
    └── Data/              # preflop tables (Standard{n}.csv)
```
