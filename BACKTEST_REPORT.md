# Why the bot wasn't working — audit findings + backtest

Audit of the full strategy/execution stack, the bugs found (ranked by damage),
and a backtest of the before/after behavior on real BTC 1-minute data.

## TL;DR

1. **The ICT strategy could never fire a single trade.** The fib-leg validity
   rule (`is_valid = recent_low > equilibrium`) declared every leg dead the
   moment price retraced to 0.5 — but the rejection-block detector only accepts
   candles AT OR BEYOND the 0.5 retracement. The two conditions are mutually
   exclusive. Every evaluation bailed at "No valid fib levels". The `legacy`
   backtest variant reproduces this: **zero ICT trades, ever**.
2. **Signals were evaluated against a still-forming candle.** Bybit returns the
   in-progress candle as the newest row; every module treated `iloc[-1]` as a
   closed confirmation candle, so "confirmation" was the first seconds of a
   fresh candle. Fixed by dropping the forming row in the data feed.
3. **Fees eat the VWAP strategy alive.** Median entry-to-exit move is 0.083 %
   of price; the round-trip cost is ~0.075–0.11 % of ~10× notional. Over 60
   days: gross −$650, **fees $3,611**, net −$4,261 (−43 % of the account, with
   ICT contributing nothing). Fee/risk is independent of position size, so no
   sizing rule fixes it. Paper trading never showed this because PnL was
   logged in points with no qty and no fees.
4. **Futures-scale constants on a BTC chart.** Stop buffers of "2.0 points"
   (~0.003 % of BTC) parked stops on top of entries — ICT trades died to noise
   within the entry minute. `LARGE_RB_THRESHOLD = 40` points classifies nearly
   every 5m BTC candle as "large". These numbers are NQ-scale, not BTC-scale.
5. **The tier R:R floors starve the strategy.** With TP = *nearest* liquidity
   level and honest stop distances, requiring 1:5 (Tier 1) / 1:3 (Tier 2)
   rejects every setup: 60-day backtest with tier gates on → **zero** ICT
   trades; off → 5 trades, 60 % win rate, +$95 net, profit factor 1.42. Tiny
   sample, but the only configuration showing positive expectancy.

Everything below is fixed on this branch (toggles preserve the documented
behavior where it was clearly intentional), and `run_backtest.py` reproduces
all numbers.

## Bug list

### A. Show-stoppers — why it "wasn't working"

| # | Where | Bug | Fix |
|---|-------|-----|-----|
| 1 | `strategy/fibonacci.py` | Leg "valid" only while price has NOT touched 0.5; entries require ≥ 0.5 retracement → **no ICT signal can ever exist** (also makes the documented 0.62/0.79 re-entries impossible) | `FIB_VALIDITY_MODE=structural` (default): leg valid until its origin swing breaks. `legacy` kept for comparison |
| 2 | `data/feed.py` | Bybit's newest row is the in-progress candle; RB confirmation, VWAP band-reclaim close, bias close and ATR switching all read it as CLOSED | Feed drops the forming candle by default (`drop_forming=True`) |
| 3 | `main.py` (`_update_nwog`) | NWOG needs Friday-close + Sunday-open 1m candles; the code fetched 200 minutes of history, so NWOG was never found unless the bot booted Sunday evening | Targeted weekend-anchor fetch (`get_weekend_candles_1m`) |
| 4 | `main.py` + `execution/risk.py` | `can_re_enter()` *incremented* the re-entry counter and was called every tick while stopped out → the 2-re-entry budget burned within ~2 minutes, before any trade. Setup identity was keyed by RB timestamp, so a genuine re-entry looked like a new setup and reset the counter anyway | Split into pure check + `record_re_entry()` consumed on execution; setup identity = the fib leg (`TradeSignal.setup_id`) |
| 5 | `strategy/signals.py` | Judas swing direction was detected, stored… and never read. Dead filter | Wired as a directional gate (active when `require_10am_filter` is on) |
| 6 | `main.py` | `logs/` is gitignored but logging opened `logs/bot.log` at import → fresh clone crashes on boot | `os.makedirs("logs", exist_ok=True)` |
| 7 | `strategy/levels.py` + `main.py` | Midnight/10AM opens were searched in a 200-minute 1m window — by the NY AM session, midnight had scrolled out, so both DOL levels silently vanished for most of the day | 1m fetch depth 1000 + vectorized lookup |

