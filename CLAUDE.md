# Powell Trades Bot — CLAUDE.md

## Stack
- Python (no TypeScript, no React, no frontend)
- Bybit API (via `pybit`) for market data and order execution
- Deployed on Vultr VPS
- Paper trading mode toggled via `config.TESTING_MODE`

## Project Layout
```
strategy/
  bias.py        — HTF bias (4H > 1H priority, FVG confluence)
  signals.py     — Signal engine: RB detection, fib alignment, Judas swing
  fibonacci.py   — OTE/discount/premium fib zone calculation
  levels.py      — Key levels: NWOG, DOL, sus candles
  rejection_block.py — RB detection and classification
execution/
  orders.py      — Order placement + paper trade simulation
  risk.py        — Daily/weekly trade limits, re-entry logic, news blackouts
main.py          — Main loop, ATR mode switching, position monitoring
config.py        — All tuneable parameters (TESTING_MODE, ENTRY_MODE, etc.)
```

## Core Rules
- After every correction or mistake, update this file with a rule to prevent repeating it.
  End corrections with: "Now update CLAUDE.md so you don't make that mistake again."
- Update DEVLOG.md with EVERY code/config change: version entry (or patch note), what changed,
  which bug/evidence motivated it, commit hash, and backtest result once available. Newest first.
  A change without a DEVLOG entry is not done.
- Start every complex task in plan mode. Pour energy into the plan, then 1-shot the implementation.
- When something goes sideways, switch back to plan mode. Don't keep pushing.
- Use subagents for parallel workstreams. Only one agent edits a given file at a time.
- Keep the main context window clean — offload isolated tasks to subagents.

## Bias System
- `HTFBias.evaluate()` returns `"BULLISH"`, `"BEARISH"`, or `"NEUTRAL"` — never `"LONG"` or `"SHORT"`.
- 4H structure always takes priority. 1H is confluence only when 4H is neutral.
- FVG checks use only the last 20 1H candles — never the full DataFrame history.

## Code Style
- Pure Python — no type: ignore shortcuts, use Optional[] and proper types
- Keep strategy logic in `strategy/`, execution logic in `execution/`
- Log every significant state change with `logger.info()`
- No bare `except:` — always catch specific exceptions

## Lessons Learned
- `HTFBias.evaluate()` returns "BULLISH"/"BEARISH"/"NEUTRAL" — never compare against "LONG"/"SHORT".
  Hybrid zone invalidation (signals.py) was silently broken because of this mismatch.

- Weekly trade counters must use `(year, week)` tuples as keys, not bare ISO week integers.
  ISO week 1 of 2025 and ISO week 1 of 2026 are different weeks — a plain int key collides across year boundaries.

- Judas swing window is 9:30 <= t < 10:00 (exclusive upper bound).
  The 10:00 candle is the start of the post-manipulation period, not part of the detection window.

- ATR mode switcher must always run — never gate it on `ENTRY_MODE != "hybrid"`.
  Without this, once in hybrid mode the bot could never auto-switch out regardless of ATR conditions.

- FVG detection over full DataFrame history causes both bullish and bearish signals every candle in a wide range.
  Always slice to recent candles (e.g., `df.iloc[-20:]`) before calling `detect_fvg()`.

- `find_swing_highs` / `find_swing_lows` use `==` to max/min, which marks duplicate-valued candles as swings.
  Use `iloc[-1]` on the result to get the most recent swing — this naturally resolves duplicates.

- `find_swing_highs(df_4h)` with default `lookback=5` excludes the last 20 hours of 4H candles from being swing candidates.
  Always call it with `lookback=2` in bias.py so swings within the last 8 hours are still detectable.

- ATR mode switching must use symmetric hysteresis — both the 5m switch and the 1m switch need `ATR_COOLDOWN_CANDLES`
  consecutive candles before firing. A single-candle trigger on 5m causes thrashing when ATR momentarily spikes.

- Sus candle detection uses two separate `if` blocks (upper wick / lower wick). A marubozu candle fires both,
  logging the same price twice. Always add a body direction guard: `close >= open` for BULLISH, `close < open` for BEARISH.

- VWAP `session_df["vwap"]` can contain NaN rows (zero-volume candles produce NaN in cumulative VWAP).
  Always call `.dropna()` on the window before passing to `np.polyfit` — otherwise the fit silently fails and returns 0.0.

- ATR ratio guard in `ATRModeSwitcher` must check both `avg_atr == 0` AND `current_atr <= 0`. A zero-range
  bad tick produces `current_atr = 0.0`, making `ratio = 0.00`, which incorrectly triggers the low-ATR counter.

