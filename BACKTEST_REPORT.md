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
3. **Fees eat the VWAP strategy alive.** Stops are 0.1–0.2 % of price; taker
   fees are 0.11 % of notional round-trip. Fee/risk is independent of position
   size, so every VWAP trade pays ~0.6–1.0 R in fees no matter what. Even
   take-profit exits frequently lose money net. Paper trading never showed this
   because PnL was logged in points with no qty and no fees.
4. **Futures-scale constants on a BTC chart.** Stop buffers of "2.0 points"
   (~0.003 % of BTC) parked stops on top of entries — ICT trades died to noise
   within the entry minute. `LARGE_RB_THRESHOLD = 40` points classifies nearly
   every 5m BTC candle as "large". These numbers are NQ-scale, not BTC-scale.
5. **The tier R:R floors starve the strategy.** With TP = *nearest* liquidity
   level and honest stop distances, requiring 1:5 (Tier 1) / 1:3 (Tier 2)
   rejects essentially every setup. 60-day backtest: tier gates on → almost no
   ICT trades; off → a real sample of trades.

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

### Results — 60 days (RESULTS_PENDING: filled after run)

### Reading the results

RESULTS_DISCUSSION_PENDING

## What to change before expecting profitability

1. **Fees are the first-class enemy.** With 0.1–0.2 % stops on Bybit non-VIP
   taker fees, the VWAP strategy pays most of a full R in fees per trade —
   no signal quality survives that. Either enter with post-only limits and
   widen stops (fee/risk falls proportionally), or don't scalp 5m mean
   reversion on a taker-fee venue.
2. **Re-tune the tier floors to BTC scale.** 1:5 on Tier 1 with nearest-DOL
   targets is a unicorn filter; the backtest shows what relaxing it does.
3. **Treat NWOG as a target, not a bias override** (now the default).
4. **Run the backtest before every parameter change** — that's what
   `run_backtest.py` is for. Paper CSV in points was flying blind.
