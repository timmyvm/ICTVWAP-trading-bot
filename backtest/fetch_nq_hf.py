"""
NQ futures 1m bars with real volume -> backtest/data_cache/local/nq_hf_1m.pkl (the v0.34-exp input).

Source: the Hugging Face dataset mdelcristo/NQ-F_1min_OHLCV_Parquet (MIT), one parquet per year,
2015-01 -> 2025-07-25, columns timestamp (naive UTC), open, high, low, close, volume. The download
loop and this conversion were first run as one-off shell commands during v0.34; they are committed
here so the cache can be rebuilt after a container reset (CLAUDE.md: reference code lives in backtest/).

Checks printed by --check (run in v0.34, DEVLOG v0.34-exp "Data"):
- the stamps are UTC: volume peaks at 15:59 New York every year, and the 09:30 bar carries many
  times the median minute's volume;
- minute alignment: 1m log returns correlate 0.88-0.99 with HistData NSXUSD at lag 0, ~0 at +/-1.
Sessions where a one-minute move differs from the CFD by > 0.5 % (roll switches, bad ticks) are
excluded later, in emt_experiment.load_nq(), not here.

  python3 backtest/fetch_nq_hf.py                 # download missing years, build, re-load
  python3 backtest/fetch_nq_hf.py --check         # plus the clock and alignment checks
"""

import argparse
import os
import sys
from typing import Optional

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, ".")
from backtest.data import load_cached_1m  # noqa: E402

URL = "https://huggingface.co/datasets/mdelcristo/NQ-F_1min_OHLCV_Parquet/resolve/main/NQ_1min_{y}.parquet"
LOCAL = "backtest/data_cache/local"
YEARS = range(2015, 2026)


def download(raw_dir: str) -> None:
    os.makedirs(raw_dir, exist_ok=True)
    for y in YEARS:
        path = f"{raw_dir}/NQ_1min_{y}.parquet"
        if os.path.exists(path) and os.path.getsize(path) > 0:
            continue
        for k in range(4):
            try:
                r = requests.get(URL.format(y=y), timeout=120)
                r.raise_for_status()
                break
            except requests.RequestException as e:
                if k == 3:
                    raise
                print(f"  {y}: {e}; retrying")
        with open(path, "wb") as f:
            f.write(r.content)
        print(f"  {y}: {len(r.content) / 1e6:.1f} MB")


def build(raw_dir: str) -> pd.DataFrame:
    """Exactly the v0.34 conversion: concat years, drop duplicate stamps, index by UTC time."""
    df = pd.concat([pd.read_parquet(f"{raw_dir}/NQ_1min_{y}.parquet") for y in YEARS])
    df = df.drop_duplicates("timestamp").sort_values("timestamp")
    idx = pd.DatetimeIndex(df["timestamp"]).tz_localize("UTC")
    return df.set_index(idx)[["open", "high", "low", "close", "volume"]]


def check(nq: pd.DataFrame, cfd_path: Optional[str]) -> None:
    ny = nq.tz_convert("America/New_York")
    wk = ny.index.weekday < 5
    for y in sorted(set(ny.index.year)):
        sel = wk & (ny.index.year == y)
        mod = ny.index[sel].hour * 60 + ny.index[sel].minute
        pv = ny["volume"][sel].groupby(mod).mean()
        tv = int(pv.idxmax())
        print(f"  {y}: largest mean volume at {tv // 60:02d}:{tv % 60:02d} NY; 09:30 {pv.get(570, 0) / pv.median():.1f}x "
              f"median, 08:30 {pv.get(510, 0) / pv.median():.1f}x, 07:30 {pv.get(450, 0) / pv.median():.1f}x")
    if not cfd_path or not os.path.exists(cfd_path):
        print(f"  (alignment check skipped: {cfd_path} not found; fetch NSXUSD with backtest/fetch_histdata.py)")
        return
    h = load_cached_1m(cfd_path)
    h.index = h.index.tz_convert("UTC")
    a, b = np.log(nq["close"]).diff(), np.log(h["close"]).diff()
    for y in (2015, 2018, 2021, 2023, 2025):
        aa = a[a.index.year == y]
        out = {}
        for lag in (-1, 0, 1):
            bb = b.copy()
            bb.index = bb.index + pd.Timedelta(minutes=lag)
            j = pd.concat([aa, bb], axis=1, join="inner").dropna()
            out[lag] = round(float(j.iloc[:, 0].corr(j.iloc[:, 1])), 3)
        print(f"  {y}: corr with HistData NSXUSD 1m returns at lag -1 {out[-1]}, 0 {out[0]}, +1 {out[1]}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-dir", default=f"{LOCAL}/nq_hf_raw")
    ap.add_argument("--out", default=f"{LOCAL}/nq_hf_1m.pkl")
    ap.add_argument("--cfd", default=f"{LOCAL}/nas100_histdata_1m_2015_2026.csv.gz")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    download(a.raw_dir)
    nq = build(a.raw_dir)
    nq.to_pickle(a.out)
    back = pd.read_pickle(a.out)
    pd.testing.assert_frame_equal(back, nq)
    print(f"saved+reloaded {a.out}: {len(back)} rows, {back.index.min()} -> {back.index.max()}")
    if a.check:
        check(back, a.cfd)
    print("NQ_HF_DONE")


if __name__ == "__main__":
    sys.exit(main())
