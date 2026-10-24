"""
Fetch Yahoo chart bars (1d unadjusted, 1h, 1m) for one symbol into backtest/data_cache/local/yahoo_intraday/
(v0.35-audit Addendum A: QQQ daily closes scale the NSXUSD proxy, hourly bars give early closes and a clock
check over the whole span, 1m bars cover the last 30 days directly).

Yahoo serves 1m bars for the last 30 days only (at most 8 days per request) and 1h bars for the last 730
days. Regular-session bars only (includePrePost=false). Bars are indexed by their START in New York time.
The 1d close is split-adjusted but not dividend-adjusted (QQQ has no split in the window).

  python3 backtest/fetch_yahoo_intraday.py --symbol QQQ --interval 1d --start 2024-11-01
  python3 backtest/fetch_yahoo_intraday.py --symbol QQQ --interval 1h
  python3 backtest/fetch_yahoo_intraday.py --symbol QQQ --interval 1m
"""

import argparse
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import pandas as pd
import requests

CACHE = "backtest/data_cache/local/yahoo_intraday"
URL = ("https://query1.finance.yahoo.com/v8/finance/chart/{s}?period1={p1}&period2={p2}"
       "&interval={iv}&includePrePost=false&events=splits")
UA = {"User-Agent": "Mozilla/5.0"}
NY = "America/New_York"


def path_for(sym: str, interval: str) -> str:
    return f"{CACHE}/{sym}_{interval}.csv.gz"


def fetch_chunk(session: requests.Session, sym: str, interval: str, p1: int, p2: int) -> Optional[pd.DataFrame]:
    url = URL.format(s=sym, p1=p1, p2=p2, iv=interval)
    for attempt in range(5):
        try:
            r = session.get(url, headers=UA, timeout=30)
        except requests.RequestException as e:
            print(f"  {type(e).__name__}; retrying", flush=True)
            time.sleep(2 ** (attempt + 1))
            continue
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2 ** (attempt + 1))
            continue
        if r.status_code != 200:
            print(f"  HTTP {r.status_code}: {r.text[:160]}", flush=True)
            return None
        res = (r.json().get("chart") or {}).get("result")
        if not res or not res[0].get("timestamp"):
            return pd.DataFrame()
        res = res[0]
        q = res["indicators"]["quote"][0]
        idx = pd.to_datetime(res["timestamp"], unit="s", utc=True).tz_convert(NY)
        df = pd.DataFrame({"o": q["open"], "h": q["high"], "l": q["low"], "c": q["close"], "v": q["volume"]},
                          index=idx)
        if (res.get("events") or {}).get("splits"):
            print("  WARNING: split events in the window; the 1d close is split-adjusted", flush=True)
        return df.dropna(subset=["o", "h", "l", "c"])
    return None


def fetch(sym: str, interval: str, start: Optional[str]) -> pd.DataFrame:
    now = datetime.now(timezone.utc)
    if interval == "1m":
        lo, step = now - timedelta(days=29, hours=12), timedelta(days=7)
    elif interval == "1h":
        lo, step = now - timedelta(days=725), timedelta(days=120)
    else:
        lo, step = datetime.fromisoformat(start or "2024-11-01").replace(tzinfo=timezone.utc), timedelta(days=4000)
    session = requests.Session()
    parts: List[pd.DataFrame] = []
    t = lo
    while t < now:
        t2 = min(t + step, now)
        df = fetch_chunk(session, sym, interval, int(t.timestamp()), int(t2.timestamp()))
        if df is None:
            raise SystemExit(f"fetch failed for {sym} {interval} {t:%Y-%m-%d}")
        parts.append(df)
        t = t2
        time.sleep(0.5)
    out = pd.concat(parts)
    out = out[~out.index.duplicated(keep="last")].sort_index()
    if interval == "1d":
        out.index = out.index.normalize()
    return out


def load(sym: str, interval: str) -> Optional[pd.DataFrame]:
    p = path_for(sym, interval)
    if not os.path.exists(p):
        return None
    df = pd.read_csv(p, index_col=0)
    df.index = pd.to_datetime(df.index, utc=True).tz_convert(NY)
    return df


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="QQQ")
    ap.add_argument("--interval", choices=["1d", "1h", "1m"], required=True)
    ap.add_argument("--start", default=None, help="1d only (YYYY-MM-DD)")
    a = ap.parse_args()
    os.makedirs(CACHE, exist_ok=True)
    df = fetch(a.symbol, a.interval, a.start)
    df.index.name = "start"
    df.to_csv(path_for(a.symbol, a.interval), compression="gzip", float_format="%.6f")
    back = load(a.symbol, a.interval)
    assert back is not None and len(back) == len(df) and back.index.is_monotonic_increasing, "did not re-load cleanly"
    assert (back["h"] >= back["l"]).all(), "high below low"
    print(f"{a.symbol} {a.interval}: {len(back)} bars, {back.index[0]} -> {back.index[-1]}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, ".")
    sys.exit(main())
