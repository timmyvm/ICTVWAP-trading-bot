"""
v0.35-audit — replay a frozen options-signal trade table on real option minute bars (DEVLOG v0.35-audit).

Inputs (all local, gitignored; the repository is public):
  backtest/data_cache/local/discord/v035/trades_frozen.jsonl   one trade per line (from discord_trades.py --freeze)
  backtest/data_cache/local/massive/opt/<contract>_<date>.json  option minute bars (fetch_massive_options.py)
  backtest/data_cache/local/massive/stk/QQQ_<yyyy-mm>.json      QQQ minute bars (session end, intrinsic value)

Follower model (pre-registered):
  entry   volume-weighted price of the first minute bar starting >= 30 s after the post (after the edit for
          an edited post), never the 09:30 opening print; no bar within 3 minutes -> "unfillable"
  costs   half-spread max($0.01, 2 % of premium) per side, doubled 09:30-09:45, x2 in the stress run;
          commission $0.65 per contract per side
  exits   half at the first executed trim; full exit cues at the first bar >= 30 s later; a BE stop is live
          from the next bar and fills at min(open, entry) - half-spread when a trade prints at or below the
          follower's entry (immediately if already below when posted); otherwise a time stop at 15:50 ET or
          10 minutes before an early close (session end from the QQQ bars)
  verdicts V1: mean net return on premium > 0, t >= 2.24 clustered by ISO (year, week)
           V2: his entries vs 2,000 random entries within +-60 min on the same contract-day, fixed 30-min hold

  python3 backtest/options_signal_audit.py --selftest
  python3 backtest/options_signal_audit.py --report
"""

import argparse
import json
import math
import os
import random
import sys
from datetime import date, datetime, time
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

LOCAL = "backtest/data_cache/local"
TRADES = f"{LOCAL}/discord/v035/trades_frozen.jsonl"
OPT_DIR = f"{LOCAL}/massive/opt"
STK_DIR = f"{LOCAL}/massive/stk"
NY = "America/New_York"

COMMISSION = 0.65 / 100                      # $ per share per side ($0.65 per 100-share contract)
MIN_LAG = pd.Timedelta(seconds=30)
MAX_WAIT = pd.Timedelta(minutes=3)
OPEN_T, EARLY_T = time(9, 30), time(9, 45)
TIME_STOP = time(15, 50)
HOLD = pd.Timedelta(minutes=30)
NULL_DRAWS, NULL_WINDOW = 2000, pd.Timedelta(minutes=60)
PASS_T = 2.24
EXIT_TYPES = ("EXIT", "STOPPED")


# ---------------------------------------------------------------------------------------------------
# costs and fills
# ---------------------------------------------------------------------------------------------------
def half_spread(premium: float, ts: pd.Timestamp, mult: float = 1.0) -> float:
    hs = max(0.01, 0.02 * premium)
    if OPEN_T <= ts.time() < EARLY_T:
        hs *= 2
    return hs * mult


def first_bar(bars: pd.DataFrame, after: pd.Timestamp, wait: Optional[pd.Timedelta] = MAX_WAIT,
              skip_open: bool = True, lag: pd.Timedelta = MIN_LAG) -> Optional[pd.Timestamp]:
    """Start of the first bar starting >= after + lag (within `wait` of that, if given), never 09:30:00."""
    lo = after + lag
    idx = bars.index[bars.index >= lo]
    if skip_open:
        idx = idx[~((idx.hour == 9) & (idx.minute == 30))]
    if len(idx) == 0:
        return None
    if wait is not None and idx[0] > lo + wait:
        return None
    return idx[0]


def buy_at(bars: pd.DataFrame, t: pd.Timestamp, mult: float) -> float:
    vw = float(bars.at[t, "vw"])
    return vw + half_spread(vw, t, mult)


def sell_at(bars: pd.DataFrame, t: pd.Timestamp, mult: float) -> float:
    vw = float(bars.at[t, "vw"])
    return max(0.0, vw - half_spread(vw, t, mult))


def session_stop(day: date, close_ts: Optional[pd.Timestamp]) -> pd.Timestamp:
    """15:50 ET, or 10 minutes before an early close seen in the QQQ bars."""
    stop = pd.Timestamp(datetime.combine(day, TIME_STOP)).tz_localize(NY)
    if close_ts is not None:
        stop = min(stop, close_ts - pd.Timedelta(minutes=10))
    return stop


