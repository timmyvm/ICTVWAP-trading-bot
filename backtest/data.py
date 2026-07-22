"""
Historical data layer for backtesting.

Two sources, in order of preference:

1. Bybit v5 kline API (paginated) — real BTCUSDT linear-perp candles. This is
   what the live bot trades, so use it whenever the machine running the
   backtest can reach api.bybit.com (e.g. the Vultr VPS).

2. A committed 1m OHLCV cache (backtest/data_cache/btcusd_1m.csv.gz) sourced
   from Bitstamp spot BTC/USD. Spot vs perp differ by a few dollars of basis —
   irrelevant for strategy-level backtesting — and it makes the backtest
   reproducible on machines without exchange API access.

All higher timeframes (5m/15m/1h/4h) are resampled from 1m in UTC so candle
boundaries match Bybit's, then converted to NY time like data.feed.DataFeed.
"""

import gzip
import logging
import os
import time as _time
from typing import Optional

import pandas as pd
import pytz

logger = logging.getLogger(__name__)

NY_TZ = pytz.timezone("America/New_York")

CACHE_DIR = os.path.join(os.path.dirname(__file__), "data_cache")
CACHE_1M = os.path.join(CACHE_DIR, "btcusd_1m.csv.gz")

# Bybit interval code per resample rule
RESAMPLE_RULES = {
    "5m": "5min",
    "15m": "15min",
    "1h": "1h",
    "4h": "4h",
    "1d": "1D",  # UTC-anchored days, matching Bybit's daily candles
}


def load_cached_1m() -> pd.DataFrame:
    """Load the committed 1m cache into a NY-tz indexed OHLCV DataFrame."""
    if not os.path.exists(CACHE_1M):
        raise FileNotFoundError(
            f"No cached data at {CACHE_1M}. Run fetch_bybit_1m() on a machine "
            "with exchange API access, or restore the committed cache file."
        )
    df = pd.read_csv(CACHE_1M)
    return _normalize_1m(df)


def _normalize_1m(df: pd.DataFrame) -> pd.DataFrame:
    """timestamp(epoch s or ms),open,high,low,close,volume -> NY-tz indexed."""
    ts = df["timestamp"].astype(float)
    unit = "ms" if ts.iloc[0] > 1e12 else "s"
    # as_unit("ns") keeps the index at nanosecond resolution regardless of the
    # source unit — pandas 2.x otherwise carries datetime64[s] through and
    # unit-dependent integer views misbehave.
    idx = pd.to_datetime(ts, unit=unit, utc=True).dt.tz_convert(NY_TZ)
    idx = pd.DatetimeIndex(idx).as_unit("ns")
    out = df[["open", "high", "low", "close", "volume"]].astype(float)
    out.index = idx
    out.index.name = "timestamp"
    out = out[~out.index.duplicated(keep="last")].sort_index()
    return out


def save_cache_1m(df: pd.DataFrame):
    """Write a NY-tz indexed 1m frame back to the committed cache (epoch seconds)."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    dump = df.copy()
    epoch_s = (dump.index.tz_convert("UTC") - pd.Timestamp(0, tz="UTC")) // pd.Timedelta(seconds=1)
    dump.insert(0, "timestamp", epoch_s)
    with gzip.open(CACHE_1M, "wt", newline="") as f:
        dump.to_csv(f, index=False)
    logger.info("Saved %d 1m candles to %s", len(dump), CACHE_1M)


def fetch_bybit_1m(days: int, symbol: str = "BTCUSDT", testnet: bool = False) -> pd.DataFrame:
    """
    Paginated fetch of 1m klines from Bybit v5 (public endpoint, no API key).

    Use on a machine that can reach api.bybit.com. Returns NY-tz indexed OHLCV
    and refreshes the local cache.
    """
    from pybit.unified_trading import HTTP

    session = HTTP(testnet=testnet)
    end_ms = int(_time.time() * 1000)
    start_ms = end_ms - days * 86400 * 1000

    frames = []
    cursor_end = end_ms
    while cursor_end > start_ms:
        resp = session.get_kline(
            category="linear", symbol=symbol, interval="1",
            end=cursor_end, limit=1000,
        )
        rows = resp["result"]["list"]
        if not rows:
            break
        chunk = pd.DataFrame(
            reversed(rows),
            columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"],
        ).drop(columns=["turnover"])
        frames.append(chunk)
        oldest = int(float(rows[-1][0]))  # rows are newest-first
        if oldest >= cursor_end:
            break
        cursor_end = oldest - 1
        _time.sleep(0.05)  # stay friendly to rate limits

    if not frames:
        raise RuntimeError("Bybit returned no kline data")

    df = pd.concat(frames)
    df = _normalize_1m(df)
    df = df[df.index >= pd.Timestamp(start_ms, unit="ms", tz="UTC").tz_convert(NY_TZ)]
    save_cache_1m(df)
    return df


def resample_ohlcv(df_1m: pd.DataFrame, tf: str) -> pd.DataFrame:
    """
    Resample 1m OHLCV to a higher timeframe.

    Resampling happens in UTC so 4h candles align to 00/04/08... UTC exactly
    like Bybit's, then the index is converted back to NY time.
    """
    rule = RESAMPLE_RULES[tf]
    utc = df_1m.tz_convert("UTC")
    out = utc.resample(rule, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    out = out.dropna(subset=["open"])
    return out.tz_convert(NY_TZ)


def load_frames(days: Optional[int] = None) -> dict[str, pd.DataFrame]:
    """
    Load 1m data (cache) and build all strategy timeframes.

    Args:
        days: keep only the trailing N days (None = everything cached).

    Returns:
        {"1m": ..., "5m": ..., "15m": ..., "1h": ..., "4h": ...}
    """
    df_1m = load_cached_1m()
    if days is not None:
        cutoff = df_1m.index.max() - pd.Timedelta(days=days)
        df_1m = df_1m[df_1m.index >= cutoff]

    frames = {"1m": df_1m}
    for tf in RESAMPLE_RULES:
        frames[tf] = resample_ohlcv(df_1m, tf)

    logger.info(
        "Frames loaded: %s",
        {tf: len(f) for tf, f in frames.items()},
    )
    return frames
