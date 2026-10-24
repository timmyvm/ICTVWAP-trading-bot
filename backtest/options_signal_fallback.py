"""
v0.35-audit Addendum A — the keyless fallback (DEVLOG v0.35-audit, Addendum A).

The pre-registered primary (V1/V2) needs real option minute bars. The data key never reached the session, so
these FALLBACK tests run on the underlying instead, and none of them can pass or fail V1/V2:
  A1  direction over his holds (model-free)          A2  timing against random entries (model-free)
  A3  Black-Scholes option bars through the unchanged pre-registered replay (an estimate)
  A4  % gain claims against the underlying's path (a bound)
  A5  pre-market bias calls from the analysis channel (model-free)

QQQ path: HistData NSXUSD 1m x that day's ratio (QQQ's official close / NSXUSD's close in the last regular
minute); Yahoo QQQ 1m after the HistData cache ends. Early closes come from Yahoo QQQ hourly bars.

Inputs (local, gitignored; the repository is public and the report prints aggregates only):
  backtest/data_cache/local/nas100_histdata_1m_2015_2026.csv.gz
  backtest/data_cache/local/yahoo_intraday/QQQ_{1d,1h,1m}.csv.gz             (fetch_yahoo_intraday.py)
  backtest/data_cache/local/discord/v035/trades_frozen.jsonl                (discord_trades.py --freeze)
  backtest/data_cache/local/discord/v036/bias_frozen.jsonl, bias_daymap.json (discord_bias_calls.py)

  python3 backtest/options_signal_fallback.py --selftest
  python3 backtest/options_signal_fallback.py --proxy-check
  python3 backtest/options_signal_fallback.py --report
"""

import argparse
import json
import math
import os
import random
import re
import sys
from datetime import date, datetime, time
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from backtest.options_signal_audit import (HOLD, LOCAL, MIN_LAG, NY, TRADES, cluster_t, describe,  # noqa: E402
                                           first_bar, fmt, last_bar_before, null_diff, replay, session_stop,
                                           ts_of, week_key)

NSX = f"{LOCAL}/nas100_histdata_1m_2015_2026.csv.gz"
V035 = f"{LOCAL}/discord/v035"
V036 = f"{LOCAL}/discord/v036"
A_T = 2.39                                    # one-sided 2.5 %, Bonferroni over A1, A2, A5
YEAR_MIN = 252 * 390                          # trading-time year in regular-session minutes
SIG_LO, SIG_HI = 0.05, 3.0
CLAIM_VOL, CLAIM_HEADROOM = 1.5, 1.2
TIMING_DRAWS, TIMING_WINDOW = 2000, pd.Timedelta(minutes=60)
FIXED_HOLDS = (5, 15, 30, 60)
A1_EXITS = ("EXIT", "STOPPED", "TRIM_EXECUTED")
STRIKE_BAND = 0.03
OPEN_T = time(9, 30)

_erf = np.vectorize(math.erf, otypes=[float])


# ---------------------------------------------------------------------------------------------------
# Black-Scholes (r = q = 0), trading-time T
# ---------------------------------------------------------------------------------------------------
def ncdf(x: np.ndarray) -> np.ndarray:
    return 0.5 * (1.0 + _erf(np.asarray(x, dtype=float) / math.sqrt(2.0)))


def bs(cp: str, s, k: float, t_years, sigma: float) -> np.ndarray:
    """Vectorized over s and t_years; t_years <= 0 gives the intrinsic value."""
    s, t = np.broadcast_arrays(np.atleast_1d(np.asarray(s, dtype=float)),
                               np.atleast_1d(np.asarray(t_years, dtype=float)))
    intr = np.maximum(s - k, 0.0) if cp == "C" else np.maximum(k - s, 0.0)
    out = intr.astype(float).copy()
    live = t > 0
    if live.any():
        sv = sigma * np.sqrt(t[live])
        d1 = (np.log(s[live] / k) + 0.5 * sv ** 2) / sv
        d2 = d1 - sv
        if cp == "C":
            out[live] = s[live] * ncdf(d1) - k * ncdf(d2)
        else:
            out[live] = k * ncdf(-d2) - s[live] * ncdf(-d1)
    return np.maximum(out, intr)


def bs1(cp: str, s: float, k: float, t_years: float, sigma: float) -> float:
    return float(bs(cp, s, k, t_years, sigma)[0])


