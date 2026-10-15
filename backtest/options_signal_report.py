"""
v0.35-audit report: the pre-registered verdicts, secondaries, honesty tests and data checks.

Prints AGGREGATES ONLY (the repository and its logs are public-safe); per-trade results are written to
backtest/data_cache/local/discord/v035/results_per_trade.csv (gitignored).

  python3 backtest/options_signal_audit.py --report
"""

import json
import os
import re
from datetime import date, datetime, time
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from backtest.fetch_massive_options import load_bars, option_ticker
from backtest.options_signal_audit import (HOLD, LOCAL, NY, OPEN_T, OPT_DIR, PASS_T, STK_DIR, TRADES, COMMISSION,
                                           cluster_t, describe, fmt, half_spread, null_diff, qqq_close, replay,
                                           session_stop, ts_of, week_key)

V035 = f"{LOCAL}/discord/v035"
STRIKE_BAND = 0.03


def contract_of(t: dict) -> str:
    return option_ticker("QQQ", date.fromisoformat(t["date"]), t["cp"], t["strike"])


def opt_bars(t: dict) -> Optional[pd.DataFrame]:
    p = os.path.join(OPT_DIR, f"{contract_of(t).replace(':', '_')}_{t['date']}.json")
    return load_bars(p) if os.path.exists(p) else None


_QQQ: Dict[str, pd.DataFrame] = {}


def qqq_day(day: str) -> pd.DataFrame:
    ym = day[:7]
    if ym not in _QQQ:
        p = os.path.join(STK_DIR, f"QQQ_{ym}.json")
        _QQQ[ym] = load_bars(p) if os.path.exists(p) else pd.DataFrame()
    b = _QQQ[ym]
    return b[b.index.strftime("%Y-%m-%d") == day] if not b.empty else b


def qqq_at(day: str, ts: pd.Timestamp) -> Optional[float]:
    b = qqq_day(day)
    prev = b[b.index <= ts.floor("min")]
    return float(prev["c"].iloc[-1]) if len(prev) else None


def intrinsic(cp: str, strike: float, s: float) -> float:
    return max(0.0, s - strike) if cp == "C" else max(0.0, strike - s)


