# Hold'em Lab

A Texas Hold'em lab I built in Python. It estimates how often your hand wins with Monte Carlo simulation, turns that into decisions (play, call or fold) by working out what your opponent likely holds, and trains a machine-learning bot that learns to beat different kinds of players. It also checks its own math against exact answers.

```
 cards ──► EQUITY ──► RANGES ──► DECISIONS ──► BOT
          how often   what they   call / fold,   learns each opponent,
          you win     likely hold pot odds, EV   trained with ML on profit
          (Monte      (from their
           Carlo)      actions)

        + ACCURACY: is the equity right, and how many sims is enough?
```

---

## Start here

| I want to... | Run |
|---|---|
| See how often my hand wins | `python3 hand_analysis.py` |
| Know whether to play, call or fold | `python3 advise.py` |
| Watch bots play simulated opponents | `python3 bots/arena.py` |
| Train the ML bot | `python3 bots/train.py` |
| Check the sim against exact answers | `python3 accuracy/validate.py` |
| See how many sims are enough | `python3 accuracy/convergence.py` |

Every script asks for its inputs if you run it with no options. After each result it asks **Try another?**, and the next round starts with your previous answers in brackets, so you can press enter to keep them and change only what you want, e.g. the same hand with a different board or player count. Ctrl-C quits. You can also pass options (shown in each section) to skip the questions. Run everything from the project folder.

---

## Setup

Needs Python 3.10 or newer.

```bash
pip install matplotlib pandas scikit-learn
```

(numpy and Pillow, used by the convergence animation, come with these.)

---

## 1. Equity: how often you win

`hand_analysis.py` asks for your hole cards (like `AS KH`; use `10H` for the ten of hearts), the number of players including you, the number of simulations (enter for 10,000), and the community cards, if any.

* Win / tie / loss estimates for 2-9 players, from preflop through the river
* Two views of your hand (see below), each compared with what an average hand would get
* An equity-by-street plot that compares preflop, flop, turn and river equity

### Two ways to look at your hand

