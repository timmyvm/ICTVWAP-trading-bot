"""
Massive (formerly Polygon.io) minute bars -> local JSON cache (v0.35-audit).

Free "Options Basic" / "Stocks Basic": 5 calls per minute, 2 years of history, minute aggregates
(open, high, low, close, volume, volume-weighted price, trade count; bar start in UTC milliseconds).

Authentication: the key is NEVER passed on the command line, written to disk or put in a URL.
  - Preferred: a cloud-environment Network secret for api.massive.com (header Authorization,
    prefix Bearer); the proxy attaches it, so this script sends no key at all.
  - Fallback: environment variable MASSIVE_API_KEY, sent only as an Authorization header.

  python3 backtest/fetch_massive_options.py --check                       # one cheap call, prints HTTP status
  python3 backtest/fetch_massive_options.py --contracts <list.jsonl>      # lines {"contract": "O:QQQ...", "date": "YYYY-MM-DD"}
  python3 backtest/fetch_massive_options.py --stock QQQ --months 2024-12:2026-10
Calls are spaced 12.5 s (5/min), oldest first, resumable (cached responses are skipped). A response
with zero results is cached as such and counted apart from HTTP errors, which are retried and never
cached.
"""

import argparse
import json
import os
import sys
import time
from datetime import date, datetime, timezone
from typing import Dict, List, Optional, Tuple

import requests

BASE = "https://api.massive.com"
CACHE = "backtest/data_cache/local/massive"
SPACING = 12.5


def option_ticker(underlying: str, expiry: date, cp: str, strike: float) -> str:
    """OCC-style ticker: O:QQQ250916P00591000 (strike x 1000, 8 digits)."""
    assert cp in ("C", "P"), cp
    milli = int(round(strike * 1000))
    assert 0 < milli < 10 ** 8, strike
    return f"O:{underlying}{expiry:%y%m%d}{cp}{milli:08d}"


def aggs_url(ticker: str, start: str, end: str) -> str:
    return f"{BASE}/v2/aggs/ticker/{ticker}/range/1/minute/{start}/{end}?adjusted=true&sort=asc&limit=50000"


def headers() -> Dict[str, str]:
    key = os.environ.get("MASSIVE_API_KEY", "").strip()
    return {"Authorization": f"Bearer {key}"} if key else {}


def get(session: requests.Session, url: str, tries: int = 5) -> Tuple[Optional[dict], str]:
    """(json, status) where status is 'ok', 'zero', or an error label. Never logs the headers."""
    for k in range(tries):
        try:
            r = session.get(url, headers=headers(), timeout=60)
        except requests.RequestException as e:
            status = f"neterr:{type(e).__name__}"
            time.sleep(SPACING * (k + 1))
            continue
        if r.status_code == 429:
            status = "http429"
            time.sleep(60)
            continue
        if r.status_code in (401, 403):
            return None, f"http{r.status_code}"
        if r.status_code >= 500:
            status = f"http{r.status_code}"
            time.sleep(SPACING * (k + 1))
            continue
        if r.status_code != 200:
            return None, f"http{r.status_code}"
        j = r.json()
        if j.get("status") not in ("OK", "DELAYED"):
            return None, f"api:{j.get('status')}"
        if j.get("next_url"):
            return None, "paginated"           # one contract-day never needs a second page; refuse silently-partial data
        return j, ("ok" if j.get("resultsCount", len(j.get("results") or [])) else "zero")
    return None, status


def cache_path(kind: str, name: str) -> str:
    safe = name.replace(":", "_")
    return os.path.join(CACHE, kind, f"{safe}.json")


def fetch_list(items: List[Tuple[str, str, str, str]]) -> Dict[str, int]:
    """items: (kind, cache name, url-ticker, start, end) are packed as (kind, name, ticker, start|end)."""
    session = requests.Session()
    counts: Dict[str, int] = {}
    last = 0.0
    for i, (kind, name, ticker, span) in enumerate(items):
        path = cache_path(kind, name)
        if os.path.exists(path):
            counts["cached"] = counts.get("cached", 0) + 1
            continue
        wait = SPACING - (time.time() - last)
        if wait > 0:
            time.sleep(wait)
        start, end = span.split("|")
        j, status = get(session, aggs_url(ticker, start, end))
        last = time.time()
        counts[status] = counts.get(status, 0) + 1
        if j is not None:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"ticker": ticker, "start": start, "end": end, "status": status,
                           "results": j.get("results") or []}, f)
            with open(tmp, encoding="utf-8") as f:
                assert json.load(f)["ticker"] == ticker
            os.replace(tmp, path)
        if status in ("http401", "http403"):
            print(f"stopping: {status} (no valid key reaches api.massive.com)", flush=True)
            break
        if (i + 1) % 25 == 0:
            print(f"  {i + 1}/{len(items)} {counts}", flush=True)
    return counts


