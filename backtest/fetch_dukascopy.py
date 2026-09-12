"""
Dukascopy public datafeed -> the standard 1m cache format (backtest/data.py).

URL pattern (no auth):
  https://datafeed.dukascopy.com/datafeed/{SYMBOL}/{YYYY}/{MM}/{DD}/{SIDE}_candles_min_1.bi5
  MM is ZERO-BASED (00 = January). One file per UTC day: LZMA-compressed
  records of struct '>iiiiif' = (seconds from 00:00 UTC, open, CLOSE, LOW,
  HIGH, volume) — note the field order — prices scaled by 1000 for index
  CFDs (USATECHIDXUSD 2021-06-01 00:00 UTC: 13689109 -> 13689.109).

The free endpoint is throttled for bulk use (v0.16d, 2026-09-12): the
python-requests User-Agent gets HTTP 429 outright, a browser User-Agent
gets HAProxy 503s and resets at ~15-25 s per successful file, and the
vendor's wiki now points to a paid requester-pays S3 bucket. So this
script is for SMALL, polite jobs: sequential by default, a delay between
requests, long backoff on 429/503, and a per-day raw pickle cache so a
re-run only fetches what is still missing.

Two modes:
  range: --start/--end fetch every day (mid of --sides when both exist).
  fill : --fill-from CACHE fetches only the weekdays whose 09:30-16:00 NY
         session is deficient in CACHE (no 09:30 bar or < --min-session
         bars), replaces those UTC days' rows and writes --out.
The saved artifact is re-loaded through load_cached_1m() and reported.
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
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                         "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"}
REC = struct.Struct(">iiiiif")
SCALE = 1000.0
PX = ["open", "high", "low", "close"]
NY = "America/New_York"
_FAILED: list[str] = []
_LOCK = threading.Lock()
_SESSION = requests.Session()
_SESSION.headers.update(HEADERS)


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
              delay: float, retries: int = 8) -> pd.DataFrame | None:
    key = os.path.join(raw_dir, f"{symbol}_{day.date()}_{side}.pkl")
    if os.path.exists(key):
        df = pd.read_pickle(key)
        return None if df.empty else df
    url = f"{BASE}/{symbol}/{day.year}/{day.month - 1:02d}/{day.day:02d}/{side}_candles_min_1.bi5"
    for k in range(retries):
        time.sleep(delay)
        try:
            r = _SESSION.get(url, timeout=90)
            if r.status_code in (429, 503):
                time.sleep(float(r.headers.get("Retry-After", 20 * (k + 1))))
                continue
            if r.status_code == 404 or not r.content:
                pd.DataFrame().to_pickle(key)
                return None
            r.raise_for_status()
            df = decode(r.content, day)
            df.to_pickle(key)
            print(f"  got {day.date()} {side} ({len(df)} rows)", flush=True)
            return None if df.empty else df
        except (requests.RequestException, lzma.LZMAError) as exc:
            if k == retries - 1:
                print(f"  FAILED {url}: {exc}", flush=True)
                break
            time.sleep(10 * (k + 1))
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


def nyse_holidays(start: str, end: str) -> set:
    """Approximate NYSE full-closure calendar (regular holidays; ad-hoc closures are not
    listed and simply get fetched — harmless, just slow)."""
    from pandas.tseries.holiday import (AbstractHolidayCalendar, GoodFriday, Holiday,
                                        USLaborDay, USMartinLutherKingJr, USMemorialDay,
                                        USPresidentsDay, USThanksgivingDay, nearest_workday)

    class NYSE(AbstractHolidayCalendar):
        rules = [
            Holiday("NewYearsDay", month=1, day=1, observance=nearest_workday),
            USMartinLutherKingJr, USPresidentsDay, GoodFriday, USMemorialDay,
            Holiday("Juneteenth", month=6, day=19, start_date="2022-01-01", observance=nearest_workday),
            Holiday("IndependenceDay", month=7, day=4, observance=nearest_workday),
            USLaborDay, USThanksgivingDay,
            Holiday("Christmas", month=12, day=25, observance=nearest_workday),
        ]
    return set(pd.Timestamp(d.date()) for d in NYSE().holidays(pd.Timestamp(start), pd.Timestamp(end)))


def deficient_days(cache: pd.DataFrame, start: str, end: str, min_session: int) -> list[pd.Timestamp]:
    """Weekdays (NY) in [start, end] whose 09:30-16:00 session is missing its 09:30 bar
    or has fewer than min_session 1m bars — excluding NYSE holidays and early-close days
    (a 13:00 close gives ~210 bars: recognized as last session bar <= 13:05 with >= 195
    bars). Returned as naive day stamps (the UTC day file of that date)."""
    mod = cache.index.hour * 60 + cache.index.minute
    sess = cache[(mod >= 570) & (mod < 960)]
    per_day = sess.groupby(sess.index.normalize()).size()
    last_bar = sess.groupby(sess.index.normalize()).apply(lambda g: g.index.max())
    opens = set(cache[mod == 570].index.normalize())
    hol = nyse_holidays(start, end)
    out = []
    for d in pd.bdate_range(start, end, tz=NY):
        if pd.Timestamp(d.date()) in hol:
            continue
        n = per_day.get(d, 0)
        if d in opens and n >= min_session:
            continue
        if d in last_bar.index and n >= 195:
            lb = last_bar[d]
            if lb.hour * 60 + lb.minute <= 13 * 60 + 5:      # early close, complete
                continue
        out.append(pd.Timestamp(d.date()))
    return out


def report(chk: pd.DataFrame, out: str) -> None:
    diffs = chk.index.to_series().diff()
    print(f"saved+reloaded {out}: {len(chk)} rows, {chk.index.min()} -> {chk.index.max()}, "
          f"unique={chk.index.is_unique}, gaps>5min={int((diffs > pd.Timedelta(minutes=5)).sum())}, "
          f"gaps>1day={int((diffs > pd.Timedelta(days=1)).sum())}")
    mod = chk.index.hour * 60 + chk.index.minute
    sess = chk[(mod >= 570) & (mod < 960) & (chk.index.weekday < 5)]
    per_day = sess.groupby(sess.index.normalize()).size()
    opens = chk[(mod == 570) & (chk.index.weekday < 5)]
    print("session completeness by year: days with 09:30 bar / days with >= 380 session bars / weekday dates / mean bars")
    for y, g in per_day.groupby(per_day.index.year):
        print(f"  {y}: {int((opens.index.year == y).sum())} / {int((g >= 380).sum())} / {len(g)} / {g.mean():.0f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="USATECHIDXUSD")
    ap.add_argument("--start", default="2019-01-01")
    ap.add_argument("--end", default="2026-08-31")
    ap.add_argument("--out", default="backtest/data_cache/local/nas100_duka_1m_2019_2026.csv.gz")
    ap.add_argument("--raw-dir", default="backtest/data_cache/local/duka_raw")
    ap.add_argument("--sides", default="BID,ASK")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--delay", type=float, default=3.0, help="seconds to wait before each request")
    ap.add_argument("--fill-from", default=None, help="existing cache to gap-fill (fill mode)")
    ap.add_argument("--min-session", type=int, default=380, help="fill mode: session bars below this = deficient")
    ap.add_argument("--dry-run", action="store_true", help="fill mode: list the deficient days and exit")
    args = ap.parse_args()
    os.makedirs(args.raw_dir, exist_ok=True)
    sides = args.sides.split(",")

    base = None
    if args.fill_from:
        base = load_cached_1m(args.fill_from)
        days = deficient_days(base, args.start, args.end, args.min_session)
        print(f"fill mode: {len(days)} deficient weekdays in {args.fill_from} between {args.start} and {args.end}", flush=True)
        if args.dry_run:
            by_year = pd.Series([d.year for d in days]).value_counts().sort_index().to_dict()
            print("  by year:", by_year)
            print("  first 30:", [str(d.date()) for d in days[:30]])
            return
    else:
        days = list(pd.date_range(args.start, args.end, freq="D"))

    jobs = [(d, s) for d in days for s in sides]
    got: dict[tuple, pd.DataFrame] = {}
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(fetch_day, args.symbol, d, s, args.raw_dir, args.delay): (d, s) for d, s in jobs}
        for i, f in enumerate(cf.as_completed(futs), 1):
            df = f.result()
            if df is not None:
                got[futs[f]] = df
            if i % 25 == 0:
                print(f"  {i}/{len(jobs)} files, {len(got)} with data, {len(_FAILED)} failed, "
                      f"{time.time() - t0:.0f}s", flush=True)

    per_day = []
    for d in days:
        parts = [got[(d, s)] for s in sides if (d, s) in got]
        if parts:
            per_day.append(combine(parts))
    if not per_day and base is None:
        raise SystemExit("no data fetched")
    fetched = pd.concat(per_day).sort_values("timestamp") if per_day else pd.DataFrame(columns=["timestamp"] + PX + ["volume"])
    fetched = fetched[~fetched["timestamp"].duplicated(keep="last")]
    filler = (fetched["volume"] == 0) & (fetched["open"] == fetched["high"]) & \
             (fetched["high"] == fetched["low"]) & (fetched["low"] == fetched["close"])
    print(f"fetched rows {len(fetched)}, filler dropped {int(filler.sum())}, unfetched {len(_FAILED)}")
    fetched = fetched[~filler]

    if base is not None:
        keep = base.copy()
        keep_utc = keep.index.tz_convert("UTC")
        replaced_days = set(pd.DatetimeIndex(fetched["timestamp"]).tz_convert("UTC").normalize())
        keep = keep[~keep_utc.normalize().isin(list(replaced_days))]
        merged = pd.concat([
            pd.DataFrame({"timestamp": epoch_seconds(keep_utc[~keep_utc.normalize().isin(list(replaced_days))]),
                          **{c: keep[c].to_numpy() for c in PX + ["volume"]}}),
            pd.DataFrame({"timestamp": epoch_seconds(pd.DatetimeIndex(fetched["timestamp"])),
                          **{c: fetched[c].to_numpy() for c in PX + ["volume"]}}),
        ]).sort_values("timestamp")
        print(f"fill: replaced {len(replaced_days)} UTC days ({len(base) - len(keep)} old rows) with {len(fetched)} fetched rows")
        out_df = merged
    else:
        out_df = fetched.copy()
        out_df["timestamp"] = epoch_seconds(pd.DatetimeIndex(out_df["timestamp"]))
    out_df.to_csv(args.out, index=False, compression="gzip")

    chk = load_cached_1m(args.out)
    report(chk, args.out)
    if _FAILED:
        print(f"UNFETCHED ({len(_FAILED)}): re-run to fill (raw cache keeps what succeeded)")
        for u in _FAILED[:20]:
            print("  ", u)
        raise SystemExit(2)
    print("DUKA_DONE")


if __name__ == "__main__":
    main()