def solve_sigma(cp: str, s: float, k: float, t_years: float, premium: float) -> Optional[float]:
    """Annualized sigma that prices the option at `premium`, or None outside [SIG_LO, SIG_HI]."""
    if t_years <= 0 or not (bs1(cp, s, k, t_years, SIG_LO) <= premium <= bs1(cp, s, k, t_years, SIG_HI)):
        return None
    lo, hi = SIG_LO, SIG_HI
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if bs1(cp, s, k, t_years, mid) < premium:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def t_mid(index: pd.DatetimeIndex, close_ts: pd.Timestamp) -> np.ndarray:
    """Years to the close from each bar's midpoint."""
    mins = (close_ts - (index + pd.Timedelta(seconds=30))).total_seconds().to_numpy() / 60.0
    return np.maximum(mins, 0.0) / YEAR_MIN


def typical(bars: pd.DataFrame) -> pd.Series:
    return (bars["o"] + bars["h"] + bars["l"] + bars["c"]) / 4.0


def model_bars(bars: pd.DataFrame, cp: str, k: float, sigma: float, close_ts: pd.Timestamp) -> pd.DataFrame:
    """Option minute bars implied by the underlying's minute bars (A3)."""
    t = t_mid(bars.index, close_ts)
    up, dn = (bars["h"], bars["l"]) if cp == "C" else (bars["l"], bars["h"])
    return pd.DataFrame({"o": bs(cp, bars["o"], k, t, sigma), "h": bs(cp, up, k, t, sigma),
                         "l": bs(cp, dn, k, t, sigma), "c": bs(cp, bars["c"], k, t, sigma),
                         "v": 1.0, "vw": bs(cp, typical(bars), k, t, sigma)}, index=bars.index)


# ---------------------------------------------------------------------------------------------------
# A1 / A2 on the underlying
# ---------------------------------------------------------------------------------------------------
def a1_trade(tr: dict, bars: pd.DataFrame, stop: pd.Timestamp) -> dict:
    post = ts_of(tr, "announce", True)
    t_in = first_bar(bars, post)
    if t_in is None or t_in >= stop:
        return {"status": "unfillable"}
    d = 1.0 if tr["cp"] == "C" else -1.0
    p = typical(bars)
    after = bars[bars.index > t_in]
    t_out, reason = None, "time stop"
    for e in sorted(tr.get("events", []), key=lambda e: ts_of(e, "", True)):
        if e["type"] not in A1_EXITS:
            continue
        t_cue = ts_of(e, "", True)
        if t_cue < stop:
            t_eff = first_bar(after, max(t_cue, t_in), wait=None, skip_open=False)
            if t_eff is not None and t_eff <= stop:
                t_out, reason = t_eff, e["type"].lower()
        break
    if t_out is None:
        t_out = first_bar(after, stop - MIN_LAG, wait=None, skip_open=False)
        if t_out is None:
            t_out = last_bar_before(after, stop + pd.Timedelta(minutes=11))
    if t_out is None:
        return {"status": "no exit bar"}
    out = {"status": "ok", "d": d, "t_in": t_in, "t_out": t_out, "reason": reason,
           "r": d * math.log(p[t_out] / p[t_in]), "hold_min": (t_out - t_in).total_seconds() / 60.0}
    for h in FIXED_HOLDS:
        th = first_bar(after, t_in + pd.Timedelta(minutes=h) - MIN_LAG, wait=None, skip_open=False)
        if th is None or th > stop:
            th = last_bar_before(after, stop)
        out[f"r{h}"] = d * math.log(p[th] / p[t_in]) if th is not None else float("nan")
    return out


def a2_null(bars: pd.DataFrame, t_in: pd.Timestamp, t_out: pd.Timestamp, d: float, stop: pd.Timestamp,
            seed: int) -> Optional[float]:
    """Mean return of random same-direction entries within +-60 min of t_in, each held as long as his trade
    (capped at the time-stop bar)."""
    idx = bars.index
    p = typical(bars).to_numpy()
    stop_pos = int(idx.searchsorted(stop))
    if stop_pos >= len(idx):
        stop_pos = len(idx) - 1
    hold = t_out - t_in
    elig = np.where((idx >= t_in - TIMING_WINDOW) & (idx <= t_in + TIMING_WINDOW) & (idx < stop)
                    & ~((idx.hour == 9) & (idx.minute == 30)))[0]
    if len(elig) < 5:
        return None
    rng = random.Random(seed)
    rets = []
    for _ in range(TIMING_DRAWS):
        i = elig[rng.randrange(len(elig))]
        j = min(int(idx.searchsorted(idx[i] + hold)), stop_pos)
        rets.append(d * math.log(p[j] / p[i]))
    return float(np.mean(rets))


# ---------------------------------------------------------------------------------------------------
# A4 claim bound, A5 session returns
# ---------------------------------------------------------------------------------------------------
def claim_bound(bars: pd.DataFrame, cp: str, k: float, sigma: float, close_ts: pd.Timestamp,
                t_from: pd.Timestamp, t_to: pd.Timestamp, stated: float) -> Optional[float]:
    w = bars[(bars.index >= t_from.floor("min")) & (bars.index <= t_to.floor("min"))]
    if not len(w):
        return None
    fav = w["h"] if cp == "C" else w["l"]
    return float(bs(cp, fav, k, t_mid(w.index, close_ts), CLAIM_VOL * sigma).max()) / stated - 1.0


