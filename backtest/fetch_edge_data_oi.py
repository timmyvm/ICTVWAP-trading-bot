"""
Edge-lab flow data for H010 / H012: Binance USDT-M perp 1h klines (with taker buy
volume) and the daily `metrics` files (5-minute open interest, long/short ratios,
taker buy/sell volume ratio), consolidated to one file per symbol, plus the
validation and outcome-blind funnel counts reported in
research/data_reports/H010_flow_data.md.

Conventions follow backtest/fetch_binance_archive.py (same BASE, months(),
epoch-subtraction for epoch seconds, re-load every saved artifact through the
consumer loader before reporting success). Downloads: at most 4 concurrent
requests, retries with exponential backoff, a small per-request delay.
Downloaded files are untrusted: they are only ever parsed by pandas/zipfile.
Run with `python3 -I` (isolated mode; the script adds the repo root itself).

    # 1h perp klines, 2020-01 .. 2026-09 (one csv.gz per symbol)
    python3 -I backtest/fetch_edge_data_oi.py klines --symbols BTCUSDT,ETHUSDT --start 2020-01 --end 2026-09
    # daily metrics zips (only days present in the S3 listing), then one parquet per symbol
    python3 -I backtest/fetch_edge_data_oi.py metrics --symbols BTCUSDT,ETHUSDT --start 2020-09-01 --end 2026-09-30
    python3 -I backtest/fetch_edge_data_oi.py consolidate --symbols BTCUSDT,ETHUSDT
    # symbol lists from the point-in-time universe file written by fetch_edge_data_funding.py
    python3 -I backtest/fetch_edge_data_oi.py symbols --tier A        # prints a comma list
    # validation, timestamp-convention test, OI-vs-volume anomaly, cross-vendor, counts
    python3 -I backtest/fetch_edge_data_oi.py validate --symbols ALL
    python3 -I backtest/fetch_edge_data_oi.py stampcheck --symbols BTCUSDT,ETHUSDT,SOLUSDT
    python3 -I backtest/fetch_edge_data_oi.py bybit --symbols BTCUSDT,SOLUSDT,XRPUSDT --months 2021-05,2022-05,2022-11
    python3 -I backtest/fetch_edge_data_oi.py counts

Consumer loaders (import these from engines):
    load_um1h(sym)     -> UTC-indexed (bar OPEN time) 1h frame: open high low close volume
                          quote_volume trades taker_buy_base taker_buy_quote
    load_metrics(sym)  -> UTC-indexed (row stamp) 5m frame: oi (coin units), oi_value (USDT),
                          toptrader_ls_accounts, toptrader_ls_positions, global_ls_accounts,
                          taker_ls_vol_ratio
    oi_at(metrics, times, lag="5min") -> OI from the latest row stamped at or before time-lag

THE COUNTS ARE OUTCOME-BLIND: every quantity used is known at or before the
decision bar's close. Nothing after t is read.
"""

import argparse
import concurrent.futures as cf
import io
import json
import os
import random
import re
import sys
import threading
import time
import zipfile
from typing import Optional

import numpy as np
import pandas as pd
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

BASE = "https://data.binance.vision/data"
LIST = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
EDGE = os.path.join(ROOT, "backtest", "data_cache", "local", "edge")
K1H_DIR = os.path.join(EDGE, "um1h")
MRAW_DIR = os.path.join(EDGE, "metrics_raw")
MET_DIR = os.path.join(EDGE, "metrics")
UNIVERSE = os.path.join(EDGE, "universe_pit.csv")
OUT_DIR = os.path.join(EDGE, "h010_checks")
MAX_WORKERS = min(4, int(os.environ.get("EDGE_WORKERS", "4")))   # never more than 4
STAMP_SWITCH = pd.Timestamp("2024-03-04 00:00", tz="UTC")       # metrics stamp convention change
DELAY = 0.05

KLINE_COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time",
              "quote_volume", "trades", "taker_buy_base", "taker_buy_quote", "ignore"]
MET_COLS = {"create_time": "ts", "sum_open_interest": "oi",
            "sum_open_interest_value": "oi_value",
            "count_toptrader_long_short_ratio": "toptrader_ls_accounts",
            "sum_toptrader_long_short_ratio": "toptrader_ls_positions",
            "count_long_short_ratio": "global_ls_accounts",
            "sum_taker_long_short_vol_ratio": "taker_ls_vol_ratio"}

_tls = threading.local()


def _session() -> requests.Session:
    s = getattr(_tls, "s", None)
    if s is None:
        s = requests.Session()
        _tls.s = s
    return s


def http_get(url: str, tries: int = 6) -> Optional[bytes]:
    """GET with retries and exponential backoff. None on 404."""
    for i in range(tries):
        try:
            time.sleep(DELAY)
            r = _session().get(url, timeout=60)
            if r.status_code == 404:
                return None
            if r.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"HTTP {r.status_code}")
            r.raise_for_status()
            return r.content
        except (requests.RequestException, ConnectionError) as e:
            if i == tries - 1:
                raise
            wait = min(60.0, 1.5 * 2 ** i) + random.random()
            print(f"    retry {i + 1} {url[-60:]}: {e}; sleep {wait:.1f}s", flush=True)
            time.sleep(wait)
    return None


def s3_list(prefix: str) -> dict:
    """All keys (with sizes) under an S3 prefix of data.binance.vision, paginated."""
    out, marker = {}, ""
    while True:
        url = f"{LIST}?prefix={prefix}" + (f"&marker={marker}" if marker else "")
        body = http_get(url)
        if body is None:
            return out
        t = body.decode("utf-8", "replace")
        keys = re.findall(r"<Key>([^<]+)</Key>", t)
        sizes = re.findall(r"<Size>(\d+)</Size>", t)
        out.update(dict(zip(keys, map(int, sizes))))
        if "<IsTruncated>true</IsTruncated>" not in t or not keys:
            return out
        marker = keys[-1]


def months(start: str, end: str):
    cur, last = pd.Period(start, "M"), pd.Period(end, "M")
    while cur <= last:
        yield str(cur)
        cur += 1


def epoch_seconds(ts: pd.DatetimeIndex) -> pd.Index:
    return (ts - pd.Timestamp(0, tz="UTC")) // pd.Timedelta(seconds=1)


def read_zip_csv(raw: bytes) -> pd.DataFrame:
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        data = z.read(z.namelist()[0])
    first = data.split(b"\n", 1)[0]
    header = 0 if first.split(b",")[0].strip(b'"').replace(b"_", b"").isalpha() else None
    return pd.read_csv(io.BytesIO(data), header=header)


# ---------------------------------------------------------------- symbol lists

def universe_symbols(tier: str) -> list[str]:
    """Symbols ever in turnover ranks 3-40 (A) or 41-120 (C), plus BTC/ETH (B)."""
    if tier == "B":
        return ["BTCUSDT", "ETHUSDT"]
    u = load_universe_long()
    u = u[u["month"] >= "2020-09"]                      # metrics (OI) start 2020-09
    lo, hi = (3, 40) if tier == "A" else (41, 120)
    if tier == "A25":
        lo, hi = 3, 25
    sel = u[(u["rank"] >= lo) & (u["rank"] <= hi)]["symbol"].unique()
    if tier == "C":                                     # C excludes anything ever in A
        sel = sorted(set(sel) - set(universe_symbols("A")))
    return sorted(set(sel))


