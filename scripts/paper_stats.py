"""
Paper-trade status for the v0.10c EMA-bracket forward test.

Usage (from the repo root on the VPS):
    python scripts/paper_stats.py

Reads logs/trades.csv and prints equity, win rate, and the recent trades.
Rows without a qty (legacy points-only rows) are excluded from $ stats.
"""

import sys

import pandas as pd

sys.path.insert(0, ".")
import config  # noqa: E402


def main():
    try:
        t = pd.read_csv(config.TRADE_LOG_PATH, dtype=str, keep_default_na=False)
    except FileNotFoundError:
        print(f"No trade log yet at {config.TRADE_LOG_PATH} — no trades taken.")
        return

    t["qty_f"] = pd.to_numeric(t["qty"], errors="coerce")
    t["pnl_f"] = pd.to_numeric(t["pnl"], errors="coerce")
    dollar = t[t["qty_f"] > 0]
    closed = dollar[dollar["result"].isin(["STOPPED", "TP_HIT"])]
    open_rows = dollar[dollar["result"].isin(["PAPER", "OPEN"])]

    start = config.PAPER_START_BALANCE
    realized = closed["pnl_f"].sum() if not closed.empty else 0.0
    print(f"start balance : ${start:,.2f}")
    print(f"realized PnL  : ${realized:+,.2f}  ({len(closed)} closed trades)")
    print(f"equity        : ${start + realized:,.2f}")
    if not closed.empty:
        wins = (closed["pnl_f"] > 0).sum()
        print(f"win rate      : {100 * wins / len(closed):.1f}%  "
              f"({wins}W / {len(closed) - wins}L)  |  validated expectation ~58%")
        first = pd.to_datetime(closed["timestamp"].iloc[0]).date()
        print(f"trading since : {first}")
    if len(closed) and closed["symbol"].nunique() > 1:
        print("\nper symbol:")
        for sym, g in closed.groupby("symbol"):
            w = (g["pnl_f"] > 0).sum()
            print(f"  {sym:10s} {len(g):4d} trades  {100 * w / len(g):5.1f}% win  "
                  f"${g['pnl_f'].sum():+,.2f}")
    if not open_rows.empty:
        for _, r in open_rows.iterrows():
            print(f"open position : {r['symbol']} {r['direction']} {r['qty']} @ {r['entry']} "
                  f"(SL {r['sl']} / TP {r['tp']})")
    else:
        print("open position : none")
    if not closed.empty:
        cols = ["timestamp", "direction", "entry", "sl", "tp", "qty", "result", "pnl"]
        print("\nlast 5 closed:")
        print(closed.tail(5)[cols].to_string(index=False))


if __name__ == "__main__":
    main()