# ---------------------------------------------------------------------------------------------------
# one trade
# ---------------------------------------------------------------------------------------------------
def replay(tr: dict, bars: pd.DataFrame, stop_ts: pd.Timestamp, mult: float = 1.0, trim: str = "half",
           be: str = "touch", exit_on_claim: bool = False, fixed_hold: Optional[pd.Timedelta] = None,
           use_edits: bool = True, expiry_value: Optional[float] = None,
           entry_lag: pd.Timedelta = MIN_LAG, entry_on_open: bool = False) -> dict:
    """Follower P&L for one trade. Returns status and the net return on premium (incl. both commissions).
    entry_lag / entry_on_open only serve the latency curve (next open, +2 min, +5 min)."""
    post = ts_of(tr, "announce", use_edits)
    t_in = first_bar(bars, post, lag=entry_lag)
    if t_in is None or t_in >= stop_ts:
        return {"status": "unfillable"}
    if entry_on_open:
        o = float(bars.at[t_in, "o"])
        px_in = o + half_spread(o, t_in, mult)
    else:
        px_in = buy_at(bars, t_in, mult)
    cost = px_in + COMMISSION
    after = bars[bars.index > t_in]
    legs: List[Tuple[float, float, str, pd.Timestamp]] = []          # (fraction, price, reason, time)
    qty = 1.0

    def close(frac: float, t: pd.Timestamp, reason: str, price: Optional[float] = None) -> None:
        nonlocal qty
        p = sell_at(bars, t, mult) if price is None else price
        legs.append((frac, p, reason, t))
        qty -= frac

    if fixed_hold is not None:
        t_out = first_bar(after, t_in + fixed_hold - MIN_LAG, wait=None, skip_open=False)
        if t_out is None or t_out > stop_ts:
            t_out = last_bar_before(after, stop_ts)
        if t_out is None:
            return {"status": "no exit bar"}
        close(1.0, t_out, "fixed hold")
        return summarize(px_in, cost, legs, t_in)

    events = sorted((e for e in tr.get("events", [])), key=lambda e: ts_of(e, "", use_edits))
    be_from: Optional[pd.Timestamp] = None
    trimmed = False
    for e in events:
        if qty <= 1e-9:
            break
        t_cue = ts_of(e, "", use_edits)
        if t_cue >= stop_ts:
            break
        t_eff = first_bar(after, max(t_cue, t_in), wait=None, skip_open=False)
        # a live BE stop can fire before this event takes effect
        if be_from is not None:
            hit = be_trigger(after, be_from, t_eff if t_eff is not None else stop_ts, px_in, be)
            if hit is not None:
                close(qty, hit[0], "BE stop", max(0.0, hit[1] - half_spread(hit[1], hit[0], mult)))
                break
        if t_eff is None or t_eff > stop_ts:
            break
        kind = e["type"]
        if kind == "TRIM_EXECUTED" and not trimmed:
            trimmed = True
            close(qty if trim == "full" else qty / 2, t_eff, "trim")
        elif kind in EXIT_TYPES or (exit_on_claim and kind == "CLAIM"):
            close(qty, t_eff, kind.lower())
        elif kind == "BE_STOP" and be_from is None:
            prev = bars[bars.index < t_cue + MIN_LAG]
            if len(prev) and float(prev["c"].iloc[-1]) < px_in:           # already below the entry
                close(qty, t_eff, "BE (already below)")
            else:
                be_from = t_cue.floor("min") + pd.Timedelta(minutes=1)
    if qty > 1e-9 and be_from is not None:
        hit = be_trigger(after, be_from, stop_ts, px_in, be)
        if hit is not None:
            close(qty, hit[0], "BE stop", max(0.0, hit[1] - half_spread(hit[1], hit[0], mult)))
    if qty > 1e-9:
        if expiry_value is not None:
            legs.append((qty, expiry_value, "expiry", stop_ts))
            qty = 0.0
        else:
            t_out = first_bar(after, stop_ts - MIN_LAG, wait=None, skip_open=False)
            if t_out is None:
                t_out = last_bar_before(after, stop_ts + pd.Timedelta(minutes=11))
            if t_out is None:
                return {"status": "no exit bar"}
            close(qty, t_out, "time stop")
    return summarize(px_in, cost, legs, t_in)


def be_trigger(after: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, stop: float,
               mode: str) -> Optional[Tuple[pd.Timestamp, float]]:
    w = after[(after.index >= start) & (after.index < end)]
    if mode == "close":
        hit = w[w["c"] <= stop]
        return (hit.index[0], float(hit["c"].iloc[0])) if len(hit) else None
    hit = w[w["l"] <= stop]
    if not len(hit):
        return None
    t = hit.index[0]
    return t, min(float(hit.at[t, "o"]), stop)


def last_bar_before(bars: pd.DataFrame, t: pd.Timestamp) -> Optional[pd.Timestamp]:
    idx = bars.index[bars.index < t]
    return idx[-1] if len(idx) else None


