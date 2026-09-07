"""
v0.15-exp — ComLucro "Two/Three-Candle Liquidity Grab Reversal", BTC 1H.

Mechanized spec — pre-registered in DEVLOG BEFORE any run:
- External-liquidity context: the sweep candle must take out the rolling
  K=24-bar extreme (ending before C1), not merely C1's wick.
- 2-candle (bullish): l2 < l1, l2 < K-low, close2 > high1 -> confirmed
  at C2 close. 3-candle (bullish): l2 < l1, l2 < K-low, C2 fails the
  2-candle close, then l3 >= l2 and close3 > max(open2, close2).
  Bearish mirrored. 2-candle takes precedence when both match.
- Enter next bar open (taker+slip). Stop at the sweep extreme.
  TP1 = 1R on HALF the position, TP2 = 2R on the rest; stop unchanged
  after TP1 (no breakeven move stated in the video). Stop-first
  conservative; no targets on the entry bar; one position at a time.
- 1% equity risk, 10x cap, (0.055% taker + 0.01% slip) on both legs.
"""

import argparse
import sys
from typing import Optional

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from backtest.data import load_cached_1m, resample_ohlcv  # noqa: E402

K = 24
TAKER, SLIP = 0.00055, 0.0001
COST = TAKER + SLIP
RISK_PCT, MAX_LEV = 1.0, 10.0


