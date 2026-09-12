"""
v0.16-exp — First Candle Range (FCR) breakout + retest, fixed 1:3.

Mechanized spec — pre-registered in DEVLOG BEFORE any run:
- FCR = max high / min low of the five 1m bars 9:30-9:34 NY.
- Breakout: first 1m CLOSE outside the range between 9:35 and 10:29
  (above High -> long bias, below Low -> short bias). One attempt/day.
- Retest (short case; long mirrored): within RETEST_WINDOW bars after
  the breakout, the first bar whose high touches the Low while its close
  stays below it. A bar that first CLOSES back inside the range voids
  the day (failed breakout).
- Entry: next bar open after the retest bar (taker + slip). Stop at the
  retest bar's extreme (structure stop, no buffer). Target = 3R.
  Stop-first conservative, no same-bar target on the entry bar,
  force-flat 16:00, max one trade per day.
- 1% equity risk, 10x notional cap, (taker 0.002% + slip 0.005%) per
  side on both legs — the house futures-CFD cost model.
"""

import argparse
import sys
from typing import Optional

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from backtest.data import load_cached_1m  # noqa: E402

TAKER, SLIP = 0.00002, 0.00005
COST = TAKER + SLIP
RISK_PCT, MAX_LEV = 1.0, 10.0
RR = 3.0
BREAKOUT_DEADLINE = 10 * 60 + 30   # breakout close must occur before 10:30 NY
RETEST_WINDOW = 30                  # bars after the breakout to find the retest
SESSION_START, SESSION_END = 9 * 60 + 30, 16 * 60


def simulate(df1m: pd.DataFrame, start_bal: float = 10_000.0) -> dict:
    idx = df1m.index
    mod = (idx.hour * 60 + idx.minute).to_numpy()
    day = idx.normalize()
    o = df1m["open"].to_numpy(); h = df1m["high"].to_numpy()
    l = df1m["low"].to_numpy(); c = df1m["close"].to_numpy()

    bal = start_bal
    trades = []
    peak = start_bal; max_dd = 0.0

    for _, day_pos in pd.Series(np.arange(len(df1m)), index=day).groupby(level=0):
        p = day_pos.to_numpy()
        pm = mod[p]
        sess = p[(pm >= SESSION_START) & (pm < SESSION_END)]
        if len(sess) < 60:
            continue
        fcr_bars = p[(pm >= SESSION_START) & (pm < SESSION_START + 5)]
        if len(fcr_bars) < 5:
            continue
        fcr_high, fcr_low = h[fcr_bars].max(), l[fcr_bars].min()

        state = "WAIT_BREAK"   # -> WAIT_RETEST -> IN_POS / DONE
        dr = 0; break_n = -1; pos: Optional[dict] = None

        for n_j, j in enumerate(sess):
            last_bar = n_j == len(sess) - 1
            m = mod[j]

            if pos is not None:
                hit_stop = h[j] >= pos["stop"] if dr < 0 else l[j] <= pos["stop"]
                hit_tgt = (l[j] <= pos["tgt"] if dr < 0 else h[j] >= pos["tgt"]) \
                    and j > pos["entry_bar"]
                px = reason = None
                if hit_stop:
                    px, reason = pos["stop"], "STOP"
                elif hit_tgt:
                    px, reason = pos["tgt"], "TP"
                elif last_bar:
                    px, reason = c[j], "EOD"
                if px is not None:
                    net = dr * (px - pos["e"]) * pos["q"] - (pos["e"] + px) * pos["q"] * COST
                    bal += net
                    trades.append({"ts": idx[j], "dir": "LONG" if dr > 0 else "SHORT",
                                   "net": net, "reason": reason,
                                   "risk_pct": pos["risk_pct"], "cost_r": pos["cost_r"]})
                    pos = None
                    state = "DONE"

            elif state == "WAIT_BREAK" and SESSION_START + 5 <= m < BREAKOUT_DEADLINE:
                if c[j] > fcr_high:
                    dr, state, break_n = 1, "WAIT_RETEST", n_j
                elif c[j] < fcr_low:
                    dr, state, break_n = -1, "WAIT_RETEST", n_j

            elif state == "WAIT_RETEST":
                level = fcr_low if dr < 0 else fcr_high
                closed_inside = c[j] > level if dr < 0 else c[j] < level
                touched = h[j] >= level if dr < 0 else l[j] <= level
                if closed_inside:
                    state = "DONE"               # failed breakout
                elif n_j - break_n > RETEST_WINDOW:
                    state = "DONE"               # no retest in time
                elif touched and n_j + 1 < len(sess):
                    jj = sess[n_j + 1]
                    e = o[jj] * (1 + dr * SLIP)
                    stop = h[j] if dr < 0 else l[j]
                    dist = dr * (e - stop)
                    if dist > 0:
                        q = min(bal * RISK_PCT / 100.0 / dist, bal * MAX_LEV / e)
                        tgt = e + dr * RR * dist
                        # Bracket invariants: stop adverse, target favorable.
                        # A sign slip here produced a plausible-looking -100%
                        # on the first run of this engine.
                        assert dr * (e - stop) > 0 and dr * (tgt - e) > 0, "inverted bracket"
                        pos = {"dr": dr, "e": e, "stop": stop, "tgt": tgt,
                               "q": q, "entry_bar": jj,
                               "risk_pct": 100 * dist / e,
                               "cost_r": (2 * e * COST) / dist}
                    else:
                        state = "DONE"           # fill already beyond the stop

            m2m = bal + (dr * (c[j] - pos["e"]) * pos["q"] if pos else 0.0)
            peak = max(peak, m2m); max_dd = max(max_dd, (peak - m2m) / peak)

    t = pd.DataFrame(trades)
    if t.empty:
        return {"n": 0}
    wins = t[t.net > 0]; losses = t[t.net <= 0]
    gw = wins.net.sum(); gl = -losses.net.sum()
    t["y"] = t.ts.dt.year
    return {
        "n": len(t), "win_pct": round(100 * len(wins) / len(t), 1),
        "net": round(t.net.sum(), 0), "end_bal": round(bal, 0),
        "pf": round(gw / gl, 2) if gl > 0 else float("inf"),
        "max_dd_pct": round(100 * max_dd, 1),
        "avg_stop_pct_of_price": round(t.risk_pct.mean(), 3),
        "avg_cost_per_R": round(t.cost_r.mean(), 3),
        "reasons": t.reason.value_counts().to_dict(),
        "by_dir": t.groupby("dir")["net"].agg(["count", "sum"]).round(0).to_dict(orient="index"),
        "per_year": {y: round(g.net.sum(), 0) for y, g in t.groupby("y")},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="backtest/data_cache/local/nas100_1m_2015_2020.csv.gz")
    ap.add_argument("--explore-end", default="2018-01-01")
    args = ap.parse_args()

    df = load_cached_1m(args.cache)
    cut = pd.Timestamp(args.explore_end, tz="America/New_York")
    for name, seg in [("EXPLORE", df[df.index < cut]), ("HOLDOUT", df[df.index >= cut])]:
        print(f"{name} {seg.index.min().date()} -> {seg.index.max().date()} ({len(seg)} bars)")
        if name == "HOLDOUT":
            print("  (judged per pre-registration: explore n>=100 & net>0 gates adoption, printed regardless)")
        print(" ", simulate(seg))


if __name__ == "__main__":
    main()