def claim_implausible(pct: float, bound: float) -> bool:
    return 1.0 + pct / 100.0 > CLAIM_HEADROOM * (1.0 + bound)


def session_returns(b: pd.DataFrame) -> Dict[str, float]:
    """Log returns from the 09:30 open to the close, to 10:30 and to 12:00."""
    o = float(b["o"].iloc[0])
    out = {"oc": math.log(float(b["c"].iloc[-1]) / o)}
    for key, hm in (("o1030", time(10, 29)), ("o1200", time(11, 59))):
        w = b[b.index.time <= hm]
        out[key] = math.log(float(w["c"].iloc[-1]) / o) if len(w) else float("nan")
    return out


def close_from_hourly(starts: List[pd.Timestamp]) -> pd.Timestamp:
    """Yahoo hourly bars start at :30; the last one is a half-hour bar ending at the close."""
    last = max(starts)
    return last + pd.Timedelta(minutes=30 if last.minute == 30 else 60)


# ---------------------------------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------------------------------
class Underlying:
    def __init__(self, lo: str = "2024-11-01", hi: str = "2026-10-31") -> None:
        from backtest.fetch_yahoo_intraday import load
        d1, h1, m1 = load("QQQ", "1d"), load("QQQ", "1h"), load("QQQ", "1m")
        assert d1 is not None and h1 is not None and m1 is not None, "run fetch_yahoo_intraday.py first"
        self.daily = {ts.date(): float(c) for ts, c in d1["c"].items()}
        h1 = h1[h1.index.time < time(16, 0)]
        self.close_ts: Dict[date, pd.Timestamp] = {}
        for d, g in h1.groupby(h1.index.date):
            self.close_ts[d] = close_from_hourly(list(g.index))
        self.m1 = m1[m1.index.time < time(16, 0)]
        raw = pd.read_csv(NSX, usecols=["timestamp", "open", "high", "low", "close"])
        t0 = int(pd.Timestamp(lo, tz="UTC").timestamp())
        t1 = int(pd.Timestamp(hi, tz="UTC").timestamp())
        raw = raw[(raw["timestamp"] >= t0) & (raw["timestamp"] < t1)]
        idx = pd.DatetimeIndex(pd.to_datetime(raw["timestamp"].to_numpy(), unit="s", utc=True)).tz_convert(NY)
        nsx = pd.DataFrame({"o": raw["open"].to_numpy(), "h": raw["high"].to_numpy(),
                            "l": raw["low"].to_numpy(), "c": raw["close"].to_numpy()}, index=idx)
        self.nsx_end = nsx.index[-1]
        nsx = nsx[(nsx.index.time >= OPEN_T) & (nsx.index.time < time(16, 0))]
        self.nsx_days = {d: g for d, g in nsx.groupby(nsx.index.date)}
        self.m1_days = {d: g for d, g in self.m1.groupby(self.m1.index.date)}
        self.source: Dict[date, str] = {}
        self._cache: Dict[date, Optional[pd.DataFrame]] = {}

    def sessions(self) -> List[date]:
        return sorted(d for d in self.daily if d in self.close_ts)

    def proxy_day(self, d: date) -> Optional[pd.DataFrame]:
        close = self.close_ts.get(d)
        g = self.nsx_days.get(d)
        if close is None or g is None or d not in self.daily or close > self.nsx_end:
            return None
        g = g[g.index < close]
        if len(g) < 0.9 * (close - pd.Timestamp(datetime.combine(d, OPEN_T)).tz_localize(NY)).total_seconds() / 60:
            return None
        k = self.daily[d] / float(g["c"].iloc[-1])
        return g * k

    def day(self, d: date) -> Optional[pd.DataFrame]:
        if d in self._cache:
            return self._cache[d]
        b = self.proxy_day(d)
        self.source[d] = "proxy"
        if b is None and d in self.m1_days and d in self.close_ts and d > self.nsx_end.date():
            g = self.m1_days[d]
            b = g[g.index < self.close_ts[d]][["o", "h", "l", "c"]]
            self.source[d] = "yahoo 1m"
        self._cache[d] = b
        return b


