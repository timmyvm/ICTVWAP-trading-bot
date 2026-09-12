"""
v0.17-exp — Fixed-range volume-profile POC pullback (IG reel), BTC 1H.

Mechanized spec — pre-registered in DEVLOG BEFORE any run:
- Swing high/low = extreme of +/-K bars, confirmed K bars later.
- Trend = last confirmed swing low then a confirmed swing high with
  impulse >= 3*ATR14 (shorts mirrored). Setup arms on confirmation.
- Fixed-range profile over the impulse: 40 bins, bar volume spread
  uniformly across the bins its range overlaps. POC = max bin; value
  area = 70% of volume grown from the POC; VAH/VAL = its edges.
- Entry: resting limit at the POC while live (price between POC and the
  swing high at arming; a new high cancels; 100-bar expiry).
- Stop = VAL - 0.1*ATR; TP1 = VAH on half, TP2 = swing high on the rest.
- Maker fee on limit fills (entry, TPs); taker + slip on stops.
"""

import argparse
import sys
from typing import Optional

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from backtest.data import load_cached_1m, resample_ohlcv  # noqa: E402

K = 12
MIN_IMPULSE_ATR = 3.0
BINS = 40
VALUE_AREA = 0.70
MAX_WAIT = 100
STOP_BUFFER_ATR = 0.1
MIN_STOP_ATR = 0.2
MAKER, TAKER, SLIP = 0.0002, 0.00055, 0.0001
RISK_PCT, MAX_LEV = 1.0, 10.0


def profile(h: np.ndarray, l: np.ndarray, v: np.ndarray, lo: float, hi: float):
    """POC, VAH, VAL of a fixed-range profile over the given bars."""
    edges = np.linspace(lo, hi, BINS + 1)
    vol = np.zeros(BINS)
    for bh, bl, bv in zip(h, l, v):
        span = max(bh - bl, 1e-12)
        top = np.minimum(edges[1:], bh)
        bot = np.maximum(edges[:-1], bl)
        overlap = np.clip(top - bot, 0.0, None)
        vol += bv * overlap / span
    if vol.sum() <= 0:
        return None
    p = int(np.argmax(vol))
    lo_i = hi_i = p
    acc = vol[p]
    target = VALUE_AREA * vol.sum()
    while acc < target and (lo_i > 0 or hi_i < BINS - 1):
        up = vol[hi_i + 1] if hi_i < BINS - 1 else -1.0
        dn = vol[lo_i - 1] if lo_i > 0 else -1.0
        if up >= dn:
            hi_i += 1; acc += up
        else:
            lo_i -= 1; acc += dn
    poc = 0.5 * (edges[p] + edges[p + 1])
    return poc, edges[hi_i + 1], edges[lo_i]


