"""
v0.12-exp — FVG-wick continuation, 0.3:1 bracket (user-supplied rule).

Mechanized spec (pre-registered in DEVLOG before results):
- 3-candle fair value gap on CLOSED 5m candles; gap stays live for
  MAX_AGE bars and dies if fully traded through.
- Resting limit at the gap's proximal edge (the "wick" fills it),
  direction WITH the gap.
- Bracket: stop 0.3*ATR14, target 1.0*ATR14 (breakeven ~23.1% + costs).
- Maker fee on entry & target (limits), taker + slip on stops; gap-guard.
- 1% equity risk, 10x notional cap, one position, stop-first.
"""

import argparse
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from backtest.data import load_cached_1m, resample_ohlcv  # noqa: E402

MAX_AGE = 20
REJECT_MODE = False
GEOM = "atr03_1"  # atr03_1 | atr1_03 | wick03
STOP_M, TGT_M = 0.3, 1.0
MAKER, TAKER, SLIP = 0.00001, 0.00002, 0.00005  # fractions per side


def simulate(df: pd.DataFrame, start_bal: float = 10_000.0) -> dict:
    o = df["open"].to_numpy(); h = df["high"].to_numpy()
    l = df["low"].to_numpy(); c = df["close"].to_numpy()
    close = df["close"]
    tr = pd.concat([df["high"] - df["low"],
                    (df["high"] - close.shift()).abs(),
                    (df["low"] - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().to_numpy()

    bal = start_bal
    gaps = []          # dicts: dir(+1/-1), top, bottom, born
    pos = None         # (dr, entry, stop, tgt, qty, risk$)
    pending = None     # (dr, entry_price, born)
    rows = []
    peak = start_bal; max_dd = 0.0

    for i in range(20, len(df)):
        # --- manage open position (stop-first) ---
        if pos:
            dr, e, st, tg, q, ra = pos
            hit_st = l[i] <= st if dr > 0 else h[i] >= st
            hit_tg = h[i] >= tg if dr > 0 else l[i] <= tg
            if hit_st:
                px = st * (1 - SLIP) if dr > 0 else st * (1 + SLIP)
                net = dr * (px - e) * q - e * q * MAKER - px * q * TAKER
                bal += net; rows.append({"ts": df.index[i], "net": net, "risk": ra}); pos = None
            elif hit_tg:
                px = tg
                net = dr * (px - e) * q - e * q * MAKER - px * q * MAKER
                bal += net; rows.append({"ts": df.index[i], "net": net, "risk": ra}); pos = None

        # --- v0.12b rejection-wick trigger: tap candle closed last bar with
        # body outside the zone -> enter at THIS bar's open (taker) ---
        if REJECT_MODE and pos is None and pending is not None:
            dr, ep_zone, born = pending  # ep_zone = (top, bottom) for reject mode
            a = atr[i - 1]
            if not np.isnan(a) and a > 0:
                fill = o[i] * (1 + dr * SLIP)
                if GEOM == "atr1_03":      # risk 1*ATR to make 0.3*ATR
                    sdist, tdist = 1.0 * a, 0.3 * a
                elif GEOM == "wick03":     # stop beyond the tap-wick, target 0.3x risk
                    wick = l[i - 1] if dr > 0 else h[i - 1]
                    sdist = max(abs(fill - wick) + 0.05 * a, 0.1 * a)
                    tdist = 0.3 * sdist
                else:                       # original: risk 0.3*ATR to make 1*ATR
                    sdist, tdist = 0.3 * a, 1.0 * a
                st = fill - dr * sdist
                tg = fill + dr * tdist
                q = min(bal * 0.01 / sdist, bal * 10 / fill)
                if (dr > 0 and l[i] <= st) or (dr < 0 and h[i] >= st):
                    px = st * (1 - SLIP) if dr > 0 else st * (1 + SLIP)
                    net = dr * (px - fill) * q - (fill + px) * q * TAKER
                    bal += net
                    rows.append({"ts": df.index[i], "net": net, "risk": q * sdist})
                else:
                    pos = (dr, fill, st, tg, q, q * sdist)
            pending = None

        # --- fill pending limit ---
        if pos is None and pending is not None:
            dr, ep, born = pending
            if i - born > MAX_AGE:
                pending = None
            else:
                touched = l[i] <= ep if dr > 0 else h[i] >= ep
                if touched and not np.isnan(atr[i - 1]) and atr[i - 1] > 0:
                    fill = min(ep, o[i]) if dr > 0 else max(ep, o[i])
                    a = atr[i - 1]
                    st = fill - dr * STOP_M * a
                    tg = fill + dr * TGT_M * a
                    q = min(bal * 0.01 / (STOP_M * a), bal * 10 / fill)
                    pending = None
                    # same-bar stop check (stop-first, conservative; the tight
                    # 0.3*ATR stop is frequently inside the fill bar's range).
                    # Same-bar targets are never granted.
                    if (dr > 0 and l[i] <= st) or (dr < 0 and h[i] >= st):
                        px = st * (1 - SLIP) if dr > 0 else st * (1 + SLIP)
                        net = dr * (px - fill) * q - fill * q * MAKER - px * q * TAKER
                        bal += net
                        rows.append({"ts": df.index[i], "net": net, "risk": q * STOP_M * a})
                    else:
                        pos = (dr, fill, st, tg, q, q * STOP_M * a)

        # --- update gap inventory with the just-closed bar ---
        gaps = [g for g in gaps if i - g["born"] <= MAX_AGE]
        gaps = [g for g in gaps
                if not (g["dir"] > 0 and l[i] <= g["bottom"])
                and not (g["dir"] < 0 and h[i] >= g["top"])]
        if l[i] > h[i - 2]:      # bullish FVG
            gaps.append({"dir": 1, "top": l[i], "bottom": h[i - 2], "born": i, "used": False})
        elif h[i] < l[i - 2]:    # bearish FVG
            gaps.append({"dir": -1, "top": l[i - 2], "bottom": h[i], "born": i, "used": False})

        # --- arm/refresh pending to the most recent live gap ---
        if pos is None and pending is None:
            live = [g for g in gaps if not g["used"]]
            if REJECT_MODE:
                for g in reversed(live):
                    if g["born"] == i:
                        continue  # a gap cannot be tapped by its own birth bar
                    if g["dir"] > 0 and l[i] <= g["top"] and min(o[i], c[i]) > g["top"]:
                        g["used"] = True; pending = (1, None, i); break
                    if g["dir"] < 0 and h[i] >= g["bottom"] and max(o[i], c[i]) < g["bottom"]:
                        g["used"] = True; pending = (-1, None, i); break
            elif live:
                g = live[-1]
                g["used"] = True   # one trade per gap — the tap consumes it
                ep = g["top"] if g["dir"] > 0 else g["bottom"]
                pending = (g["dir"], ep, g["born"])

        m2m = bal + (pos[0] * (c[i] - pos[1]) * pos[4] if pos else 0.0)
        peak = max(peak, m2m); max_dd = max(max_dd, (peak - m2m) / peak)

    t = pd.DataFrame(rows)
    if t.empty:
        return {"n": 0}
    wins = t[t.net > 0]; losses = t[t.net <= 0]
    gw = wins.net.sum(); gl = -losses.net.sum()
    t["y"] = t.ts.dt.year
    return {
        "n": len(t), "win_pct": round(100 * len(wins) / len(t), 1),
        "net": round(t.net.sum(), 0), "end_bal": round(bal, 0),
        "pf": round(gw / gl, 2) if gl > 0 else float("inf"),
        "avg_win_R": round((wins.net / wins.risk).mean(), 2),
        "avg_loss_R": round((losses.net / losses.risk).mean(), 2),
        "max_dd_pct": round(100 * max_dd, 1),
        "trades_per_day": round(len(t) / max((t.ts.max() - t.ts.min()).days, 1), 2),
        "per_year": {y: round(g.net.sum(), 0) for y, g in t.groupby("y")},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="backtest/data_cache/local/xau_5m_2006_2020.csv.gz")
    ap.add_argument("--explore-end", default="2013-01-01")
    ap.add_argument("--reject", action="store_true")
    ap.add_argument("--geom", default="atr03_1", choices=["atr03_1", "atr1_03", "wick03"])
    args = ap.parse_args()
    global REJECT_MODE, GEOM
    REJECT_MODE = args.reject
    GEOM = args.geom

    df = resample_ohlcv(load_cached_1m(args.cache), "5m")
    cut = pd.Timestamp(args.explore_end, tz="America/New_York")
    for name, seg in [("EXPLORE", df[df.index < cut]), ("HOLDOUT", df[df.index >= cut])]:
        print(f"{name} {seg.index.min().date()} -> {seg.index.max().date()} ({len(seg)} bars)")
        if name == "HOLDOUT":
            print("  (run only if explore passed n>=100 and net>0 — printed regardless, judged per pre-registration)")
        print(" ", simulate(seg))


if __name__ == "__main__":
    main()
