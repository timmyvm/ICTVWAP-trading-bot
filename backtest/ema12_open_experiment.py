"""
v0.19-exp — First 5-min candle vs 12-EMA, EMA-ratchet trailing stop (QuantLab reel).

Mechanized spec — pre-registered in DEVLOG BEFORE any run:
- EMA12 on the continuous 5m close series.
- Signal = the 09:30 5m bar: close > EMA12 -> LONG, close < EMA12 -> SHORT.
  Entry at the 09:35 bar open (taker + slip).
- Initial stop at the signal bar's opposite extreme. From the next bar,
  the stop ratchets to the last CLOSED bar's EMA12 when tighter; never
  loosens. Intrabar stop-first, no target, flat at the 16:00 close.
- 1% risk on the initial stop distance, 4x cap, house futures-CFD costs
  (0.002% + 0.005% per side, both legs), --cost-mult for the stress.
"""

import argparse
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from backtest.data import load_cached_1m, resample_ohlcv  # noqa: E402

TAKER, SLIP = 0.00002, 0.00005
COST = TAKER + SLIP
RISK_PCT, MAX_LEV = 1.0, 4.0
EMA_SPAN = 12
SIGNAL_MOD, ENTRY_MOD, SESSION_END = 9 * 60 + 30, 9 * 60 + 35, 16 * 60


def simulate(df5: pd.DataFrame, start_bal: float = 10_000.0, cost_mult: float = 1.0) -> dict:
    idx = df5.index
    mod = (idx.hour * 60 + idx.minute).to_numpy()
    day = idx.normalize()
    o = df5["open"].to_numpy(); h = df5["high"].to_numpy()
    l = df5["low"].to_numpy(); c = df5["close"].to_numpy()
    ema = df5["close"].ewm(span=EMA_SPAN, adjust=False).mean().to_numpy()
    slip = SLIP * cost_mult
    cost = COST * cost_mult

    bal = start_bal
    trades = []
    peak = start_bal; max_dd = 0.0

    for _, day_pos in pd.Series(np.arange(len(df5)), index=day).groupby(level=0):
        p = day_pos.to_numpy()
        pm = mod[p]
        sig = p[pm == SIGNAL_MOD]
        sess = p[(pm >= ENTRY_MOD) & (pm < SESSION_END)]
        if len(sig) != 1 or len(sess) < 20 or sess[0] != sig[0] + 1:
            continue
        s = sig[0]
        if c[s] == ema[s] or np.isnan(ema[s]):
            continue
        dr = 1 if c[s] > ema[s] else -1
        jj = sess[0]
        e = o[jj] * (1 + dr * slip)
        stop = l[s] if dr > 0 else h[s]
        dist = dr * (e - stop)
        if dist <= 0:
            continue
        assert dr * (e - stop) > 0, "inverted stop"
        q = min(bal * RISK_PCT / 100.0 / dist, bal * MAX_LEV / e)
        init_stop = stop

        px = reason = None
        for j in sess:
            if j > jj:   # ratchet to the last closed bar's EMA when tighter
                trail = ema[j - 1]
                stop = max(stop, trail) if dr > 0 else min(stop, trail)
            hit = l[j] <= stop if dr > 0 else h[j] >= stop
            if hit:
                px, reason = stop, ("STOP" if stop == init_stop else "TRAIL")
            elif j == sess[-1]:
                px, reason = c[j], "EOD"
            if px is not None:
                break
            m2m = bal + dr * (c[j] - e) * q
            peak = max(peak, m2m); max_dd = max(max_dd, (peak - m2m) / peak)

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
        "n": len(t), "win_pct": round(100 * len(wins) / len(t), 1),
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
    ap.add_argument("--cost-mult", type=float, default=1.0)
    args = ap.parse_args()

    df5 = resample_ohlcv(load_cached_1m(args.cache), "5m")
    cut = pd.Timestamp(args.explore_end, tz="America/New_York")
    for name, seg in [("EXPLORE", df5[df5.index < cut]), ("HOLDOUT", df5[df5.index >= cut])]:
        print(f"[x{args.cost_mult:g} costs] {name} {seg.index.min().date()} -> {seg.index.max().date()}")
        if name == "HOLDOUT":
            print("  (judged per pre-registration: explore n>=100 & net>0 gates adoption, printed regardless)")
        print(" ", simulate(seg, cost_mult=args.cost_mult))


if __name__ == "__main__":
    main()
