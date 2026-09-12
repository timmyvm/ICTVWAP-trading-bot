"""
Weekly sanity audit: does the live paper bot take the trades the RULE takes?

Replays recent real candles (Binance public archive: last two monthly files
plus the current month's daily files) through the frozen reference engine
(backtest/bracket_experiment.simulate) and prints the entries and closed
trades since --since, to compare against logs/trades.csv or the dashboard.
Binance spot prices sit within a small basis of Bybit's perp, so entries
should match within ~0.1-0.3% and stops/targets within dollars; timing
differences of a few minutes are the 60s tick cadence.

    python scripts/audit_paper_vs_rule.py --symbol BTCUSDT --since 2026-09-07
"""

import argparse
import sys

import pandas as pd

sys.path.insert(0, ".")
from backtest.bracket_experiment import simulate  # noqa: E402
from backtest.data import _normalize_1m, resample_ohlcv  # noqa: E402
from backtest.fetch_binance_archive import BASE, KLINE_COLS, fetch_zip_csv  # noqa: E402


def recent_1m(symbol: str, since: pd.Timestamp) -> pd.DataFrame:
    """Monthly files back to ~6 weeks before `since` (EMA warmup) + daily files this month."""
    today = pd.Timestamp.utcnow().normalize()
    first_month = (since - pd.Timedelta(days=45)).to_period("M")
    urls = []
    m = first_month
    while m < today.to_period("M"):
        urls.append(f"{BASE}/spot/monthly/klines/{symbol}/1m/{symbol}-1m-{m}.zip")
        m += 1
    d = today.replace(day=1)
    while d < today:
        urls.append(f"{BASE}/spot/daily/klines/{symbol}/1m/{symbol}-1m-{d.date()}.zip")
        d += pd.Timedelta(days=1)
    frames = []
    for u in urls:
        df = fetch_zip_csv(u)
        if df is None:
            continue
        df = df.iloc[:, :6]
        df.columns = KLINE_COLS[:6]
        t = df["open_time"].astype("int64")
        if t.iloc[0] > 10**14:
            t = t // 1000
        df["open_time"] = t
        frames.append(df)
    raw = pd.concat(frames, ignore_index=True).rename(columns={"open_time": "timestamp"})
    return _normalize_1m(raw)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="BTCUSDT")
    ap.add_argument("--since", required=True, help="ISO date (NY) to print trades from")
    args = ap.parse_args()
    since = pd.Timestamp(args.since, tz="America/New_York")

    df1h = resample_ohlcv(recent_1m(args.symbol, since.tz_convert("UTC")), "1h")
    print(f"{args.symbol}: {len(df1h)} 1H bars, {df1h.index.min()} -> {df1h.index.max()}")
    res = simulate(df1h, return_trades=True)
    if res["n"] == 0:
        print("no trades in window"); return
    en = res["entries"]; tr = res["trades"]
    pd.set_option("display.width", 160)
    print(f"\nENTRIES the rule takes since {since.date()} (signal candle, dir, fill, stop, tp):")
    print(en[en.signal_ts >= since][["signal_ts", "dir", "entry", "stop", "tp"]]
          .to_string(index=False, float_format=lambda x: f"{x:.2f}"))
    print(f"\nCLOSED trades since {since.date()} (exit bar, dir, entry, exit, reason, net @ $10k sizing):")
    print(tr[tr.ts >= since][["ts", "dir", "entry", "exit", "reason", "net"]]
          .to_string(index=False, float_format=lambda x: f"{x:.2f}"))


if __name__ == "__main__":
    main()