- Entry conditions and validity conditions must be satisfiable TOGETHER. The fib leg was "valid" only while
  price had NOT retraced to 0.5, but every RB entry requires price AT >= 0.5 retracement — mutually exclusive,
  so the ICT strategy could never fire. Validity now means "origin swing unbroken" (FIB_VALIDITY_MODE).

- Bybit's newest kline row is the still-forming candle. Never treat `iloc[-1]` as a closed confirmation
  candle — the feed drops the forming row (`drop_forming=True`) so all modules see closed candles only.

- Never hard-code price-scale constants. "2.0 points" of stop buffer is ~0.003% on BTC — stops sat on top of
  entries and died to noise. Use %-of-price (STOP_BUFFER_PCT) or ATR-relative distances.

- Budget-style checks must be split into a pure peek and an explicit consume. `can_re_enter()` incremented
  its counter on every call and the main loop called it every tick — the whole re-entry budget burned in
  ~2 minutes. Peek in the signal path; `record_re_entry()` only when a trade executes.

- Paper PnL must include qty, fees, and slippage. Points-only logging hid that taker fees on tight-stop
  trades cost 0.6-1.0 R per trade — trades that "won" in the CSV lost money net.

- One-shot state overrides need an explicit clear path. The NWOG bias override was set when unfilled but
  never cleared after the gap filled — bias stuck BEARISH for the process lifetime.

- Paper-position tracking must cover ALL open rows, not `iloc[-1]` — a second concurrent trade orphaned the
  first as "PAPER" forever and its outcome never counted in stats.

- Backtest any strategy change with `run_backtest.py` before deploying. The engine reuses the real strategy
  stack via injected `now` params — keep every new time-dependent code path injectable (`now: Optional[datetime]`).

- Before claiming a "single-variable" experiment, diff the FULL effective config against the baseline —
  flags are not the only config. The v0.7 run silently carried changed session-window CONSTANTS along with
  the intended trigger change. Make experiment-relevant constants env-controllable.

- The paper-trade CSV is read with `dtype=str` — write STRING values back (`str(round(pnl, 2))`), never
  floats. A float `.at` assignment raises `Invalid value for dtype 'str'` on pandas 2.x+ and aborts the
  entire position-resolution pass on every tick, so paper positions never close.

- A strategy validated in a scratchpad script is not validated until that script is COMMITTED. The v0.10c
  validation script was wiped by a container restart; its semantics had to be recovered from the session
  transcript because the DEVLOG prose under-specified three execution details (signal bar, exit ordering,
  fee legs). Reference implementations live in backtest/, never in /tmp.

- NEVER `.astype("int64")` a pandas datetime to get epoch values — pandas 2.x carries the source unit
  (ms/s), so `// 10**9` silently yields garbage. Always use the epoch-subtraction idiom
  (`(idx - pd.Timestamp(0, tz="UTC")) // pd.Timedelta(seconds=1)`, see save_cache_1m). And validate the
  SAVED artifact by re-loading it through the consumer's own loader — the v0.10e funding CSV passed every
  in-memory sanity check and was still corrupt on disk.

- NEVER fill a re-entry at a bar's OPEN after an exit that happened later inside the same bar — the open
  is a price the market has already left, and the exit event was not knowable at the open. The v0.10c
  reference engine (reproduced verbatim from the original validation script) did exactly this; after-win
  re-entries got a stale favorable price and after-loss re-entries a stale adverse one, and the ENTIRE
  validated edge (58% win, PF 1.18, "robust across six markets") collapsed to ~52% / PF ~1.0 under
  realistic re-entry (fill at the exit price, or wait for the next bar). Three rules follow:
  (1) exact reproduction of a reference is not validation — the reference's semantics must themselves be
  audited for lookahead (every fill priced at a time before the information that triggered it);
  (2) a result that is uniformly strong across unrelated markets with the same magnitude is a signature
  of an ENGINE mechanism, not an economic one — treat it as a trigger for an execution-semantics audit;
  (3) any filter that improves Sharpe several-fold from a one-line change is removing an artifact, not
  adding an edge — audit the engine before celebrating.

