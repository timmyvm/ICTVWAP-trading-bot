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
