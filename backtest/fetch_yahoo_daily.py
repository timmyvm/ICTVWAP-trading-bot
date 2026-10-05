"""
Fetch Yahoo daily bars for every symbol in the earnings event set, plus SPY (v0.28-exp).

One gz CSV per symbol in backtest/data_cache/local/yahoo_daily/ (date, open, close, adjclose,
volume, split_adj), indexed by New York session date. Yahoo's close is adjusted for ALL later splits;
split_adj is the product of the split ratios dated AFTER each session, so close * split_adj is the
price that actually traded that day (needed to scale as-reported EPS; volume * close is unaffected). Resumable: cached symbols and symbols already recorded in
missing.txt are skipped. Nasdaq symbols are mapped to Yahoo's format ('.' and '/' -> '-');
preferreds, warrants and units ('^', '~', '=', spaces) are skipped. Yahoo only serves symbols that
still trade, which is the same survivor universe as the Nasdaq calendar (DEVLOG v0.28-exp).

Usage:
  python backtest/fetch_yahoo_daily.py                    # every event symbol with EPS and a forecast
  python backtest/fetch_yahoo_daily.py --symbols SPY,AAPL
"""

import argparse
import os
import re
import sys
import time
from datetime import datetime, timezone
from typing import Optional

import pandas as pd
import requests

sys.path.insert(0, ".")
from backtest.fetch_earnings_calendar import load_events  # noqa: E402

CACHE = "backtest/data_cache/local/yahoo_daily"
MISSING = f"{CACHE}/missing.txt"
YF = "https://query1.finance.yahoo.com/v8/finance/chart/{t}?period1={p1}&period2={p2}&interval=1d&events=splits"
UA = {"User-Agent": "Mozilla/5.0"}
START = datetime(2014, 1, 1, tzinfo=timezone.utc)
END = datetime(2026, 10, 6, tzinfo=timezone.utc)
VALID = re.compile(r"^[A-Z][A-Z0-9./-]{0,9}$")


def yahoo_symbol(sym: str) -> str:
    return sym.replace(".", "-").replace("/", "-")


def path_for(sym: str) -> str:
    return f"{CACHE}/{yahoo_symbol(sym)}.csv.gz"


def fetch(sym: str, session: requests.Session) -> str:
    """Download one symbol. Returns 'ok', 'missing' (Yahoo has no data) or 'error' (retry later)."""
    url = YF.format(t=yahoo_symbol(sym), p1=int(START.timestamp()), p2=int(END.timestamp()))
    for attempt in range(6):
        try:
            r = session.get(url, headers=UA, timeout=30)
        except requests.RequestException as e:
            print(f"  {sym}: {type(e).__name__}", flush=True)
            time.sleep(2 ** (attempt + 1))
            continue
        if r.status_code == 404:
            return "missing"
        if r.status_code == 429 or r.status_code >= 500:
            time.sleep(2 ** (attempt + 1))
            continue
        if r.status_code != 200:
            return "missing"
        try:
            chart = r.json()["chart"]
        except (ValueError, KeyError):
            return "error"
        if chart.get("error") or not chart.get("result"):
            return "missing"
        res = chart["result"][0]
        ts = res.get("timestamp")
        if not ts:
            return "missing"
        q = res["indicators"]["quote"][0]
        adj = (res["indicators"].get("adjclose") or [{}])[0].get("adjclose") or q["close"]
        idx = pd.to_datetime(ts, unit="s", utc=True).tz_convert("America/New_York").normalize().tz_localize(None)
        df = pd.DataFrame({"open": q["open"], "close": q["close"], "adjclose": adj, "volume": q["volume"]},
                          index=idx)
        df = df[~df.index.duplicated(keep="last")].dropna(subset=["close", "adjclose"])
        df["split_adj"] = 1.0
        for sp in ((res.get("events") or {}).get("splits") or {}).values():
            when = pd.Timestamp(sp["date"], unit="s", tz="UTC").tz_convert("America/New_York").normalize().tz_localize(None)
            if sp.get("denominator"):
                df.loc[df.index < when, "split_adj"] *= sp["numerator"] / sp["denominator"]
        df.index.name = "date"
        df.to_csv(path_for(sym), compression="gzip", float_format="%.8g")
        return "ok"
    return "error"


def load_daily(sym: str) -> Optional[pd.DataFrame]:
    p = path_for(sym)
    if not os.path.exists(p):
        return None
    df = pd.read_csv(p, index_col="date", parse_dates=["date"])
    return df


def event_symbols() -> list:
    ev = load_events()
    ok = ev[ev.eps.notna() & ev.eps_forecast.notna() & (ev.n_ests >= 1)]
    syms = sorted({s for s in ok.symbol.dropna().unique() if VALID.match(s)})
    return ["SPY"] + [s for s in syms if s != "SPY"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", default=None, help="comma list; default = all event symbols")
    ap.add_argument("--pause", type=float, default=0.15)
    a = ap.parse_args()
    os.makedirs(CACHE, exist_ok=True)
    syms = a.symbols.split(",") if a.symbols else event_symbols()
    missing = set(open(MISSING).read().split()) if os.path.exists(MISSING) else set()
    todo = [s for s in syms if s not in missing and not os.path.exists(path_for(s))]
    print(f"{len(syms)} symbols, {len(syms) - len(todo)} cached or known-missing, {len(todo)} to fetch", flush=True)
    session = requests.Session()
    counts = {"ok": 0, "missing": 0, "error": 0}
    for i, s in enumerate(todo, 1):
        status = fetch(s, session)
        counts[status] += 1
        if status == "missing":
            with open(MISSING, "a") as f:
                f.write(s + "\n")
        if i % 250 == 0:
            print(f"  {i}/{len(todo)} {counts}", flush=True)
        time.sleep(a.pause)
    print(f"finished: {counts}", flush=True)
    spy = load_daily("SPY")
    assert spy is not None and len(spy) > 2500 and spy.index.is_monotonic_increasing, "SPY did not re-load cleanly"
    print(f"SPY re-loaded: {len(spy)} sessions {spy.index[0].date()} -> {spy.index[-1].date()}")


if __name__ == "__main__":
    main()
