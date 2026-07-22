"""
Configuration for the Powell Trades ICT Bot.

All toggles and parameters are loaded from environment variables with sensible defaults.
The strategy is built around ICT concepts: bias, Fibonacci OTE entries, rejection blocks,
and strict risk management.

Two operational modes:
  TESTING_MODE=True  -> relaxed params for backtesting / paper trade validation
  TESTING_MODE=False -> strict params for live trading
"""

import os
from dotenv import load_dotenv

load_dotenv()

# --- Exchange ---
BYBIT_API_KEY = os.getenv("BYBIT_API_KEY", "")
BYBIT_API_SECRET = os.getenv("BYBIT_API_SECRET", "")
BYBIT_TESTNET = True  # Always testnet for safety

# --- Symbol ---
SYMBOL = os.getenv("SYMBOL", "BTCUSDT")
CATEGORY = "linear"  # Linear perpetual

# --- Timeframes ---
TIMEFRAMES = ["1", "5", "15", "60", "240"]  # Bybit interval codes for 1m, 5m, 15m, 1h, 4h
TIMEFRAME_MAP = {
    "1m": "1",
    "5m": "5",
    "15m": "15",
    "1h": "60",
    "4h": "240",
}

# --- Entry Mode ---
# "1m"  = use 1-minute candles for rejection block detection
# "5m"  = use 5-minute candles (wider stops, typically 1:3–1:6 R:R)
# "hybrid" = confirm on 5m, then refine entry on 1m for tighter stop
ENTRY_MODE = os.getenv("ENTRY_MODE", "5m")

# --- Paper Trading ---
# When True, no real orders are placed — trades are logged to CSV instead
PAPER_TRADE = os.getenv("PAPER_TRADE", "true").lower() == "true"

# ═══════════════════════════════════════════════════════════════════════════════
# TESTING vs LIVE MODE
# ═══════════════════════════════════════════════════════════════════════════════
# Set to False when going live. All strategy logic reads from active_params().
TESTING_MODE = os.getenv("TESTING_MODE", "true").lower() == "true"

TESTING_PARAMS = {
    "min_rr": 1.3,
    "sessions": ["ny_am", "london"],
    "symbols": ["BTCUSDT", "ETHUSDT"],
    "max_daily_trades": 5,
    "max_weekly_trades": 999,
    "require_10am_filter": False,
    "htf_bias_strict": False,
}

LIVE_PARAMS = {
    "min_rr": 1.4,
    "sessions": ["ny_am"],
    "symbols": ["BTCUSDT"],
    "max_daily_trades": 3,
    "max_weekly_trades": 3,
    "require_10am_filter": True,
    "htf_bias_strict": True,
}


def active_params() -> dict:
    """Return the active parameter set based on TESTING_MODE."""
    return TESTING_PARAMS if TESTING_MODE else LIVE_PARAMS


# --- Derived from active mode (convenience accessors) ---
# These are the "old" top-level vars, now reading from the active mode.
MAX_DAILY_TRADES = int(os.getenv("MAX_DAILY_TRADES", str(active_params()["max_daily_trades"])))
MAX_WEEKLY_TRADES = int(os.getenv("MAX_WEEKLY_TRADES", str(active_params()["max_weekly_trades"])))
MIN_RR = float(os.getenv("MIN_RR", str(active_params()["min_rr"])))

# --- Risk ---
RISK_PER_TRADE_PCT = float(os.getenv("RISK_PER_TRADE_PCT", "1.0"))  # % of account per trade

# Cap position notional at account_balance * MAX_LEVERAGE. Without this, a tight
# stop (risk_amt / tiny_stop_dist) produces absurd notional sizes that Bybit would
# reject and whose fees alone exceed the intended risk.
MAX_LEVERAGE = float(os.getenv("MAX_LEVERAGE", "10.0"))

# --- Execution Economics ---
# Bybit linear perp fees as % of notional per fill. Paper trading and backtests
# must charge these — with tight stops the round-trip fee can exceed the risk.
TAKER_FEE_PCT = float(os.getenv("TAKER_FEE_PCT", "0.055"))
MAKER_FEE_PCT = float(os.getenv("MAKER_FEE_PCT", "0.02"))
SLIPPAGE_PCT = float(os.getenv("SLIPPAGE_PCT", "0.01"))  # % applied to market fills

