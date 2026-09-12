"""
Fetch Binance public-archive data into this project's cache formats.

    python backtest/fetch_binance_archive.py klines --symbol ETHUSDT \
        --start 2017-08 --end 2026-08 --out backtest/data_cache/local/ethusd_1m_2017_2026.csv.gz
    python backtest/fetch_binance_archive.py funding --symbol ETHUSDT \
        --start 2019-11 --end 2026-08 --out backtest/data_cache/funding_ethusdt_binance.csv

klines: spot monthly 1m files -> timestamp(epoch s),open,high,low,close,volume
        (what backtest.data.load_cached_1m expects).
funding: USDT-M perp monthly fundingRate files -> timestamp(epoch s),rate
        (what backtest.bracket_experiment.load_funding expects).

Every saved file is re-loaded through the consumer's own loader before the
script reports success (CLAUDE.md: validate the SAVED artifact).
Archive gotchas handled: spot kline open_time is milliseconds before 2025
and MICROSECONDS from 2025-01; newer files carry a header row.
"""

import argparse
import gzip
import io
import sys
import zipfile

import pandas as pd
import requests

sys.path.insert(0, ".")

BASE = "https://data.binance.vision/data"
KLINE_COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time",
              "quote_volume", "trades", "taker_base", "taker_quote", "ignore"]


def months(start: str, end: str):
    cur = pd.Period(start, "M")
    last = pd.Period(end, "M")
    while cur <= last:
        yield str(cur)
        cur += 1


def fetch_zip_csv(url: str) -> pd.DataFrame | None:
    r = requests.get(url, timeout=60)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        name = z.namelist()[0]
        raw = z.read(name)
    first = raw.split(b"\n", 1)[0]
    header = 0 if first.split(b",")[0].strip(b'"').replace(b"_", b"").isalpha() else None
    return pd.read_csv(io.BytesIO(raw), header=header)


def epoch_seconds(ts: pd.DatetimeIndex) -> pd.Index:
    return (ts - pd.Timestamp(0, tz="UTC")) // pd.Timedelta(seconds=1)


def fetch_klines(symbol: str, start: str, end: str, out: str,
                 interval: str = "1m", market: str = "spot"):
    """market: 'spot' or 'um' (USDT-M perps); interval: any archive interval."""
    prefix = "spot" if market == "spot" else "futures/um"
    frames = []
    for m in months(start, end):
        url = f"{BASE}/{prefix}/monthly/klines/{symbol}/{interval}/{symbol}-{interval}-{m}.zip"
        d = fetch_zip_csv(url)
        if d is None:
            print(f"  {m}: missing")
            continue
        d = d.iloc[:, :6]
        d.columns = KLINE_COLS[:6]
        t = d["open_time"].astype("int64")
        if t.iloc[0] > 10**14:          # microseconds (2025+ spot files)
            t = t // 1000
        d["open_time"] = t
        frames.append(d)
        print(f"  {m}: {len(d)} rows")
    df = pd.concat(frames, ignore_index=True)
    ts = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    out_df = pd.DataFrame({
        "timestamp": epoch_seconds(pd.DatetimeIndex(ts)),
        "open": df["open"].astype(float), "high": df["high"].astype(float),
        "low": df["low"].astype(float), "close": df["close"].astype(float),
        "volume": df["volume"].astype(float),
    }).drop_duplicates("timestamp").sort_values("timestamp")
    with gzip.open(out, "wt", newline="") as f:
        out_df.to_csv(f, index=False)

    from backtest.data import load_cached_1m
    chk = load_cached_1m(out)
    step = pd.Timedelta(interval.replace("m", "min") if interval.endswith("m") else interval)
    gaps = (chk.index.to_series().diff() > 5 * step).sum()
    print(f"saved+reloaded {out}: {len(chk)} rows, {chk.index.min()} -> {chk.index.max()}, "
          f"unique={chk.index.is_unique}, gaps>5steps={gaps}")


def fetch_funding(symbol: str, start: str, end: str, out: str):
    frames = []
    for m in months(start, end):
        url = f"{BASE}/futures/um/monthly/fundingRate/{symbol}/{symbol}-fundingRate-{m}.zip"
        d = fetch_zip_csv(url)
        if d is None:
            print(f"  {m}: missing")
            continue
        d.columns = [c.strip() for c in d.columns] if d.columns.dtype == object and "calc_time" in d.columns \
            else ["calc_time", "funding_interval_hours", "last_funding_rate"]
        frames.append(d[["calc_time", "last_funding_rate"]])
    df = pd.concat(frames, ignore_index=True)
    ts = pd.to_datetime(df["calc_time"].astype("int64"), unit="ms", utc=True).dt.floor("h")
    out_df = pd.DataFrame({"timestamp": epoch_seconds(pd.DatetimeIndex(ts)),
                           "rate": df["last_funding_rate"].astype(float).to_numpy()})
    out_df = out_df.drop_duplicates("timestamp").sort_values("timestamp")
    out_df.to_csv(out, index=False)

    from backtest.bracket_experiment import load_funding
    s = load_funding(out)
    print(f"saved+reloaded {out}: {len(s)} rows, {s.index.min()} -> {s.index.max()}, "
          f"unique={s.index.is_unique}, hours={sorted(s.index.hour.unique())}, "
          f"mean ann {100 * s.mean() * 3 * 365:+.1f}%")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["klines", "funding"])
    ap.add_argument("--symbol", required=True)
    ap.add_argument("--start", required=True, help="YYYY-MM")
    ap.add_argument("--end", required=True, help="YYYY-MM")
    ap.add_argument("--out", required=True)
    ap.add_argument("--interval", default="1m", help="klines only: archive interval (1m, 1h, 1d)")
    ap.add_argument("--market", default="spot", choices=["spot", "um"], help="klines only")
    args = ap.parse_args()
    if args.kind == "klines":
        fetch_klines(args.symbol, args.start, args.end, args.out,
                     interval=args.interval, market=args.market)
    else:
        fetch_funding(args.symbol, args.start, args.end, args.out)


if __name__ == "__main__":
    main()