# ---------------------------------------------------------------------------------------------------
# proxy check
# ---------------------------------------------------------------------------------------------------
def proxy_check(ub: Underlying) -> bool:
    print("=" * 100 + "\nPROXY CHECK: scaled NSXUSD vs Yahoo QQQ\n" + "=" * 100)
    both = [d for d in ub.sessions() if d in ub.m1_days and ub.proxy_day(d) is not None]
    ok = True
    if both:
        px = pd.concat([ub.proxy_day(d) for d in both])
        q = pd.concat([ub.m1_days[d] for d in both])
        q = q[q.index.isin(px.index)]
        rp, rq = np.log(px["c"]).diff(), np.log(q["c"]).diff()
        cors = {}
        for lag in range(-3, 4):
            j = pd.concat([rq, rp.shift(lag)], axis=1).dropna()
            cors[lag] = float(j.corr().iloc[0, 1])
        best = max(cors, key=cors.get)
        lvl = (px["c"].reindex(q.index) - q["c"]).dropna()
        print(f"  1m overlap: {len(both)} sessions, {len(lvl)} minutes; return correlation by lag "
              + " ".join(f"{k:+d}:{v:.3f}" for k, v in cors.items()) + f"  -> best lag {best:+d}")
        print(f"  level error (proxy - QQQ): RMS ${math.sqrt(float((lvl ** 2).mean())):.3f}, "
              f"median |err| ${float(lvl.abs().median()):.3f}, 99th pct |err| ${float(lvl.abs().quantile(0.99)):.3f}")
        ok &= best == 0
    else:
        print("  no 1m overlap sessions")
    from backtest.fetch_yahoo_intraday import load
    h1 = load("QQQ", "1h")
    h1 = h1[h1.index.time < time(16, 0)]
    rows = []
    for d in ub.sessions():
        b = ub.proxy_day(d)
        if b is None:
            continue
        hb = h1[h1.index.date == d]
        for st, row in hb.iloc[:-1].iterrows():          # the last bar is the close the ratio is fitted to
            end = st + pd.Timedelta(minutes=60)
            for shift in (-60, 0, 60):
                w = b[b.index < end + pd.Timedelta(minutes=shift)]
                w = w[w.index >= end + pd.Timedelta(minutes=shift) - pd.Timedelta(minutes=1)]
                if len(w):
                    rows.append((d.strftime("%Y-%m"), shift, float(w["c"].iloc[-1]) - float(row["c"])))
    e = pd.DataFrame(rows, columns=["month", "shift", "err"])
    if len(e):
        rms = e.groupby("shift")["err"].apply(lambda x: math.sqrt(float((x ** 2).mean())))
        print("  hourly closes, whole span: RMS $ by proxy shift " + "  ".join(f"{s:+d} min: {v:.3f}" for s, v in rms.items()))
        m = e[e["shift"] == 0].groupby("month")["err"].apply(lambda x: math.sqrt(float((x ** 2).mean())))
        print("  by month (shift 0): worst " + ", ".join(f"{k} {v:.3f}" for k, v in m.sort_values().tail(4).items())
              + f"; median month {float(m.median()):.3f}")
        ok &= bool(rms.idxmin() == 0)
    print(f"  proxy clock: {'OK (lag 0)' if ok else 'NOT OK - stop'}")
    return ok