# --- Fibonacci Leg Validity ---
# "structural" (default): a fib leg stays tradeable until its origin swing is
#   violated (recent low breaks the swing low for longs). This is what allows
#   entries in the 0.5-0.79 discount zone at all.
# "legacy": the original rule — leg is valid only while price has NOT retraced
#   to 0.5. Kept for comparison; it contradicts the RB requirement that entries
#   form AT >= 0.5 retracement, so no ICT signal can ever fire under it.
FIB_VALIDITY_MODE = os.getenv("FIB_VALIDITY_MODE", "structural")

# --- Tier R:R Enforcement ---
# Tier floors (T1 >= 5.0 in OTE/DD, T2 >= 3.0 elsewhere) per the README.
# Toggleable so backtests can quantify how much signal starvation they cause.
ENFORCE_TIER_RR = os.getenv("ENFORCE_TIER_RR", "true").lower() == "true"

# --- HTF Trend Alignment Gate (RESEARCH.md action #1) ---
# Blocks entries whose bias fights the broader 4H trend. Osler's cascade
# asymmetry (continuation beats reversal at swept levels) + our backtest
# (all 6 counter-trend longs in the March crash lost; shorts were net
# positive) both point the same way. Trend = 4H close vs SMA of the last
# TREND_SMA_PERIOD 4H closes, with a neutral band where the gate stays out.
# DEFAULT OFF after v0.4.1 validation: with both gates on, win rate fell
# 45.5% -> 28.6% and the gross edge went negative (+$378 -> -$76) — the gates
# removed February's small-target winners while two March longs still slipped
# through the neutral band. Untested in isolation; see DEVLOG backlog.
TREND_ALIGNMENT_FILTER = os.getenv("TREND_ALIGNMENT_FILTER", "false").lower() == "true"
TREND_SMA_PERIOD = int(os.getenv("TREND_SMA_PERIOD", "50"))          # ~8.3 days of 4H
TREND_NEUTRAL_BAND_PCT = float(os.getenv("TREND_NEUTRAL_BAND_PCT", "0.5"))

# --- Minimum Take-Profit Distance (RESEARCH.md action #2) ---
# Reject signals whose nearest-DOL target is closer than this % of price.
# DEFAULT OFF (0.0) after v0.4.1: the nearest-pool small targets ARE the win
# rate — skipping them destroyed the gross edge. The fee problem is real but
# has to be solved on the cost side (fee tiers/venue), not by discarding the
# strategy's best trades.
MIN_TP_DISTANCE_PCT = float(os.getenv("MIN_TP_DISTANCE_PCT", "0.0"))

# --- Rejection Block Filters ---
# "No-wick" threshold: if wick is less than this fraction of total range,
# the candle is considered a "sus candle" (suspicious = strong directional intent).
# These levels become draw-on-liquidity (DOL) targets.
NO_WICK_THRESHOLD = float(os.getenv("NO_WICK_THRESHOLD", "0.05"))

# Large rejection block threshold (points). Blocks bigger than this
# use CE (50%) or 25% level for entry instead of the open.
LARGE_RB_THRESHOLD = float(os.getenv("LARGE_RB_THRESHOLD", "40.0"))

# Stop-loss buffer beyond the swept level, as % of price. The old constant was
# 2.0 POINTS — a futures-scale number that is ~0.003% on BTC, so stops sat on
# top of entries and died to spread noise within the first minute.
# 0.1% of a 65k BTC ≈ 65 points. A 2-point floor is kept for tiny-priced symbols.
STOP_BUFFER_PCT = float(os.getenv("STOP_BUFFER_PCT", "0.1"))

# --- News Filter ---
# Skip trading during high-impact news windows.
NEWS_BLACKOUT_EVENTS = [
    # Example: ("NFP", "first_friday"),
    # Example: ("CPI", [(3, 12), (4, 10)]),
]
NEWS_BLACKOUT_WINDOW_MINUTES = 30

# --- News Levels (DOL targets from news events) ---
# Manually populated. Each entry: {"level": price, "type": "nfp_low"|"cpi_high", "date": "YYYY-MM-DD"}
# Per Powell V4: "News highs/lows (e.g. NFP low) are almost as powerful as equal highs/lows"
NEWS_LEVELS: list[dict] = [
    # Example: {"level": 70500, "type": "nfp_low", "date": "2026-03-08"},
]

