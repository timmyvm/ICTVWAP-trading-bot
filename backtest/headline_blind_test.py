"""
v0.27-exp — Can headlines alone call the next-session stock move? (DEVLOG v0.27-exp)

Blind protocol (pre-registered before any event was read):
1. The event set is fixed by rule: the most recent quarterly earnings release
   between 2026-07-01 and 2026-10-02 (after the predictor's training cutoff) of
   the 20 companies in TICKERS.
2. Collector agents write the facts known at release time — press release, that
   day's call, PRE-release consensus — to backtest/headline_events/events_*.json
   using a fixed template (two key metrics per company, named before the search),
   with every mention of the price reaction stripped. Source URLs go to a
   separate file the predictor does not read until scoring is done.
3. --leakscan flags reaction vocabulary per ticker and prints pattern ids only,
   never the text, so the scan itself cannot leak.
4. Predictions are written to predictions.json and committed + pushed BEFORE
   --score fetches a single price.

Primary measure: total return from the last close before the release to the
close of the first regular session after it (AMC: next close / release-day
close; BMO: release-day close / prior close; non-trading day: first close after
/ last close before). Secondary: market-adjusted (minus SPY over the same
window) and the TRADEABLE move, first post-release open -> that session's close.

Usage:
  python backtest/headline_blind_test.py --selftest   # window logic on the 2 revealed game events
  python backtest/headline_blind_test.py --merge      # events_*.json -> events.json (+ checks)
  python backtest/headline_blind_test.py --leakscan   # per-ticker flags, no text printed
  python backtest/headline_blind_test.py --score      # ONLY after predictions are committed
"""

import argparse
import glob
import json
import math
import os
import re
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import pandas as pd
import requests

DIR = "backtest/headline_events"
CACHE = "backtest/data_cache/local/headline_prices"
TICKERS = ["MSFT", "GOOGL", "META", "AAPL", "AMZN", "NVDA", "AVGO", "ORCL", "PLTR", "TSLA",
           "JPM", "V", "MA", "WMT", "COST", "LLY", "JNJ", "ABBV", "XOM", "NFLX"]
# The usual release slot, used only to flag a collector error; never overrides the file.
USUAL_TIMING = {t: "AMC" for t in ("MSFT", "GOOGL", "META", "AAPL", "AMZN", "NVDA", "AVGO",
                                   "ORCL", "PLTR", "TSLA", "V", "COST", "NFLX")}
USUAL_TIMING.update({t: "BMO" for t in ("JPM", "MA", "WMT", "LLY", "JNJ", "ABBV", "XOM")})
WINDOW = (date(2026, 7, 1), date(2026, 10, 2))
FIELDS = ("ticker", "company", "period", "release_date_et", "release_time_et", "timing",
          "revenue_reported", "revenue_consensus", "eps_reported", "eps_consensus", "eps_basis",
          "guidance", "key_metrics", "other_announcements", "headline", "notes")
SMALL, BIG = 0.02, 0.05
COST_RT = 0.0010             # round-trip cost assumed for the tradeable test (liquid mega-caps)
UA = {"User-Agent": "Mozilla/5.0"}
YF = "https://query1.finance.yahoo.com/v8/finance/chart/{t}?period1={p1}&period2={p2}&interval=1d"

LEAK_PATTERNS = [
    r"\b(shares?|stocks?)\b[^.;\n]{0,40}\b(rose|rise[sn]?|rising|fell|falls?|falling|jump\w*|surg\w*|soar\w*"
    r"|plung\w*|tumbl\w*|slid|slid\w+|sank|sink\w*|rall\w*|drop\w*|gain\w*|climb\w*|declin\w*|spik\w*"
    r"|slump\w*|dip|dipp\w*|rebound\w*|higher|lower)\b",
    r"after[- ]hours|extended[- ]trading|pre-?market|post-?market",
    r"\b(sell-?off|rallied|tumbled|plunged|soared|surged|skyrocket\w*|nosediv\w*)\b",
    r"\binvestors?\b",
    r"\b(price target|downgrad\w*|outperform|underperform)\b",
    r"\b(blowout|disappoint\w*|cheer\w*|stellar|lacklust\w*)\b",
    r"\bmarket (reaction|value|cap\w*)\b|\bmarket-cap\b",
    r"https?://|www\.",
]


def size_bucket(r: float) -> str:
    a = abs(r)
    return "small" if a < SMALL else ("big" if a > BIG else "medium")


def first_float(s) -> Optional[float]:
    m = re.search(r"-?\d+(?:\.\d+)?", str(s).replace(",", ""))
    return float(m.group()) if m else None


def binom_tail(k: int, n: int) -> float:
    """One-sided P(X >= k) for X ~ Binomial(n, 0.5)."""
    return sum(math.comb(n, i) for i in range(k, n + 1)) / 2 ** n


# ---------------------------------------------------------------------------- events

