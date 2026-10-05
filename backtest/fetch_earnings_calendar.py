"""
Fetch the Nasdaq earnings calendar day by day (v0.28-exp, DEVLOG v0.28-exp).

https://api.nasdaq.com/api/calendar/earnings?date=YYYY-MM-DD returns, for past dates, every company
that reported that day with actual EPS, consensus forecast, number of estimates and % surprise.
Caveats found when probing (2026-10-05): no release time for past dates ("time-not-supplied"); the
market cap is TODAY's value, so it must never be used as a historical filter; companies delisted
since are absent, so the event set is a survivor universe.

Resumable: one raw JSON per weekday in backtest/data_cache/local/earnings_calendar/; cached days are
skipped. --consolidate writes backtest/data_cache/local/earnings_events.csv.gz and validates the SAVED
file by re-loading it through load_events().

Usage:
  python backtest/fetch_earnings_calendar.py --start 2014-07-01 --end 2026-10-02
  python backtest/fetch_earnings_calendar.py --consolidate
"""

import argparse
import glob
import json
import math
import os
import time
from datetime import date, timedelta

import pandas as pd
import requests

CACHE = "backtest/data_cache/local/earnings_calendar"
OUT = "backtest/data_cache/local/earnings_events.csv.gz"
URL = "https://api.nasdaq.com/api/calendar/earnings?date={d}"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
           "Accept": "application/json, text/plain, */*"}
COLUMNS = ["date", "symbol", "name", "eps", "eps_forecast", "n_ests", "surprise_pct", "fiscal_quarter"]


def money(s) -> float:
    """'$1.23' -> 1.23, '($0.15)' -> -0.15, '' / 'N/A' -> nan."""
    if s is None:
        return math.nan
    s = str(s).strip()
    if s in ("", "N/A", "--", "n/a"):
        return math.nan
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()").replace("$", "").replace(",", "")
    try:
        v = float(s)
    except ValueError:
        return math.nan
    return -v if neg else v


def fetch_day(d: date, session: requests.Session) -> bool:
    path = f"{CACHE}/{d}.json"
    if os.path.exists(path):
        return True
    for attempt in range(6):
        try:
            r = session.get(URL.format(d=d), headers=HEADERS, timeout=30)
            if r.status_code == 200:
                json.loads(r.text)                     # must parse before it is cached
                with open(path, "w") as f:
                    f.write(r.text)
                return True
            wait = 2 ** (attempt + 1)
            print(f"  {d}: HTTP {r.status_code}, retry in {wait}s", flush=True)
        except (requests.RequestException, ValueError) as e:
            wait = 2 ** (attempt + 1)
            print(f"  {d}: {type(e).__name__}, retry in {wait}s", flush=True)
        time.sleep(wait)
    return False


def run(start: date, end: date, pause: float) -> None:
    os.makedirs(CACHE, exist_ok=True)
    session = requests.Session()
    days = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    days = [d for d in days if d.weekday() < 5]
    todo = [d for d in days if not os.path.exists(f"{CACHE}/{d}.json")]
    print(f"{len(days)} weekdays, {len(days) - len(todo)} cached, {len(todo)} to fetch", flush=True)
    failed = []
    for i, d in enumerate(todo, 1):
        if not fetch_day(d, session):
            failed.append(d)
        if i % 100 == 0:
            print(f"  {i}/{len(todo)} done (last {d}); failures so far {len(failed)}", flush=True)
        time.sleep(pause)
    print(f"finished; {len(failed)} days failed" + (f": {[str(d) for d in failed[:20]]}" if failed else ""),
          flush=True)


def consolidate() -> pd.DataFrame:
    rows = []
    for path in sorted(glob.glob(f"{CACHE}/*.json")):
        d = os.path.basename(path)[:-5]
        try:
            data = (json.load(open(path)) or {}).get("data") or {}
        except ValueError:
            print(f"  skipping unreadable {path} (being written?)")
            continue
        for r in data.get("rows") or []:
            rows.append({
                "date": d, "symbol": str(r.get("symbol", "")).strip().upper(), "name": r.get("name", ""),
                "eps": money(r.get("eps")), "eps_forecast": money(r.get("epsForecast")),
                "n_ests": money(r.get("noOfEsts")), "surprise_pct": money(r.get("surprise")),
                "fiscal_quarter": r.get("fiscalQuarterEnding", ""),
            })
    df = pd.DataFrame(rows, columns=COLUMNS)
    df.to_csv(OUT, index=False, compression="gzip")
    back = load_events()
    assert len(back) == len(df), "saved event file does not re-load to the same row count"
    assert back["date"].notna().all() and back["symbol"].notna().all(), "saved file lost dates or symbols"
    assert abs(back["eps"].sum() - df["eps"].sum()) < 1e-6 * max(1.0, abs(df["eps"].sum())), "EPS changed on reload"
    q = back.groupby(back["date"].dt.to_period("Q")).size()
    print(f"{len(back)} rows, {back['symbol'].nunique()} symbols, {back['date'].min().date()} -> "
          f"{back['date'].max().date()}; with EPS and forecast: "
          f"{int((back.eps.notna() & back.eps_forecast.notna()).sum())}")
    print("rows per quarter:", ", ".join(f"{p}:{n}" for p, n in q.items()))
    return back


def load_events(path: str = OUT) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"symbol": str, "name": str, "fiscal_quarter": str},
                     keep_default_na=False, na_values=[""])
    df["date"] = pd.to_datetime(df["date"])
    for c in ("eps", "eps_forecast", "n_ests", "surprise_pct"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2014-07-01")
    ap.add_argument("--end", default="2026-10-02")
    ap.add_argument("--pause", type=float, default=0.5)
    ap.add_argument("--consolidate", action="store_true")
    a = ap.parse_args()
    if a.consolidate:
        consolidate()
    else:
        run(date.fromisoformat(a.start), date.fromisoformat(a.end), a.pause)


if __name__ == "__main__":
    main()