def summarize(px_in: float, cost: float, legs: List[Tuple[float, float, str, pd.Timestamp]],
              t_in: pd.Timestamp) -> dict:
    proceeds = sum(f * max(0.0, p - COMMISSION) for f, p, _, _ in legs)
    ret = proceeds / cost - 1.0
    last_t = max(t for _, _, _, t in legs)
    return {"status": "ok", "entry_px": px_in, "ret": ret, "exit_reasons": "+".join(r for _, _, r, _ in legs),
            "hold_min": (last_t - t_in).total_seconds() / 60.0, "t_in": t_in}


def ts_of(obj: dict, prefix: str, use_edits: bool) -> pd.Timestamp:
    """Timestamp at which the information was known: the edit time for edited posts (when use_edits)."""
    key = f"{prefix}_utc" if prefix else "utc"
    ekey = f"{prefix}_edited_utc" if prefix else "edited_utc"
    t = obj.get(ekey) if use_edits and obj.get(ekey) else obj[key]
    return pd.Timestamp(t).tz_convert(NY)


# ---------------------------------------------------------------------------------------------------
# luck null (V2): same contract-day, random entry minutes, fixed 30-minute hold, no extra data
# ---------------------------------------------------------------------------------------------------
def null_diff(tr: dict, bars: pd.DataFrame, stop_ts: pd.Timestamp, mult: float, seed: int) -> Optional[dict]:
    his = replay(tr, bars, stop_ts, mult, fixed_hold=HOLD)
    if his.get("status") != "ok":
        return None
    t0 = his["t_in"]
    lo, hi = t0 - NULL_WINDOW, t0 + NULL_WINDOW
    elig = bars.index[(bars.index >= lo) & (bars.index <= hi) & (bars.index <= stop_ts - HOLD)]
    elig = elig[~((elig.hour == 9) & (elig.minute == 30))]
    if len(elig) < 5:
        return None
    rng = random.Random(seed)
    rets = []
    cache: Dict[pd.Timestamp, float] = {}
    for _ in range(NULL_DRAWS):
        t = elig[rng.randrange(len(elig))]
        if t not in cache:
            px = buy_at(bars, t, mult)
            after = bars[bars.index > t]
            t_out = first_bar(after, t + HOLD - MIN_LAG, wait=None, skip_open=False)
            if t_out is None or t_out > stop_ts:
                t_out = last_bar_before(after, stop_ts)
            cache[t] = (max(0.0, sell_at(bars, t_out, mult) - COMMISSION) / (px + COMMISSION) - 1.0
                        if t_out is not None else float("nan"))
        rets.append(cache[t])
    r = np.array(rets)
    r = r[np.isfinite(r)]
    if not len(r):
        return None
    return {"his": his["ret"], "rand": float(r.mean()), "diff": his["ret"] - float(r.mean())}


# ---------------------------------------------------------------------------------------------------
# statistics
# ---------------------------------------------------------------------------------------------------
def week_key(d: date) -> str:
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def cluster_t(x: np.ndarray, groups: np.ndarray) -> Tuple[float, float]:
    n = len(x)
    if n < 3:
        return (float(np.mean(x)) if n else float("nan")), float("nan")
    m = float(np.mean(x))
    dev = pd.Series(x - m).groupby(groups).sum().to_numpy()
    g = len(dev)
    se = math.sqrt(float((dev ** 2).sum()) * g / max(g - 1, 1)) / n
    return m, (m / se if se > 0 else float("nan"))


def describe(rets: np.ndarray, weeks: np.ndarray, seed: int = 7) -> dict:
    if not len(rets):
        return {"n": 0}
    m, t = cluster_t(rets, weeks)
    pos, neg = rets[rets > 0].sum(), -rets[rets < 0].sum()
    uw = np.unique(weeks)
    by = {w: rets[weeks == w] for w in uw}
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(4000):
        pick = rng.choice(uw, size=len(uw), replace=True)
        boots.append(np.concatenate([by[w] for w in pick]).mean())
    srt = np.sort(rets)
    se = abs(m / t) if t and np.isfinite(t) and t != 0 else float("nan")
    return {"n": len(rets), "win": float((rets > 0).mean()), "pf": float(pos / neg) if neg > 0 else float("inf"),
            "mean": m, "t": t, "median": float(np.median(rets)), "worst": float(srt[0]),
            "ci": (float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))),
            "mean_ex_top3": float(srt[:-3].mean()) if len(srt) > 3 else float("nan"),
            "mde": (PASS_T + 0.84) * se}


