"""
v0.20-diag — Does the LIVE exit detector agree with the BACKTEST exit detector?

The live bot polls every 60 s: it fetches ONE mark price and compares it to the
open row's stop and target (execution/orders.py check_paper_position). It never
sees a candle's high or low, and it never sees a tick. The backtest checks each
1H bar's HIGH and LOW and forbids a same-bar exit. Three consequences, all
untested until now:
  1. a wick that pierces the stop and recovers inside the minute is an exit in
     the backtest and INVISIBLE to the live bot;
  2. the live bot can exit inside the entry hour, which the backtest forbids;
  3. both book the fill AT the bracket level, but the live mark is already past
     it when the poll sees it — real money fills at the polled price, not the level.

One variable at a time: identical entries, identical sizing, identical costs,
no same-bar re-entry in any mode. ONLY the exit detector changes.
  bar       = backtest semantics: 1H high/low, stop-first, no same-bar exit,
              fill at the bracket level.
  poll      = live semantics: scan 1m CLOSES (one 60 s sample per bar) from the
              minute after entry, fill at the bracket level (what the paper CSV
              records today).
  poll_real = live detection, both legs filled at the POLLED price, i.e. the
              first 1m close beyond the level. Diagnostic only: it grants a
              FAVOURABLE overshoot on targets, which a resting limit order
              would never collect.
  poll_asym = the honest live-money case: target fills at the level (a resting
              limit gets no better), stop fills at the polled price (a
              stop-market gets whatever the book shows when the poll fires).
"""

import argparse
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from backtest.bracket_experiment import ENTRY_T, EXIT_MULT, WARMUP, indicators  # noqa: E402
from backtest.data import load_cached_1m, resample_ohlcv  # noqa: E402

MODES = ("bar", "poll", "poll_real", "poll_asym")


def simulate(df1m: pd.DataFrame, mode: str, taker_pct: float = 0.055, slip_pct: float = 0.01,
             risk_pct: float = 1.0, max_lev: float = 10.0, start_bal: float = 10_000.0) -> dict:
    assert mode in MODES
    df1h = resample_ohlcv(df1m, "1h")
    atr, d = indicators(df1h)
    o = df1h["open"].to_numpy()
    h = df1h["high"].to_numpy()
    low = df1h["low"].to_numpy()
    c1h = df1h["close"].to_numpy()
    idx1h = df1h.index

    m_close = df1m["close"].to_numpy()
    m_idx = df1m.index
    # first 1m row at or after each 1H bar's start
    starts = m_idx.searchsorted(idx1h)

    slip = slip_pct / 100.0
    cost = (taker_pct + slip_pct) / 100.0
    bal = start_bal
    trades: list[dict] = []
    peak = start_bal
    max_dd = 0.0

    i = WARMUP
    while i < len(df1h):
        if np.isnan(d[i - 1]) or np.isnan(atr[i - 1]) or abs(d[i - 1]) < ENTRY_T:
            i += 1
            continue
        dr = 1 if d[i - 1] >= ENTRY_T else -1
        e = o[i] * (1 + dr * slip)
        dist = EXIT_MULT * atr[i - 1]
        stop = e - dr * dist
        tgt = e + dr * dist
        assert dr * (e - stop) > 0 and dr * (tgt - e) > 0, "inverted bracket"
        q = min(bal * risk_pct / 100.0 / dist, bal * max_lev / e)

        px = reason = None
        exit_bar = None
        if mode == "bar":
            for j in range(i + 1, len(df1h)):
                hit_stop = low[j] <= stop if dr > 0 else h[j] >= stop
                hit_tgt = h[j] >= tgt if dr > 0 else low[j] <= tgt
                if hit_stop:
                    px, reason, exit_bar = stop, "STOP", j
                elif hit_tgt:
                    px, reason, exit_bar = tgt, "TP", j
                if px is not None:
                    break
        else:
            # live: one sample per minute, starting the minute AFTER entry
            k = starts[i] + 1
            end = len(m_close)
            while k < end:
                p = m_close[k]
                hit_stop = p <= stop if dr > 0 else p >= stop
                hit_tgt = p >= tgt if dr > 0 else p <= tgt
                if hit_stop:
                    # a stop-market fills at whatever the poll sees, except in
                    # "poll" (the paper CSV's optimistic fill-at-the-level model)
                    px = stop if mode == "poll" else p
                    reason = "STOP"
                elif hit_tgt:
                    # a resting limit at the target never fills BETTER than the
                    # target, so only the diagnostic "poll_real" mode takes p
                    px = p if mode == "poll_real" else tgt
                    reason = "TP"
                if px is not None:
                    exit_bar = int(idx1h.searchsorted(m_idx[k], side="right") - 1)
                    break
                k += 1
        if px is None:
            break  # still open at the end of the data

        net = dr * (px - e) * q - (e + px) * q * cost
        bal += net
        peak = max(peak, bal)
        max_dd = max(max_dd, (peak - bal) / peak)
        trades.append({
            "ts": idx1h[i], "dir": "LONG" if dr > 0 else "SHORT", "net": net,
            "reason": reason, "r": net / (dist * q),
            "bars_held": exit_bar - i, "same_hour": exit_bar == i,
            "slip_r": abs(px - (stop if reason == "STOP" else tgt)) / dist,
        })
        i = max(exit_bar, i) + 1  # no same-bar re-entry in ANY mode

    t = pd.DataFrame(trades)
    if t.empty:
        return {"n": 0}
    wins = t[t.net > 0]
    gl = -t.loc[t.net <= 0, "net"].sum()
    t["y"] = t.ts.dt.year
    return {
        "mode": mode, "n": len(t), "win_pct": round(100 * len(wins) / len(t), 1),
        "net": round(t.net.sum(), 0), "end_bal": round(bal, 0),
        "pf": round(wins.net.sum() / gl, 2) if gl > 0 else float("inf"),
        "max_dd_pct": round(100 * max_dd, 1),
        "stop_share_pct": round(100 * (t.reason == "STOP").mean(), 1),
        "same_hour_exit_pct": round(100 * t.same_hour.mean(), 1),
        "median_bars_held": int(t.bars_held.median()),
        "avg_slip_R": round(t.slip_r.mean(), 4),
        "per_year": {y: round(g.net.sum(), 0) for y, g in t.groupby("y")},
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="backtest/data_cache/local/btcusd_1m_2019_2022.csv.gz")
    ap.add_argument("--start", default=None)
    ap.add_argument("--label", default="")
    ap.add_argument("--modes", default=",".join(MODES))
    args = ap.parse_args()
    df1m = load_cached_1m(args.cache)
    if args.start:
        df1m = df1m[df1m.index >= pd.Timestamp(args.start, tz="America/New_York")]
    tag = f"[{args.label}] " if args.label else ""
    print(f"{tag}{df1m.index.min()} -> {df1m.index.max()} ({len(df1m)} 1m rows)", flush=True)
    for mode in args.modes.split(","):
        print(tag, simulate(df1m, mode.strip()), flush=True)


if __name__ == "__main__":
    main()