def load_bars(path: str):
    """Cached response -> DataFrame indexed by bar start (America/New_York), columns o h l c v vw n."""
    import pandas as pd
    with open(path, encoding="utf-8") as f:
        j = json.load(f)
    rows = j.get("results") or []
    if not rows:
        return pd.DataFrame(columns=["o", "h", "l", "c", "v", "vw", "n"])
    df = pd.DataFrame(rows)
    df.index = pd.to_datetime(df["t"], unit="ms", utc=True).dt.tz_convert("America/New_York")
    df.index.name = "start"
    if "vw" not in df:
        df["vw"] = (df["h"] + df["l"] + df["c"]) / 3
    return df[["o", "h", "l", "c", "v", "vw"] + (["n"] if "n" in df else [])].sort_index()


def month_spans(spec: str) -> List[Tuple[str, str, str]]:
    a, b = spec.split(":")
    y, m = map(int, a.split("-"))
    y2, m2 = map(int, b.split("-"))
    out = []
    while (y, m) <= (y2, m2):
        ny, nm = (y + (m == 12), m % 12 + 1)
        last = (date(ny, nm, 1) - date.resolution).isoformat()
        out.append((f"{y:04d}-{m:02d}", f"{y:04d}-{m:02d}-01", last))
        y, m = ny, nm
    return out


def selftest() -> int:
    ok = True

    def check(name: str, cond: bool) -> None:
        nonlocal ok
        ok &= bool(cond)
        print(f"{'PASS' if cond else 'FAIL'}  {name}")

    check("put ticker", option_ticker("QQQ", date(2025, 9, 16), "P", 591) == "O:QQQ250916P00591000")
    check("half-strike call ticker", option_ticker("QQQ", date(2026, 1, 26), "C", 625.5) == "O:QQQ260126C00625500")
    url = aggs_url("O:QQQ250916P00591000", "2025-09-16", "2025-09-16")
    check("URL carries no key", "apikey" not in url.lower() and "key=" not in url.lower())
    old = os.environ.pop("MASSIVE_API_KEY", None)
    check("no header without an env key (network secret path)", headers() == {})
    os.environ["MASSIVE_API_KEY"] = "dummy"
    check("Bearer header from env key", headers() == {"Authorization": "Bearer dummy"})
    os.environ.pop("MASSIVE_API_KEY")
    if old is not None:
        os.environ["MASSIVE_API_KEY"] = old
    spans = month_spans("2024-12:2025-02")
    check("month spans", [s[1:] for s in spans] == [("2024-12-01", "2024-12-31"), ("2025-01-01", "2025-01-31"),
                                                    ("2025-02-01", "2025-02-28")])
    import tempfile
    d = tempfile.mkdtemp()
    p = os.path.join(d, "x.json")
    t0 = int(datetime(2025, 9, 16, 13, 31, tzinfo=timezone.utc).timestamp() * 1000)
    with open(p, "w") as f:
        json.dump({"results": [{"o": 1, "h": 2, "l": 0.5, "c": 1.5, "v": 10, "vw": 1.2, "t": t0, "n": 3}]}, f)
    df = load_bars(p)
    check("bar start converted to New York time", df.index[0].strftime("%H:%M") == "09:31" and df["vw"].iloc[0] == 1.2)
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--contracts", default=None)
    ap.add_argument("--stock", default=None)
    ap.add_argument("--months", default=None, help="YYYY-MM:YYYY-MM for --stock")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.check:
        r = requests.get(f"{BASE}/v1/marketstatus/now", headers=headers(), timeout=30)
        print(f"api.massive.com marketstatus: HTTP {r.status_code}")
        return 0 if r.status_code == 200 else 1
    items: List[Tuple[str, str, str, str]] = []
    if a.stock and a.months:
        for ym, s, e in month_spans(a.months):
            items.append(("stk", f"{a.stock}_{ym}", a.stock, f"{s}|{e}"))
    if a.contracts:
        with open(a.contracts, encoding="utf-8") as f:
            rows = [json.loads(x) for x in f if x.strip()]
        rows.sort(key=lambda r: (r["date"], r["contract"]))          # oldest first: the free window rolls
        seen = set()
        for r in rows:
            key = (r["contract"], r["date"])
            if key in seen:
                continue
            seen.add(key)
            items.append(("opt", f"{r['contract']}_{r['date']}", r["contract"], f"{r['date']}|{r['date']}"))
    print(f"{len(items)} requests queued (~{len(items) * SPACING / 60:.0f} min at 5/min before cache hits)", flush=True)
    counts = fetch_list(items)
    print("done:", counts, flush=True)
    print("MASSIVE_FETCH_DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
