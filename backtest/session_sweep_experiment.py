"""
v0.14-exp — Session-sweep 1m FVG reversal ("wake up at 9am NY" reel).

Mechanized spec — pre-registered in DEVLOG BEFORE any run:
- Sessions (NY): Asia 18:00-02:00, London 02:00-08:00; levels frozen 09:00.
- Sweeps counted 09:00-11:59. First breach of an unused level opens a
  reversal context (direction against the sweep, anchor = running sweep
  extreme, 30-bar expiry). Every level is consumed on its first breach.
  A bar breaching both sides opens nothing.
- Entry: first 1m FVG against the sweep whose first candle is no earlier
  than the sweep bar; enter next bar open. Stop at the sweep extreme,
  target fixed 1:2 on the raw stop distance. Stop-first conservative, no
  same-bar target, gap-skip if the entry fills beyond the stop.
  Force-flat 16:00. One position at a time; one trade per level per day.
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

TAKER, SLIP = 0.00002, 0.00005     # fractions per side
COST = TAKER + SLIP                # charged on both legs
RISK_PCT, MAX_LEV = 1.0, 10.0
SWEEP_CUTOFF = 12 * 60             # sweeps counted before 12:00 NY
CTX_EXPIRY = 30                    # bars a sweep context stays alive
MIN_SESSION_BARS = 10


def simulate(df1m: pd.DataFrame, start_bal: float = 10_000.0,
             return_trades: bool = False) -> dict:
    idx = df1m.index
    shifted = idx + pd.Timedelta(hours=6)   # Asia 18:00 maps into its NY day
    sday = shifted.normalize()
    mod = idx.hour * 60 + idx.minute

    o = df1m["open"].to_numpy(); h = df1m["high"].to_numpy()
    l = df1m["low"].to_numpy(); c = df1m["close"].to_numpy()
    smod = shifted.hour * 60 + shifted.minute

    bal = start_bal
    trades = []
    peak = start_bal; max_dd = 0.0

    for day, day_pos in pd.Series(np.arange(len(df1m)), index=sday).groupby(level=0):
        p = day_pos.to_numpy()
        pm = smod[p]
        asia = p[(pm >= 0) & (pm < 8 * 60)]          # real 18:00-02:00
        lond = p[(pm >= 8 * 60) & (pm < 14 * 60)]    # real 02:00-08:00
        ny = p[(pm >= 15 * 60) & (pm < 22 * 60)]     # real 09:00-16:00
        if len(asia) < MIN_SESSION_BARS or len(lond) < MIN_SESSION_BARS or len(ny) < 30:
            continue

        levels = {
            "AH": h[asia].max(), "AL": l[asia].min(),
            "LH": h[lond].max(), "LL": l[lond].min(),
        }
        used = {k: False for k in levels}
        ctx: Optional[dict] = None
        pos: Optional[dict] = None

        for n_j, j in enumerate(ny):
            last_bar = n_j == len(ny) - 1

            # --- manage open position (stop-first; no same-bar target) ---
            if pos is not None:
                dr = pos["dr"]
                hit_stop = l[j] <= pos["stop"] if dr > 0 else h[j] >= pos["stop"]
                hit_tgt = (h[j] >= pos["tgt"] if dr > 0 else l[j] <= pos["tgt"]) \
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
                                   "level": pos["level"], "net": net, "reason": reason})
                    pos = None

            # --- sweep detection (arming gated to < 12:00) ---
            hi_x = [k for k in ("AH", "LH") if not used[k] and h[j] > levels[k]]
            lo_x = [k for k in ("AL", "LL") if not used[k] and l[j] < levels[k]]
            for k in hi_x + lo_x:
                used[k] = True
            if ctx is None and pos is None and mod[j] < SWEEP_CUTOFF:
                if hi_x and not lo_x:
                    ctx = {"dr": -1, "anchor": h[j], "sweep_bar": j,
                           "expiry": n_j + CTX_EXPIRY, "level": hi_x[0]}
                elif lo_x and not hi_x:
                    ctx = {"dr": 1, "anchor": l[j], "sweep_bar": j,
                           "expiry": n_j + CTX_EXPIRY, "level": lo_x[0]}
                # both sides breached on one bar -> nothing armed

            # --- context: update anchor, expire, look for the reversal FVG ---
            if ctx is not None and pos is None:
                dr = ctx["dr"]
                ctx["anchor"] = max(ctx["anchor"], h[j]) if dr < 0 else min(ctx["anchor"], l[j])
                if n_j > ctx["expiry"] or last_bar:
                    ctx = None
                elif j - 2 >= ctx["sweep_bar"]:
                    fvg = h[j] < l[j - 2] if dr < 0 else l[j] > h[j - 2]
                    if fvg:
                        jj = j + 1  # entry bar (next 1m bar)
                        if jj == ny[n_j + 1]:  # stay inside the NY window
                            e = o[jj] * (1 + dr * SLIP)
                            stop = ctx["anchor"]
                            dist = dr * (stop - e) * -1.0  # = |e-stop| when stop is adverse
                            if dist > 0:
                                q = min(bal * RISK_PCT / 100.0 / dist, bal * MAX_LEV / e)
                                tgt = e + dr * 2.0 * dist
                                pos = {"dr": dr, "e": e, "stop": stop, "tgt": tgt,
                                       "q": q, "entry_bar": jj, "level": ctx["level"]}
                        ctx = None  # one shot per context, filled or not

            # --- equity tracking ---
            m2m = bal + (pos["dr"] * (c[j] - pos["e"]) * pos["q"] if pos else 0.0)
            peak = max(peak, m2m); max_dd = max(max_dd, (peak - m2m) / peak)

    t = pd.DataFrame(trades)
    if t.empty:
        return {"n": 0}
    if return_trades:
        return {"n": len(t), "trades": t}
    wins = t[t.net > 0]; losses = t[t.net <= 0]
    gw = wins.net.sum(); gl = -losses.net.sum()
    t["y"] = t.ts.dt.year
    days = max((t.ts.max() - t.ts.min()).days, 1)
    return {
        "n": len(t), "win_pct": round(100 * len(wins) / len(t), 1),
        "net": round(t.net.sum(), 0), "end_bal": round(bal, 0),
        "pf": round(gw / gl, 2) if gl > 0 else float("inf"),
        "max_dd_pct": round(100 * max_dd, 1),
        "trades_per_day": round(len(t) / days, 2),
        "reasons": t.reason.value_counts().to_dict(),
        "by_level": t.groupby("level")["net"].sum().round(0).to_dict(),
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