# ---------------------------------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------------------------------
def report() -> int:
    ub = Underlying()
    if not proxy_check(ub):
        print("stopping: the proxy's clock is off (pre-registered: nothing is shifted to fit)")
        return 1
    trades = [json.loads(x) for x in open(TRADES, encoding="utf-8") if x.strip()]
    excl = {"no underlying bars": 0, "strike outside 3 %": 0}
    rows = []
    for t in trades:
        d = date.fromisoformat(t["date"])
        b = ub.day(d)
        if b is None:
            excl["no underlying bars"] += 1
            continue
        post = ts_of(t, "announce", True)
        prev = b[b.index <= post.floor("min")]
        s0 = float(prev["c"].iloc[-1]) if len(prev) else float(b["o"].iloc[0])
        if abs(t["strike"] / s0 - 1) > STRIKE_BAND:
            excl["strike outside 3 %"] += 1
            continue
        close = ub.close_ts[d]
        rows.append((t, b, session_stop(d, close), close))
    print(f"\nfrozen trades {len(trades)}; excluded (counted): {excl}; scored {len(rows)}; "
          f"sources: {pd.Series([ub.source[date.fromisoformat(t['date'])] for t, *_ in rows]).value_counts().to_dict()}")

    # ---------------- A1 / A2
    print("\n" + "=" * 100 + "\nA1 DIRECTION over his holds and A2 TIMING vs random entries (model-free)\n" + "=" * 100)
    recs = []
    for i, (t, b, stop, close) in enumerate(rows):
        a = a1_trade(t, b, stop)
        rec = {"trade_id": t["trade_id"], "date": t["date"], "kind": t["kind"], "cp": t["cp"], "status": a["status"]}
        if a["status"] == "ok":
            rnd = a2_null(b, a["t_in"], a["t_out"], a["d"], stop, seed=5000 + i)
            rec.update({k: a[k] for k in ("r", "reason", "hold_min", *[f"r{h}" for h in FIXED_HOLDS])})
            rec["rand"] = rnd
        recs.append(rec)
    df = pd.DataFrame(recs)
    ok = df[df["status"] == "ok"].copy()
    wk = np.array([week_key(date.fromisoformat(x)) for x in ok["date"]])
    bp = lambda x: f"{1e4 * x:+.1f} bp"

    def line(label: str, x: np.ndarray, w: np.ndarray) -> Tuple[float, float]:
        m, tt = cluster_t(x, w)
        print(f"  {label:46s} n {len(x):4d}  mean {bp(m):>10s}  t {tt:+5.2f}  hit {100 * float((x > 0).mean()):5.1f}%  "
              f"median {bp(float(np.median(x)))}")
        return m, tt

    print(f"  unfillable {int((df['status'] == 'unfillable').sum())}; exit reasons {ok['reason'].value_counts().to_dict()}; "
          f"median hold {ok['hold_min'].median():.0f} min")
    m1, t1 = line("A1 signed return to his exit cue / time stop", ok["r"].to_numpy(float), wk)
    for k in ("live", "after"):
        s = ok["kind"] == k
        line(f"   {k} entries", ok.loc[s, "r"].to_numpy(float), wk[s.to_numpy()])
    for cp in ("C", "P"):
        s = ok["cp"] == cp
        line(f"   {'calls' if cp == 'C' else 'puts'}", ok.loc[s, "r"].to_numpy(float), wk[s.to_numpy()])
    for h in FIXED_HOLDS:
        x = ok[f"r{h}"].to_numpy(float)
        f = np.isfinite(x)
        line(f"   fixed {h}-min hold", x[f], wk[f])
    drift = []
    for d in ub.sessions():
        b = ub.day(d) if date(2024, 12, 1) <= d else None
        if b is None:
            continue
        p = typical(b).to_numpy()
        if len(p) > 31:
            drift.append(np.log(p[30:] / p[:-30]))
    if drift:
        allr = np.concatenate(drift)
        print(f"  unconditional 30-min drift over every session minute: mean {bp(float(allr.mean()))}, "
              f"sd {bp(float(allr.std()))}")
    g = ok[ok["rand"].notna()]
    diff = g["r"].to_numpy(float) - g["rand"].to_numpy(float)
    wg = np.array([week_key(date.fromisoformat(x)) for x in g["date"]])
    print(f"  A2: his mean {bp(float(g['r'].mean()))}, random mean {bp(float(g['rand'].mean()))}")
    m2, t2 = line("A2 his return minus random entries (same hold)", diff, wg)
    df.to_csv(f"{V035}/fallback_per_trade.csv", index=False)

    # ---------------- A3
    print("\n" + "=" * 100 + "\nA3 MODELLED option P&L (Black-Scholes on the underlying; an estimate, no verdict)\n" + "=" * 100)
    sig, how = {}, {}
    for t, b, stop, close in rows:
        if not t.get("stated_entry"):
            continue
        st = pd.Timestamp(t.get("stated_entry_utc") or t["announce_utc"]).tz_convert(NY).floor("min")
        if st not in b.index:
            how[t["trade_id"]] = "entry minute outside the session"
            continue
        s = float(typical(b.loc[[st]]).iloc[0])
        tt = float(t_mid(pd.DatetimeIndex([st]), close)[0])
        prem = float(t["stated_entry"])
        sv = solve_sigma(t["cp"], s, t["strike"], tt, prem)
        if sv is None:
            intr = max(0.0, s - t["strike"]) if t["cp"] == "C" else max(0.0, t["strike"] - s)
            how[t["trade_id"]] = "below model intrinsic" if prem < intr else "outside sigma bounds"
        else:
            sig[t["trade_id"]], how[t["trade_id"]] = sv, "solved"
    by_month: Dict[str, List[float]] = {}
    for t, *_ in rows:
        if t["trade_id"] in sig:
            by_month.setdefault(t["date"][:7], []).append(sig[t["trade_id"]])
    med = {m: float(np.median(v)) for m, v in by_month.items()}
    months = sorted(med)

    def month_sigma(m: str) -> float:
        if m in med:
            return med[m]
        key = lambda x: (abs((int(x[:4]) * 12 + int(x[5:])) - (int(m[:4]) * 12 + int(m[5:]))), x)
        return med[min(months, key=key)]

    sigma = {t["trade_id"]: sig.get(t["trade_id"], month_sigma(t["date"][:7])) for t, *_ in rows}
    for t, *_ in rows:
        how.setdefault(t["trade_id"], "no stated premium")
    print(f"  sigma: {pd.Series(list(how.values())).value_counts().to_dict()}; solved median "
          f"{100 * np.median(list(sig.values())):.0f}% (IQR {100 * np.percentile(list(sig.values()), 25):.0f}-"
          f"{100 * np.percentile(list(sig.values()), 75):.0f}%)")

    def run(scale: float = 1.0, **kw) -> pd.DataFrame:
        out = []
        for t, b, stop, close in rows:
            mb = model_bars(b, t["cp"], t["strike"], scale * sigma[t["trade_id"]], close)
            r = replay(t, mb, stop, **kw)
            out.append({"trade_id": t["trade_id"], "date": t["date"], "kind": t["kind"], "status": r["status"],
                        "ret": r.get("ret"), "reasons": r.get("exit_reasons")})
        return pd.DataFrame(out)

    def show(label: str, d3: pd.DataFrame) -> dict:
        okk = d3[d3["status"] == "ok"]
        dd = describe(okk["ret"].to_numpy(float), np.array([week_key(date.fromisoformat(x)) for x in okk["date"]]))
        print(f"  {label:40s} {fmt(dd)}")
        return dd

    base = run()
    db = show("modelled primary (sigma x1)", base)
    show("modelled stress (double spread)", run(mult=2.0))
    show("sigma x0.8", run(0.8))
    show("sigma x1.2", run(1.2))
    for k in ("live", "after"):
        show(f"   {k} entries", base[base["kind"] == k])
    show("full exit at the first trim", run(trim="full"))
    show("fixed 30-minute hold", run(fixed_hold=HOLD))
    print("  exit reasons:", base[base["status"] == "ok"]["reasons"].value_counts().head(6).to_dict())
    nd, wk3 = [], []
    for i, (t, b, stop, close) in enumerate(rows):
        r = null_diff(t, model_bars(b, t["cp"], t["strike"], sigma[t["trade_id"]], close), stop, 1.0, seed=1000 + i)
        if r is not None:
            nd.append(r["diff"])
            wk3.append(week_key(date.fromisoformat(t["date"])))
    m3, t3 = cluster_t(np.array(nd), np.array(wk3))
    print(f"  modelled V2 (his entry vs 2,000 random, 30-min hold): n {len(nd)}, difference {100 * m3:+.1f}% (t {t3:+.2f})")
    msgs = [json.loads(x) for x in open(f"{V035}/caller_messages.jsonl", encoding="utf-8") if x.strip()]
    perfect = set()
    for m in msgs:
        g2 = re.search(r"\b(\d{1,2})\s?/\s?(\d{1,2})\b", m["text"])
        if g2 and re.search(r"week|today|day", m["text"], re.I):
            a_, b_ = map(int, g2.groups())
            if a_ == b_ and a_ > 0:
                perfect.add(week_key(date.fromisoformat(m["date"])))
    bok = base[base["status"] == "ok"]
    pw = bok[bok["date"].map(lambda x: week_key(date.fromisoformat(x))).isin(perfect)]
    print(f"  weeks he called perfect: {len(perfect)}; modelled follower trades those weeks {len(pw)}, "
          f"losers {int((pw['ret'] < 0).sum())}")

    # ---------------- A4
    print("\n" + "=" * 100 + "\nA4 GAIN CLAIMS vs the underlying's path (sigma x1.5, 20 % headroom)\n" + "=" * 100)
    n_cl, n_imp, untracked, early = 0, 0, 0, 0
    ratios = []
    for t, b, stop, close in rows:
        claims = [e for e in t["events"] if e["type"] == "CLAIM" and e.get("pct") is not None]
        if not t.get("stated_entry"):
            untracked += len(claims)
            continue
        st = pd.Timestamp(t.get("stated_entry_utc") or t["announce_utc"]).tz_convert(NY)
        for e in claims:
            try:
                pct = float(e["pct"])
            except (TypeError, ValueError):
                continue
            if pct <= 0:
                continue
            bound = claim_bound(b, t["cp"], t["strike"], sigma[t["trade_id"]], close, st,
                                ts_of(e, "", True), float(t["stated_entry"]))
            if bound is None:
                early += 1
                continue
            n_cl += 1
            n_imp += claim_implausible(pct, bound)
            ratios.append((1 + pct / 100) / (1 + bound))
    print(f"  claims checked {n_cl}; implausible {n_imp} ({100 * n_imp / max(n_cl, 1):.0f}%); claims on trades without a "
          f"stated entry (not checked) {untracked}; posted before the stated-entry minute (not checked) {early}")
    if ratios:
        r_ = np.array(ratios)
        print(f"  (1 + claim) / (1 + bound): median {np.median(r_):.2f}, 90th pct {np.percentile(r_, 90):.2f}, max {r_.max():.2f}")

    # ---------------- A5
    print("\n" + "=" * 100 + "\nA5 PRE-MARKET BIAS CALLS vs the session (model-free)\n" + "=" * 100)
    v5 = None
    fz = f"{V036}/bias_frozen.jsonl"
    if os.path.exists(fz):
        labels = {int(json.loads(x)["day"]): json.loads(x)["label"] for x in open(fz) if x.strip()}
        dmap = {int(k): date.fromisoformat(v) for k, v in json.load(open(f"{V036}/bias_daymap.json")).items()}
        print(f"  agreed labels: {pd.Series(list(labels.values())).value_counts().to_dict()}")
        lab_dates = [dmap[k] for k in labels]
        lo, hi = min(lab_dates), max(lab_dates)
        sess = {}
        for d in ub.sessions():
            if lo <= d <= hi:
                b = ub.day(d)
                if b is not None and len(b):
                    sess[d] = session_returns(b)
        mu = {k: float(np.nanmean([s[k] for s in sess.values()])) for k in ("oc", "o1030", "o1200")}
        sc, nob = [], 0
        for k, lab in labels.items():
            if lab not in ("BULL", "BEAR"):
                continue
            d = dmap[k]
            if d not in sess:
                nob += 1
                continue
            sgn = 1.0 if lab == "BULL" else -1.0
            sc.append({"date": d, "d": sgn, **{f"r_{x}": sgn * sess[d][x] for x in mu},
                       **{f"x_{x}": sgn * (sess[d][x] - mu[x]) for x in mu}})
        s5 = pd.DataFrame(sc)
        print(f"  sessions in span {len(sess)}; mean open-to-close {bp(mu['oc'])}; scored calls {len(s5)} "
              f"(BULL {int((s5['d'] > 0).sum())}, BEAR {int((s5['d'] < 0).sum())}); calls on days without bars {nob}")
        w5 = np.array([week_key(d) for d in s5["date"]])
        m5, t5 = line("A5 drift-adjusted signed open-to-close", s5["x_oc"].to_numpy(float), w5)
        line("   raw signed open-to-close (hit rate = share > 0)", s5["r_oc"].to_numpy(float), w5)
        line("   09:30 -> 10:30 (drift-adjusted)", s5["x_o1030"].to_numpy(float), w5)
        line("   09:30 -> 12:00 (drift-adjusted)", s5["x_o1200"].to_numpy(float), w5)
        v5 = (m5, t5)
    else:
        print("  bias labels not frozen yet")

    print("\n" + "=" * 100 + "\nADDENDUM A RESULTS (fallback; V1/V2 stay open until real option bars)\n" + "=" * 100)
    print(f"  A1 direction over his holds: {'PASS' if m1 > 0 and t1 >= A_T else 'FAIL'} (mean {bp(m1)}, t {t1:+.2f}; bar {A_T})")
    print(f"  A2 timing vs random entries: {'PASS' if m2 > 0 and t2 >= A_T else 'FAIL'} (mean {bp(m2)}, t {t2:+.2f})")
    print(f"  A3 modelled follower (estimate): mean {100 * db['mean']:+.1f}% per trade, t {db['t']:+.2f}, "
          f"win {100 * db['win']:.0f}%, PF {db['pf']:.2f}")
    if v5:
        print(f"  A5 pre-market bias calls: {'PASS' if v5[0] > 0 and v5[1] >= A_T else 'FAIL'} "
              f"(mean {bp(v5[0])}, t {v5[1]:+.2f})")
    print("FALLBACK_REPORT_DONE")
    return 0


