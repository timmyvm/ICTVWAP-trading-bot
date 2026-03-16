# Powell Trades ICT Bot

Algorithmic trading bot implementing the Powell Trades ICT strategy on Bybit Testnet (BTCUSDT Linear Perpetual).

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Bybit Testnet API keys
```

## Configuration

Edit `.env` or `config.py`:

| Variable | Default | Description |
|---|---|---|
| `ENTRY_MODE` | `5m` | `1m`, `5m`, or `hybrid` |
| `PAPER_TRADE` | `true` | Skip order execution, log only |
| `MAX_DAILY_TRADES` | `3` | Max trades per day |
| `MIN_RR` | `1.3` / `1.4` | R:R pre-filter (testing / live) — see below |
| `RISK_PER_TRADE_PCT` | `1.0` | % of account risked per trade |

### R:R Enforcement (Tiered System)

R:R validation is two-stage. `MIN_RR` in config is a **pre-filter** that rejects obviously bad setups before the real check runs. It is not the actual trading minimum.

| Stage | Check | Threshold |
|---|---|---|
| 1. Pre-filter | `MIN_RR` from config | `1.3` (testing) / `1.4` (live) |
| 2. Tier check | Tier 1 — premium entry (OTE or Deep Discount fib zone) | **1:5 minimum** |
| 2. Tier check | Tier 2 — confirmation entry (Equilibrium or shallower) | **1:3 minimum** |

The pre-filter always passes before the tier check, so the **effective minimums are the tier values** (1:3 for Tier 2, 1:5 for Tier 1). A signal must clear both stages.

## Running

```bash
python main.py
```

## Strategy Overview

1. **HTF Bias** (1H/4H) — determine long or short direction
2. **Fibonacci** — identify discount zones on unbalanced legs
3. **Rejection Block** — detect entry triggers with liquidity sweeps
4. **Key Levels** — track NWOG, session opens, sus candles as targets
5. **Risk Management** — position sizing, trade limits, breakeven stops

## Project Structure

```
main.py            — Main loop
config.py          — All configuration toggles
strategy/
  bias.py          — HTF directional bias
  fibonacci.py     — Fib retracement levels
  rejection_block.py — RB entry detection
  levels.py        — Key ICT levels (NWOG, opens, sus candles)
  signals.py       — Signal engine orchestrator
execution/
  orders.py        — Order placement / paper logging
  risk.py          — Position sizing & trade limits
data/
  feed.py          — Bybit data fetching
logs/
  trades.csv       — Trade log
```