def simulate(df1h: pd.DataFrame, start_bal: float = 10_000.0) -> dict:
    o = df1h["open"].to_numpy(); h = df1h["high"].to_numpy()
    l = df1h["low"].to_numpy(); c = df1h["close"].to_numpy()
    idx = df1h.index
    rl = pd.Series(l).rolling(K).min().shift(1).to_numpy()  # K-bar low before bar i
    rh = pd.Series(h).rolling(K).max().shift(1).to_numpy()

    bal = start_bal
    pos: Optional[dict] = None
    pending: Optional[tuple] = None  # (dr, stop, kind)
    trades = []
    peak = start_bal; max_dd = 0.0

    for i in range(K + 3, len(df1h)):
        # 1) fill pending entry at this bar's open
        if pos is None and pending is not None:
            dr, stop, kind = pending
            e = o[i] * (1 + dr * SLIP)
            dist = dr * (e - stop)
            if dist > 0:
                q = min(bal * RISK_PCT / 100.0 / dist, bal * MAX_LEV / e)
                pos = {"dr": dr, "e": e, "stop": stop,
                       "tp1": e + dr * dist, "tp2": e + dr * 2.0 * dist,
                       "q1": q / 2.0, "q2": q / 2.0, "half_done": False,
                       "entry_bar": i, "kind": kind,
                       "realized": -e * q * COST}  # entry leg cost, full size
            pending = None

        # 2) manage position (stop-first; targets banned on the entry bar)
        if pos is not None:
            dr = pos["dr"]
            hit_stop = l[i] <= pos["stop"] if dr > 0 else h[i] >= pos["stop"]
            if hit_stop:
                px = pos["stop"]
                rem = pos["q2"] + (0.0 if pos["half_done"] else pos["q1"])
                pos["realized"] += dr * (px - pos["e"]) * rem - px * rem * COST
                bal += pos["realized"]
                reason = "TP1+STOP" if pos["half_done"] else "STOP"
                trades.append({"ts": idx[i], "dir": "LONG" if dr > 0 else "SHORT",
                               "kind": pos["kind"], "net": pos["realized"], "reason": reason})
                pos = None
            elif i > pos["entry_bar"]:
                if not pos["half_done"]:
                    hit1 = h[i] >= pos["tp1"] if dr > 0 else l[i] <= pos["tp1"]
                    if hit1:
                        px = pos["tp1"]
                        pos["realized"] += dr * (px - pos["e"]) * pos["q1"] - px * pos["q1"] * COST
                        pos["half_done"] = True
                if pos is not None and pos["half_done"]:
                    hit2 = h[i] >= pos["tp2"] if dr > 0 else l[i] <= pos["tp2"]
                    if hit2:
                        px = pos["tp2"]
                        pos["realized"] += dr * (px - pos["e"]) * pos["q2"] - px * pos["q2"] * COST
                        bal += pos["realized"]
                        trades.append({"ts": idx[i], "dir": "LONG" if dr > 0 else "SHORT",
                                       "kind": pos["kind"], "net": pos["realized"],
                                       "reason": "TP1+TP2"})
                        pos = None

        # 3) pattern detection on the just-closed bar (flat only)
        if pos is None and pending is None and not np.isnan(rl[i - 1]) and not np.isnan(rl[i - 2]):
            # 2-candle: C1 = i-1, C2 = i
            if l[i] < l[i - 1] and l[i] < rl[i - 1] and c[i] > h[i - 1]:
                pending = (1, l[i], "2C")
            elif h[i] > h[i - 1] and h[i] > rh[i - 1] and c[i] < l[i - 1]:
                pending = (-1, h[i], "2C")
            # 3-candle: C1 = i-2, C2 = i-1, C3 = i
            elif (l[i - 1] < l[i - 2] and l[i - 1] < rl[i - 2]
                  and not c[i - 1] > h[i - 2]
                  and l[i] >= l[i - 1] and c[i] > max(o[i - 1], c[i - 1])):
                pending = (1, l[i - 1], "3C")
            elif (h[i - 1] > h[i - 2] and h[i - 1] > rh[i - 2]
                  and not c[i - 1] < l[i - 2]
                  and h[i] <= h[i - 1] and c[i] < min(o[i - 1], c[i - 1])):
                pending = (-1, h[i - 1], "3C")

        # 4) equity tracking
        m2m = bal
        if pos is not None:
            rem = pos["q2"] + (0.0 if pos["half_done"] else pos["q1"])
            m2m += pos["realized"] + pos["dr"] * (c[i] - pos["e"]) * rem
        peak = max(peak, m2m); max_dd = max(max_dd, (peak - m2m) / peak)

    t = pd.DataFrame(trades)
    if t.empty:
        return {"n": 0}
    wins = t[t.net > 0]; losses = t[t.net <= 0]
    gw = wins.net.sum(); gl = -losses.net.sum()
    t["y"] = t.ts.dt.year
    days = max((t.ts.max() - t.ts.min()).days, 1)
    return {
        "n": len(t), "win_pct": round(100 * len(wins) / len(t), 1),
        "net": round(t.net.sum(), 0), "end_bal": round(bal, 0),
        "pf": round(gw / gl, 2) if gl > 0 else float("inf"),
        "max_dd_pct": round(100 * max_dd, 1),
        "trades_per_week": round(7 * len(t) / days, 2),
        "by_kind": t.groupby("kind")["net"].agg(["count", "sum"]).round(0)
                    .to_dict(orient="index"),
        "reasons": t.reason.value_counts().to_dict(),
        "per_year": {y: round(g.net.sum(), 0) for y, g in t.groupby("y")},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--explore-cache", default="backtest/data_cache/local/btcusd_1m_2023_2026.csv.gz")
    ap.add_argument("--holdout-cache", default="backtest/data_cache/local/btcusd_1m_2019_2022.csv.gz")
    args = ap.parse_args()

    for name, cache in [("EXPLORE", args.explore_cache), ("HOLDOUT", args.holdout_cache)]:
        df = resample_ohlcv(load_cached_1m(cache), "1h")
        print(f"{name} {df.index.min().date()} -> {df.index.max().date()} ({len(df)} bars)")
        if name == "HOLDOUT":
            print("  (judged per pre-registration: explore n>=100 & net>0 gates adoption, printed regardless)")
        print(" ", simulate(df))


if __name__ == "__main__":
    main()