def fmt(d: dict) -> str:
    if not d.get("n"):
        return "n 0"
    return (f"n {d['n']:4d}  win {100 * d['win']:5.1f}%  PF {d['pf']:5.2f}  mean {100 * d['mean']:+6.1f}%  "
            f"t {d['t']:+5.2f}  median {100 * d['median']:+6.1f}%  worst {100 * d['worst']:+6.1f}%  "
            f"95% CI [{100 * d['ci'][0]:+.1f}%, {100 * d['ci'][1]:+.1f}%]  ex-top3 {100 * d['mean_ex_top3']:+.1f}%")


# ---------------------------------------------------------------------------------------------------
# data access
# ---------------------------------------------------------------------------------------------------
def load_opt(contract: str, day: str) -> Optional[pd.DataFrame]:
    from backtest.fetch_massive_options import load_bars
    p = os.path.join(OPT_DIR, f"{contract.replace(':', '_')}_{day}.json")
    return load_bars(p) if os.path.exists(p) else None


_STK: Dict[str, pd.DataFrame] = {}


def qqq_close(day: str) -> Optional[pd.Timestamp]:
    """Last regular-session minute bar start + 1 min for the day (detects early closes)."""
    from backtest.fetch_massive_options import load_bars
    ym = day[:7]
    if ym not in _STK:
        p = os.path.join(STK_DIR, f"QQQ_{ym}.json")
        _STK[ym] = load_bars(p) if os.path.exists(p) else pd.DataFrame()
    b = _STK[ym]
    if b.empty:
        return None
    d = b[(b.index.strftime("%Y-%m-%d") == day)]
    rth = d[(d.index.time >= OPEN_T) & (d.index.time < time(16, 0))]
    return rth.index[-1] + pd.Timedelta(minutes=1) if len(rth) else None


# ---------------------------------------------------------------------------------------------------
# self-tests on synthetic bars
# ---------------------------------------------------------------------------------------------------
def synth(day: str, prices: Dict[str, Tuple[float, float, float, float]]) -> pd.DataFrame:
    rows = []
    for hm, (o, h, l, c) in prices.items():
        rows.append({"start": pd.Timestamp(f"{day} {hm}").tz_localize(NY), "o": o, "h": h, "l": l, "c": c,
                     "v": 100, "vw": (o + c) / 2})
    return pd.DataFrame(rows).set_index("start")


