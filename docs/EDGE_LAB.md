# Edge lab: a chair and five agents that look for an edge

The repo's 34 experiments are one agent testing one idea at a time, with the user supplying the
ideas (reels, channels, friends). Every one failed its bar or was withdrawn after an engine audit.
This is the next stage: a team that generates and tests ideas **starting from a reason**, and that
cannot fool itself. Run it with `/edge-lab <family|next>`.

## 1. Why the work is split this way

A single agent that both proposes and judges an idea will, over enough tries, find a number it
likes. The expected maximum of N zero-edge trials is about sqrt(2 ln N) standard errors, so with
68 past tests and a team that can run hundreds more, a "t of 3" is what luck produces. The split
removes each agent's chance to grade itself:

| Role | Does | Never does |
|---|---|---|
| **Chair** (the main session) | Runs the gates, commits pre-registrations, calls the ledger, talks to the user | Judges its own team's results alone |
| **mechanism-scout** | Proposes hypotheses from a mechanism, with a numeric prediction | Sees any result or data |
| **data-engineer** | Gets and validates data, finds the variables the old tests lacked | Computes a signal or a return |
| **quant-builder** | Writes the engine and its self-tests | Reads results before the audit; opens the verdict era |
| **edge-auditor** | Tries to break the engine, then any winner | Edits the engine |
| **edge-statistician** | Power, pre-registration, verdict against the bars and the total trial count | Writes engine code |

Subagents cannot start subagents, which is why the chair is the main session.

## 2. What an edge is, as a measurement

`backtest/edge_lab/measure.py` measures each clause of one sentence: *a signal whose excess
return per trade is large next to the all-in cost of trading it, that survives a market hedge,
and that a null built from the same signal cannot reproduce.*

| Measurement | Function | What it answers |
|---|---|---|
| Gross drift-matched excess, bp per trade | `information_test` | Is there any information at all, before costs? |
| Cost ratio = excess / 13 bp round trip | `information_test` | Can it pay for itself? Repo rule: >= 3-5 |
| Clustered t (week), de-overlapped trades | `cluster_mean_t` | Is it distinguishable from noise, without double counting overlapping windows? |
| Net per trade after cost and real funding | `information_test` | What the account would actually earn |
| Hedged alpha and beta to the market | `information_test(mkt_ret=...)` | Is it skill, or just being long in a bull market? |
| Circular-shift null, p-value | `null_shift_p` | Does the same signal at the wrong times do as well? |
| Years positive | `information_test` | Is it one regime? (v0.16d, v0.19 lived in single years) |
| Plateau score | `plateau_score` | Is the best parameter an island or a plateau? |
| Dollar-neutral long-short, full-turnover cost | `cross_sectional_ls` | Cross-sectional edges without market exposure |
| Lookahead test | `truncation_guard` | Does the signal at t change when the future is cut off? |
| Power / minimum detectable edge | `power.feasible` | Can this sample size resolve the claimed edge at all? |
| Deflated Sharpe vs total trials | `ledger.deflated_sharpe(total_trials())` | Does it survive the count of everything ever tried? |

The information test cannot see lookahead. A signal that peeks at the outcome scores t = 61 in
the self-test. Only `truncation_guard` and the auditor catch that, which is why they are
mandatory gates and not optional extras.

Cost model: taker 0.055 % + 0.01 % slippage per side (13 bp round trip), real settled funding.
Adverse selection on resting limit orders is **not** modelled (the user's instruction for now),
so the harness assumes taker fills. A maker-based variant must be a labelled secondary until a fill
model exists.

## 3. The gates

```
Gate 0  scout cards ──► chair screen (failure_path 5 points; predicted edge >= ~40 bp)
Gate 1  data report + power check + pre-registration  ──► commit, push, ledger.register
Gate 2  engine + self-tests, outcome-blind
Gate 3  auditor stage A  ──► ledger.mark_audited
Gate 4  --report (open_holdout, once) ──► statistician verdict ──► auditor stage B on a pass
Gate 5  DEVLOG, HANDOFF row, CLAUDE.md lesson if new, commit, push, tell the user
```

What the code enforces (`backtest/edge_lab/ledger.py`): a pre-registration must be a committed,
pushed, unmodified file; the verdict era opens once, only after the audit, and only if the
pre-registration is byte-identical to what was registered; every exploratory screen and every cell
is appended to `ledger.jsonl`, and `total_trials()` (legacy 68 plus everything since) is what the
deflated Sharpe uses. An agent can bypass the code; the bypass is then visible in git.

## 4. Where the data now reaches

Verified reachable from the cloud container: `data.binance.vision` and `public.bybit.com`
(bulk archives; the exchange APIs are blocked). Binance USDT-M futures carry what the old
kline-only tests never had: open interest, top-trader and global long/short ratios, taker
buy/sell volume (5-minute, from 2020-09), funding-premium klines, and book depth (from 2023-01).
No liquidation feed was found for BTCUSDT.

## 5. What to expect

The honest prior is low. The ledger's 34 failures cover mechanized chart patterns, news, signal
channels and one lookahead-free funding carry that passes its bar at ~10-14 %/yr, under the
~14-15 % pre-tax hurdle of the user's real alternative. Retail-sized edges that exist tend to be
thin, capacity-limited, and either low-turnover (so the move dwarfs the 13 bp cost) or
market-neutral. The team's value is partly the discovery of anything real and partly speed and
rigour in killing what is not. Treat a pass as a claim until stage B and a forward paper period
have failed to break it.

## 6. Starting backlog (families, not hypotheses; the scout turns them into cards)

None of these has been tested. Listed by how directly the mechanism can be stated, not by hope.

1. **Cross-sectional carry:** long low-funding, short high-funding perps, market neutral. The
   funding differential is paid, not predicted. Tests whether the price leg erases it.
2. **Forced-flow states:** open-interest build-up with funding at an extreme, then liquidation
   cascades (Osler's stop-clustering mechanism, RESEARCH.md section 1), daily horizon.
3. **Cross-sectional momentum or reversal across a point-in-time universe of 30-50 perps,**
   weekly rebalance, dollar neutral. Low turnover, so the cost ratio is reachable.
4. **Taker-flow imbalance** (taker buy/sell ratio, long/short ratios) as a 4-24 h predictor,
   conditioned on the state rather than a level.
5. **Premium-index dislocations:** perp-vs-spot premium extremes mean-reverting over 8-24 h
   (v0.24 killed the 1-5 bp funding-settlement version on cost; this asks about larger moves).
6. **Listing and delisting events** on small perps. Capacity-limited, which is the point.

Not on the list, because the data is not reachable or the ledger already answers it: options
volatility premium (no free archive), news and earnings reaction (v0.27, v0.32), anything drawn
from a chart (docs/failure_path.md).