def simulate(df1h: pd.DataFrame, start_bal: float = 10_000.0) -> dict:
    o = df1h["open"].to_numpy(); h = df1h["high"].to_numpy()
    l = df1h["low"].to_numpy(); c = df1h["close"].to_numpy()
    v = df1h["volume"].to_numpy(); idx = df1h.index
    close = df1h["close"]
    tr = pd.concat([df1h["high"] - df1h["low"],
                    (df1h["high"] - close.shift()).abs(),
                    (df1h["low"] - close.shift()).abs()], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().to_numpy()
    n = len(df1h)
    # swing flags at the swing bar itself (confirmed K bars later)
    is_sh = np.zeros(n, bool); is_sl = np.zeros(n, bool)
    for i in range(K, n - K):
        is_sh[i] = h[i] == h[i - K:i + K + 1].max()
        is_sl[i] = l[i] == l[i - K:i + K + 1].min()

    bal = start_bal
    pos: Optional[dict] = None
    setup: Optional[dict] = None
    last_sl: Optional[int] = None; last_sh: Optional[int] = None
    trades = []; skipped = {"below_poc": 0, "degenerate": 0}
    peak = start_bal; max_dd = 0.0

    for i in range(2 * K + 14, n):
        # --- manage open position (stop-first; targets from the next bar) ---
        if pos is not None:
            dr = pos["dr"]
            hit_stop = l[i] <= pos["stop"] if dr > 0 else h[i] >= pos["stop"]
            if hit_stop:
                px = pos["stop"] * (1 - dr * SLIP)
                rem = pos["q2"] + (0.0 if pos["half"] else pos["q1"])
                pos["realized"] += dr * (px - pos["e"]) * rem - px * rem * TAKER
                bal += pos["realized"]
                trades.append({"ts": idx[i], "dir": "LONG" if dr > 0 else "SHORT",
                               "net": pos["realized"], "reason": "TP1+STOP" if pos["half"] else "STOP",
                               "stop_pct": pos["stop_pct"], "cost_r": pos["cost_r"]})
                pos = None
            elif i > pos["entry_bar"]:
                if not pos["half"]:
                    hit1 = h[i] >= pos["tp1"] if dr > 0 else l[i] <= pos["tp1"]
                    if hit1:
                        px = pos["tp1"]
                        pos["realized"] += dr * (px - pos["e"]) * pos["q1"] - px * pos["q1"] * MAKER
                        pos["half"] = True
                if pos["half"]:
                    hit2 = h[i] >= pos["tp2"] if dr > 0 else l[i] <= pos["tp2"]
                    if hit2:
                        px = pos["tp2"]
                        pos["realized"] += dr * (px - pos["e"]) * pos["q2"] - px * pos["q2"] * MAKER
                        bal += pos["realized"]
                        trades.append({"ts": idx[i], "dir": "LONG" if dr > 0 else "SHORT",
                                       "net": pos["realized"], "reason": "TP1+TP2",
                                       "stop_pct": pos["stop_pct"], "cost_r": pos["cost_r"]})
                        pos = None

        # --- swing confirmation (bar i confirms swings at i-K) ---
        s = i - K
        if is_sl[s]:
            last_sl = s
        if is_sh[s]:
            last_sh = s
        new_setup = None
        a = atr[i]
        if not np.isnan(a) and a > 0:
            if is_sh[s] and last_sl is not None and last_sl < s and h[s] - l[last_sl] >= MIN_IMPULSE_ATR * a:
                pr = profile(h[last_sl:s + 1], l[last_sl:s + 1], v[last_sl:s + 1], l[last_sl], h[s])
                if pr is not None:
                    new_setup = {"dr": 1, "poc": pr[0], "vah": pr[1], "val": pr[2],
                                 "ext": h[s], "born": i, "atr": a}
            elif is_sl[s] and last_sh is not None and last_sh < s and h[last_sh] - l[s] >= MIN_IMPULSE_ATR * a:
                pr = profile(h[last_sh:s + 1], l[last_sh:s + 1], v[last_sh:s + 1], l[s], h[last_sh])
                if pr is not None:
                    new_setup = {"dr": -1, "poc": pr[0], "vah": pr[1], "val": pr[2],
                                 "ext": l[s], "born": i, "atr": a}
        if new_setup is not None:
            dr = new_setup["dr"]
            spent = c[i] < new_setup["poc"] if dr > 0 else c[i] > new_setup["poc"]
            if spent:
                skipped["below_poc"] += 1
            else:
                setup = new_setup     # latest confirmed swing replaces any older setup

        # --- pending limit at the POC ---
        if setup is not None and pos is None:
            dr = setup["dr"]
            new_ext = h[i] > setup["ext"] if dr > 0 else l[i] < setup["ext"]
            if new_ext or i - setup["born"] > MAX_WAIT:
                setup = None
            else:
                touched = l[i] <= setup["poc"] if dr > 0 else h[i] >= setup["poc"]
                if touched:
                    e = min(setup["poc"], o[i]) if dr > 0 else max(setup["poc"], o[i])
                    a = setup["atr"]
                    stop = setup["val"] - STOP_BUFFER_ATR * a if dr > 0 else setup["vah"] + STOP_BUFFER_ATR * a
                    tp1 = setup["vah"] if dr > 0 else setup["val"]
                    tp2 = setup["ext"]
                    dist = dr * (e - stop)
                    ok = dist >= MIN_STOP_ATR * a and dr * (tp1 - e) > 0 and dr * (tp2 - tp1) >= 0
                    if ok:
                        assert dr * (e - stop) > 0 and dr * (tp1 - e) > 0, "inverted bracket"
                        q = min(bal * RISK_PCT / 100.0 / dist, bal * MAX_LEV / e)
                        pos = {"dr": dr, "e": e, "stop": stop, "tp1": tp1, "tp2": tp2,
                               "q1": q / 2, "q2": q / 2, "half": False, "entry_bar": i,
                               "realized": -e * q * MAKER,
                               "stop_pct": 100 * dist / e,
                               "cost_r": (e * MAKER + e * (TAKER + SLIP)) / dist}
                        # same-bar stop check on the fill bar (stop-first)
                        if (dr > 0 and l[i] <= stop) or (dr < 0 and h[i] >= stop):
                            px = stop * (1 - dr * SLIP)
                            pos["realized"] += dr * (px - e) * q - px * q * TAKER
                            bal += pos["realized"]
                            trades.append({"ts": idx[i], "dir": "LONG" if dr > 0 else "SHORT",
                                           "net": pos["realized"], "reason": "STOP",
                                           "stop_pct": pos["stop_pct"], "cost_r": pos["cost_r"]})
                            pos = None
                    else:
                        skipped["degenerate"] += 1
                    setup = None

        m2m = bal
        if pos is not None:
            rem = pos["q2"] + (0.0 if pos["half"] else pos["q1"])
            m2m += pos["realized"] + pos["dr"] * (c[i] - pos["e"]) * rem
        peak = max(peak, m2m); max_dd = max(max_dd, (peak - m2m) / peak)

    t = pd.DataFrame(trades)
    if t.empty:
        return {"n": 0, "skipped": skipped}
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
        "avg_stop_pct_of_price": round(t.stop_pct.mean(), 3),
        "avg_cost_per_R": round(t.cost_r.mean(), 3),
        "exit_mix": t.reason.value_counts().to_dict(),
        "by_dir": t.groupby("dir")["net"].agg(["count", "sum"]).round(0).to_dict(orient="index"),
        "per_year": {y: round(g.net.sum(), 0) for y, g in t.groupby("y")},
        "skipped": skipped,
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
