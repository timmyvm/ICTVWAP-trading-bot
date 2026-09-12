"""
Dukascopy public datafeed -> the standard 1m cache format (backtest/data.py).

URL pattern (no auth):
  https://datafeed.dukascopy.com/datafeed/{SYMBOL}/{YYYY}/{MM}/{DD}/{SIDE}_candles_min_1.bi5
  MM is ZERO-BASED (00 = January). One file per UTC day: LZMA-compressed
  records of struct '>iiiiif' = (seconds from 00:00 UTC, open, CLOSE, LOW,
  HIGH, volume) — note the field order — prices scaled by 1000 for index
  CFDs (USATECHIDXUSD 2021-06-01 00:00 UTC: 13689109 -> 13689.109).
Mid = (BID + ASK) / 2 on minutes where both sides exist, otherwise the
side present. Filler rows (volume 0 and open == high == low == close) are
dropped. The saved artifact is re-loaded through load_cached_1m() and
reported (CLAUDE.md: validate the SAVED file through the consumer's loader).

The feed rate-limits (HTTP 429) above a few requests per second, so the
fetch runs with a small worker count, a per-request delay, Retry-After /
escalating backoff on 429, and a per-day pickle cache (--raw-dir) so a
re-run only fetches what is still missing. Days that could not be
fetched are listed at the end and make the script exit non-zero.
"""

import argparse
import concurrent.futures as cf
import lzma
import os
import struct
import sys
import threading
import time

import pandas as pd
import requests

sys.path.insert(0, ".")
from backtest.data import load_cached_1m  # noqa: E402
from backtest.fetch_binance_archive import epoch_seconds  # noqa: E402

BASE = "https://datafeed.dukascopy.com/datafeed"
REC = struct.Struct(">iiiiif")
SCALE = 1000.0
PX = ["open", "high", "low", "close"]
_FAILED: list[str] = []
_LOCK = threading.Lock()


def decode(content: bytes, day: pd.Timestamp) -> pd.DataFrame:
    raw = lzma.decompress(content)
    n = len(raw) // REC.size
    rows = [REC.unpack_from(raw, i * REC.size) for i in range(n)]
    df = pd.DataFrame(rows, columns=["sec", "open", "close", "low", "high", "volume"])
    df["timestamp"] = pd.Timestamp(day, tz="UTC") + pd.to_timedelta(df["sec"], unit="s")
    for c in PX:
        df[c] = df[c] / SCALE
    return df[["timestamp"] + PX + ["volume"]]


def fetch_day(symbol: str, day: pd.Timestamp, side: str, raw_dir: str,
              delay: float, retries: int = 6) -> pd.DataFrame | None:
    key = os.path.join(raw_dir, f"{symbol}_{day.date()}_{side}.pkl")
    if os.path.exists(key):
        df = pd.read_pickle(key)
        return None if df.empty else df
    url = f"{BASE}/{symbol}/{day.year}/{day.month - 1:02d}/{day.day:02d}/{side}_candles_min_1.bi5"
    for k in range(retries):
        time.sleep(delay)
        try:
            r = requests.get(url, timeout=60)
            if r.status_code == 429:
                time.sleep(float(r.headers.get("Retry-After", 15 * (k + 1))))
                continue
            if r.status_code == 404 or not r.content:
                pd.DataFrame().to_pickle(key)
                return None
            r.raise_for_status()
            df = decode(r.content, day)
            df.to_pickle(key)
            return None if df.empty else df
        except (requests.RequestException, lzma.LZMAError) as exc:
            if k == retries - 1:
                print(f"  FAILED {url}: {exc}", flush=True)
                break
            time.sleep(2 ** k)
    with _LOCK:
        _FAILED.append(url)
    return None