- NEVER trust a data vendor's stated timezone for session-based strategies — verify it with a per-month
  lag scan against a known-good source (shift the new series by ±60/±30/0 min, take the lag that minimizes
  the RMS close difference, month by month). HistData's "EST without DST" was in fact UTC−5/UTC−4
  switching on the EUROPEAN DST dates: a one-hour error in March and late October only, invisible in an
  annual check, fatal for an opening-range rule. `--tz-mode eu` in fetch_histdata.py; the scan is in the
  v0.16d DEVLOG entry.

- Before believing a tight-stop strategy's backtest, run it on TWO vendors' quotes of the same instrument
  over the same window (backtest/duka_overlap_check.py). If the trade list agrees but the net differs by
  more than the pass margin, the P&L belongs to the quote stream, not the market: no single-vendor
  backtest can validate it, and a live venue is a third quote stream. The v0.16b ORB ATR cell gave
  PF 1.42 on Oanda and PF 1.23 on Dukascopy for the same 320 trades.

- Test a candidate on the FRESHEST untouched era BEFORE spending trials on refinements. Both ORB
  refinements (v0.19 EMA trail, v0.16d wider stop) looked acceptable on the 2015-2020 cache and both
  fail on 2020-2026; the published cell itself is negative in five of six post-2020 years. Regime
  concentration in-sample ("2016 alone", "2019 alone") and a reel curve back-loaded to the last two
  years are the same warning: the era is the variable, not the geometry.

- A paper simulator must resolve brackets on the price PATH (1m high/low since the row opened), never on
  one mark sample per tick. A 60-second point check misses 6-10 % of stop touches — wicks that pierce and
  recover inside the minute — which silently lets paper positions survive stops a live account would
  take, flattering net by $486-$2,188 per $10k and understating maxDD by 4-8 points (v0.20-diag,
  backtest/exit_detector_audit.py; fixed in v0.21). Exclude bars older than the row's own entry, and
  check the stop BEFORE the target when a window touches both.

- Read the ORDER PATH before modelling fills. v0.20-diag prescribed filling stops at the polled price,
  which would have modelled a bot-managed stop; `_live_trade` actually sends stopLoss/takeProfit WITH the
  order, so the exchange holds the bracket, fills on any touch, and slippage is milliseconds not minutes.
  Whether your stop is exchange-side or bot-side changes which fill model is honest — check, don't assume.

- A TARGET below the cost floor kills a strategy exactly like a stop below it. Report the planned R:R
  distribution and the "unwinnable" share (planned R:R <= round-trip cost in R) as first-class outputs of
  any engine with a dynamic or level-based target. The v0.22 VWAP target had a median of 0.6 R against a
  structural stop, and 14-30 % of trades could not profit even when price reached the target exactly —
  which is why its 55-58 % target-hit rate produced a 34-50 % win rate.

- When a strategy with several stages fails, locate the fault with a ONE-VARIABLE diagnostic before
  touching anything else, and pre-state it before reading the results. v0.22's D1 kept the bias, zones,
  trigger, entry, stop and the skip rule identical and changed only the target to a fixed 2R: it still
  lost everywhere, which proved the entry carried no edge and that no target geometry could have rescued
  it. Keep the trade population identical between the cell and its diagnostic, or the comparison is
  confounded rather than informative.

- "The packaged strategy loses" is NOT "there is no signal". Before retiring a family, strip the
  packaging off and measure the entry's INFORMATION content directly: forward return in the signal's
  direction at several horizons, minus the drift-matched unconditional return, printed beside the
  round-trip cost as an excess/cost ratio (backtest/sd_signal_information.py). v0.22 looked dead at
  PF 0.31-0.62 and its entry turned out to be positive in 12 of 12 cells, worth 2.9x the fee on ETH at
  24 h. The edge was real and the stop/target/horizon were wrong. Run this BEFORE writing a family off.

- When a signal survives an information test, immediately ablate the stage the user believes in most,
  or you will invite the wrong update. v0.22's zone ablation showed the bare structure shift already
  carries about half the edge (so "supply and demand is everything" is false) while the zone still
  roughly doubles per-signal excess in 10 of 12 cells (so "zones are nonsense" is also false). Both
  halves matter; reporting only one is misleading.

- Every new backtest engine must assert bracket invariants at position creation:
  `dr * (entry - stop) > 0` and `dr * (target - entry) > 0`. The v0.16 engine shipped with
  `tgt = e - dr * RR * dist` (sign flipped), which fills every "TP" as a -3R loss and produces a
  plausible-looking -100% that could have passed as a strategy verdict. Read the first run's output for
  impossibilities (TP exits with 0% wins) before believing it — and read the sign of every
  `entry ± dr * …` line against the four engines that already have it right.
