"""
Standalone 1H 200-EMA distance experiment (v0.10-exp).

Two mirror rules, both tested because the proposing message was ambiguous:
  trend : d >= +T -> LONG,  d <= -T -> SHORT   (ride the trend)
  revert: d >= +T -> SHORT, d <= -T -> LONG    (fade the stretch)
where d = (close - EMA200) / ATR14 on 1H bars.

Exit: d crosses 0 (EMA touch), executed at next bar open; protective stop at
2*ATR from entry, checked intrabar (stop-first, conservative). Entries fill
at next bar open with taker fee + slippage. One position at a time.

Protocol: exploration window first; only exploration-positive cells run the
untouched holdout window. Everything at honest costs.
"""

import argparse
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from backtest.data import load_cached_1m, resample_ohlcv  # noqa: E402


def simulate(df1h: pd.DataFrame, mode: str, T: float,
             taker_pct: float, slip_pct: float,
             risk_pct: float = 1.0, max_lev: float = 10.0,
             start_bal: float = 10_000.0) -> dict:
    o = df1h["open"].to_numpy()
    h = df1h["high"].to_numpy()
    l = df1h["low"].to_numpy()
    c = df1h["close"].to_numpy()
    idx = df1h.index

    close = df1h["close"]
    ema = close.ewm(span=200, adjust=False).mean().to_numpy()
    tr = pd.concat([
        df1h["high"] - df1h["low"],
        (df1h["high"] - close.shift()).abs(),
        (df1h["low"] - close.shift()).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(14).mean().to_numpy()
    d = (c - ema) / np.where(atr > 0, atr, np.nan)

    taker = taker_pct / 100.0
    slip = slip_pct / 100.0

    bal = start_bal
    pos = None  # dict(direction, qty, entry, stop, entry_fee)
    pending_exit = False
    pending_entry = None  # "LONG"/"SHORT"
    trades = []
    equity_low = start_bal
    peak = start_bal
    max_dd = 0.0

    for i in range(210, len(df1h)):
        # 1) execute pending orders at this bar's open
        if pos is not None and pending_exit:
            px = o[i] * (1 - slip) if pos["direction"] == "LONG" else o[i] * (1 + slip)
            sign = 1.0 if pos["direction"] == "LONG" else -1.0
            gross = sign * (px - pos["entry"]) * pos["qty"]
            fees = pos["entry_fee"] + px * pos["qty"] * taker
            bal += gross - fees
            trades.append({"ts": idx[i], "dir": pos["direction"], "entry": pos["entry"],
                           "exit": px, "gross": gross, "fees": fees, "net": gross - fees,
                           "reason": "EMA"})
            pos = None
        pending_exit = False

        if pos is None and pending_entry is not None and not np.isnan(atr[i - 1]):
            direction = pending_entry
            fill = o[i] * (1 + slip) if direction == "LONG" else o[i] * (1 - slip)
            stop_dist = 2.0 * atr[i - 1]
            qty = (bal * risk_pct / 100.0) / stop_dist
            qty = min(qty, bal * max_lev / fill)
            if qty > 0:
                stop = fill - stop_dist if direction == "LONG" else fill + stop_dist
                pos = {"direction": direction, "qty": qty, "entry": fill,
                       "stop": stop, "entry_fee": fill * qty * taker}
        pending_entry = None

        # 2) intrabar stop check (stop-first, conservative)
        if pos is not None:
            hit = l[i] <= pos["stop"] if pos["direction"] == "LONG" else h[i] >= pos["stop"]
            if hit:
                px = pos["stop"] * (1 - slip) if pos["direction"] == "LONG" else pos["stop"] * (1 + slip)
                sign = 1.0 if pos["direction"] == "LONG" else -1.0
                gross = sign * (px - pos["entry"]) * pos["qty"]
                fees = pos["entry_fee"] + px * pos["qty"] * taker
                bal += gross - fees
                trades.append({"ts": idx[i], "dir": pos["direction"], "entry": pos["entry"],
                               "exit": px, "gross": gross, "fees": fees, "net": gross - fees,
                               "reason": "STOP"})
                pos = None

        # 3) signals at this bar's close -> pending for next open
        if np.isnan(d[i]):
            continue
        if pos is not None:
            # exit when distance crosses back through zero relative to the side
            # that OPENED the position (symmetric for both modes)
            side_long = pos["direction"] == "LONG"
            crossed = d[i] <= 0 if (side_long == (mode == "trend")) else d[i] >= 0
            pending_exit = crossed
        else:
            if d[i] >= T:
                pending_entry = "LONG" if mode == "trend" else "SHORT"
            elif d[i] <= -T:
                pending_entry = "SHORT" if mode == "trend" else "LONG"

        # equity tracking (mark-to-market)
        eq = bal
        if pos is not None:
            sign = 1.0 if pos["direction"] == "LONG" else -1.0
            eq += sign * (c[i] - pos["entry"]) * pos["qty"]
        peak = max(peak, eq)
        max_dd = max(max_dd, (peak - eq) / peak)

    t = pd.DataFrame(trades)
    if t.empty:
        return {"n": 0}
    wins = (t["net"] > 0).sum()
    gw = t.loc[t["net"] > 0, "net"].sum()
    gl = -t.loc[t["net"] <= 0, "net"].sum()
    t["year"] = pd.to_datetime(t["ts"], utc=True).dt.year
    per_year = t.groupby("year")["net"].sum().round(0).to_dict()
    return {
        "n": int(len(t)), "win_pct": round(100 * wins / len(t), 1),
        "gross": round(t["gross"].sum(), 0), "fees": round(t["fees"].sum(), 0),
        "net": round(t["net"].sum(), 0), "pf": round(gw / gl, 2) if gl > 0 else float("inf"),
        "end_bal": round(bal, 0), "max_dd_pct": round(100 * max_dd, 1),
        "per_year": per_year,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--explore-end", required=True, help="ISO date: explore < end <= holdout")
    ap.add_argument("--taker", type=float, required=True)
    ap.add_argument("--slip", type=float, required=True)
    args = ap.parse_args()

    df1m = load_cached_1m(args.cache)
    df1h = resample_ohlcv(df1m, "1h")
    cut = pd.Timestamp(args.explore_end, tz="America/New_York")
    explore, holdout = df1h[df1h.index < cut], df1h[df1h.index >= cut]
    print(f"[{args.label}] explore {explore.index.min()} -> {explore.index.max()} ({len(explore)} bars)")
    print(f"[{args.label}] holdout {holdout.index.min()} -> {holdout.index.max()} ({len(holdout)} bars)\n")

    survivors = []
    for mode in ("trend", "revert"):
        for T in (1.0, 2.0, 3.0):
            r = simulate(explore, mode, T, args.taker, args.slip)
            print(f"EXPLORE {mode:6s} T={T}: {r}")
            if r.get("n", 0) >= 20 and r.get("net", 0) > 0:
                survivors.append((mode, T))
    print(f"\nsurvivors -> holdout: {survivors or 'NONE'}\n")
    for mode, T in survivors:
        r = simulate(holdout, mode, T, args.taker, args.slip)
        print(f"HOLDOUT {mode:6s} T={T}: {r}")


if __name__ == "__main__":
    main()