def combine(parts: list[pd.DataFrame]) -> pd.DataFrame:
    if len(parts) == 1:
        return parts[0]
    a = parts[0].set_index("timestamp")
    b = parts[1].set_index("timestamp")
    both = a.index.intersection(b.index)
    mid = (a.loc[both, PX] + b.loc[both, PX]) / 2.0
    mid["volume"] = (a.loc[both, "volume"] + b.loc[both, "volume"]) / 2.0
    only = a.index.symmetric_difference(b.index)
    rest = pd.concat([a.reindex(only.intersection(a.index)), b.reindex(only.intersection(b.index))])
    return pd.concat([mid, rest]).sort_index().reset_index()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="USATECHIDXUSD")
    ap.add_argument("--start", default="2019-01-01")
    ap.add_argument("--end", default="2026-08-31")
    ap.add_argument("--out", default="backtest/data_cache/local/nas100_duka_1m_2019_2026.csv.gz")
    ap.add_argument("--raw-dir", default="backtest/data_cache/local/duka_raw")
    ap.add_argument("--sides", default="BID,ASK")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--delay", type=float, default=0.5, help="seconds to wait before each request")
    args = ap.parse_args()
    os.makedirs(args.raw_dir, exist_ok=True)

    days = pd.date_range(args.start, args.end, freq="D")
    sides = args.sides.split(",")
    jobs = [(d, s) for d in days for s in sides]
    got: dict[tuple, pd.DataFrame] = {}
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(fetch_day, args.symbol, d, s, args.raw_dir, args.delay): (d, s) for d, s in jobs}
        for i, f in enumerate(cf.as_completed(futs), 1):
            df = f.result()
            if df is not None:
                got[futs[f]] = df
            if i % 250 == 0:
                print(f"  {i}/{len(jobs)} files, {len(got)} with data, {len(_FAILED)} failed, "
                      f"{time.time() - t0:.0f}s", flush=True)

    per_day, n_both, n_one = [], 0, 0
    for d in days:
        parts = [got[(d, s)] for s in sides if (d, s) in got]
        if not parts:
            continue
        n_both += len(parts) == 2
        n_one += len(parts) == 1
        per_day.append(combine(parts))
    if not per_day:
        raise SystemExit("no data fetched")
    df = pd.concat(per_day).sort_values("timestamp")
    df = df[~df["timestamp"].duplicated(keep="last")]
    filler = (df["volume"] == 0) & (df["open"] == df["high"]) & (df["high"] == df["low"]) & (df["low"] == df["close"])
    print(f"days with both sides {n_both}, one side {n_one}; rows {len(df)}, filler dropped {int(filler.sum())}")
    df = df[~filler]

    out = df.copy()
    out["timestamp"] = epoch_seconds(pd.DatetimeIndex(out["timestamp"]))
    out.to_csv(args.out, index=False, compression="gzip")

    chk = load_cached_1m(args.out)
    diffs = chk.index.to_series().diff()
    print(f"saved+reloaded {args.out}: {len(chk)} rows, {chk.index.min()} -> {chk.index.max()}, "
          f"unique={chk.index.is_unique}, gaps>5min={int((diffs > pd.Timedelta(minutes=5)).sum())}, "
          f"gaps>1day={int((diffs > pd.Timedelta(days=1)).sum())}")
    mod = chk.index.hour * 60 + chk.index.minute
    opens = chk[(mod == 9 * 60 + 30) & (chk.index.weekday < 5)]
    n_weekdays = len(set(chk.index.normalize()[chk.index.weekday < 5]))
    print(f"09:30 NY bars on weekdays: {len(opens)} (of {n_weekdays} weekday dates)")
    print(opens.iloc[[0, len(opens) // 2, -1]])
    if _FAILED:
        print(f"UNFETCHED ({len(_FAILED)}): re-run to fill (raw cache keeps what succeeded)")
        for u in _FAILED[:20]:
            print("  ", u)
        raise SystemExit(2)
    print("DUKA_DONE")


if __name__ == "__main__":
    main()