### B. Direction / quality bugs — why results skewed negative

| # | Where | Bug | Fix |
|---|-------|-----|-----|
| 8 | `strategy/bias.py` + `signals.py` | NWOG override forced BEARISH under ANY unfilled gap below price — including up-gap bullish weeks (shorting into strength). Worse: the level was never cleared after the gap filled, so the override stuck for the process lifetime | Stale level cleared on fill; override now opt-in (`NWOG_BIAS_OVERRIDE`, default off — CE stays a DOL target) |
| 9 | `main.py` (`_tick_vwap`) | Breakeven moved the stop to `current_price` (the ±1σ band — where price oscillates on its way to VWAP) instead of entry, wicking winners into scratches. In paper mode the CSV stop was never updated at all | Stop moves to entry; paper CSV updated |
| 10 | `execution/orders.py` | Only the LAST CSV row was monitored → any earlier open trade was orphaned as "PAPER" forever (stats never counted it) | All open rows tracked and resolved |
| 11 | `strategy/vwap.py` / `vwap_signals.py` | No session warm-up: minutes after the midnight VWAP reset, ±2σ bands are computed from 2–3 candles and hug price → noise entries in the deadest hours | `VWAP_MIN_SESSION_CANDLES` (default 12) |
| 12 | `strategy/regime.py` | "Current ATR" was a single candle's true range vs the 20-mean — one wide candle flipped the regime to TRENDING/NEWS, randomly blocking valid entries | 3-candle mean |
| 13 | `strategy/signals.py` | Stop buffers hard-coded at 2.0 *points* (~0.003 % of BTC) → stops sat on entries and died to spread noise | `STOP_BUFFER_PCT` (default 0.1 % of price) |

### C. Economics — why even winners lost money

| # | Where | Bug | Fix |
|---|-------|-----|-----|
| 14 | `execution/risk.py` | `qty = risk / stop_dist` with no notional cap: a 0.1 %-stop trade on 1 % risk wants ~10× account notional (Bybit would reject or margin-call it); paper mode pretended it filled | `MAX_LEVERAGE` cap (default 10×) |
| 15 | everywhere | **No fees or slippage anywhere** — paper PnL was logged in points, without qty. Bybit taker round-trip is 0.11 % of notional; with 0.1–0.2 % stops that is 0.6–1.0 R per trade, invisible in the CSV | Fee/slippage config; backtester charges them; report shows gross vs net |
| 16 | `strategy/signals.py` | Tier floors (1:5 premium / 1:3 confirmation) stacked on `MIN_RR` and the 5m-mode [3,6] band, with TP at the *nearest* DOL — near-total signal starvation | Kept (documented design) but toggleable: `ENFORCE_TIER_RR` |

### D. Deferred (documented, not fixed)

* `_live_trade` places GTC limit orders with no expiry or invalidation-cancel —
  stale fills hours later. (Backtester expires unfilled orders after 60 min;
  live order lifecycle management still TODO.)
* Live signal loop would stack multiple GTC orders if signals repeat before a
  fill; the backtester replaces the pending order instead.
* `ATRModeSwitcher` can never recommend "hybrid" — once it switches out, hybrid
  is unreachable.
* ICT breakeven (`calculate_breakeven_level`) exists but was never wired into
  `main.py`; the backtester doesn't simulate it either.
* VWAP has no session filter — it trades 3 AM liquidity the same as NY AM.

## Backtest

`python run_backtest.py --days 60 --variant all`

* Data: real BTC/USD 1m candles (Bitstamp spot; committed to
  `backtest/data_cache/`, 180 days). On the VPS, `--refresh-data 180` re-pulls
  Bybit BTCUSDT perp klines instead (public endpoint — this sandbox couldn't
  reach it).
* The engine reuses the **actual strategy stack** (bias → fibs → RB → levels →
  signals, VWAP → regime → signals, RiskManager sizing/limits) with an injected
  clock, windowed frames identical to the live fetch limits, and closed candles
  only. Fills: ICT = resting limit orders that must be touched (maker,
  60-minute TTL); VWAP = market at next 1m open (taker + 0.01 % slippage).
  SL/TP resolve on the 1m stream; stop wins any candle containing both;
  same-candle TP on the fill candle is not granted. Fees: 0.055 % taker /
  0.02 % maker. Sizing: 1 % risk, 10× notional cap, $10k start.