# ---------------------------------------------------------------------------------------------------
# self-tests on synthetic data
# ---------------------------------------------------------------------------------------------------
def selftest() -> int:
    ok = True

    def check(name: str, cond: bool) -> None:
        nonlocal ok
        ok &= bool(cond)
        print(f"{'PASS' if cond else 'FAIL'}  {name}")

    for s, tt in ((500.0, 0.002), (480.0, 0.0005), (530.0, 1e-5)):
        c, p = bs1("C", s, 505.0, tt, 0.25), bs1("P", s, 505.0, tt, 0.25)
        check(f"put-call parity at S {s:.0f}", abs((c - p) - (s - 505.0)) < 1e-9)
    check("T = 0 gives intrinsic", bs1("C", 510, 505, 0.0, 0.3) == 5.0 and bs1("P", 510, 505, 0.0, 0.3) == 0.0)
    tt = 120 / YEAR_MIN
    prem = bs1("P", 500.0, 498.0, tt, 0.37)
    check("sigma solver recovers a planted sigma", abs(solve_sigma("P", 500.0, 498.0, tt, prem) - 0.37) < 1e-6)
    check("premium below intrinsic -> unsolvable", solve_sigma("P", 490.0, 498.0, tt, 7.5) is None)

    day = date(2025, 9, 16)
    close = pd.Timestamp("2025-09-16 16:00", tz=NY)
    idx = pd.date_range("2025-09-16 09:30", "2025-09-16 15:59", freq="1min", tz=NY)
    lin = 500.0 * np.exp(1e-4 * np.arange(len(idx)))
    bars = pd.DataFrame({"o": lin, "h": lin * 1.0002, "l": lin * 0.9998, "c": lin}, index=idx)
    stop = session_stop(day, close)
    u = lambda hm: pd.Timestamp(f"2025-09-16 {hm}", tz=NY).tz_convert("UTC").isoformat()
    tr = {"cp": "C", "announce_utc": u("10:00:10"), "events": [{"type": "QUOTE", "utc": u("10:05:00")},
                                                               {"type": "EXIT", "utc": u("10:20:00")}]}
    a = a1_trade(tr, bars, stop)
    p = typical(bars)
    t_in, t_out = pd.Timestamp("2025-09-16 10:01", tz=NY), pd.Timestamp("2025-09-16 10:21", tz=NY)
    check("A1 entry >= 30 s after the post, exit >= 30 s after the cue", a["t_in"] == t_in and a["t_out"] == t_out)
    check("A1 call on a rising path: exact log return", abs(a["r"] - math.log(p[t_out] / p[t_in])) < 1e-12 and a["r"] > 0)
    a_put = a1_trade(dict(tr, cp="P"), bars, stop)
    check("A1 put on the same path: the negative", abs(a_put["r"] + a["r"]) < 1e-12)
    a_tr = a1_trade(tr, bars[bars.index <= t_out], stop)
    check("A1 truncation guard (bars after the exit change nothing)", abs(a_tr["r"] - a["r"]) < 1e-12)
    check("A1 no exit cue -> time stop at 15:50", a1_trade(dict(tr, events=[]), bars, stop)["t_out"].strftime("%H:%M") == "15:50")
    n = a2_null(bars, a["t_in"], a["t_out"], 1.0, stop, seed=3)
    check("A2 on a constant-drift path: his entry == random entries", n is not None and abs(a["r"] - n) < 1e-9)
    jump = np.where(idx >= t_in + pd.Timedelta(minutes=1), 1.01, 1.0) * 500.0
    jb = pd.DataFrame({"o": jump, "h": jump, "l": jump, "c": jump}, index=idx)
    aj = a1_trade(tr, jb, stop)
    nj = a2_null(jb, aj["t_in"], aj["t_out"], 1.0, stop, seed=3)
    check("A2 a move right after his entry beats random entries", aj["r"] - nj > 0.003)

    mb = model_bars(bars, "P", 505.0, 0.3, close)
    check("modelled put bars: h >= o, c >= l", bool((mb["h"] >= mb[["o", "c"]].max(axis=1) - 1e-12).all()
                                                  and (mb["l"] <= mb[["o", "c"]].min(axis=1) + 1e-12).all()))
    flat = pd.DataFrame({"o": 500.0, "h": 500.0, "l": 500.0, "c": 500.0}, index=idx)
    r_flat = replay({"announce_utc": u("10:00:10"), "events": []}, model_bars(flat, "C", 501.0, 0.2, close), stop)
    check("flat underlying: a held OTM call loses to time decay", r_flat["status"] == "ok" and r_flat["ret"] < -0.5)
    st = pd.Timestamp("2025-09-16 10:00", tz=NY)
    b0 = claim_bound(bars, "C", 505.0, 0.2, close, st, pd.Timestamp("2025-09-16 11:00", tz=NY),
                     bs1("C", float(p[st]), 505.0, float(t_mid(pd.DatetimeIndex([st]), close)[0]), 0.2))
    check("claim bound is positive on a rising path", b0 is not None and b0 > 0)
    check("a claim above 1.2 x (1 + bound) is flagged, one below is not",
          claim_implausible(100 * (1.25 * (1 + b0) - 1), b0) and not claim_implausible(100 * b0, b0))
    sr = session_returns(bars)
    check("session open-to-close return", abs(sr["oc"] - math.log(lin[-1] / lin[0])) < 1e-12)
    check("close from hourly bars: 12:30 -> 13:00, 15:30 -> 16:00",
          close_from_hourly([pd.Timestamp("2025-11-28 12:30", tz=NY)]).strftime("%H:%M") == "13:00"
          and close_from_hourly([pd.Timestamp("2025-11-26 15:30", tz=NY)]).strftime("%H:%M") == "16:00")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--proxy-check", action="store_true")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.proxy_check:
        return 0 if proxy_check(Underlying()) else 1
    if a.report:
        return report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