def selftest() -> int:
    ok = True

    def check(name: str, cond: bool) -> None:
        nonlocal ok
        ok &= bool(cond)
        print(f"{'PASS' if cond else 'FAIL'}  {name}")

    day = "2025-09-16"
    flat = {f"10:{m:02d}": (1.0, 1.0, 1.0, 1.0) for m in range(0, 60)}
    flat.update({f"11:{m:02d}": (1.0, 1.0, 1.0, 1.0) for m in range(0, 60)})
    b = synth(day, flat)
    stop = session_stop(date(2025, 9, 16), None)
    u = lambda hm: pd.Timestamp(f"{day} {hm}").tz_localize(NY).tz_convert("UTC").isoformat()

    check("fill bar >= 30 s after the post (10:00:15 -> 10:01)", first_bar(b, pd.Timestamp(f"{day} 10:00:15").tz_localize(NY)).strftime("%H:%M") == "10:01")
    check("fill bar >= 30 s after the post (10:00:45 -> 10:02)", first_bar(b, pd.Timestamp(f"{day} 10:00:45").tz_localize(NY)).strftime("%H:%M") == "10:02")
    bo = synth(day, {"09:30": (1, 1, 1, 1), "09:31": (1, 1, 1, 1)})
    check("never the 09:30 opening print", first_bar(bo, pd.Timestamp(f"{day} 09:29:50").tz_localize(NY)).strftime("%H:%M") == "09:31")
    gap = synth(day, {"10:00": (1, 1, 1, 1), "10:06": (1, 1, 1, 1)})
    check("no bar within 3 minutes -> unfillable", replay({"announce_utc": u("10:00:05"), "events": []}, gap, stop)["status"] == "unfillable")
    check("half-spread floor $0.01 and 2 %", half_spread(0.2, pd.Timestamp(f"{day} 11:00").tz_localize(NY)) == 0.01
          and abs(half_spread(2.0, pd.Timestamp(f"{day} 11:00").tz_localize(NY)) - 0.04) < 1e-12)
    check("half-spread doubled 09:30-09:45", abs(half_spread(1.0, pd.Timestamp(f"{day} 09:40").tz_localize(NY)) - 0.04) < 1e-12)

    # planted trade: entry at 1.00 (10:01 bar), trim at 1.50, exit at 2.00
    p = dict(flat)
    p.update({f"10:{m:02d}": (1.5, 1.5, 1.5, 1.5) for m in range(10, 20)})
    p.update({f"10:{m:02d}": (2.0, 2.0, 2.0, 2.0) for m in range(20, 60)})
    bp = synth(day, p)
    tr = {"announce_utc": u("10:00:10"), "events": [{"type": "TRIM_EXECUTED", "utc": u("10:12:00")},
                                                    {"type": "EXIT", "utc": u("10:25:00")}]}
    r = replay(tr, bp, stop)
    px_in = 1.0 + 0.02
    exp = (0.5 * (1.5 - 0.03 - COMMISSION) + 0.5 * (2.0 - 0.04 - COMMISSION)) / (px_in + COMMISSION) - 1
    check("planted half-trim + exit P&L exact", r["status"] == "ok" and abs(r["ret"] - exp) < 1e-12)
    rf = replay(tr, bp, stop, trim="full")
    check("full exit at trim (secondary)", abs(rf["ret"] - ((1.5 - 0.03 - COMMISSION) / (px_in + COMMISSION) - 1)) < 1e-12)

    # BE stop: entry 1.00 -> rises to 1.5 -> BE posted 10:12 -> later a trade prints at 0.9
    q = dict(flat)
    q.update({f"10:{m:02d}": (1.5, 1.5, 1.5, 1.5) for m in range(5, 30)})
    q.update({"10:30": (1.1, 1.1, 0.9, 0.95)})
    q.update({f"10:{m:02d}": (0.95, 0.95, 0.95, 0.95) for m in range(31, 60)})
    bq = synth(day, q)
    trb = {"announce_utc": u("10:00:10"), "events": [{"type": "BE_STOP", "utc": u("10:12:00")}]}
    rb = replay(trb, bq, stop)
    stop_px = px_in
    exp_b = (min(1.1, stop_px) - half_spread(min(1.1, stop_px), pd.Timestamp(f"{day} 10:30").tz_localize(NY)) - COMMISSION) / (px_in + COMMISSION) - 1
    check("BE stop fills at min(open, entry) - half-spread on the first touch", rb["exit_reasons"] == "BE stop" and abs(rb["ret"] - exp_b) < 1e-12)
    check("a BE exit is a loss after costs", rb["ret"] < 0)
    r2 = dict(flat)
    r2.update({f"10:{m:02d}": (0.8, 0.8, 0.8, 0.8) for m in range(5, 60)})
    trc = {"announce_utc": u("10:00:10"), "events": [{"type": "BE_STOP", "utc": u("10:10:00")}]}
    check("BE posted while already below entry exits at the next fill", replay(trc, synth(day, r2), stop)["exit_reasons"] == "BE (already below)")

    # time stop and early close
    s = {f"{h}:{m:02d}": (1.0, 1.0, 1.0, 1.0) for h in (14, 15) for m in range(0, 60)}
    bs = synth(day, s)
    rt = replay({"announce_utc": u("14:00:10"), "events": []}, bs, stop)
    check("no cue -> time stop at 15:50", rt["exit_reasons"] == "time stop" and abs(rt["hold_min"] - 109) < 1e-9)
    early = session_stop(date(2025, 11, 28), pd.Timestamp("2025-11-28 13:00").tz_localize(NY))
    check("early close -> time stop 12:50", early.strftime("%H:%M") == "12:50")

    # edits: an edited announcement is known only at the edit time
    tre = {"announce_utc": u("10:00:10"), "announce_edited_utc": u("10:20:10"), "events": []}
    check("edited post fills after the edit", replay(tre, bp, stop)["entry_px"] == 2.0 + 0.04)

    # truncation guard: deleting bars after the exit changes nothing
    r_full = replay(tr, bp, stop)
    r_trunc = replay(tr, bp[bp.index <= pd.Timestamp(f"{day} 10:26").tz_localize(NY)], stop)
    check("truncation guard (no lookahead)", abs(r_full["ret"] - r_trunc["ret"]) < 1e-12)

    # null: deterministic, and a flat market gives his == random
    nd = null_diff({"announce_utc": u("10:00:10"), "events": []}, b, stop, 1.0, seed=1)
    check("null on a flat market: his entry == random entries", nd is not None and abs(nd["diff"]) < 1e-12)
    check("week key is (ISO year, week)", week_key(date(2026, 1, 1)) == "2026-W01" and week_key(date(2024, 12, 30)) == "2025-W01")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.report:
        from backtest.options_signal_report import report
        return report()
    return 0


if __name__ == "__main__":
    sys.path.insert(0, ".")
    sys.exit(main())
