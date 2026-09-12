"""
v0.16b-exp — Zarattini & Aziz (2023) 5-minute ORB, both published cells.

Rules (verified against summaries + an independent replication):
- Direction = body of the first 5-min bar (9:30-9:35): up -> LONG,
  down -> SHORT, doji -> skip. Entry at the 9:35 bar open.
- Cell A "base": stop at the opening bar's opposite extreme, target
  10R, flat at 16:00.
- Cell B "atr":  stop = 5% of session-daily ATR14, no target, flat 16:00.
- Sizing: min(1% equity / R, 4x equity / entry). One trade/day.
- House costs (harsher than the paper's zero-slippage assumption):
  taker 0.002% + slip 0.005% per side, both legs.
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
RISK_PCT, MAX_LEV = 1.0, 4.0
SESSION_START, SESSION_END = 9 * 60 + 30, 16 * 60
DOJI_PCT = 0.0001            # |close-open| below this fraction of price = doji
ATR_STOP_FRAC = 0.05         # Cell B: 5% of daily ATR14
TARGET_R = 10.0              # Cell A


def session_atr14(df1m: pd.DataFrame) -> pd.Series:
    """Daily ATR14 built from 9:30-16:00 session OHLC, shifted one day."""
    mod = df1m.index.hour * 60 + df1m.index.minute
    s = df1m[(mod >= SESSION_START) & (mod < SESSION_END)]
    daily = s.groupby(s.index.normalize()).agg(
        high=("high", "max"), low=("low", "min"), close=("close", "last"))
    prev_close = daily["close"].shift()
    tr = pd.concat([daily["high"] - daily["low"],
                    (daily["high"] - prev_close).abs(),
                    (daily["low"] - prev_close).abs()], axis=1).max(axis=1)
    return tr.rolling(14).mean().shift(1)


def simulate(df1m: pd.DataFrame, cell: str, start_bal: float = 10_000.0,
             cost_mult: float = 1.0, atr_frac: float = ATR_STOP_FRAC) -> dict:
    # atr_frac: Cell B stop as a fraction of daily ATR14. 0.05 = the published
    # cell (v0.16b); 0.10 = the single pre-registered v0.16d refinement (R1).
    idx = df1m.index
    mod = (idx.hour * 60 + idx.minute).to_numpy()
    day = idx.normalize()
    o = df1m["open"].to_numpy(); h = df1m["high"].to_numpy()
    l = df1m["low"].to_numpy(); c = df1m["close"].to_numpy()
    atr = session_atr14(df1m)
    # v0.16c cost stress: every per-side cost (fee, slippage, and the
    # slipped entry price) scales together by cost_mult.
    slip = SLIP * cost_mult
    cost = COST * cost_mult

    bal = start_bal
    trades = []
    peak = start_bal; max_dd = 0.0

    for d, day_pos in pd.Series(np.arange(len(df1m)), index=day).groupby(level=0):
        p = day_pos.to_numpy()
        pm = mod[p]
        sess = p[(pm >= SESSION_START) & (pm < SESSION_END)]
        first = p[(pm >= SESSION_START) & (pm < SESSION_START + 5)]
        entry_bars = p[pm == SESSION_START + 5]
        if len(sess) < 60 or len(first) < 5 or len(entry_bars) != 1:
            continue
        a = atr.get(d, np.nan)
        if cell == "atr" and (np.isnan(a) or a <= 0):
            continue

        f_open, f_close = o[first[0]], c[first[-1]]
        if abs(f_close - f_open) < DOJI_PCT * f_open:
            continue
        dr = 1 if f_close > f_open else -1
        jj = entry_bars[0]
        e = o[jj] * (1 + dr * slip)
        if cell == "base":
            stop = l[first].min() if dr > 0 else h[first].max()
        else:
            stop = e - dr * atr_frac * a
        dist = dr * (e - stop)
        if dist <= 0:
            continue
        tgt: Optional[float] = e + dr * TARGET_R * dist if cell == "base" else None
        assert dr * (e - stop) > 0 and (tgt is None or dr * (tgt - e) > 0), "inverted bracket"
        q = min(bal * RISK_PCT / 100.0 / dist, bal * MAX_LEV / e)

        px = reason = None
        for j in sess[sess >= jj]:
            last_bar = j == sess[-1]
            hit_stop = l[j] <= stop if dr > 0 else h[j] >= stop
            hit_tgt = tgt is not None and j > jj and (h[j] >= tgt if dr > 0 else l[j] <= tgt)
            if hit_stop:
                px, reason = stop, "STOP"
            elif hit_tgt:
                px, reason = tgt, "TP"
            elif last_bar:
                px, reason = c[j], "EOD"
            if px is not None:
                break
            m2m = bal + dr * (c[j] - e) * q
            peak = max(peak, m2m); max_dd = max(max_dd, (peak - m2m) / peak)

        if px is None:
            continue
        net = dr * (px - e) * q - (e + px) * q * cost
        bal += net
        peak = max(peak, bal); max_dd = max(max_dd, (peak - bal) / peak)
        trades.append({"ts": idx[jj], "dir": "LONG" if dr > 0 else "SHORT", "net": net,
                       "reason": reason, "r": net / (dist * q),
                       "stop_pct": 100 * dist / e, "cost_r": 2 * e * cost / dist})

    t = pd.DataFrame(trades)
    if t.empty:
        return {"n": 0}
    wins = t[t.net > 0]; losses = t[t.net <= 0]
    gw = wins.net.sum(); gl = -losses.net.sum()
    t["y"] = t.ts.dt.year
    return {
        "cell": cell, "n": len(t), "win_pct": round(100 * len(wins) / len(t), 1),
        "net": round(t.net.sum(), 0), "end_bal": round(bal, 0),
        "pf": round(gw / gl, 2) if gl > 0 else float("inf"),
        "max_dd_pct": round(100 * max_dd, 1),
        "avg_R": round(t.r.mean(), 3),
        "avg_stop_pct_of_price": round(t.stop_pct.mean(), 3),
        "avg_cost_per_R": round(t.cost_r.mean(), 3),
        "exit_mix_pct": (100 * t.reason.value_counts(normalize=True)).round(1).to_dict(),
        "by_dir": t.groupby("dir")["net"].agg(["count", "sum"]).round(0).to_dict(orient="index"),
        "per_year": {y: round(g.net.sum(), 0) for y, g in t.groupby("y")},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="backtest/data_cache/local/nas100_1m_2015_2020.csv.gz")
    ap.add_argument("--explore-end", default="2018-01-01")
    ap.add_argument("--cost-mult", type=float, default=1.0,
                    help="v0.16c stress: multiply every per-side cost by this")
    ap.add_argument("--cells", default="base,atr")
    ap.add_argument("--atr-frac", type=float, default=ATR_STOP_FRAC,
                    help="Cell B stop as a fraction of daily ATR14 (0.05 published, 0.10 = v0.16d R1)")
    ap.add_argument("--start", default=None, help="ISO date lower bound (NY time), optional")
    ap.add_argument("--end", default=None, help="ISO date upper bound (NY time, exclusive), optional")
    ap.add_argument("--single", default=None, metavar="LABEL",
                    help="run the whole (sliced) frame as ONE window with this label instead of the explore/holdout split")
    args = ap.parse_args()

    df = load_cached_1m(args.cache)
    if args.start:
        df = df[df.index >= pd.Timestamp(args.start, tz="America/New_York")]
    if args.end:
        df = df[df.index < pd.Timestamp(args.end, tz="America/New_York")]
    cut = pd.Timestamp(args.explore_end, tz="America/New_York")
    if args.single:
        windows = [(args.single, df)]
    else:
        windows = [("EXPLORE", df[df.index < cut]), ("HOLDOUT", df[df.index >= cut])]
    for cell in args.cells.split(","):
        tag = f"{cell}" + (f" atr_frac={args.atr_frac:g}" if cell == "atr" else "")
        for name, seg in windows:
            print(f"[{tag} x{args.cost_mult:g} costs] {name} {seg.index.min().date()} -> {seg.index.max().date()}")
            if name == "HOLDOUT":
                print("  (judged per pre-registration: explore n>=100 & net>0 gates adoption, printed regardless)")
            print(" ", simulate(seg, cell, cost_mult=args.cost_mult, atr_frac=args.atr_frac))
        print()


if __name__ == "__main__":
    main()
