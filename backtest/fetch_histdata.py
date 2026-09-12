"""
HistData.com -> the standard 1m cache format (backtest/data.py).

NSXUSD = NASDAQ-100 index CFD, "generic ASCII" M1 files:
  `YYYYMMDD HHMMSS;open;high;low;close;volume` (volume always 0), yearly
  zips for past years and monthly zips for the current year, fetched with
  the `histdata` client (pip install histdata).
Verified 2026-09-12: these bars ARE Dukascopy's USATECHIDXUSD BID candles
(2021-06-01 13:30 UTC identical to the third decimal), i.e. the same feed
as backtest/fetch_dukascopy.py, whose free bi5 endpoint is throttled.
Timestamps are naive "US Eastern"; whether that means fixed EST or Eastern
with DST is settled EMPIRICALLY by backtest/duka_overlap_check.py against
the Oanda cache — build both variants (--tz-mode ny|est) and keep the one
whose 1H closes match. Filler rows (open == high == low == close) are kept:
the index CFD quotes continuously, and the ORB engine only reads the
9:30-16:00 session. The saved file is re-loaded through load_cached_1m().
"""

import argparse
import os
import sys
import zipfile

import pandas as pd

sys.path.insert(0, ".")
from backtest.data import load_cached_1m  # noqa: E402
from backtest.fetch_binance_archive import epoch_seconds  # noqa: E402

COLS = ["ts", "open", "high", "low", "close", "volume"]


def download(pair: str, year: int, month: int | None, raw_dir: str) -> str:
    from histdata import download_hist_data as dl
    from histdata.api import Platform, TimeFrame
    tag = f"{year}" if month is None else f"{year}{month:02d}"
    path = os.path.join(raw_dir, f"DAT_ASCII_{pair.upper()}_M1_{tag}.zip")
    if os.path.exists(path):
        return path
    out = dl(year=year, month=month, pair=pair, platform=Platform.GENERIC_ASCII,
             time_frame=TimeFrame.ONE_MINUTE, output_directory=raw_dir, verbose=False)
    got = out if os.path.isabs(out) else os.path.join(os.getcwd(), out)
    if os.path.abspath(got) != os.path.abspath(path):
        os.replace(got, path)
    return path


def read_zip(path: str) -> pd.DataFrame:
    z = zipfile.ZipFile(path)
    name = [n for n in z.namelist() if n.endswith(".csv")][0]
    with z.open(name) as f:
        df = pd.read_csv(f, sep=";", header=None, names=COLS)
    df["ts"] = pd.to_datetime(df["ts"], format="%Y%m%d %H%M%S")
    return df


def localize(naive: pd.Series, mode: str) -> pd.DatetimeIndex:
    """
    HistData's naive stamps -> UTC.
      est: fixed UTC-5 (what HistData's FAQ says).
      ny : America/New_York with US DST dates.
      eu : UTC-5 in winter / UTC-4 in summer, switching on the EUROPEAN DST
           dates (last Sunday of March / October) — i.e. Europe/London minus
           five hours. Found empirically (v0.16d): against the Oanda cache the
           'ny' variant is one hour off exactly between the US and EU switch
           dates (March, late October), and Dukascopy's own UTC day file for
           2020-03-13 confirms HistData's "14:59" bar is 19:59 UTC.
    """
    idx = pd.DatetimeIndex(naive)
    if mode == "est":
        return idx.tz_localize("Etc/GMT+5").tz_convert("UTC")      # fixed UTC-5, no DST
    if mode == "eu":
        return (idx + pd.Timedelta(hours=5)).tz_localize(
            "Europe/London", ambiguous="NaT", nonexistent="shift_forward").tz_convert("UTC")
    return idx.tz_localize("America/New_York", ambiguous="NaT",
                           nonexistent="shift_forward").tz_convert("UTC")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pair", default="nsxusd")
    ap.add_argument("--years", default="2019-2025", help="inclusive range of past years, yearly files")
    ap.add_argument("--current-year", type=int, default=2026)
    ap.add_argument("--current-months", default="1-8", help="inclusive month range of the current year")
    ap.add_argument("--tz-mode", choices=["eu", "ny", "est"], default="eu")
    ap.add_argument("--raw-dir", default="backtest/data_cache/local/histdata_raw")
    ap.add_argument("--out", default="backtest/data_cache/local/nas100_histdata_1m_2019_2026.csv.gz")
    args = ap.parse_args()
    os.makedirs(args.raw_dir, exist_ok=True)

    y0, y1 = (int(x) for x in args.years.split("-"))
    m0, m1 = (int(x) for x in args.current_months.split("-"))
    jobs = [(y, None) for y in range(y0, y1 + 1)] + [(args.current_year, m) for m in range(m0, m1 + 1)]
    parts = []
    for year, month in jobs:
        path = download(args.pair, year, month, args.raw_dir)
        df = read_zip(path)
        print(f"  {os.path.basename(path)}: {len(df)} rows {df['ts'].min()} -> {df['ts'].max()}", flush=True)
        parts.append(df)
    df = pd.concat(parts).drop_duplicates("ts").sort_values("ts")

    utc = localize(df["ts"], args.tz_mode)
    keep = ~utc.isna()
    df = df[keep].copy()
    df["timestamp"] = epoch_seconds(utc[keep])
    df = df[["timestamp", "open", "high", "low", "close", "volume"]]
    df.to_csv(args.out, index=False, compression="gzip")

    chk = load_cached_1m(args.out)
    mod = chk.index.hour * 60 + chk.index.minute
    opens = chk[(mod == 9 * 60 + 30) & (chk.index.weekday < 5)]
    n_weekdays = len(set(chk.index.normalize()[chk.index.weekday < 5]))
    print(f"saved+reloaded [{args.tz_mode}] {args.out}: {len(chk)} rows, {chk.index.min()} -> {chk.index.max()}, "
          f"unique={chk.index.is_unique}; 09:30 NY bars on weekdays {len(opens)} of {n_weekdays} weekday dates")
    print(opens.iloc[[0, len(opens) // 2, -1]])
    print("HISTDATA_DONE")


if __name__ == "__main__":
    main()