def report() -> int:
    trades = [json.loads(x) for x in open(TRADES, encoding="utf-8") if x.strip()]
    msgs = [json.loads(x) for x in open(f"{V035}/caller_messages.jsonl", encoding="utf-8") if x.strip()]
    print(f"frozen trades: {len(trades)}")
    excl = {"no option bars": 0, "no QQQ bars": 0, "strike outside 3 %": 0}
    rows = []
    for t in trades:
        b = opt_bars(t)
        if b is None or b.empty:
            excl["no option bars"] += 1
            continue
        qd = qqq_day(t["date"])
        if qd.empty:
            excl["no QQQ bars"] += 1
            continue
        post = ts_of(t, "announce", True)
        s0 = qqq_at(t["date"], post)
        if s0 is None or abs(t["strike"] / s0 - 1) > STRIKE_BAND:
            excl["strike outside 3 %"] += 1
            continue
        close_ts = qqq_close(t["date"])
        stop = session_stop(date.fromisoformat(t["date"]), close_ts)
        s_close = qqq_at(t["date"], (close_ts or stop) - pd.Timedelta(minutes=1))
        rows.append((t, b, stop, s_close))
    print("excluded (counted, not scored):", excl)
    print(f"scored trades: {len(rows)}")

    def run(label: str, **kw) -> pd.DataFrame:
        out = []
        drop_edited = kw.get("use_edits") is False
        for t, b, stop, s_close in rows:
            if drop_edited:
                if t.get("announce_edited_utc"):
                    continue
                t = dict(t, events=[e for e in t["events"] if not e.get("edited_utc")])
            r = replay(t, b, stop, **kw)
            out.append({"trade_id": t["trade_id"], "date": t["date"], "kind": t["kind"], "status": r["status"],
                        "ret": r.get("ret"), "reasons": r.get("exit_reasons"), "hold": r.get("hold_min"),
                        "entry_px": r.get("entry_px")})
        df = pd.DataFrame(out)
        return df

    def show(label: str, df: pd.DataFrame) -> dict:
        ok = df[df["status"] == "ok"]
        rets = ok["ret"].to_numpy(dtype=float)
        weeks = np.array([week_key(date.fromisoformat(d)) for d in ok["date"]])
        d = describe(rets, weeks)
        unf = int((df["status"] == "unfillable").sum())
        print(f"  {label:44s} {fmt(d)}  unfillable {unf}")
        return d

    print("\n" + "=" * 110 + "\nPRIMARY (literal follower) and STRESS\n" + "=" * 110)
    prim = run("primary")
    d1 = show("primary (half at trim, BE touch, 15:50 stop)", prim)
    stress = run("stress", mult=2.0)
    d1s = show("stress: double spread", stress)
    ok = prim[prim["status"] == "ok"].copy()
    ok["year"] = ok["date"].str[:4]
    for k in ("live", "after"):
        show(f"  {k} entries", prim[prim["kind"] == k])
    for y, g in ok.groupby("year"):
        show(f"  {y}", g)
    cost_share = []
    for t, b, stop, _ in rows:
        r = prim[prim["trade_id"] == t["trade_id"]]
        if len(r) and r["status"].iloc[0] == "ok":
            px = float(r["entry_px"].iloc[0])
            cost_share.append((2 * half_spread(px, pd.Timestamp("2025-01-02 11:00").tz_localize(NY)) + 2 * COMMISSION) / px)
    if cost_share:
        print(f"  round-trip cost as a share of premium: median {100 * np.median(cost_share):.1f}%, "
              f"mean {100 * np.mean(cost_share):.1f}%")
    print("  exit reasons:", prim[prim["status"] == "ok"]["reasons"].value_counts().head(8).to_dict())

    print("\n" + "=" * 110 + "\nSECONDARIES (labelled; cannot change a verdict)\n" + "=" * 110)
    show("full exit at the first trim", run("s1", trim="full"))
    show("exit at his first % claim", run("s2", exit_on_claim=True))
    fh = run("s3", fixed_hold=HOLD)
    dfh = show("fixed 30-minute hold", fh)
    show("BE stop triggered on the close", run("s5", be="close"))
    show("edited messages excluded", run("s6", use_edits=False))
    exp_rows = []
    for t, b, stop, s_close in rows:
        if s_close is None:
            continue
        r = replay(t, b, stop, expiry_value=intrinsic(t["cp"], t["strike"], s_close))
        exp_rows.append({"trade_id": t["trade_id"], "date": t["date"], "kind": t["kind"], "status": r["status"],
                         "ret": r.get("ret")})
    show("hold to expiry at intrinsic value", pd.DataFrame(exp_rows))
    print("  latency curve (entry later than the primary 30 s):")
    show("    next bar's open", run("lat0", entry_lag=pd.Timedelta(seconds=0), entry_on_open=True))
    show("    +2 min", run("lat2", entry_lag=pd.Timedelta(minutes=2)))
    show("    +5 min", run("lat5", entry_lag=pd.Timedelta(minutes=5)))

    print("\n" + "=" * 110 + "\nV2: do his entries beat random entries on the same contract-day? (fixed 30-min hold)\n" + "=" * 110)
    diffs, his, rnd, wk = [], [], [], []
    for i, (t, b, stop, _) in enumerate(rows):
        nd = null_diff(t, b, stop, 1.0, seed=1000 + i)
        if nd is None:
            continue
        diffs.append(nd["diff"]); his.append(nd["his"]); rnd.append(nd["rand"])
        wk.append(week_key(date.fromisoformat(t["date"])))
    diffs_a = np.array(diffs)
    m, tt = cluster_t(diffs_a, np.array(wk)) if len(diffs_a) else (float("nan"), float("nan"))
    print(f"  trades with a null: {len(diffs)}; his mean {100 * np.mean(his):+.1f}%, random mean {100 * np.mean(rnd):+.1f}%, "
          f"difference {100 * m:+.1f}% (t {tt:+.2f})")
    v2 = bool(len(diffs_a) and m > 0 and tt >= PASS_T)
    if dfh.get("n") and d1.get("n"):
        print(f"  value of his exits = primary − fixed hold = {100 * (d1['mean'] - dfh['mean']):+.1f}% per trade")

    print("\n" + "=" * 110 + "\nHONESTY TESTS (no fill assumptions)\n" + "=" * 110)
    prev_time = {}
    for d in sorted({m['date'] for m in msgs}):
        day_m = sorted((m for m in msgs if m["date"] == d), key=lambda m: m["posted_utc"])
        for a, bm in zip(day_m, day_m[1:]):
            prev_time[bm["posted_utc"]] = a["posted_utc"]
    n_entry, imp_open, imp_prev = 0, 0, 0
    n_claim, imp_claim = 0, 0
    for t, b, stop, _ in rows:
        day_open = pd.Timestamp(datetime.combine(date.fromisoformat(t["date"]), OPEN_T)).tz_localize(NY)
        if t.get("stated_entry"):
            st_utc = t.get("stated_entry_utc") or t["announce_utc"]
            st = pd.Timestamp(st_utc).tz_convert(NY)
            w = b[(b.index >= day_open) & (b.index <= st.floor("min"))]
            if len(w):
                n_entry += 1
                px = float(t["stated_entry"])
                tol = max(0.01, 0.02 * px)
                imp_open += px < float(w["l"].min()) - tol
                pv = prev_time.get(st_utc)
                if pv:
                    w2 = b[(b.index >= pd.Timestamp(pv).tz_convert(NY).floor("min")) & (b.index <= st.floor("min"))]
                    imp_prev += bool(len(w2)) and px < float(w2["l"].min()) - tol
        for e in t["events"]:
            if e["type"] != "CLAIM" or e.get("pct") is None:
                continue
            try:
                pct = float(e["pct"])
            except (TypeError, ValueError):
                continue
            if pct <= 0:
                continue
            ct = pd.Timestamp(e["utc"]).tz_convert(NY)
            w = b[(b.index >= day_open) & (b.index <= ct.floor("min"))]
            if len(w) < 2:
                continue
            n_claim += 1
            if t.get("stated_entry"):
                best = float(w["h"].max()) / float(t["stated_entry"]) - 1
            else:
                lows = w["l"].cummin().to_numpy()
                best = float(np.max(w["h"].to_numpy() / np.maximum(lows, 0.01))) - 1
            imp_claim += pct / 100 > best + 0.02
    print(f"  stated entry prices checked: {n_entry}; below every trade since the open: {imp_open}; "
          f"below every trade since his previous message: {imp_prev}")
    print(f"  % gain claims checked: {n_claim}; higher than the market ever allowed: {imp_claim}")
    recaps = [m for m in msgs if re.search(r"\b(\d{1,2})\s?/\s?(\d{1,2})\b", m["text"]) and
              re.search(r"week|today|day", m["text"], re.I)]
    perfect_weeks = set()
    for m in recaps:
        a, bb = map(int, re.search(r"\b(\d{1,2})\s?/\s?(\d{1,2})\b", m["text"]).groups())
        if a == bb and a > 0:
            perfect_weeks.add(week_key(date.fromisoformat(m["date"])))
    pw = ok[ok["date"].map(lambda d: week_key(date.fromisoformat(d))).isin(perfect_weeks)]
    print(f"  weeks he called perfect: {len(perfect_weeks)}; follower trades those weeks: {len(pw)}, "
          f"of which losers: {int((pw['ret'] < 0).sum())}")

    print("\n" + "=" * 110 + "\nVERDICTS (pre-registered; both must hold at the stress level)\n" + "=" * 110)
    v1 = bool(d1.get("n") and d1["mean"] > 0 and d1["t"] >= PASS_T and d1s["mean"] > 0 and d1s["t"] >= PASS_T)
    print(f"  V1 follower net > 0: {'PASS' if v1 else 'FAIL'}  (primary mean {100 * d1.get('mean', float('nan')):+.1f}%, "
          f"t {d1.get('t', float('nan')):+.2f}; stress mean {100 * d1s.get('mean', float('nan')):+.1f}%, t {d1s.get('t', float('nan')):+.2f})")
    print(f"  V2 his entries beat chance: {'PASS' if v2 else 'FAIL'}  (difference {100 * m:+.1f}%, t {tt:+.2f})")
    if d1.get("n"):
        print(f"  smallest mean effect this sample could detect at t {PASS_T}: about {100 * d1['mde']:.1f}% per trade")
    prim.to_csv(f"{V035}/results_per_trade.csv", index=False)
    print("OPTIONS_REPORT_DONE")
    return 0