* `TESTING_MODE` params (the mode the bot actually runs in): NY AM + London
  sessions, max 5 trades/day.

### Results — 60 days (2026-05-21 → 2026-07-20, $10k start)

| Variant | ICT trades | ICT net | VWAP trades | VWAP net (fees) | Total return | Max DD |
|---|---|---|---|---|---|---|
| `legacy` (your original code) | **0** — cannot fire | — | 73 (24.7% win, PF 0.12) | **−$4,514** ($3,564 fees) | **−45.1 %** | 45.6 % |
| `fixed` (all bug fixes) | 0 — tier floors reject all | — | 76 (19.7% win, PF 0.30) | −$4,261 ($3,611 fees) | −42.6 % | 43.5 % |
| `fixed_notier` (tier floors off) | **5 (60 % win, PF 1.42)** | **+$95** | 76 | −$4,307 | −42.1 % | 43.0 % |
| `fixed_nwog` (NWOG override on) | 5 — identical | +$95 | 76 | −$4,307 | −42.1 % | — |

Order lifecycle (`fixed_notier`): ICT placed 7 limit orders → 5 filled, 1
expired, 1 replaced. VWAP placed 81 → 76 filled, 5 expired.

### Reading the results

1. **The original code loses the most while trading the least.** Its ICT side
   is structurally incapable of producing a signal (0 trades in 60 days — the
   fib validity contradiction), and its VWAP side has the worst per-trade
   economics (PF 0.12; breakeven stops parked at the ±1σ band turned winners
   into losers — only 3 of 73 trades reached TP vs 14 of 76 after the fix).
2. **VWAP is the account killer, and the killer is fees, not signals.** Median
   entry-to-exit move: 0.083 % of price. Round-trip cost: ~0.075 % (maker in,
   taker stop out) on ~10× notional. Result: gross −$650 (≈ noise) but
   **$3,611 in fees** → −$4,261 net. Both band-2 and band-3 setups lose. No
   entry filter can fix this — the trade's expected move is the same size as
   its cost. The VWAP rulebook's own warning ("taker orders at this account
   size will destroy profitability… ~$118 per round trip") underestimated the
   problem: even *maker* entries can't carry a 0.08 % target.
3. **ICT after the fixes is a small positive sample.** 5 filled trades, 60 %
   win rate, +$95 net after fees, avg +0.33 R, PF 1.42 — with stops that are
   honest (median move 0.197 %, fees ~15 % of risk instead of ~100 %). This is
   nowhere near the rulebook's 50-trade minimum sample, but it is the first
   evidence the ICT implementation can make money at all. With the tier floors
   ON, all of these trades are rejected and the strategy does nothing.
4. **The NWOG override changed nothing** in this window (identical trade list)
   — the weekly gap was either tapped early or outside the 5 % proximity band.
   Keeping it off by default costs nothing; the CE still serves as a target.

## What to change before expecting profitability

1. **Turn VWAP off until it's redesigned** (`VWAP_ENABLED=false`). Its target
   size (~0.08 % of price) is the same order as the round-trip cost — that is a
   fee-donation machine, not an edge. A viable redesign needs targets ≥ 4–5×
   the round-trip cost: wider bands on a higher timeframe (e.g. ±2σ on 15m/1h),
   post-only entries, TP beyond VWAP — then re-backtest.
2. **Run ICT with relaxed tier floors** (`ENFORCE_TIER_RR=false`, or lower the
   floors to ~1:2.5–1:3): floors ON produced literally zero trades in 60 days;
   OFF produced a 60 %-win, PF 1.42 sample. 5 trades is not proof — extend the
   window (`--days 180`), but it's the only configuration with a pulse.
3. **Keep NWOG as a target, not a bias override** (now the default; measured
   zero effect on this window).
4. **Grow the sample before touching live.** The rulebook demands 50 trades
   before live capital; at the observed ICT rate (~5 per 60 days) that means
   either a much longer backtest window, more symbols, or accepting more
   Tier-2 setups.
5. **Run `run_backtest.py` before every parameter change.** The points-only
   paper CSV was flying blind — it could never have shown any of the above.