# ---------------------------------------------------------------- 1h klines

def k1h_path(sym: str) -> str:
    return os.path.join(K1H_DIR, f"{sym}.csv.gz")


def fetch_klines_1h(sym: str, start: str, end: str) -> str:
    os.makedirs(K1H_DIR, exist_ok=True)
    listing = s3_list(f"data/futures/um/monthly/klines/{sym}/1h/")
    have = {re.search(r"-(\d{4}-\d{2})\.zip$", k).group(1)
            for k in listing if k.endswith(".zip")}
    want = [m for m in months(start, end) if m in have]
    urls = [f"{BASE}/futures/um/monthly/klines/{sym}/1h/{sym}-1h-{m}.zip" for m in want]
    with cf.ThreadPoolExecutor(MAX_WORKERS) as ex:
        raws = list(ex.map(http_get, urls))
    frames, units = [], {}
    for m, raw in zip(want, raws):
        if raw is None:
            continue
        d = read_zip_csv(raw).iloc[:, :11]
        d.columns = KLINE_COLS[:11]
        t = d["open_time"].astype("int64")
        units[m] = "us" if t.iloc[0] > 10 ** 14 else "ms"
        if units[m] == "us":
            t = t // 1000
        d["open_time"] = t
        frames.append(d)
    if not frames:
        print(f"{sym}: no 1h klines in {start}..{end}")
        return ""
    df = pd.concat(frames, ignore_index=True)
    ts = pd.DatetimeIndex(pd.to_datetime(df["open_time"], unit="ms", utc=True))
    out = pd.DataFrame({"timestamp": epoch_seconds(ts)})
    for c in ["open", "high", "low", "close", "volume", "quote_volume", "trades",
              "taker_buy_base", "taker_buy_quote"]:
        out[c] = pd.to_numeric(df[c], errors="coerce").to_numpy()
    n0 = len(out)
    out = out.drop_duplicates("timestamp").sort_values("timestamp")
    path = k1h_path(sym)
    out.to_csv(path, index=False, compression="gzip")
    chk = load_um1h(sym)
    gaps = int((chk.index.to_series().diff() > pd.Timedelta("1h")).sum())
    print(f"{sym}: {len(want)} months ({want[0]}..{want[-1]}), units={sorted(set(units.values()))}, "
          f"rows {len(chk)} (dups dropped {n0 - len(out)}), {chk.index.min()} -> {chk.index.max()}, "
          f"gaps {gaps}, unique={chk.index.is_unique}", flush=True)
    if gaps:
        patch_klines_1h(sym)
    return path


def patch_klines_1h(sym: str) -> dict:
    """Some MONTHLY 1h zips are truncated (e.g. SOL/XRP 2022-02-26..28, 2022-04-01..02)
    while the DAILY files for those days exist. Fill gaps from the same vendor's daily
    files only; never interpolate. Patched days are logged to <sym>.patched.json."""
    k = pd.read_csv(k1h_path(sym))
    ts = pd.DatetimeIndex(pd.to_datetime(k["timestamp"], unit="s", utc=True))
    full = pd.date_range(ts.min(), ts.max(), freq="1h")
    miss_days = sorted(set(full.difference(ts).strftime("%Y-%m-%d")))
    frames, patched, absent = [], [], []
    for day in miss_days:
        raw = http_get(f"{BASE}/futures/um/daily/klines/{sym}/1h/{sym}-1h-{day}.zip")
        if raw is None:
            absent.append(day)
            continue
        d = read_zip_csv(raw).iloc[:, :11]
        d.columns = KLINE_COLS[:11]
        t = d["open_time"].astype("int64")
        t = t // 1000 if t.iloc[0] > 10 ** 14 else t
        o = pd.DataFrame({"timestamp": epoch_seconds(pd.DatetimeIndex(pd.to_datetime(t, unit="ms", utc=True)))})
        for c in ["open", "high", "low", "close", "volume", "quote_volume", "trades",
                  "taker_buy_base", "taker_buy_quote"]:
            o[c] = pd.to_numeric(d[c], errors="coerce").to_numpy()
        frames.append(o)
        patched.append(day)
    if frames:
        k = pd.concat([k] + frames, ignore_index=True)
        k = k.drop_duplicates("timestamp", keep="first").sort_values("timestamp")
        k.to_csv(k1h_path(sym), index=False, compression="gzip")
    chk = load_um1h(sym)
    gaps = int((chk.index.to_series().diff() > pd.Timedelta("1h")).sum())
    info = {"symbol": sym, "missing_days": miss_days, "patched_from_daily": patched,
            "absent_in_daily": absent, "gaps_after": gaps, "rows_after": len(chk)}
    with open(os.path.join(K1H_DIR, f"{sym}.patched.json"), "w") as f:
        json.dump(info, f)
    print(json.dumps(info), flush=True)
    return info


def load_um1h(sym: str) -> pd.DataFrame:
    """Consumer loader: UTC index = bar OPEN time; the bar's close is index + 1h."""
    df = pd.read_csv(k1h_path(sym))
    idx = pd.DatetimeIndex(pd.to_datetime(df["timestamp"].astype("int64"), unit="s", utc=True)).as_unit("ns")
    out = df.drop(columns=["timestamp"]).astype(float)
    out.index = idx
    out.index.name = "open_time"
    return out[~out.index.duplicated(keep="last")].sort_index()


# ---------------------------------------------------------------- metrics

def met_path(sym: str) -> str:
    return os.path.join(MET_DIR, f"{sym}.parquet")


def fetch_metrics(sym: str, start: str, end: str) -> dict:
    """Download every listed daily metrics zip in [start, end] not already on disk."""
    d = os.path.join(MRAW_DIR, sym)
    os.makedirs(d, exist_ok=True)
    listing = s3_list(f"data/futures/um/daily/metrics/{sym}/")
    days = sorted(re.search(r"(\d{4}-\d{2}-\d{2})\.zip$", k).group(1)
                  for k in listing if k.endswith(".zip"))
    sel = [x for x in days if start <= x <= end]
    todo = [x for x in sel if not os.path.exists(os.path.join(d, f"{sym}-metrics-{x}.zip"))]

    def one(day: str) -> bool:
        raw = http_get(f"{BASE}/futures/um/daily/metrics/{sym}/{sym}-metrics-{day}.zip")
        if raw is None:
            return False
        tmp = os.path.join(d, f".{day}.part")
        with open(tmp, "wb") as f:
            f.write(raw)
        os.replace(tmp, os.path.join(d, f"{sym}-metrics-{day}.zip"))
        return True

    t0 = time.time()
    with cf.ThreadPoolExecutor(MAX_WORKERS) as ex:
        ok = sum(ex.map(one, todo))
    info = {"symbol": sym, "listed_days": len(days), "first_listed": days[0] if days else None,
            "last_listed": days[-1] if days else None, "in_range": len(sel),
            "downloaded_now": ok, "secs": round(time.time() - t0, 1)}
    print(json.dumps(info), flush=True)
    with open(os.path.join(MRAW_DIR, f"{sym}.listing.json"), "w") as f:
        json.dump({"days": days, "info": info}, f)
    return info