def merge() -> list:
    rows = []
    for p in sorted(glob.glob(f"{DIR}/events_[A-Z].json")):
        rows.extend(json.load(open(p)))
    by = {r["ticker"].upper(): r for r in rows}
    missing = [t for t in TICKERS if t not in by]
    out, problems = [], []
    for t in TICKERS:
        if t not in by:
            continue
        r = by[t]
        absent = [f for f in FIELDS if f not in r]
        if absent:
            problems.append(f"{t}: missing fields {absent}")
        d = date.fromisoformat(r["release_date_et"])
        if not WINDOW[0] <= d <= WINDOW[1]:
            problems.append(f"{t}: release date {d} outside {WINDOW[0]}..{WINDOW[1]}")
        if r["timing"] not in ("AMC", "BMO", "INTRADAY", "NON-TRADING-DAY"):
            problems.append(f"{t}: timing '{r['timing']}' not recognised")
        elif r["timing"] != USUAL_TIMING[t]:
            problems.append(f"{t}: timing {r['timing']} differs from the usual {USUAL_TIMING[t]} — verify")
        out.append(r)
    json.dump(out, open(f"{DIR}/events.json", "w"), indent=2)
    print(f"merged {len(out)} of {len(TICKERS)} events -> {DIR}/events.json"
          + (f"; MISSING {missing}" if missing else ""))
    for p in problems:
        print("  CHECK:", p)
    return out


def leakscan() -> int:
    """Count reaction vocabulary per ticker. Prints pattern ids only — never the matched text."""
    ev = json.load(open(f"{DIR}/events.json"))
    flagged = 0
    for r in ev:
        hits = []
        for f in FIELDS:
            v = r.get(f, "")
            text = " ".join(v) if isinstance(v, list) else str(v)
            for i, pat in enumerate(LEAK_PATTERNS):
                if re.search(pat, text, flags=re.IGNORECASE):
                    hits.append(f"{f}:p{i}")
        if hits:
            flagged += 1
            print(f"  {r['ticker']}: {', '.join(hits)}")
    print(f"leakscan: {flagged} of {len(ev)} events flagged")
    return flagged


# ---------------------------------------------------------------------------- prices

def daily(ticker: str, lo: date, hi: date) -> pd.DataFrame:
    """Yahoo daily bars indexed by New York session date: open, close, adjclose."""
    os.makedirs(CACHE, exist_ok=True)
    path = f"{CACHE}/{ticker}_{lo}_{hi}.json"
    if not os.path.exists(path):
        p1 = int(datetime(lo.year, lo.month, lo.day, tzinfo=timezone.utc).timestamp())
        p2 = int(datetime(hi.year, hi.month, hi.day, tzinfo=timezone.utc).timestamp())
        r = requests.get(YF.format(t=ticker, p1=p1, p2=p2), headers=UA, timeout=60)
        r.raise_for_status()
        open(path, "w").write(r.text)
    d = json.load(open(path))["chart"]["result"][0]
    q = d["indicators"]["quote"][0]
    adj = d["indicators"].get("adjclose", [{}])[0].get("adjclose") or q["close"]
    idx = pd.to_datetime(d["timestamp"], unit="s", utc=True).tz_convert("America/New_York").date
    df = pd.DataFrame({"open": q["open"], "close": q["close"], "adjclose": adj}, index=idx)
    df = df[~df.index.duplicated(keep="last")].dropna()
    return df


def window(df: pd.DataFrame, d: date, timing: str) -> tuple:
    """(base session, reaction session) for a release on date d with the given timing."""
    days = list(df.index)
    before = [x for x in days if x < d]
    after = [x for x in days if x > d]
    on = d in df.index
    if timing == "AMC" and on:
        return d, after[0]
    if timing in ("BMO", "INTRADAY") and on:
        return before[-1], d
    return before[-1], after[0]      # non-trading day, or AMC/BMO dated on a closed day


def reaction(ticker: str, d: date, timing: str) -> dict:
    df = daily(ticker, d - timedelta(days=12), d + timedelta(days=12))
    b, s = window(df, d, timing)
    spy = daily("SPY", d - timedelta(days=12), d + timedelta(days=12))
    tot = df.at[s, "adjclose"] / df.at[b, "adjclose"] - 1.0
    mkt = spy.at[s, "adjclose"] / spy.at[b, "adjclose"] - 1.0
    trade = df.at[s, "close"] / df.at[s, "open"] - 1.0 if timing != "INTRADAY" else float("nan")
    gap = df.at[s, "open"] / df.at[b, "close"] - 1.0
    return {"base": b, "session": s, "total": tot, "spy": mkt, "excess": tot - mkt,
            "gap": gap, "tradeable": trade}