1. **vs random hands (nobody folds).** Everyone gets two random cards and stays in to showdown. This is the classic equity calculator.
2. **At a real table (weak hands fold).** Everyone is dealt random cards, then anyone holding an unplayable hand folds. Folded cards stay dead (they can't land on the board) and you play whoever is left. If everyone folds, you take the pot.

Each view is compared with **what an average hand gets in that same situation**. With nobody folding, that's 1 / players (11.1% at 9 players). At a real table it's higher, since an average hand faces fewer opponents and sometimes wins when everyone folds. It's measured by running the same sim with a random hand in your seat.

### How "playable" gets decided

The preflop tables are already included in `poker/Data/` as `Standard{n}.csv`, for 3, 5, 7 and 9 players. Each one has all 169 starting hands simulated against random opponents (10,000 sims per hand). `poker/Data/preflop_tables.py` builds them and looks hands up:

```bash
python3 poker/Data/preflop_tables.py                          # asks: build or find
python3 poker/Data/preflop_tables.py --find "J10 Suited" --players 9
python3 poker/Data/preflop_tables.py --build 6                # add a 6-player table
```

The real-table view needs a table for your player count; without one, `hand_analysis.py` shows the random-hands view and tells you to build it.

A hand counts as playable if its equity is at least the table's fair share, which is 1 / number of players. At 9 players that's about 11.1%, and 94 of the 169 hand types make the cut. It's a single cut, with no repeated rounds of tightening.

### The math

Every tool runs on one Monte Carlo engine (`poker/equity.py`). Equity is your average share of the pot, with tied pots split exactly among whoever tied, and it's shown with a 95% confidence interval. The two views differ only in the opponent model the engine is given: random hands, or random hands where the weak ones fold.

A few honest caveats: in `hand_analysis.py`, opponents' hands don't depend on how they bet, and folding only happens preflop based on the starting hand. "Playable" is judged purely by equity against random hands. Betting is handled in `advise.py` and the bots below.

### Example

* **Hole cards:** 7H 2S
* **Players:** 9
* **Simulations:** 3000
* **Community cards:** AH QD 2H 7D 7C

That makes sevens full of twos.

```
--- VS RANDOM HANDS (nobody folds) ---
Win:  88.4%
Tie:  1.4%
Loss: 10.1%
Equity: 89.1% ± 1.1  (an average hand here: 11.1%)

--- AT A REAL TABLE (weak hands fold, their cards stay dead) ---
Win:  92.3%  (0.6% because everyone folded)
Tie:  0.0%
Loss: 7.7%
Average opponents left in: 3.55
Equity: 92.3% ± 1.0  (an average hand here: 20.8%)
```

At a real table the loss rate drops: more than half of the eight opponents fold, so only about three or four are left to beat you. The hands that beat this one are AA, QQ, or the 7 of spades with an ace or a queen. Ties drop to 0.0% because the only hands that tie are the 7 of spades with a 2, and 7-2 isn't a hand people play.


The plot shows the same hand street by street, in both views. Each solid line has a matching baseline in the same color: the dashed line is an average hand with nobody folding (11.1%), and the dotted line is an average hand at a real table (about 18–22% here). Here 7-2 sits below the real-table average until the turn, then climbs well above it. The plot and the text come from the same run, so their numbers match.

<img width="899" height="552" alt="Screenshot 2026-11-21 at 2 30 57 AM" src="https://github.com/user-attachments/assets/56642ed5-2fb2-4f2a-a493-203611d33f1b" />


---

## 2. Decisions: play, call or fold

`advise.py` turns equity into a decision:

```bash
python3 advise.py                                                   # asks you questions
python3 advise.py --hole "AS 10S" --players 9                       # preflop: playable?
python3 advise.py --hole "KH KD" --board "KS 9H 4H 7C 2H" --pot 10 --bet pot --stack 40
python3 advise.py --hole "QH JH" --board "10H 4C 2H" --opponents 2 --pot 60 --bet 20 --bb 2
python3 advise.py --hole "9S 9D" --board "7H 4C 2D 3S JC" --pot 10 --bet pot --action "raise big"
python3 advise.py --hole "9S 9D" --board "7H 4C 2D 3S JC" --pot 10 --bet pot --action raise --flop "bet half" --turn check
```

* **Preflop:** PLAY / FOLD / CLOSE, comparing your equity with the fair share (1 / players), the same cutoff the preflop tables use.
* **Facing a bet:** CALL / FOLD / CLOSE. In CLOSE spots it also says how often to call (closer to break-even means closer to 50%), and `--roll` picks one for you at that rate.
* **Pot odds:** You need equity of at least call ÷ (pot + call) to break even, and EV(call) = equity × (pot + call) − call, with folding worth 0. The bet can be an amount or `third`, `half`, `pot`, `75%`, `2x`.
* **Units:** amounts are in big blinds, and EV is reported in big blinds. If you'd rather type chips, pass `--bb` with the big blind's size (`--bb 2` makes `--pot 60` mean 30bb). `2.5bb` always means big blinds.
* **Stack (optional):** `--stack` is your stack before calling. It shows what's left behind and the stack-to-pot ratio. If calling puts you all in, it uses only the part of the bet you can match, and notes that pot odds are exact since no more betting follows.
* **CLOSE** means the equity is within 3 points of break-even, or within its confidence interval. Those are the spots where the right answer depends on who you're playing.

Equity is shown against random hands and against played hands (the hands people actually play, since anyone still in the hand chose to play), with a 95% interval, and the verdict uses played hands when there's a table for that many players. Tied pots are split exactly.

**Big bets:** players who bet half the pot or more usually hold strong hands or bluffs, not the average playable hand. So for those the CLOSE band is wider and the output warns that the equity is likely too optimistic, unless ranging (below) has already accounted for the bet.

### Ranging: what they could have

`advise.py` narrows the opponent's possible hands based on what they did, then computes your equity against that range:

* **Preflop action** (`--action`, or asked): `raise` keeps roughly their top 20% of hands, `raise big` / `3bet` the top 6%, and `call` / `limp` hands inside the top 40% (with top hands less likely, since they'd usually raise). If you don't give one, it assumes they played a hand, roughly the top 45%.
* **Flop and turn actions** (`--flop`, `--turn`, or asked): `check`, `call`, `raise`, or `bet` with a size (`bet half`, `bet pot`, `bet 75%`, `bet 2x`). Draws (flush draws, open-ended straight draws, gutshots) are tracked separately, since players often bet them as semi-bluffs:

  | They... | Strong hands | Draws | In-between | Missed |
  |---|---|---|---|---|
  | bet | kept (bigger bets need stronger) | often | sometimes | sometimes (c-bet bluffs) |
  | check | rarely (they'd usually bet) | sometimes | kept | mostly kept |
  | call | sometimes (might have raised) | kept | kept | rarely |
  | raise | kept, stronger | sometimes | rarely | rarely |

  A bet you're facing on the flop or turn counts the same way.
* **River bet:** the bet you're facing narrows it further. Hands that beat most of the possible hands on this board bet for value (bigger bets need stronger hands), in-between hands rarely bet, and missed hands are kept as bluffs. With no read, bluffs are assumed to make up a balanced share of their bets: bet ÷ (pot + 2 × bet), which is a third for a pot-sized bet.
* **Output:** their most likely hands, what they're holding on the board (pairs, flushes, nothing), what they're drawing to before the river, how much of their range beats you, and your equity vs the range. On the river against one opponent that's exact, so no ± is shown.

For example, a big preflop raiser bets pot on a low river. Against random hands 9-9 looks like an easy call (75%), but their range is mostly AA–JJ plus AK/AQ that missed, so your equity drops to 31%, just under the 33% you need. The verdict is CLOSE, and it comes down to whether this player bluffs a balanced amount.

The assumed tendencies live in `Tendencies` in `poker/ranges.py`: how wide they raise, how often they c-bet, semi-bluff, trap and float.

**Why river bluff-catchers come out CLOSE with no read:** a balanced bluffing amount is, by definition, the amount that makes a bluff-catching hand break even. So with no read, hands that only beat bluffs land near the pot odds, and the earlier streets mostly change which value hands they have, not how many bluffs. That's the honest no-read answer. What decides those spots is how this particular player bluffs, which is what the bots learn.

---

## 3. Bots: learning to beat opponents

`bots/` plays simulated opponents, learns how each one plays, and trains a machine-learning bot on the results.

### The arena

```bash
python3 bots/arena.py                      # asks you questions
python3 bots/arena.py --hands 100000 --session 1000 --save arena.png
```

**The game:** a heads-up river with 10bb in the pot. Players take turns acting first, so each one alternates between betting or checking and calling or folding. Each opponent plays one session (1,000 hands by default) and is a randomly nudged version of one of four profiles in `bots/profiles.py`: nit, regular, calling station and maniac. The bot meets every new opponent knowing nothing about them.

**Real cards, fast:** the first run scores every possible hand on 1,000 real river boards (about 45 seconds, cached in `bots/cache/`). Both players are dealt hands people actually play, and the bot ranges its opponent with real cards, blockers included, using the same value-and-bluff logic as `advise.py`. 100,000 hands take about 10 seconds per bot.

**Bot versions** (the hand-built bot in `bots/ml_agent.py`), all playing exactly the same deals and opponents:

* **no read:** the same no-read assumptions as `advise.py`, and never learns
* **no read + mixing:** randomizes in CLOSE spots
* **learner:** learns what this opponent's bets look like at showdown and how often they call its bets, starting from the no-read assumptions held as if it had seen about 8 hands, and mixes
* **learner, no mixing**
* **oracle:** knows the opponent's exact profile, but still plays the hand-built rules

**Results** (100,000 hands, new opponent every 1,000):

| bb/100 | no read | no read + mixing | learner | learner, no mixing | oracle |
|---|---|---|---|---|---|
| all | +42.2 | +26.5 | +53.0 | +55.3 | +63.3 |
| vs nits | −16.3 | −15.5 | +16.2 | +16.9 | +33.4 |

* Even "no read" profits, because the opponents are simple fixed rules and fixed rules are exploitable. So the meaningful number is each bot's **edge over "no read" on the same hands**, which the arena reports with a 95% interval.
* The learner without mixing is +13.1 ± 1.7 bb/100 ahead of "no read" and clearly ahead from about **hand 100** against a new opponent. The biggest gain is against nits: it learns they rarely bluff and stops paying them off.
* **Mixing costs money here** (about 16 bb/100), because these opponents never adapt. Mixing is protection against opponents who learn your patterns, like other bots in a competition. Against fixed opponents it's just a cost.

The plot shows cumulative profit for each bot, and each bot's edge over "no read" by how many hands into a new opponent it is.

### Training the ML bot

```bash
python3 bots/train.py                      # asks you questions
python3 bots/train.py --rounds 5 --hands 20000 --save training.png
```

The ML bot (`MLAgent` in `bots/ml_agent.py`) uses two gradient-boosted models (scikit-learn's `HistGradientBoostingRegressor`). One predicts the profit of calling a bet. The other predicts the profit of checking and of betting ½, ¾ or 1¼ pot. Its features are the hand-built bot's guidance: hand strength, equity vs the ranged opponent, pot odds, the hand-built EV of each action, and its reads on this opponent (bluff share, call rate, how many hands of evidence).

Training works in rounds:

1. **Play** hands against random opponents. Every decision is logged with the profit the hand made, which is the reward. Early rounds explore a lot (30% random actions), later ones less (5%).
2. **Retrain** both models on everything collected so far.
3. **Test** a frozen copy on held-out hands against held-out opponents, including a "tricky" type (over-bets with very strong hands or bluffs) it never trains against.

Results (100,000 training hands, about 2 minutes):

| Test opponents | ML bot | no read | learner | oracle |
|---|---|---|---|---|
| all | +97.5 | +70.3 | +78.6 | +87.3 |
| nit | +20.5 | −10.9 | +11.9 | +20.1 |
| calling station | +113.8 | +73.1 | +88.2 | +86.3 |
| tricky (never trained on) | +54.0 | +43.1 | +34.4 | +52.7 |

Its edge over the hand-built learner grows from +3.4 ± 5.0 bb/100 after 20,000 hands to +18.9 ± 4.3 after 100,000. It even beats the "oracle" overall. The oracle knows the opponent's profile but still plays the hand-built rules, with one bet size. The ML bot learns things those rules miss, like betting bigger for value against calling stations. The trained models are saved to `bots/cache/ml_model.joblib`.

To watch it learn, add `--animate training.gif` (10 rounds of 10,000 hands works well: `--rounds 10 --hands 10000`). Each frame is one round and shows:

* its win rate and its edge over the hand-built learner so far;
* what it does when it acts first, at each hand strength (check, or bet ½, ¾ or 1¼ pot);
* how often it calls a bet, at each hand strength, next to the hand-built guidance it started from;
* which inputs each model relies on.

Every round replays the same fixed set of spots, so the changes come from what it learned, not from new cards.

### What the ML bot relies on

```bash
python3 bots/explain.py --save explain.png
```

The script plays 20,000 hands with the trained bot, then draws two views:

* **Which inputs matter:** it scrambles one input at a time and measures how much the model's own predictions change. The more they change, the more the model relies on that input.
* **Its logic as a tree:** a 3-level decision tree is fitted to imitate each model, so its main splits can be read as if/else rules. The title shows how closely the small tree matches the full model (R²).

What it shows:

* **The calling model** leans most on your equity against their whole range, then on the hand-built EV of calling and the bet size. The reads (call rate, bluff share) matter, but mostly through the ranged equity, which already uses them. "Pot odds needed" is ignored, since bet size already carries that information.
* **The betting model** relies almost entirely on the hand-built EV of each option (a 3-level tree matches it with R² = 0.97). So it learned to trust the guidance, and its edge comes from correcting it: which size to pick, and when the hand-built numbers are too optimistic or too pessimistic.

---

## 4. Accuracy: is the math right?

### Validation

`accuracy/validate.py` checks the Monte Carlo sim against the true equity, heads-up against one random hand:

```bash
python3 accuracy/validate.py                                   # asks you questions
python3 accuracy/validate.py --hole "AH KH" --board "QH JD 2C"
python3 accuracy/validate.py --hole "KS KD" --board ""         # preflop
python3 accuracy/validate.py --hole "7H 2S" --board "AH QD 2H 7D" --save validation.png
```

* **Flop, turn, river:** the true equity comes from enumerating every opponent hand and every runout (about 1.07 million matchups on the flop, about 35 seconds).
* **Preflop:** enumerating would mean about 2.1 billion matchups, so it uses published exact equities instead (AA, KK, QQ, JJ, TT, AKs, AQs, AKo). Only hands where both of these sources agree to two decimals are included:
  * [pailiku.com: Texas Hold'em matchup odds, exact enumerations](https://pailiku.com/matchups)
  * [pokercoaching.com: Best Texas Hold'em starting hands](https://pokercoaching.com/blog/best-texas-holdem-starting-hands/)

It then runs the sim several times and tracks a 95% confidence interval (estimate ± 1.96·σ/√n) as the number of simulations grows. It reports how many runs end with an interval that contains the true value (should be about 95%) and how many simulations you need for a given precision. Against a random hand, 10,000 sims gives roughly ±1 point. The plot shows the interval closing in on the true equity, and the interval width falling as 1/√n (4× the sims gives half the width).

The flop, turn and river checks use the same hand evaluator for both the enumeration and the sim, so they test the sampling and the interval math. The preflop check compares against outside numbers, so it also tests the evaluator.

### Convergence

`accuracy/convergence.py` shows how the estimate settles as the number of simulations grows. It works for any hand, player count and board:

```bash
python3 accuracy/convergence.py                                     # asks you questions
python3 accuracy/convergence.py --hole "AS KH" --players 6
python3 accuracy/convergence.py --hole "7H 2S" --players 9 --board "AH QD 2H" --save convergence.gif
```

It prints the running equity and its 95% confidence interval at checkpoints (100, 200, 500, 1,000, ...), how far the estimate moved since the last checkpoint, and how many sims you'd need for ±2, ±1, ±0.5 or ±0.1 points. The 95% confidence interval is estimate ± 1.96·σ/√n, so 4× the sims gives half the width.

It also plays an animation: the running estimate draws in with its confidence band shrinking around it, next to a bell curve of where the true equity probably is, which narrows into a spike. Use `--save file.gif` to save it, or `--no-animate` to skip it.

<img width="1299" height="559" alt="Screenshot 2026-11-19 at 4 46 56 PM" src="https://github.com/user-attachments/assets/ef600f3d-c15f-4d8f-86d3-4f4567a49cd7" />

---

## Project layout

```
holdem-lab/
├── README.md
├── hand_analysis.py           # 1. equity: how often your hand wins
├── advise.py                  # 2. decisions: play / call / fold, pot odds, ranging
├── bots/                      # 3. bots
│   ├── profiles.py            # opponent types (nit, regular, calling station, maniac, tricky)
│   ├── pool.py                # scores every hand on 1,000 real river boards, cached
│   ├── ml_agent.py            # the bot: hand-built versions + the ML bot
│   ├── arena.py               # plays bot versions against random opponents
│   ├── train.py               # trains the ML bot, tests on held-out opponents
│   └── explain.py             # which inputs the ML bot relies on, its logic as a tree, training animation
├── accuracy/                  # 4. accuracy
│   ├── validate.py            # sim vs exact / published equity
│   └── convergence.py         # how many sims is enough, with animation
└── poker/                     # the engine everything above uses
    ├── card.py, deck.py       # cards and deck
    ├── evaluator.py           # hand ranking
    ├── equity.py              # the Monte Carlo engine: equity + 95% CI vs an opponent model
    ├── tables.py              # preflop tables: load, playable hands, look up
    ├── ranges.py              # narrowing an opponent's range from their actions
    ├── decisions.py           # pot odds, EV and verdicts (tunable Settings)
    ├── visualizer.py          # equity-by-street plot
    ├── prompts.py             # the questions the scripts ask, with defaults
    └── Data/                  # preflop tables (Standard{n}.csv)
        └── preflop_tables.py  # builds a table or looks up a hand
```