def consolidate_metrics(sym: str) -> dict:
    d = os.path.join(MRAW_DIR, sym)
    files = sorted(f for f in os.listdir(d) if f.endswith(".zip"))
    frames, bad = [], []
    for f in files:
        try:
            with open(os.path.join(d, f), "rb") as fh:
                x = read_zip_csv(fh.read())
        except (zipfile.BadZipFile, pd.errors.ParserError, pd.errors.EmptyDataError) as e:
            bad.append(f"{f}: {e}")
            continue
        x["file_day"] = f[-14:-4]
        frames.append(x)
    df = pd.concat(frames, ignore_index=True)
    if "symbol" in df.columns:
        wrong_sym = int((df["symbol"].astype(str) != sym).sum())
        df = df[df["symbol"].astype(str) == sym]
    else:
        wrong_sym = -1
    df = df.rename(columns=MET_COLS)
    df["ts"] = pd.to_datetime(df["ts"].astype(str), utc=True).dt.as_unit("ns")
    for c in ["oi", "oi_value", "toptrader_ls_accounts", "toptrader_ls_positions",
              "global_ls_accounts", "taker_ls_vol_ratio"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    n_raw = len(df)
    vals = ["oi", "oi_value", "toptrader_ls_accounts", "toptrader_ls_positions",
            "global_ls_accounts", "taker_ls_vol_ratio"]
    exact = df.duplicated(["ts"] + vals)
    df = df[~exact]
    conflict = df.duplicated("ts", keep=False)
    n_conflict_stamps = int(df.loc[conflict, "ts"].nunique())
    # conflicting duplicates: keep the row whose file_day equals the stamp's date, then the last
    df["same_day"] = df["ts"].dt.strftime("%Y-%m-%d") == df["file_day"]
    df = df.sort_values(["ts", "same_day"]).drop_duplicates("ts", keep="last")
    off_day = int((~df["same_day"]).sum())
    df = df.drop(columns=["same_day"]).sort_values("ts")
    # Measured stamp convention (stampscan/stamp1m, report section 4): rows stamped before
    # 2024-03-04 00:00 UTC are snapshots AT the stamp (taker ratio over [T-5m, T)); from that
    # instant on, the row stamped T is the snapshot at T+5m (taker ratio over [T, T+5m)).
    shift = (df["ts"] >= STAMP_SWITCH).to_numpy()
    df["snap_ts"] = df["ts"] + pd.to_timedelta(np.where(shift, 5, 0), unit="min")
    df["oi_ok"], flag_counts = oi_validity(df["ts"].to_numpy(), df["oi"].to_numpy())
    os.makedirs(MET_DIR, exist_ok=True)
    df[["ts", "snap_ts", "file_day", "oi_ok"] + vals].to_parquet(met_path(sym), index=False)
    chk = load_metrics(sym)
    info = {"symbol": sym, "files": len(files), "bad_files": bad, "rows_raw": n_raw,
            "exact_dup_rows": int(exact.sum()), "conflicting_dup_stamps": n_conflict_stamps,
            "rows_stamped_outside_file_day": off_day, "wrong_symbol_rows": wrong_sym,
            "rows": len(chk), "first": str(chk.index.min()), "last": str(chk.index.max()),
            "unique": bool(chk.index.is_unique), "oi_flags": flag_counts,
            "oi_ok_rows": int(chk["oi_ok"].sum())}
    print(json.dumps(info), flush=True)
    with open(os.path.join(MET_DIR, f"{sym}.consolidate.json"), "w") as f:
        json.dump(info, f)
    return info


def oi_validity(ts: np.ndarray, oi: np.ndarray, ramp_tol: float = 0.03,
                spike: float = 0.4, max_gap_min: int = 30) -> tuple:
    """Backward-looking OI row validity (each row judged from rows at or before it only).
    - oi <= 0 or NaN: bad ('zero'), and starts a restart ramp;
    - a gap > max_gap_min since the previous row starts a ramp;
    - in a ramp a row is bad ('ramp') until |ln(oi / previous row's oi)| <= ramp_tol
      (the feed ramps up over 20-30 minutes after an outage, e.g. BTC 2021-05-22 05:15-05:40);
    - outside a ramp a row is bad ('spike') if |ln(oi / last good oi)| > spike, unless the
      previous row was also a spike within ramp_tol of this one (a real new level, accepted
      from its second row on)."""
    n = len(oi)
    ok = np.zeros(n, bool)
    cnt = {"zero": 0, "ramp": 0, "spike": 0, "gap_restarts": 0}
    gap = np.diff(ts.astype("datetime64[ns]")).astype("timedelta64[m]").astype(np.int64)
    in_ramp, last_ok, prev, prev_spike = True, np.nan, np.nan, False
    for i in range(n):
        x = oi[i]
        if i > 0 and gap[i - 1] > max_gap_min:
            in_ramp = True
            cnt["gap_restarts"] += 1
        if not (x > 0):
            cnt["zero"] += 1
            in_ramp, prev, prev_spike = True, np.nan, False
            continue
        if in_ramp:
            if prev > 0 and abs(np.log(x / prev)) <= ramp_tol:
                ok[i], in_ramp, last_ok = True, False, x
            elif not (prev > 0) and not (last_ok > 0):
                ok[i], in_ramp, last_ok = True, False, x        # very first row of the file set
            else:
                cnt["ramp"] += 1
            prev = x
            continue
        if last_ok > 0 and abs(np.log(x / last_ok)) > spike:
            if prev_spike and abs(np.log(x / prev)) <= ramp_tol:
                ok[i], last_ok, prev_spike = True, x, False
            else:
                cnt["spike"] += 1
                prev_spike = True
        else:
            ok[i], last_ok, prev_spike = True, x, False
        prev = x
    return ok, cnt


def load_metrics(sym: str) -> pd.DataFrame:
    """Consumer loader: UTC index = raw row stamp (create_time); column snap_ts = the
    measured time of the OI snapshot (stamp before 2024-03-04, stamp + 5 min after).
    Raw values, nothing filled. Use oi_at() rather than the raw index for decisions."""
    df = pd.read_parquet(met_path(sym))
    df.index = pd.DatetimeIndex(df.pop("ts")).as_unit("ns")
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index.name = "ts"
    if "snap_ts" in df.columns:
        sn = pd.DatetimeIndex(df["snap_ts"]).as_unit("ns")
        df["snap_ts"] = sn.tz_localize("UTC") if sn.tz is None else sn
    return df.sort_index()


def oi_at(met: pd.DataFrame, times: pd.DatetimeIndex, lag: str = "5min",
          max_age: str = "30min", col: str = "oi") -> pd.Series:
    """Value from the latest SNAPSHOT taken at or before time - lag (snap_ts, which
    corrects the 2024-03-04 stamp-convention switch); NaN if that snapshot is older than
    max_age (a gap) or the value is non-positive."""
    s = met[col].where(met[col] > 0)
    if "oi_ok" in met.columns and col in ("oi", "oi_value"):
        s = s.where(met["oi_ok"].astype(bool))
    s.index = pd.DatetimeIndex(met["snap_ts"]) if "snap_ts" in met.columns else met.index
    s = s.dropna().sort_index()
    s = s[~s.index.duplicated(keep="last")]
    q = pd.DatetimeIndex(times) - pd.Timedelta(lag)
    pos = s.index.searchsorted(q, side="right") - 1
    ok = pos >= 0
    vals = np.full(len(q), np.nan)
    idxv = s.index.values
    good = ok.copy()
    good[ok] = (q.values[ok] - idxv[pos[ok]]) <= np.timedelta64(pd.Timedelta(max_age))
    vals[good] = s.values[pos[good]]
    return pd.Series(vals, index=times)


# ---------------------------------------------------------------- validation

def validate_symbol(sym: str) -> dict:
    out = {"symbol": sym}
    if os.path.exists(k1h_path(sym)):
        k = load_um1h(sym)
        d = k.index.to_series().diff()
        gaps = d[d > pd.Timedelta("1h")]
        lr = np.log(k["close"]).diff()
        bad_ohlc = int(((k["high"] < k[["open", "close"]].max(axis=1)) |
                        (k["low"] > k[["open", "close"]].min(axis=1)) | (k["low"] <= 0)).sum())
        tb = (k["taker_buy_base"] > k["volume"] * (1 + 1e-9)).sum()
        out.update({
            "k_first": str(k.index.min()), "k_last": str(k.index.max()), "k_rows": len(k),
            "k_gaps": len(gaps), "k_missing_hours": int((gaps / pd.Timedelta("1h") - 1).sum()),
            "k_largest_gap_h": float(gaps.max() / pd.Timedelta("1h")) if len(gaps) else 0.0,
            "k_nonpos_or_bad_ohlc": bad_ohlc, "k_zero_vol_bars": int((k["volume"] <= 0).sum()),
            "k_taker_gt_vol": int(tb), "k_max_abs_1h_logret": float(lr.abs().max()),
            "k_max_ret_at": str(lr.abs().idxmax()) if lr.notna().any() else "",
            "k_bars_abs_ret_gt_25pct": int((lr.abs() > np.log(1.25)).sum()),
        })
    if os.path.exists(met_path(sym)):
        m = load_metrics(sym)
        st = m.index
        off_grid = int(((st - st.floor("5min")) != pd.Timedelta(0)).sum())
        d = st.to_series().diff()
        g = d[d > pd.Timedelta("5min")]
        days_present = pd.Index(m["file_day"].unique())
        all_days = pd.date_range(st.min().floor("D"), st.max().floor("D"), freq="D").strftime("%Y-%m-%d")
        missing_days = sorted(set(all_days) - set(days_present))
        per_day = m.groupby(m.index.floor("D")).size()
        lo = np.log(m["oi"].where(m["oi"] > 0)).diff()
        dt = m.index.to_series().diff() == pd.Timedelta("5min")
        jumps = lo[dt & (lo.abs() > np.log(1.5))]
        out.update({
            "m_first": str(st.min()), "m_last": str(st.max()), "m_rows": len(m),
            "m_off_5min_grid": off_grid, "m_gaps": len(g),
            "m_missing_5m_rows": int((g / pd.Timedelta("5min") - 1).sum()),
            "m_largest_gap_h": float(g.max() / pd.Timedelta("1h")) if len(g) else 0.0,
            "m_missing_days": len(missing_days), "m_missing_day_list": missing_days[:40],
            "m_days_lt_288": int((per_day < 288).sum()), "m_days_gt_288": int((per_day > 288).sum()),
            "m_oi_nonpos": int((m["oi"] <= 0).sum()), "m_oi_nan": int(m["oi"].isna().sum()),
            "m_oi_value_nonpos": int((m["oi_value"] <= 0).sum()),
            "m_ls_nan_rows": int(m[["toptrader_ls_accounts", "global_ls_accounts",
                                    "taker_ls_vol_ratio"]].isna().any(axis=1).sum()),
            "m_oi_5m_jumps_gt_50pct": len(jumps),
            "m_oi_jump_examples": [f"{t}:{v:+.2f}" for t, v in jumps.head(6).items()],
            "m_oi_flat_runs_ge_12": int(_flat_runs(m["oi"], 12)),
        })
        if os.path.exists(k1h_path(sym)):
            k = load_um1h(sym)
            # implied price = oi_value / oi vs 1h kline close at the stamp
            mm = m[m.index.minute == 0]
            px = mm["oi_value"] / mm["oi"]
            kc = k["close"].reindex(mm.index - pd.Timedelta("1h"))
            kc.index = mm.index
            ko = k["open"].reindex(mm.index)
            rel_c = (px / kc - 1).abs()
            rel_o = (px / ko - 1).abs()
            out.update({"m_px_vs_close_med_bp": float(1e4 * rel_c.median()),
                        "m_px_vs_open_med_bp": float(1e4 * rel_o.median()),
                        "m_px_rel_gt_5pct": int((rel_c > 0.05).sum())})
    return out


def _flat_runs(s: pd.Series, n: int) -> int:
    """Number of runs of >= n consecutive identical OI values (a stuck feed)."""
    same = s.diff() == 0
    grp = (~same).cumsum()
    runs = same.groupby(grp).sum()
    return int((runs >= n).sum())


# ---------------------------------------------------------------- stamp convention

def fetch_5m(sym: str, month: str) -> pd.DataFrame:
    raw = http_get(f"{BASE}/futures/um/monthly/klines/{sym}/5m/{sym}-5m-{month}.zip")
    d = read_zip_csv(raw).iloc[:, :11]
    d.columns = KLINE_COLS[:11]
    t = d["open_time"].astype("int64")
    t = t // 1000 if t.iloc[0] > 10 ** 14 else t
    d.index = pd.DatetimeIndex(pd.to_datetime(t, unit="ms", utc=True)).as_unit("ns")
    return d.drop(columns=["open_time", "close_time"]).astype(float)


def stampcheck(syms: list[str], months_list: list[str]) -> pd.DataFrame:
    """Which 5m kline (by open time, offset from the metrics stamp T) does each metrics
    row describe?  (a) taker_ls_vol_ratio vs kline buy/sell taker ratio, exact-match share;
    (b) corr(|dOI_T|, volume of kline at T+off) where dOI_T = OI_T - OI_{T-5m}."""
    rows = []
    for sym in syms:
        m = load_metrics(sym)
        for mo in months_list:
            k = fetch_5m(sym, mo)
            kr = k["taker_buy_base"] / (k["volume"] - k["taker_buy_base"])
            mm = m[(m.index >= k.index.min()) & (m.index <= k.index.max())]
            if len(mm) < 1000:
                continue
            dabs = np.log(mm["oi"]).diff().abs()
            dabs = dabs[mm.index.to_series().diff() == pd.Timedelta("5min")]
            for off in range(-3, 3):
                sh = pd.Timedelta(minutes=5 * off)
                kk = kr.reindex(mm.index + sh)
                rel = (mm["taker_ls_vol_ratio"].to_numpy() / kk.to_numpy() - 1)
                match = np.nanmean(np.abs(rel) < 1e-3)
                vol = np.log(k["volume"]).reindex(dabs.index + sh).to_numpy()
                ok = np.isfinite(vol) & np.isfinite(dabs.to_numpy())
                c = np.corrcoef(dabs.to_numpy()[ok], vol[ok])[0, 1]
                rows.append({"symbol": sym, "month": mo, "offset_bars": off,
                             "kline_open_minus_stamp_min": 5 * off,
                             "taker_ratio_match_share": round(float(match), 4),
                             "corr_absdOI_logvol": round(float(c), 4)})
            print(f"stampcheck {sym} {mo} done", flush=True)
    return pd.DataFrame(rows)


def stampscan(sym: str, start: str, end: str) -> pd.DataFrame:
    """Day-by-day: share of metrics rows whose taker_ls_vol_ratio equals (rel. tol 1e-3) the
    5m kline buy/sell taker ratio of the window [T-5m, T) ('end' convention) or [T, T+5m)
    ('start' convention), plus the Pearson correlation of the two at each offset."""
    m = load_metrics(sym)
    rows = []
    for mo in months(start, end):
        k = fetch_5m(sym, mo)
        kr = k["taker_buy_base"] / (k["volume"] - k["taker_buy_base"])
        mm = m[(m.index >= k.index.min()) & (m.index <= k.index.max())]
        if mm.empty:
            continue
        r = mm["taker_ls_vol_ratio"]
        e = kr.reindex(mm.index - pd.Timedelta("5min")).to_numpy()
        s = kr.reindex(mm.index).to_numpy()
        df = pd.DataFrame({"end": np.abs(r.to_numpy() / e - 1) < 1e-3,
                           "start": np.abs(r.to_numpy() / s - 1) < 1e-3,
                           "r": r.to_numpy(), "ke": e, "ks": s}, index=mm.index)
        for day, g in df.groupby(df.index.floor("D")):
            rows.append({"symbol": sym, "day": str(day.date()), "rows": len(g),
                         "match_end": round(float(g["end"].mean()), 4),
                         "match_start": round(float(g["start"].mean()), 4),
                         "corr_end": round(float(np.corrcoef(np.log(g["r"]), np.log(g["ke"]))[0, 1]), 4)
                         if np.isfinite(np.log(g[["r", "ke"]])).all().all() else np.nan,
                         "corr_start": round(float(np.corrcoef(np.log(g["r"]), np.log(g["ks"]))[0, 1]), 4)
                         if np.isfinite(np.log(g[["r", "ks"]])).all().all() else np.nan})
        print(f"stampscan {sym} {mo}", flush=True)
    return pd.DataFrame(rows)


def stamp_1m(sym: str, month: str) -> pd.DataFrame:
    """Minute-level refinement: corr(|dlnOI_T|, ln sum of 1m volume over [T+o-5m, T+o)) for
    o = -10..+10 minutes. The peak o says when the OI snapshot stamped T was taken
    (o = 0: at T; o = +5: at T+5m)."""
    m = load_metrics(sym)
    a = binance_um_1m(sym, month)
    v5 = a["volume"].rolling(5).sum()                     # index = open of the LAST minute
    v5.index = v5.index + pd.Timedelta("1min")            # -> end of the 5-minute window
    mm = m[(m.index >= a.index.min()) & (m.index <= a.index.max())]
    d = np.log(mm["oi"]).diff().abs()
    d = d[mm.index.to_series().diff() == pd.Timedelta("5min")]
    rows = []
    for o in range(-10, 11):
        v = np.log(v5.reindex(d.index + pd.Timedelta(minutes=o))).to_numpy()
        ok = np.isfinite(v) & np.isfinite(d.to_numpy())
        rows.append({"symbol": sym, "month": month, "window_end_minus_stamp_min": o,
                     "corr": round(float(np.corrcoef(d.to_numpy()[ok], v[ok])[0, 1]), 4)})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- OI vs volume

def oi_volume_anomaly(sym: str) -> pd.DataFrame:
    """Share of hours with |OI_t - OI_{t-1h}| (coin units) > volume of that hour (coin units).
    OI_t = the snapshot taken exactly at the hour boundary t (snap_ts; no lag, data check)."""
    k = load_um1h(sym)
    m = load_metrics(sym)
    oi = m["oi"].where(m["oi"] > 0)
    oi.index = pd.DatetimeIndex(m["snap_ts"])
    oi = oi[~oi.index.duplicated(keep="last")].sort_index()
    oi = oi[(oi.index.minute == 0)]
    d = oi.diff()
    d = d[oi.index.to_series().diff() == pd.Timedelta("1h")]
    # hour (t-1h, t]: kline with open time t-1h
    vol = k["volume"].reindex(d.index - pd.Timedelta("1h")).to_numpy()
    df = pd.DataFrame({"absdoi": d.abs().to_numpy(), "vol": vol, "oi_prev": (oi.shift(1)).reindex(d.index).to_numpy()},
                      index=d.index).dropna()
    df["exceed"] = df["absdoi"] > df["vol"]
    df["ratio"] = df["absdoi"] / df["vol"].where(df["vol"] > 0)
    g = df.groupby(df.index.year).agg(hours=("exceed", "size"), exceed_share=("exceed", "mean"),
                                       ratio_med=("ratio", "median"),
                                       ratio_p99=("ratio", lambda x: x.quantile(0.99)))
    g["symbol"] = sym
    return g.reset_index(names="year")


# ---------------------------------------------------------------- cross vendor

def bybit_mt4_1m(sym: str, month: str) -> Optional[tuple]:
    """public.bybit.com/kline_for_metatrader4/<SYM>/<YYYY>/<SYM>_1_<YYYY-MM-01>_<YYYY-MM-last>.csv.gz
    Columns: 'YYYY.MM.DD HH:MM', open, high, low, close, volume (1m perp bars, clock unverified)."""
    y = month[:4]
    page = http_get(f"https://public.bybit.com/kline_for_metatrader4/{sym}/{y}/")
    if page is None:
        return None
    names = [n for n in re.findall(r'href="([^"]+\.csv\.gz)"', page.decode("utf-8", "replace"))
             if n.startswith(f"{sym}_1_{month}-")]
    if not names:
        return None
    raw = http_get(f"https://public.bybit.com/kline_for_metatrader4/{sym}/{y}/{names[0]}")
    b = pd.read_csv(io.BytesIO(raw), compression="gzip", header=None)
    b = b.iloc[:, :6]
    b.columns = ["stamp", "open", "high", "low", "close", "volume"]
    ts = pd.to_datetime(b["stamp"].astype(str), format="%Y.%m.%d %H:%M", utc=True)
    b.index = pd.DatetimeIndex(ts).as_unit("ns")
    b = b[["open", "high", "low", "close", "volume"]].astype(float)
    n0 = len(b)
    b = b[~b.index.duplicated(keep="last")].sort_index()
    return b, names[0], n0 - len(b)


def binance_um_1m(sym: str, month: str) -> pd.DataFrame:
    raw = http_get(f"{BASE}/futures/um/monthly/klines/{sym}/1m/{sym}-1m-{month}.zip")
    d = read_zip_csv(raw).iloc[:, :6]
    d.columns = KLINE_COLS[:6]
    t = d["open_time"].astype("int64")
    t = t // 1000 if t.iloc[0] > 10 ** 14 else t
    d.index = pd.DatetimeIndex(pd.to_datetime(t, unit="ms", utc=True)).as_unit("ns")
    return d.drop(columns=["open_time"]).astype(float)


def bybit_compare(syms: list[str], month_list: list[str]) -> pd.DataFrame:
    """Binance USDT-M perp vs Bybit USDT perp (MT4 1m export).
    1) clock: lag scan (Bybit shifted by L minutes) minimising RMS 1m log-close difference;
    2) at the best lag, aggregate Bybit 1m to 1h (label = open) and compare with Binance 1h:
       close difference, 1h-return correlation, 24h log-return difference, and agreement of
       the card's |R_24h| >= 5% flag (contemporaneous quantities only)."""
    rows = []
    for sym in syms:
        k = load_um1h(sym)
        for mo in month_list:
            got = bybit_mt4_1m(sym, mo)
            if got is None:
                print(f"bybit {sym} {mo}: none", flush=True)
                continue
            b, name, ndup = got
            a = binance_um_1m(sym, mo)
            la = np.log(a["close"])
            lb = np.log(b["close"])
            scan = {}

            def rms(L: int) -> float:
                x = lb.copy()
                x.index = x.index - pd.Timedelta(minutes=L)
                j = pd.concat([la, x], axis=1, join="inner").dropna()
                return float(np.sqrt(((j.iloc[:, 0] - j.iloc[:, 1]) ** 2).mean()) * 1e4)

            for L in range(-14 * 60, 14 * 60 + 1, 30):          # coarse: every 30 min, +-14 h
                scan[L] = rms(L)
            c = min(scan, key=scan.get)
            for L in range(c - 10, c + 11):                    # fine: every minute near the best
                scan[L] = rms(L)
            best = min(scan, key=scan.get)
            # re-stamp Bybit to UTC with the measured offset (Bybit stamp - best minutes)
            b = b.copy()
            b.index = b.index - pd.Timedelta(minutes=best)
            lb = np.log(b["close"])
            j = pd.concat([la.rename("a"), lb.rename("b")], axis=1, join="inner").dropna()
            d1 = (j["b"] - j["a"]) * 1e4
            h = b.resample("1h", label="left", closed="left").agg(
                {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}).dropna()
            kk = k.reindex(h.index)
            ok = kk["close"].notna().to_numpy()
            h, kk = h[ok], kk[ok]
            rel = (h["close"] / kk["close"] - 1) * 1e4
            top = rel.abs().sort_values(ascending=False).head(8).index
            det = pd.DataFrame({"symbol": sym, "hour_open": top, "binance_close": kk.loc[top, "close"].to_numpy(),
                                "bybit_close": h.loc[top, "close"].to_numpy(), "diff_bp": rel.loc[top].round(1).to_numpy(),
                                "binance_vol": kk.loc[top, "volume"].to_numpy(), "bybit_vol": h.loc[top, "volume"].to_numpy()})
            det.to_csv(os.path.join(OUT_DIR, "bybit_top_divergence.csv"), mode="a", index=False,
                       header=not os.path.exists(os.path.join(OUT_DIR, "bybit_top_divergence.csv")))
            r1b, r1k = np.log(h["close"]).diff(), np.log(kk["close"]).diff()
            r24b, r24k = np.log(h["close"]).diff(24), np.log(kk["close"]).diff(24)
            fb, fk = r24b.abs() >= 0.05, r24k.abs() >= 0.05
            both = r24b.notna() & r24k.notna()
            bin_minutes = len(a)
            exp_minutes = int(pd.Period(mo, "M").days_in_month * 1440)
            rows.append({
                "symbol": sym, "month": mo, "bybit_file": name, "bybit_1m_rows": len(b),
                "bybit_dup_stamps": ndup, "bybit_missing_minutes": exp_minutes - int(((b.index >= a.index.min()) & (b.index <= a.index.max())).sum()),
                "binance_1m_rows": bin_minutes, "binance_missing_minutes": exp_minutes - bin_minutes,
                "best_lag_min": best, "rms_bp_at_best": round(scan[best], 2),
                "rms_bp_at_best+-1": round(min(scan[best + 1], scan[best - 1]), 2),
                "rms_bp_at_best+-60": round(min(scan.get(best + 60, np.inf), scan.get(best - 60, np.inf)), 2),
                "rms_bp_at_0": round(scan[0], 2),
                "m1_absdiff_bp_med": round(float(d1.abs().median()), 2),
                "m1_absdiff_bp_p999": round(float(d1.abs().quantile(0.999)), 1),
                "m1_absdiff_bp_max": round(float(d1.abs().max()), 1),
                "m1_max_at": str(d1.abs().idxmax()),
                "h1_close_diff_bp_mean": round(float(rel.mean()), 2),
                "h1_close_absdiff_bp_med": round(float(rel.abs().median()), 2),
                "h1_close_absdiff_bp_p99": round(float(rel.abs().quantile(0.99)), 1),
                "h1_ret_corr": round(float(r1b.corr(r1k)), 5),
                "r24_absdiff_bp_med": round(float(1e4 * (r24b - r24k).abs().median()), 2),
                "r24_absdiff_bp_p99": round(float(1e4 * (r24b - r24k).abs().quantile(0.99)), 1),
                "r24_ge5pct_hours_binance": int((fk & both).sum()),
                "r24_ge5pct_hours_bybit": int((fb & both).sum()),
                "r24_ge5pct_disagree_hours": int(((fb != fk) & both).sum()),
                "vol_ratio_bybit_over_binance": round(float(h["volume"].sum() / kk["volume"].sum()), 3)})
            print(json.dumps(rows[-1]), flush=True)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- outcome-blind counts

def _expanding_rank_frac(x: np.ndarray, valid: np.ndarray, lag: int, min_hist: int) -> np.ndarray:
    """For each i: share of history values x[j], j <= i - lag and valid, that are <= x[i].
    NaN until the history holds min_hist values. Point-in-time: uses only j <= i - lag."""
    import bisect
    out = np.full(len(x), np.nan)
    hist: list = []
    for i in range(len(x)):
        j = i - lag
        if j >= 0 and valid[j]:
            bisect.insort(hist, x[j])
        if valid[i] and len(hist) >= min_hist:
            out[i] = bisect.bisect_right(hist, x[i]) / len(hist)
    return out


def coin_state(sym: str) -> pd.DataFrame:
    """Hourly decision bars t (= 1h bar CLOSE). Every column is known at t."""
    k = load_um1h(sym)
    m = load_metrics(sym)
    t = k.index + pd.Timedelta("1h")                    # close time of each bar
    full = pd.date_range(t.min(), t.max(), freq="1h")
    p = pd.Series(k["close"].to_numpy(), index=t).reindex(full)
    oi = oi_at(m, full, lag="5min", max_age="30min")
    lp, loi = np.log(p), np.log(oi)
    r1 = lp.diff()
    st = pd.DataFrame(index=full)
    st["R"] = lp - lp.shift(24)
    st["dOI"] = loi - loi.shift(24)
    st["dOI2"] = loi - loi.shift(2)
    # sigma: std of 1h log returns over the 30 days ending at t-24h, x sqrt(24)
    st["sigma"] = r1.shift(24).rolling(720, min_periods=600).std() * np.sqrt(24)
    valid = st["dOI"].notna().to_numpy()
    # history of 24h OI changes up to t-24h, at least 90 days of hourly values
    st["oi_rank"] = _expanding_rank_frac(st["dOI"].to_numpy(), valid, lag=24, min_hist=90 * 24)
    st["quote_vol"] = pd.Series(k["quote_volume"].to_numpy(), index=t).reindex(full)
    st["symbol"] = sym
    return st


def tier_a_mask(states: dict, univ: pd.DataFrame) -> dict:
    """Point-in-time Tier A membership per hour from the universe file's monthly ranks.
    fetch_edge_data_funding.compute_ranks ranks month m at its first instant from the 30
    days BEFORE it ([D-30d, D)) and requires >= 90 days of history, so month m's rank is
    known at every t inside month m. A decision bar closing exactly at 00:00 on the 1st is
    assigned to the month that just ended (t - 1ns), i.e. it uses the previous month's rank."""
    masks = {}
    for sym, st in states.items():
        r = univ[univ["symbol"] == sym].set_index("month")["rank"].astype(float)
        mon = (st.index - pd.Timedelta("1ns")).to_period("M").astype(str)
        rk = pd.Series(r.reindex(mon).to_numpy(), index=st.index)
        masks[sym] = ((rk >= 3) & (rk <= 40)).to_numpy()
    return masks


def run_counts(syms: list[str], univ_long: Optional[pd.DataFrame], explore_end: str = "2024-12-31",
               tag: str = "") -> None:
    """Outcome-blind funnel counts. univ_long given: Tier A mask (ranks 3-40, point-in-time);
    None: every held hour of the listed symbols counts (Tier B control, or no universe)."""
    os.makedirs(OUT_DIR, exist_ok=True)
    states = {}
    for s in syms:
        if not (os.path.exists(k1h_path(s)) and os.path.exists(met_path(s))):
            continue
        states[s] = coin_state(s)
        print(f"state {s}: {states[s]['oi_rank'].notna().sum()} ranked hours", flush=True)
    if univ_long is not None:
        masks = tier_a_mask(states, univ_long)
    else:
        masks = {s: np.ones(len(st), bool) for s, st in states.items()}
    big = []
    for s, st in states.items():
        x = st[masks[s] & st["oi_rank"].notna() & st["sigma"].notna() & st["R"].notna()].copy()
        big.append(x)
    allx = pd.concat(big)
    allx["date"] = allx.index.floor("D")
    allx["year"] = allx.index.year
    # eligible coin-years (coin-days with any eligible hour / 365)
    elig = allx.groupby(["year", "symbol"])["date"].nunique().groupby("year").sum() / 365.25
    exp = allx[allx.index <= pd.Timestamp(explore_end + " 23:59", tz="UTC")]
    exp_cy = exp.groupby("symbol")["date"].nunique().sum() / 365.25
    # calibrate q on the explore era only: coin-days with OI rank <= q per coin-year
    grid = [0.0005, 0.001, 0.0015, 0.002, 0.003, 0.004, 0.005, 0.0075, 0.01, 0.015, 0.02, 0.03, 0.05]
    cal = []
    for q in grid:
        cd = exp[exp["oi_rank"] <= q].groupby(["symbol", "date"]).ngroups
        cal.append({"q": q, "oi_coin_days": cd, "per_coin_year": cd / exp_cy})
    cal = pd.DataFrame(cal)
    cal.to_csv(os.path.join(OUT_DIR, "q_calibration.csv"), index=False)
    print(cal.to_string(), flush=True)
    picks = {}
    for target in (2, 4, 8):
        lq = np.log(cal["q"])
        pc = cal["per_coin_year"].clip(lower=1e-9)
        picks[target] = float(np.exp(np.interp(np.log(target), np.log(pc), lq)))
    rows = []
    for target, q in picks.items():
        for kk in (2, 3):
            tail = allx["oi_rank"] <= q
            bigR = allx["R"].abs() >= np.maximum(kk * allx["sigma"], 0.05)
            comp = allx["dOI2"] >= (2 / 24) * allx["dOI"]
            stages = {"S1_oi_tail": tail, "S2_tail_and_bigR": tail & bigR,
                      "S3_plus_completion": tail & bigR & comp,
                      "S3_down_flush(R<0)": tail & bigR & comp & (allx["R"] < 0),
                      "S3_up_flush(R>0)": tail & bigR & comp & (allx["R"] > 0),
                      "P_bigR_not_tail": bigR & ~tail,
                      "P_bigR_oi_up(dOI>=0)": bigR & (allx["dOI"] >= 0),
                      "P_bigR_down_not_tail": bigR & ~tail & (allx["R"] < 0)}
            for name, msk in stages.items():
                sub = allx[msk]
                cut = pd.Timestamp(explore_end + " 23:59", tz="UTC")
                parts = list(sub.groupby("year")) + [("explore", sub[sub.index <= cut]),
                                                     ("verdict", sub[sub.index > cut]), ("all", sub)]
                for yr, grp in parts:
                    rows.append({"target_per_coin_year": target, "q": round(q, 5), "k": kk,
                                 "stage": name, "year": yr, "hours": len(grp),
                                 "coin_days": grp.groupby(["symbol", "date"]).ngroups,
                                 "events_24h_cooling": _cooled(grp),
                                 "distinct_dates": grp["date"].nunique(),
                                 "coins": grp["symbol"].nunique()})
    res = pd.DataFrame(rows)
    res.to_csv(os.path.join(OUT_DIR, f"funnel_counts{tag}.csv"), index=False)
    cal.to_csv(os.path.join(OUT_DIR, f"q_calibration{tag}.csv"), index=False)
    pd.DataFrame({"year": elig.index, "eligible_coin_years": elig.to_numpy()}).to_csv(
        os.path.join(OUT_DIR, f"eligible_coin_years{tag}.csv"), index=False)
    print(json.dumps({"q_picks": picks, "explore_coin_years": exp_cy,
                      "coins": sorted(allx["symbol"].unique())}), flush=True)


def _cooled(grp: pd.DataFrame) -> int:
    """Entries after a 24h per-coin cooling period (first qualifying hour, then skip 24h)."""
    n = 0
    for _, g in grp.groupby("symbol"):
        last = None
        for t in g.index:
            if last is None or t - last >= pd.Timedelta("24h"):
                n += 1
                last = t
    return n


# ---------------------------------------------------------------- cli

def parse_syms(s: str) -> list[str]:
    if s == "ALL":
        syms = set()
        if os.path.isdir(K1H_DIR):
            syms |= {f[:-7] for f in os.listdir(K1H_DIR) if f.endswith(".csv.gz")}
        if os.path.isdir(MET_DIR):
            syms |= {f[:-8] for f in os.listdir(MET_DIR) if f.endswith(".parquet")}
        return sorted(syms)
    return [x.strip().upper() for x in s.split(",") if x.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["klines", "metrics", "consolidate", "symbols", "validate", "stampscan", "stamp1m", "klinepatch", "coverage", "clockcheck",
                                     "stampcheck", "oivol", "bybit", "counts"])
    ap.add_argument("--symbols", default="")
    ap.add_argument("--tier", default="A")
    ap.add_argument("--start", default="")
    ap.add_argument("--end", default="")
    ap.add_argument("--months", default="2021-05,2022-06,2023-03,2024-08")
    args = ap.parse_args()
    syms = parse_syms(args.symbols) if args.symbols else []
    os.makedirs(OUT_DIR, exist_ok=True)
    if args.kind == "klines":
        for s in syms:
            try:
                fetch_klines_1h(s, args.start or "2020-01", args.end or "2026-09")
            except (requests.RequestException, ValueError, KeyError) as e:
                print(f"{s}: FAILED {e}", flush=True)
    elif args.kind == "metrics":
        for s in syms:
            try:
                fetch_metrics(s, args.start or "2020-09-01", args.end or "2026-09-30")
            except requests.RequestException as e:
                print(f"{s}: FAILED {e}", flush=True)
    elif args.kind == "consolidate":
        for s in syms:
            if os.path.isdir(os.path.join(MRAW_DIR, s)) and os.listdir(os.path.join(MRAW_DIR, s)):
                consolidate_metrics(s)
    elif args.kind == "symbols":
        print(",".join(universe_symbols(args.tier)))
    elif args.kind == "validate":
        rows = [validate_symbol(s) for s in syms]
        df = pd.DataFrame(rows)
        df.to_json(os.path.join(OUT_DIR, "validate.json"), orient="records", indent=1)
        print(df.drop(columns=[c for c in df.columns if c.endswith("_list") or c.endswith("examples")],
                      errors="ignore").to_string())
    elif args.kind == "stampcheck":
        df = stampcheck(syms, args.months.split(","))
        df.to_csv(os.path.join(OUT_DIR, "stampcheck.csv"), index=False)
        print(df.to_string())
    elif args.kind == "coverage":
        rows = []
        for s in syms:
            r = {"symbol": s}
            if os.path.exists(k1h_path(s)):
                k = load_um1h(s)
                r.update({"k1h_first": str(k.index.min())[:13], "k1h_last": str(k.index.max())[:13],
                          "k1h_rows": len(k),
                          "k1h_gaps": int((k.index.to_series().diff() > pd.Timedelta("1h")).sum())})
                pj = os.path.join(K1H_DIR, f"{s}.patched.json")
                r["k1h_days_patched_from_daily"] = len(json.load(open(pj))["patched_from_daily"]) if os.path.exists(pj) else 0
            lj = os.path.join(MRAW_DIR, f"{s}.listing.json")
            if os.path.exists(lj):
                li = json.load(open(lj))["info"]
                r.update({"metrics_listed_first": li["first_listed"], "metrics_listed_last": li["last_listed"],
                          "metrics_listed_days": li["listed_days"]})
            if os.path.exists(met_path(s)):
                m = load_metrics(s)
                ci = json.load(open(os.path.join(MET_DIR, f"{s}.consolidate.json")))
                exp = m[m.index < "2025-01-01"]
                ver = m[m.index >= "2025-01-01"]
                r.update({"metrics_files_held": ci["files"], "metrics_rows": len(m),
                          "explore_rows": len(exp), "explore_days": exp["file_day"].nunique(),
                          "verdict_rows": len(ver), "verdict_days": ver["file_day"].nunique(),
                          "exact_dup_rows": ci["exact_dup_rows"], "oi_zero": ci["oi_flags"]["zero"],
                          "oi_ramp_flagged": ci["oi_flags"]["ramp"], "oi_spike_flagged": ci["oi_flags"]["spike"],
                          "oi_ok_rows": ci["oi_ok_rows"]})
            rows.append(r)
        df = pd.DataFrame(rows)
        df.to_csv(os.path.join(OUT_DIR, "coverage.csv"), index=False)
        print(df.to_string())
    elif args.kind == "clockcheck":
        # known event: US CPI 08:30 New York -> 12:30 UTC in EDT, 13:30 UTC in EST
        for mo, day, utc in [("2022-07", "2022-07-13", "12:30"), ("2022-11", "2022-11-10", "13:30")]:
            k = fetch_5m("BTCUSDT", mo)
            d = k.loc[day + " 10:00":day + " 16:00", "volume"].sort_values(ascending=False)
            print(f"{day} CPI expected bar open {utc} UTC; top-3 5m volume bars (open, UTC): "
                  f"{[(str(t)[11:16], round(v)) for t, v in d.head(3).items()]}")
    elif args.kind == "klinepatch":
        for s in syms:
            patch_klines_1h(s)
    elif args.kind == "stampscan":
        df = pd.concat([stampscan(s, args.start, args.end) for s in syms])
        df.to_csv(os.path.join(OUT_DIR, f"stampscan_{'_'.join(syms)}.csv"), index=False)
        mo = df.assign(month=df["day"].str[:7]).groupby(["symbol", "month"])[
            ["match_end", "match_start", "corr_end", "corr_start"]].mean().round(3)
        print(mo.to_string())
    elif args.kind == "stamp1m":
        df = pd.concat([stamp_1m(s, mo) for s in syms for mo in args.months.split(",")])
        df.to_csv(os.path.join(OUT_DIR, "stamp_1m.csv"), index=False)
        print(df.pivot_table(index="window_end_minus_stamp_min", columns=["symbol", "month"],
                             values="corr").to_string())
    elif args.kind == "oivol":
        df = pd.concat([oi_volume_anomaly(s) for s in syms if os.path.exists(met_path(s))])
        df.to_csv(os.path.join(OUT_DIR, "oi_vs_volume.csv"), index=False)
        print(df.to_string())
    elif args.kind == "bybit":
        df = bybit_compare(syms, args.months.split(","))
        df.to_csv(os.path.join(OUT_DIR, "bybit_compare.csv"), index=False)
        print(df.to_string())
    elif args.kind == "counts":
        # --tier A: Tier A mask from universe_pit.csv (ranks 3-40); --tier B: no mask (BTC/ETH)
        univ = load_universe_long() if (args.tier == "A" and os.path.exists(UNIVERSE)) else None
        if args.tier == "A" and univ is None:
            print("WARNING: universe_pit.csv absent: every listed symbol-hour treated as Tier A")
        if not syms:
            syms = [s for s in parse_syms("ALL") if s not in ("BTCUSDT", "ETHUSDT")]
        run_counts(syms, univ, tag=f"_tier{args.tier}")


def load_universe_long() -> pd.DataFrame:
    """Universe file -> long (symbol, month 'YYYY-MM', rank). Accepts long or wide layouts."""
    u = pd.read_csv(UNIVERSE, dtype={"month": str})
    if {"symbol", "month", "rank"} <= set(u.columns):
        u = u[["symbol", "month", "rank"]].copy()
        u["rank"] = pd.to_numeric(u["rank"], errors="coerce")
        return u
    rank_cols = [c for c in u.columns if re.search(r"\d{4}-\d{2}", c)]
    long = u.melt(id_vars=["symbol"], value_vars=rank_cols, var_name="month", value_name="rank")
    long["month"] = long["month"].str.extract(r"(\d{4}-\d{2})")[0]
    long["rank"] = pd.to_numeric(long["rank"], errors="coerce")
    return long.dropna(subset=["rank"])


if __name__ == "__main__":
    main()