# --- Session Filter ---
# Powell V3: "Preferred session: New York AM. Also valid: London Session,
# provided HTF bias is strong."
# Times are in NY Time (ET).
NY_AM_SESSION = (9, 30, 12, 0)   # 09:30 - 12:00 NY (preferred)
LONDON_SESSION = (3, 0, 6, 0)    # 03:00 - 06:00 NY (valid if bias is clear)

# --- NWOG Proximity ---
# NWOG override only applies if the gap is within this % of current price.
# If NWOG is further than 5% away, it's too distant to force bias override.
NWOG_OVERRIDE_MAX_PCT = float(os.getenv("NWOG_OVERRIDE_MAX_PCT", "5.0"))

# Master toggle for the NWOG bias override. When True, an unfilled NWOG below
# price (within NWOG_OVERRIDE_MAX_PCT) forces BEARISH bias until tapped —
# including during bullish up-gap weeks, which shorts into strength. Off by
# default: the NWOG CE still participates as a DOL target either way.
NWOG_BIAS_OVERRIDE = os.getenv("NWOG_BIAS_OVERRIDE", "false").lower() == "true"

# --- ATR Auto Mode Switching ---
# If 5m ATR exceeds this multiplier of 20-period avg, auto switch to 5m mode.
ATR_HIGH_THRESHOLD = float(os.getenv("ATR_HIGH_THRESHOLD", "1.5"))
# If ATR falls below this for 3+ candles, switch back to 1m.
# NOTE: 1.2 came from the VWAP rulebook's *strategy selection* rule ("VWAP mode
# when ATR ratio < 1.2"), not from an entry-timeframe rule. The ATR ratio
# baseline hovers ~1.0, so a 1.2 threshold kept the bot in 1m mode virtually
# always — against the ICT rulebook's "5m is the recommended default for
# crypto" (1m = liquidation-cascade noise). 0.8 = genuinely quiet tape only.
ATR_LOW_THRESHOLD = float(os.getenv("ATR_LOW_THRESHOLD", "0.8"))
ATR_PERIOD = 20
ATR_COOLDOWN_CANDLES = 3  # Candles below threshold before switching back

# --- Re-entry ---
MAX_RE_ENTRIES = 2  # Max re-entries after a stop-out on the same setup

# --- Logging ---
TRADE_LOG_PATH = "logs/trades.csv"

# ═══════════════════════════════════════════════════════════════════════════════
# VWAP MEAN REVERSION STRATEGY
# ═══════════════════════════════════════════════════════════════════════════════
# Runs independently alongside the ICT strategy. Shares the same daily trade
# limits and CSV log. Only activates in RANGING regime.

# Master switch. The 60-day backtest (see BACKTEST_REPORT.md) shows the current
# parameterization is structurally unprofitable on Bybit fees: median move per
# trade 0.083% of price vs ~0.075-0.11% round-trip cost -> fees were $3,611 of
# a $4,260 loss. Left ON to preserve existing behavior; flip to false until the
# setup is re-parameterized for wider targets.
VWAP_ENABLED = os.getenv("VWAP_ENABLED", "true").lower() == "true"

# Standard deviation band settings
VWAP_STD_MULTIPLIER = 2.0       # Primary band multiplier (±2 SD is the main setup)
VWAP_STD_LENGTH = 20             # Rolling window for std deviation calculation

# Regime thresholds
VWAP_SLOPE_THRESHOLD = 0.01     # Normalised slope above this = TRENDING (not RANGING)
                                  # (slope is in ATR-units per candle)

# Entry filters
VWAP_VOLUME_THRESHOLD = 1.5     # Extension candle volume must be < this x vol_avg
                                  # High volume extension = real breakout, not noise
VWAP_MAX_STOP_ATR = 1.0         # Stop distance (entry to SL) must be ≤ 1x ATR
                                  # Wider stops = trade is too stretched to be mean reversion

# Session reset
VWAP_SESSION_RESET_HOUR = 0     # VWAP resets at this NY hour each day (midnight)
MAX_VWAP_TRADES_PER_SESSION = 2  # Max VWAP entries per session window

# Warm-up: minimum candles in the session before VWAP signals may fire.
# Right after the midnight reset the std bands are computed from 2-3 candles and
# hug price, so every wiggle "touches ±2σ" — those are noise trades.
VWAP_MIN_SESSION_CANDLES = int(os.getenv("VWAP_MIN_SESSION_CANDLES", "12"))