def selftest() -> None:
    """The window logic must reproduce the two events already revealed in the game."""
    for t, d, timing, want in (("NKE", date(2026, 10, 1), "AMC", -0.036),
                               ("TSLA", date(2026, 10, 2), "BMO", +0.047)):
        r = reaction(t, d, timing)
        ok = abs(r["total"] - want) < 0.002
        print(f"{t} {d} {timing}: base {r['base']} -> {r['session']}  total {100 * r['total']:+.2f}% "
              f"(expected {100 * want:+.1f}%)  gap {100 * r['gap']:+.2f}%  open->close "
              f"{100 * r['tradeable']:+.2f}%  {'OK' if ok else 'MISMATCH'}")
        assert ok, f"window logic failed for {t}"


# ---------------------------------------------------------------------------- scoring

def score() -> None:
    ev = {r["ticker"]: r for r in json.load(open(f"{DIR}/events.json"))}
    pr = {p["ticker"]: p for p in json.load(open(f"{DIR}/predictions.json"))}
    rows = []
    for t in TICKERS:
        if t not in ev or t not in pr:
            continue
        e, p = ev[t], pr[t]
        r = reaction(t, date.fromisoformat(e["release_date_et"]), e["timing"])
        sgn = 1 if p["direction"] == "UP" else -1
        conf = float(p["confidence"])
        eps_r, eps_c = first_float(e["eps_reported"]), first_float(e["eps_consensus"])
        naive = None if eps_r is None or eps_c is None else (1 if eps_r > eps_c else -1)
        rows.append({
            "ticker": t, "release": e["release_date_et"], "timing": e["timing"],
            "call": p["direction"], "size_call": p["size"], "conf": conf,
            "total": r["total"], "excess": r["excess"], "gap": r["gap"], "tradeable": r["tradeable"],
            "hit": (r["total"] > 0) == (sgn > 0),
            "hit_excess": (r["excess"] > 0) == (sgn > 0),
            "size_hit": size_bucket(r["total"]) == p["size"],
            "size_actual": size_bucket(r["total"]),
            "trade_pnl": sgn * r["tradeable"] - COST_RT,
            "naive_eps": naive, "naive_hit": None if naive is None else (r["total"] > 0) == (naive > 0),
            "brier": ((conf if sgn > 0 else 1 - conf) - (1.0 if r["total"] > 0 else 0.0)) ** 2,
        })
    df = pd.DataFrame(rows)
    df.to_csv(f"{DIR}/results.csv", index=False)

    print(f"{'ticker':6s} {'release':10s} {'tm':3s} {'call':5s} {'size':6s} {'conf':>4s} | "
          f"{'actual':>7s} {'size':6s} {'vs SPY':>7s} {'gap':>7s} {'open->cl':>8s} | hit")
    for _, r in df.iterrows():
        print(f"{r.ticker:6s} {r.release:10s} {r.timing:3s} {r.call:5s} {r.size_call:6s} {r.conf:4.2f} | "
              f"{100 * r.total:+6.1f}% {r.size_actual:6s} {100 * r.excess:+6.1f}% {100 * r.gap:+6.1f}% "
              f"{100 * r.tradeable:+7.1f}% | {'YES' if r.hit else 'no'}{' (size)' if r.size_hit else ''}")

    n, k = len(df), int(df.hit.sum())
    print(f"\nPRIMARY: {k} of {n} directions correct ({100 * k / n:.0f}%); one-sided p vs coin flip = "
          f"{binom_tail(k, n):.3f}; pass bar 15 of 20 -> {'PASS' if k >= 15 else 'FAIL'}")
    ke = int(df.hit_excess.sum())
    print(f"market-adjusted (vs SPY): {ke} of {n}; size buckets right: {int(df.size_hit.sum())} of {n}")
    nv = df.dropna(subset=["naive_hit"])
    print(f"naive 'EPS beat -> UP': {int(nv.naive_hit.astype(bool).sum())} of {len(nv)}; "
          f"'always UP': {int((df.total > 0).sum())} of {n}")
    print(f"Brier score of stated confidences: {df.brier.mean():.3f} (coin flip at 50% = 0.250; lower is better)")
    print(f"\nTRADEABLE (act at the first post-release open, exit at that close, {100 * COST_RT:.2f}% round trip):")
    print(f"  direction right on the open->close move: {int(((df.tradeable > 0) == (df.call == 'UP')).sum())} of {n}; "
          f"mean P&L per trade {100 * df.trade_pnl.mean():+.2f}%; sum {100 * df.trade_pnl.sum():+.1f}%")
    print(f"  share of the total move already in the opening gap: median "
          f"{100 * (df.gap / df.total).where(df.total.abs() > 0.005).median():.0f}%")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--merge", action="store_true")
    ap.add_argument("--leakscan", action="store_true")
    ap.add_argument("--score", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    if a.merge:
        merge()
    if a.leakscan:
        leakscan()
    if a.score:
        score()


if __name__ == "__main__":
    main()
