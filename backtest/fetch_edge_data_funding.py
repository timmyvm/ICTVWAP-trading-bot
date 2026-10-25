"""
H001 data (tail-funding cash-and-carry): point-in-time universe, funding, spot, premium index.

Extends backtest/fetch_binance_archive.py (same archive, same conventions: epoch-second
`timestamp` columns, ms/us unit detection, re-load of every saved artifact through its loader).
Data lands under backtest/data_cache/local/edge/ (gitignored; rebuild with the commands below).

    pip install pytz        # backtest.bracket_experiment (a consumer loader) imports it
    python3 backtest/fetch_edge_data_funding.py universe                        # ~40 min, 21k files
    python3 backtest/fetch_edge_data_funding.py funding --top 60 --only-rank 60 # ~12 min
    python3 backtest/fetch_edge_data_funding.py spot --coverage-only --top 60   # ~1 min
    python3 backtest/fetch_edge_data_funding.py bybit --top 60                  # ~1 min (public.bybit.com)
    python3 backtest/fetch_edge_data_funding.py counts                          # offline, ~3 min
    (checks: bybit-compare, clock-check, depth, formula-check; see research/data_reports/H001_carry_data.md)

Every command is resumable: raw zips are cached under edge/raw/ and only missing files are
fetched. Downloaded files are untrusted data: they are parsed with zipfile + pandas only.
Politeness: at most 4 requests in flight (--workers), a small per-request delay, retries with
exponential backoff on 429/5xx/connection errors.

Conventions (verified, see research/data_reports/H001_carry_data.md):
- USDT-M kline open_time is ms (files from 2025 carry a header row); spot kline open_time is
  MICROSECONDS from 2025-01. Detected per file by magnitude.
- Bars are labelled by OPEN time, UTC.
- fundingRate files: calc_time (ms, a few ms of jitter after the settlement instant),
  funding_interval_hours, last_funding_rate. Positive rate: longs pay shorts.
"""

from __future__ import annotations

import argparse
import io
import os
import re
import sys
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, ".")

from backtest.fetch_binance_archive import BASE, KLINE_COLS, epoch_seconds, months  # noqa: E402

LISTING = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
OUT = "backtest/data_cache/local/edge"
RAW = os.path.join(OUT, "raw")
DATA_END = "2026-09"          # last complete monthly archive month at build time
RANK_START = "2020-01"

# ---------------------------------------------------------------- symbol classification
STABLE_BASES = {"USDC", "BUSD", "TUSD", "USDP", "FDUSD", "DAI", "USDE", "USD1", "PYUSD", "RLUSD",
                "XUSD", "AEUR", "EUR", "GBP", "AUD", "UST", "USTC", "SUSD", "USDS", "BFUSD",
                "EURI", "U", "USDD", "FRAX", "LUSD", "GUSD", "PAX"}
INDEX_BASES = {"BTCDOM", "DEFI", "FOOTBALL", "BLUEBIRD", "ALL"}
# TradFi / commodity perps and commodity-backed tokens (spot-tracking a non-crypto asset)
TRADFI_BASES = {"XAU", "XAG", "XPT", "XPD", "PAXG", "XAUT", "TSLA", "MSTR", "COIN", "HOOD",
                "NVDA", "AAPL", "AMZN", "GOOGL", "META", "MSFT", "SPY", "QQQ", "CRCL", "CL",
                "NATGAS", "BRENT", "WTI", "COPPER", "EWY", "EWJ", "TLT", "IWM", "GLD", "SLV",
                "INTC", "AMD", "PLTR", "ORCL", "NFLX", "BABA", "SNOW", "UBER", "GME", "AMC",
                "NDX", "DJI",          # NOT "SPX": SPXUSDT is the SPX6900 meme coin (2024-12) "SPCE", "MCD", "JPM", "V", "MA", "BRK", "XOM", "GOLD", "SILVER",
                # 2025-26 Binance TradFi wave (equities, ETFs, leveraged ETFs, Asian stocks, FX).
                # Curated by name from the archive listing; all first appear in 2025 or later.
                "AAOI", "ACN", "ADBE", "ALAB", "AMAT", "ANET", "APLD", "APP", "ARM", "ASML", "ASTS",
                "AVGO", "AXTI", "BITO", "BMNR", "BRKB", "BZ", "CIEN", "COHR", "COST", "CRDO", "CRM",
                "CRWD", "CRWV", "CSCO", "CSOPSAMSUNG2L", "CSOPSKHYNIX2L", "CVNA", "CXMT", "DDOG",
                "DELL", "DIS", "DJT", "DKNG", "DRAM", "EBAY", "EWZ", "FLNC", "GDX", "GEV", "GLW",
                "GPRO", "GS", "GTLB", "HANMI", "HIMS", "HK0625", "HK0700", "HK0992", "HK1810", "HPE",
                "HUT", "HYUNDAI", "IBM", "IONQ", "IREN", "KLAC", "KO", "KODEX200", "KORU", "KUAISHOU",
                "LGELECTRONICS", "LITE", "LLY", "LRCX", "MARA", "MDB", "MEITUAN", "MRK", "MRNA", "MRVL",
                "MU", "MVLL", "NAVER", "NBIS", "NET", "NKE", "NOK", "NOW", "NVDL", "NVO", "OKLO", "ONDS",
                "PANW", "PDD", "PYPL", "QCOM", "RDDT", "RIVN", "RKLB", "SAMSUNG", "SAMSUNGEM", "SHOP",
                "SKHY", "SKHYNIX", "SMCI", "SMH", "SNDK", "SOFI", "SONY", "SOXL", "SOXS", "SQQQ", "TEM",
                "TENCENT", "TER", "TMF", "TQQQ", "TSLL", "TSM", "TTWO", "TXN", "TZA", "UNH", "URNM",
                "USDBRL", "UVXY", "WDC", "WMT", "XBI", "XLE", "ZM", "ZS", "BYD", "SKUU", "SNXX", "STXX",
                "TBT", "SKDD", "SPCX", "OPENAI", "ANTHROPIC", "ZHIPU", "MINIMAX", "UNITREE", "CBRS",
                "CRML", "USAR", "ZHONGJI", "POPMART", "PLTR", "INTW", "BE"}
MULT_PREFIX = re.compile(r"^(1000000|100000|10000|1000|1M)(?=[A-Z])")
# Known ticker changes on Binance USDT-M (old -> new). Each ticker is its own instrument in
# the universe; this table exists so a holding window that spans a change is flagged.
REBRANDS = {
    "MATICUSDT": "POLUSDT", "RNDRUSDT": "RENDERUSDT", "FTMUSDT": "SUSDT", "TOMOUSDT": "VICUSDT",
    "LUNAUSDT": "LUNA2USDT (new chain; old LUNA -> 1000LUNCUSDT)", "OCEANUSDT": "FETUSDT (ASI merger)",
    "AGIXUSDT": "FETUSDT (ASI merger)", "EOSUSDT": "AUSDT", "MKRUSDT": "SKYUSDT",
    "LENDUSDT": "AAVEUSDT", "KEEPUSDT": "TUSDT", "NUUSDT": "TUSDT", "MCUSDT": "BEAMXUSDT",
    "BTTUSDT": "1000BTTCUSDT (redenomination)", "XEMUSDT": "-", "HNTUSDT": "-",
}


def classify(symbol: str) -> tuple[str, str, int, str]:
    """-> (quote, base_after_multiplier, multiplier, exclusion_reason or '')."""
    if "_" in symbol:
        return "", symbol, 1, "dated_delivery"
    quote = next((q for q in ("USDT", "USDC", "BUSD") if symbol.endswith(q)), "")
    if not quote:
        return "", symbol, 1, "non_usd_quote"
    base = symbol[: -len(quote)]
    mult = 1
    m = MULT_PREFIX.match(base)
    if m:
        p = m.group(1)
        mult = 1_000_000 if p == "1M" else int(p)
        base = base[len(p):]
    if quote != "USDT":
        return quote, base, mult, f"quote_{quote}"
    if base in STABLE_BASES:
        return quote, base, mult, "stablecoin_base"
    if base in INDEX_BASES:
        return quote, base, mult, "index_contract"
    if base in TRADFI_BASES:
        return quote, base, mult, "tradfi_commodity"
    return quote, base, mult, ""


# ---------------------------------------------------------------- polite HTTP
class Http:
    def __init__(self, workers: int = 4, delay: float = 0.05, retries: int = 6):
        self.workers, self.delay, self.retries = workers, delay, retries
        self.local = threading.local()
        self.n_req = 0
        self.lock = threading.Lock()

    def _session(self) -> requests.Session:
        s = getattr(self.local, "s", None)
        if s is None:
            s = requests.Session()
            s.headers["User-Agent"] = "edge-lab-data/1.0 (research; polite)"
            self.local.s = s
        return s

    def get(self, url: str) -> Optional[bytes]:
        """bytes, or None on 404. Raises after `retries` failures."""
        back = 1.0
        for attempt in range(self.retries):
            try:
                time.sleep(self.delay)
                r = self._session().get(url, timeout=60)
                with self.lock:
                    self.n_req += 1
                if r.status_code == 404:
                    return None
                if r.status_code in (429, 418) or r.status_code >= 500:
                    raise requests.HTTPError(f"HTTP {r.status_code}")
                r.raise_for_status()
                return r.content
            except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as e:
                if attempt == self.retries - 1:
                    raise
                print(f"  retry {attempt + 1} {url[-70:]}: {e}", flush=True)
                time.sleep(back)
                back = min(back * 2, 30)
        return None

    def map(self, fn, items, label: str = ""):
        items = list(items)
        out = []
        t0 = time.time()
        with ThreadPoolExecutor(self.workers) as ex:
            for i, res in enumerate(ex.map(fn, items)):
                out.append(res)
                if (i + 1) % 500 == 0 or i + 1 == len(items):
                    print(f"  {label} {i + 1}/{len(items)} ({time.time() - t0:.0f}s)", flush=True)
        return out


def _listing(http: Http, prefix: str, delimiter: bool) -> list[str]:
    """All CommonPrefixes (delimiter=True) or Keys (False) under prefix, paginated by marker."""
    got: list[str] = []
    marker = ""
    while True:
        url = f"{LISTING}?prefix={prefix}&marker={marker}" + ("&delimiter=/" if delimiter else "")
        body = http.get(url)
        if body is None:
            return got
        txt = body.decode("utf-8", "replace")
        if delimiter:
            page = [p for p in re.findall(r"<Prefix>([^<]+)</Prefix>", txt) if p != prefix]
        else:
            page = re.findall(r"<Key>([^<]+)</Key>", txt)
        got += page
        if "<IsTruncated>true</IsTruncated>" not in txt or not page:
            return got
        nm = re.search(r"<NextMarker>([^<]+)</NextMarker>", txt)
        marker = nm.group(1) if nm else page[-1]


def list_symbols(http: Http, path: str) -> list[str]:
    """Symbols (directory names) under e.g. data/futures/um/monthly/klines/."""
    return sorted(p.rstrip("/").split("/")[-1] for p in _listing(http, path, True))


def list_month_sizes(http: Http, path: str) -> dict[str, int]:
    """{YYYY-MM: zip size in bytes} for a monthly per-symbol directory (one listing call)."""
    out: dict[str, int] = {}
    marker = ""
    while True:
        body = http.get(f"{LISTING}?prefix={path}&marker={marker}")
        if body is None:
            return out
        txt = body.decode("utf-8", "replace")
        pairs = re.findall(r"<Key>([^<]+)</Key>.*?<Size>(\d+)</Size>", txt)
        for k, sz in pairs:
            m = re.search(r"-(\d{4}-\d{2})\.zip$", k)
            if m:
                out[m.group(1)] = int(sz)
        if "<IsTruncated>true</IsTruncated>" not in txt or not pairs:
            return out
        marker = pairs[-1][0]


def list_months(http: Http, path: str) -> list[str]:
    """YYYY-MM of every .zip (CHECKSUM ignored) under a monthly per-symbol directory."""
    keys = [k for k in _listing(http, path, False) if k.endswith(".zip")]
    return sorted({m.group(1) for k in keys if (m := re.search(r"-(\d{4}-\d{2})\.zip$", k))})


# ---------------------------------------------------------------- raw cache + parsing
def raw_get(http: Http, url: str, dest: str) -> Optional[str]:
    """Download url to dest once (resumable). Returns dest, or None if the archive has no file."""
    if os.path.exists(dest):
        return dest
    miss = dest + ".404"
    if os.path.exists(miss):
        return None
    body = http.get(url)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    if body is None:
        open(miss, "w").close()
        return None
    tmp = dest + ".part"
    with open(tmp, "wb") as f:
        f.write(body)
    os.replace(tmp, dest)
    return dest


def read_zip_csv(path: str) -> pd.DataFrame:
    """Parse one archive zip (single CSV, optional header row) with pandas only."""
    with zipfile.ZipFile(path) as z:
        raw = z.read(z.namelist()[0])
    first = raw.split(b"\n", 1)[0]
    header = 0 if first.split(b",")[0].strip(b'"').replace(b"_", b"").isalpha() else None
    return pd.read_csv(io.BytesIO(raw), header=header)


def parse_klines(path: str) -> pd.DataFrame:
    d = read_zip_csv(path).iloc[:, :12]
    d.columns = KLINE_COLS
    t = d["open_time"].astype("int64")
    unit_us = bool((t > 10**14).any())
    if unit_us:
        t = t // 1000                      # microseconds (spot files from 2025-01)
    d["open_time"] = t
    d["unit_us"] = unit_us
    return d


def kline_frame(paths: list[str]) -> pd.DataFrame:
    frames = [parse_klines(p) for p in paths]
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    ts = pd.DatetimeIndex(pd.to_datetime(df["open_time"], unit="ms", utc=True))
    out = pd.DataFrame({
        "timestamp": np.asarray(epoch_seconds(ts)),
        "open": df["open"].astype(float).to_numpy(), "high": df["high"].astype(float).to_numpy(),
        "low": df["low"].astype(float).to_numpy(), "close": df["close"].astype(float).to_numpy(),
        "volume": df["volume"].astype(float).to_numpy(),
        "quote_volume": df["quote_volume"].astype(float).to_numpy(),
        "trades": df["trades"].astype("int64").to_numpy(),
    })
    n0 = len(out)
    out = out.drop_duplicates("timestamp").sort_values("timestamp").reset_index(drop=True)
    out.attrs["dup_dropped"] = n0 - len(out)
    return out


def load_klines(path: str) -> pd.DataFrame:
    """Consumer loader for edge kline caches: UTC open-time index, float columns."""
    f = pd.read_csv(path)
    idx = pd.DatetimeIndex(pd.to_datetime(f["timestamp"], unit="s", utc=True), name="open_time")
    return f.drop(columns=["timestamp"]).set_index(idx)


# ---------------------------------------------------------------- 1. universe
UM_KL = "data/futures/um/monthly/klines/"
SPOT_KL = "data/spot/monthly/klines/"


def build_universe(http: Http, start: str, end: str, screen_k: int = 0):
    os.makedirs(OUT, exist_ok=True)
    print("listing USDT-M kline symbols ...", flush=True)
    um_syms = list_symbols(http, UM_KL)
    print(f"  {len(um_syms)} um symbols; listing spot symbols ...", flush=True)
    spot_syms = set(list_symbols(http, SPOT_KL))
    print(f"  {len(spot_syms)} spot symbols", flush=True)

    rows = []
    for s in um_syms:
        quote, base, mult, excl = classify(s)
        rows.append({"symbol": s, "quote": quote, "base": base, "multiplier": mult, "excluded": excl})
    sym = pd.DataFrame(rows)
    keep = sym.loc[sym["excluded"] == "", "symbol"].tolist()
    print(f"  {len(keep)} USDT perps pass the category filter; listing their 1d months ...", flush=True)

    mlist = http.map(lambda s: list_months(http, f"{UM_KL}{s}/1d/"), keep, "list1d")
    mon = dict(zip(keep, mlist))
    sym["first_month"] = sym["symbol"].map(lambda s: mon[s][0] if mon.get(s) else "")
    sym["last_month"] = sym["symbol"].map(lambda s: mon[s][-1] if mon.get(s) else "")
    sym["n_months"] = sym["symbol"].map(lambda s: len(mon.get(s, [])))
    sym["spot_symbol"] = sym.apply(lambda r: f"{r['base']}USDT" if r["quote"] else "", axis=1)
    sym["listed_spot"] = sym["spot_symbol"].isin(spot_syms)
    sym.to_csv(os.path.join(OUT, "universe_symbols.csv"), index=False)   # interim, rewritten below

    # Activity pre-screen (cost control): the monthly aggTrades zip size is a trade-count proxy
    # read from ONE listing call per symbol. A symbol-month's 1d file is fetched only if the
    # symbol's size rank is <= screen_k in that month or an adjacent month (or if it has no
    # aggTrades file). The screen's safety is checked after ranking: the worst size rank of any
    # symbol that made rank_any <= 120 is reported (must sit well inside screen_k).
    lo = str(pd.Period(start, "M") - 1)
    print("  listing aggTrades sizes (activity pre-screen) ...", flush=True)
    sz = http.map(lambda s: list_month_sizes(http, f"data/futures/um/monthly/aggTrades/{s}/"), keep, "listAgg")
    agg = pd.DataFrame([{"symbol": s, "month": m, "agg_bytes": b}
                        for s, d in zip(keep, sz) for m, b in d.items()])
    agg["size_rank"] = agg.groupby("month")["agg_bytes"].rank(ascending=False, method="first")
    agg.to_csv(os.path.join(OUT, "aggtrades_sizes.csv"), index=False)
    srank = {(r.symbol, r.month): r.size_rank for r in agg.itertuples()}

    def screened(s: str, m: str) -> bool:
        if s in ("BTCUSDT", "ETHUSDT") or screen_k <= 0:
            return True
        p = pd.Period(m, "M")
        rk = [srank.get((s, str(q))) for q in (p - 1, p, p + 1)]
        if srank.get((s, m)) is None:
            return True                      # no activity proxy: keep (conservative)
        return min(r for r in rk if r is not None) <= screen_k

    all_jobs = [(s, m) for s in keep for m in mon[s] if lo <= m <= end]
    jobs = [j for j in all_jobs if screened(*j)]
    print(f"  pre-screen keeps {len(jobs)} of {len(all_jobs)} symbol-months (screen_k={screen_k})", flush=True)
    pd.DataFrame(sorted(set(all_jobs) - set(jobs)), columns=["symbol", "month"]).to_csv(
        os.path.join(OUT, "universe_screened_out.csv"), index=False)
    jobset = set(jobs)
    mon = {s: [m for m in mon[s] if (s, m) in jobset] for s in keep}
    print(f"  downloading {len(jobs)} USDT-M 1d monthly files ...", flush=True)

    def job(sm):
        s, m = sm
        return raw_get(http, f"{BASE}/futures/um/monthly/klines/{s}/1d/{s}-1d-{m}.zip",
                       f"{RAW}/um1d/{s}/{s}-1d-{m}.zip")

    http.map(job, jobs, "um1d")
    _build_from_raw(sym, keep, mon, lo, start, end)


def fill_universe(http: Http, start: str, end: str):
    """Complete the 1d cache WITHOUT the activity pre-screen (every month between a kept symbol's
    first and last archive month), reusing universe_symbols.csv instead of re-listing. The
    aggTrades screen proved unsafe (a rank-58 coin had trade-count rank 318), so the published
    universe is built from this full pass."""
    sym = pd.read_csv(os.path.join(OUT, "universe_symbols.csv"), dtype={"first_month": str, "last_month": str})
    sym["excluded"] = sym["symbol"].map(lambda s: classify(s)[3])
    # symbols re-admitted by a classification change were never listed: list them now
    unl = sym.loc[(sym["excluded"] == "") & sym["first_month"].isna() & (sym["quote"] == "USDT"), "symbol"].tolist()
    for s_, ms in zip(unl, http.map(lambda x: list_months(http, f"{UM_KL}{x}/1d/"), unl, "list1d-new")):
        if ms:
            i = sym.index[sym["symbol"] == s_][0]
            sym.loc[i, ["first_month", "last_month", "n_months"]] = [ms[0], ms[-1], len(ms)]
    keep = sym.loc[(sym["excluded"] == "") & sym["first_month"].notna(), "symbol"].tolist()
    fl = sym.set_index("symbol")
    lo = str(pd.Period(start, "M") - 1)
    mon = {s: [m for m in months(fl.loc[s, "first_month"], fl.loc[s, "last_month"]) if lo <= m <= end] for s in keep}
    jobs = [(s, m) for s in keep for m in mon[s]]
    todo = [j for j in jobs if not os.path.exists(f"{RAW}/um1d/{j[0]}/{j[0]}-1d-{j[1]}.zip")
            and not os.path.exists(f"{RAW}/um1d/{j[0]}/{j[0]}-1d-{j[1]}.zip.404")]
    print(f"fill: {len(jobs)} symbol-months, {len(todo)} not yet cached", flush=True)

    def job(sm):
        s, m = sm
        return raw_get(http, f"{BASE}/futures/um/monthly/klines/{s}/1d/{s}-1d-{m}.zip",
                       f"{RAW}/um1d/{s}/{s}-1d-{m}.zip")

    http.map(job, todo, "um1d-fill")
    _build_from_raw(sym, keep, mon, lo, start, end)


def _build_from_raw(sym: pd.DataFrame, keep: list[str], mon: dict, lo: str, start: str, end: str):
    kdir = os.path.join(OUT, "klines_1d_um")
    os.makedirs(kdir, exist_ok=True)
    defects = []
    for s in keep:
        paths = sorted(p for m in mon[s] if lo <= m <= end
                       and os.path.exists(p := f"{RAW}/um1d/{s}/{s}-1d-{m}.zip"))
        if not paths:
            continue
        k = kline_frame(paths)
        k.to_csv(os.path.join(kdir, f"{s}.csv"), index=False)
        defects.append(kline_defects(s, k, step_s=86400))
    pd.DataFrame(defects).to_csv(os.path.join(OUT, "klines_1d_um_defects.csv"), index=False)
    sym.to_csv(os.path.join(OUT, "universe_symbols.csv"), index=False)
    ranks = compute_ranks(sym, kdir, start, end)
    ranks.to_csv(os.path.join(OUT, "universe_pit.csv"), index=False)

    # re-load through the consumer loader
    u = load_universe()
    print(f"saved+reloaded universe_pit.csv: {len(u)} symbol-months, {u['symbol'].nunique()} symbols, "
          f"months {u['month'].min()}..{u['month'].max()}, ranked rows {u['rank'].notna().sum()}")
    print(u.groupby(u["month"].str[:4])["symbol"].nunique().to_string())


def kline_defects(symbol: str, k: pd.DataFrame, step_s: int) -> dict:
    """Full-history sanity scan for one kline series (counts only; nothing is filled)."""
    t = k["timestamp"].to_numpy()
    d = np.diff(t)
    c = k["close"].to_numpy()
    r = np.abs(np.diff(np.log(np.where(c > 0, c, np.nan))))
    # trailing zombie run: final consecutive bars with zero volume or a frozen OHLC
    frozen = (k["volume"].to_numpy() == 0) | ((k["high"] == k["low"]) & (k["high"] == k["close"])).to_numpy()
    tail = 0
    for f in frozen[::-1]:
        if not f:
            break
        tail += 1
    return {
        "symbol": symbol, "rows": len(k),
        "first": pd.Timestamp(t[0], unit="s", tz="UTC") if len(t) else None,
        "last": pd.Timestamp(t[-1], unit="s", tz="UTC") if len(t) else None,
        "dup_dropped": k.attrs.get("dup_dropped", 0),
        "misaligned": int((t % step_s != 0).sum()),
        "gaps": int((d > step_s).sum()), "missing_bars": int(((d[d > step_s] // step_s) - 1).sum()),
        "nonpos_price": int((k[["open", "high", "low", "close"]] <= 0).any(axis=1).sum()),
        "hl_violation": int(((k["high"] < k[["open", "close"]].max(axis=1)) |
                             (k["low"] > k[["open", "close"]].min(axis=1))).sum()),
        "zero_vol_bars": int((k["volume"] == 0).sum()),
        "max_abs_logret": float(np.nanmax(r)) if len(r) else np.nan,
        "jumps_gt_50pct": int((r > np.log(1.5)).sum()),
        "trailing_frozen_bars": tail,
    }


def compute_ranks(sym: pd.DataFrame, kdir: str, start: str, end: str) -> pd.DataFrame:
    """Rank at the first instant of each month from the 30 days before it (no lookahead).

    turnover_med30 = median daily quote volume over [D-30d, D). A symbol is rankable in month
    m if it printed a bar with volume > 0 on day D-1 (tradable at D) and has >= 20 daily bars
    in the window. `rank` additionally requires >= 90 days of history (first bar <= D-90d);
    `rank_any` does not. BTC and ETH are ranked like any other symbol (card: control only).
    """
    rows = []
    kept = sym[sym["excluded"] == ""]
    series = {}
    for s in kept["symbol"]:
        p = os.path.join(kdir, f"{s}.csv")
        if os.path.exists(p):
            series[s] = load_klines(p)
    for m in months(start, end):
        D = pd.Timestamp(m + "-01", tz="UTC")
        for s, k in series.items():
            if k.index[0] >= D or k.index[-1] < D - pd.Timedelta(days=1):
                continue
            w = k.loc[(k.index >= D - pd.Timedelta(days=30)) & (k.index < D)]
            last = k.loc[k.index == D - pd.Timedelta(days=1)]
            alive = len(last) == 1 and float(last["volume"].iloc[0]) > 0
            rows.append({"month": m, "symbol": s, "n_days30": len(w), "alive": alive,
                         "turnover_med30": float(w["quote_volume"].median()) if len(w) else np.nan,
                         "hist_days": (D - k.index[0]).days})
    r = pd.DataFrame(rows)
    ok = r["alive"] & (r["n_days30"] >= 20)
    r["rank_any"] = np.nan
    r.loc[ok, "rank_any"] = r[ok].groupby("month")["turnover_med30"].rank(ascending=False, method="first")
    ok90 = ok & (r["hist_days"] >= 90)
    r["rank"] = np.nan
    r.loc[ok90, "rank"] = r[ok90].groupby("month")["turnover_med30"].rank(ascending=False, method="first")
    info = sym.set_index("symbol")[["first_month", "last_month", "listed_spot", "spot_symbol", "multiplier"]]
    r = r.join(info, on="symbol")
    r["in_universe_3_50"] = r["rank"].between(3, 50)
    cols = ["symbol", "month", "first_month", "last_month", "listed_spot", "spot_symbol", "multiplier",
            "alive", "hist_days", "n_days30", "turnover_med30", "rank_any", "rank", "in_universe_3_50"]
    return r[cols].sort_values(["month", "rank", "symbol"]).reset_index(drop=True)


def rerank(start: str, end: str):
    """Re-apply classify() and recompute ranks from the local 1d caches (no downloads)."""
    sym = pd.read_csv(os.path.join(OUT, "universe_symbols.csv"), dtype={"first_month": str, "last_month": str})
    sym["excluded"] = sym["symbol"].map(lambda s: classify(s)[3])
    sym.to_csv(os.path.join(OUT, "universe_symbols.csv"), index=False)
    ranks = compute_ranks(sym, os.path.join(OUT, "klines_1d_um"), start, end)
    ranks.to_csv(os.path.join(OUT, "universe_pit.csv"), index=False)
    u = load_universe()
    # screen safety: worst aggTrades size rank (previous month) of any symbol ranked <= 120
    agg = pd.read_csv(os.path.join(OUT, "aggtrades_sizes.csv"), dtype={"month": str})
    agg["next_month"] = (pd.PeriodIndex(agg["month"], freq="M") + 1).astype(str)
    v = u[u["rank_any"] <= 120].merge(agg, left_on=["symbol", "month"], right_on=["symbol", "next_month"],
                                       how="left", suffixes=("", "_agg"))
    print(f"screen check: worst prior-month aggTrades size rank among rank_any<=120: "
          f"{v['size_rank'].max():.0f} (p99 {v['size_rank'].quantile(.99):.0f}); "
          f"among rank_any<=60: {v.loc[v['rank_any'] <= 60, 'size_rank'].max():.0f}")
    print(f"saved+reloaded universe_pit.csv: {len(u)} rows, {u['symbol'].nunique()} symbols, "
          f"{u['month'].min()}..{u['month'].max()}; in_universe_3_50 rows {int(u['in_universe_3_50'].sum())}")
    excl = sym[sym["excluded"] != ""].groupby("excluded")["symbol"].apply(lambda x: " ".join(sorted(x)))
    excl.to_csv(os.path.join(OUT, "universe_excluded.csv"))
    print(excl.str.len().to_string())


def load_universe(path: str = os.path.join(OUT, "universe_pit.csv")) -> pd.DataFrame:
    """Consumer loader: one row per (symbol, month) the symbol traded at the month's start."""
    u = pd.read_csv(path, dtype={"month": str, "first_month": str, "last_month": str})
    for c in ("rank", "rank_any"):
        u[c] = u[c].astype("Float64")
    return u


def ever_top(n: int, start: str = "2020-01", end: str = DATA_END) -> list[str]:
    u = load_universe()
    u = u[(u["month"] >= start) & (u["month"] <= end)]
    return sorted(u.loc[(u["rank_any"] <= n) | (u["rank"] <= n), "symbol"].unique())


# ---------------------------------------------------------------- 2. funding
FUND_DIR = os.path.join(OUT, "funding")
FLOOR_8H = 0.0001        # Binance interest rate I = 0.01% per 8 h (= 0.03%/day pro rata)


def symbol_months(symbol: str, start: str, end: str) -> list[str]:
    s = pd.read_csv(os.path.join(OUT, "universe_symbols.csv"), dtype=str).set_index("symbol")
    fm, lm = s.loc[symbol, "first_month"], s.loc[symbol, "last_month"]
    return [m for m in months(max(fm, start), min(lm, end))]


def rank_months(n: int, buffer: int = 1) -> set[tuple[str, str]]:
    """(symbol, month) pairs within `buffer` months of a month with rank_any <= n."""
    u = load_universe()
    hit = u.loc[(u["rank_any"] <= n) | (u["rank"] <= n), ["symbol", "month"]]   # rank <= rank_any is not
    # guaranteed to be inside rank_any <= n: fresh listings (< 90 d) push seasoned coins down rank_any
    out = set()
    for s, m in hit.itertuples(index=False):
        p = pd.Period(m, "M")
        for b in range(-buffer, buffer + 1):
            out.add((s, str(p + b)))
    return out


def fetch_funding_all(http: Http, syms: list[str], start: str, end: str, only_rank: int = 0):
    keep = rank_months(only_rank) if only_rank else None
    jobs = [(s, m) for s in syms for m in symbol_months(s, start, end) if keep is None or (s, m) in keep]
    print(f"funding: {len(syms)} symbols, {len(jobs)} monthly files", flush=True)

    def job(sm):
        s, m = sm
        return raw_get(http, f"{BASE}/futures/um/monthly/fundingRate/{s}/{s}-fundingRate-{m}.zip",
                       f"{RAW}/funding/{s}/{s}-fundingRate-{m}.zip")

    http.map(job, jobs, "funding")
    os.makedirs(FUND_DIR, exist_ok=True)
    reports, panel = [], []
    for s in syms:
        paths = sorted(p for m in symbol_months(s, start, end)
                       if os.path.exists(p := f"{RAW}/funding/{s}/{s}-fundingRate-{m}.zip"))
        if not paths:
            reports.append({"symbol": s, "rows": 0})
            continue
        f, rep = build_funding(s, paths)
        f.to_csv(os.path.join(FUND_DIR, f"{s}.csv"), index=False)
        reports.append(rep)
        g = load_funding_edge(s)              # re-load through the consumer loader
        assert g.index.is_unique and g.index.is_monotonic_increasing, s
        assert np.allclose(g["f8"].to_numpy(), f["f8"].to_numpy(), equal_nan=True), s
        panel.append(g.assign(symbol=s))
    rep = pd.DataFrame(reports)
    rep.to_csv(os.path.join(OUT, "funding_defects.csv"), index=False)
    p = pd.concat(panel)
    p.index.name = "time"
    p.reset_index().assign(timestamp=lambda d: np.asarray(epoch_seconds(pd.DatetimeIndex(d["time"]))))[
        ["timestamp", "symbol", "rate", "interval_h", "f8"]].to_csv(
        os.path.join(OUT, "funding_panel.csv.gz"), index=False)
    from backtest.bracket_experiment import load_funding
    chk = load_funding(os.path.join(FUND_DIR, "BTCUSDT.csv")) if "BTCUSDT" in syms else None
    pp = load_funding_panel()
    print(f"saved+reloaded funding: {pp['symbol'].nunique()} symbols, {len(pp)} settlements, "
          f"{pp.index.min()} -> {pp.index.max()}"
          + (f"; BTCUSDT via bracket_experiment.load_funding: {len(chk)} rows" if chk is not None else ""))
    print(rep.drop(columns=[c for c in rep.columns if c.startswith("floor_share")], errors="ignore")
          .describe().T.to_string())


def build_funding(symbol: str, paths: list[str]) -> tuple[pd.DataFrame, dict]:
    frames = []
    for p in paths:
        d = read_zip_csv(p)
        if d.shape[1] == 3 and "calc_time" not in [str(c) for c in d.columns]:
            d.columns = ["calc_time", "funding_interval_hours", "last_funding_rate"]
        d.columns = [str(c).strip() for c in d.columns]
        frames.append(d[["calc_time", "funding_interval_hours", "last_funding_rate"]])
    d = pd.concat(frames, ignore_index=True)
    ct = d["calc_time"].astype("int64")
    unit_us = bool((ct > 10**14).any())
    if unit_us:
        ct = ct // 1000
    ts = pd.DatetimeIndex(pd.to_datetime(ct, unit="ms", utc=True))
    settle = ts.round("h")
    off_ms = np.asarray((ts - settle) // pd.Timedelta(milliseconds=1))
    out = pd.DataFrame({"timestamp": np.asarray(epoch_seconds(settle)),
                        "rate": d["last_funding_rate"].astype(float).to_numpy(),
                        "interval_file": pd.to_numeric(d["funding_interval_hours"], errors="coerce").to_numpy(),
                        "calc_offset_ms": off_ms})
    n0 = len(out)
    out = out.sort_values("timestamp").drop_duplicates("timestamp", keep="last").reset_index(drop=True)
    # ZOMBIE rows: the archive keeps publishing klines (zero volume, frozen OHLC) and funding
    # (a constant 0.0001) for years after a contract is delisted. Drop every settlement whose
    # preceding 24 h had no perp trading (1d bar with volume 0, or no bar at all inside the
    # downloaded 1d coverage). Settlements in months without 1d coverage are kept and counted.
    kp = os.path.join(OUT, "klines_1d_um", f"{symbol}.csv")
    zombie, uncovered = 0, 0
    if os.path.exists(kp):
        k = pd.read_csv(kp, usecols=["timestamp", "volume"])
        live_days = set(k.loc[k["volume"] > 0, "timestamp"] // 86400)
        covered = set(k["timestamp"] // 86400)
        day = (out["timestamp"] - 1) // 86400          # the trading day the settlement closes
        is_cov = day.isin(covered)
        dead = is_cov & ~day.isin(live_days)
        zombie, uncovered = int(dead.sum()), int((~is_cov).sum())
        out = out[~dead].reset_index(drop=True)
    gap_h = out["timestamp"].diff().to_numpy() / 3600.0
    out["interval_derived"] = gap_h
    # interval used: the file column when present, else the spacing to the previous settlement
    iv = out["interval_file"].where(out["interval_file"].notna() & (out["interval_file"] > 0),
                                    out["interval_derived"])
    out["interval_h"] = iv
    out["f8"] = out["rate"] * 8.0 / out["interval_h"]
    floor_rate = FLOOR_8H * out["interval_h"] / 8.0
    at_floor = pd.Series(np.isclose(out["rate"], floor_rate, rtol=0, atol=5e-10), index=out.index)
    yr = pd.to_datetime(out["timestamp"], unit="s", utc=True).dt.year
    hrs = pd.to_datetime(out["timestamp"], unit="s", utc=True).dt.hour
    disagree = out["interval_file"].notna() & out["interval_derived"].notna() & \
        (np.abs(out["interval_file"] - out["interval_derived"]) > 0.01)
    rep = {
        "symbol": symbol, "rows": len(out), "dup_dropped": n0 - len(out) - zombie, "unit_us_files": unit_us,
        "zombie_dropped": zombie, "no_1d_coverage": uncovered,
        "first": pd.Timestamp(out["timestamp"].iloc[0], unit="s", tz="UTC"),
        "last": pd.Timestamp(out["timestamp"].iloc[-1], unit="s", tz="UTC"),
        "max_abs_calc_offset_ms": int(np.abs(out["calc_offset_ms"]).max()),
        "interval_missing_in_file": int(out["interval_file"].isna().sum()),
        "intervals_seen": ",".join(str(int(v)) for v in sorted(out["interval_h"].dropna().unique())),
        "interval_file_vs_spacing_disagree": int(disagree.sum()),
        "gaps_gt_interval": int((out["interval_derived"] > out["interval_h"] + 0.01).sum()),
        "off_grid_8h": int(((out["interval_h"] == 8) & (hrs % 8 != 0)).sum()),
        "max_f8": float(out["f8"].max()), "min_f8": float(out["f8"].min()),
        "at_floor_share": float(at_floor.mean()),
        "mode_f8": float(out["f8"].round(9).mode().iloc[0]),
        "mode_share": float((out["f8"].round(9) == out["f8"].round(9).mode().iloc[0]).mean()),
    }
    for y, v in at_floor.groupby(yr):
        rep[f"floor_share_{y}"] = float(v.mean())
    return out[["timestamp", "rate", "interval_h", "interval_file", "interval_derived", "f8",
                "calc_offset_ms"]], rep


def load_funding_edge(symbol: str) -> pd.DataFrame:
    """Consumer loader: settlement-time UTC index; rate (as printed), interval_h, f8 (per 8 h)."""
    f = pd.read_csv(os.path.join(FUND_DIR, f"{symbol}.csv"))
    idx = pd.DatetimeIndex(pd.to_datetime(f["timestamp"], unit="s", utc=True), name="settle_time")
    return f[["rate", "interval_h", "f8"]].set_index(idx)


def load_funding_panel(path: str = os.path.join(OUT, "funding_panel.csv.gz")) -> pd.DataFrame:
    f = pd.read_csv(path)
    idx = pd.DatetimeIndex(pd.to_datetime(f["timestamp"], unit="s", utc=True), name="settle_time")
    return f.drop(columns=["timestamp"]).set_index(idx)


# ---------------------------------------------------------------- 3. spot klines, premium index
def spot_map(syms: list[str]) -> pd.DataFrame:
    s = pd.read_csv(os.path.join(OUT, "universe_symbols.csv"), dtype={"first_month": str, "last_month": str})
    s = s.set_index("symbol").loc[syms]
    return s[["base", "multiplier", "spot_symbol", "listed_spot"]].reset_index()


def fetch_klines_set(http: Http, pairs: list[tuple[str, str]], market: str, interval: str,
                     start: str, end: str, outdir: str, month_filter=None):
    """pairs: (cache_name, archive_symbol). market 'spot' | 'um' | 'premium'."""
    path = {"spot": SPOT_KL, "um": UM_KL, "premium": "data/futures/um/monthly/premiumIndexKlines/"}[market]
    url_pre = {"spot": "spot/monthly/klines", "um": "futures/um/monthly/klines",
               "premium": "futures/um/monthly/premiumIndexKlines"}[market]
    syms = sorted({a for _, a in pairs})
    ml = http.map(lambda a: list_months(http, f"{path}{a}/{interval}/"), syms, f"list-{market}")
    mon = {a: [m for m in ms if start <= m <= end and (month_filter is None or month_filter(a, m))]
           for a, ms in zip(syms, ml)}
    jobs = [(a, m) for a in syms for m in mon[a]]
    print(f"{market} {interval}: {len(syms)} symbols, {len(jobs)} monthly files", flush=True)

    def job(am):
        a, m = am
        return raw_get(http, f"{BASE}/{url_pre}/{a}/{interval}/{a}-{interval}-{m}.zip",
                       f"{RAW}/{market}{interval}/{a}/{a}-{interval}-{m}.zip")

    http.map(job, jobs, f"{market}{interval}")
    os.makedirs(outdir, exist_ok=True)
    step = int(pd.Timedelta(interval.replace("m", "min") if interval.endswith("m") else interval).total_seconds())
    defects = []
    for name, a in pairs:
        paths = [p for m in mon[a] if os.path.exists(p := f"{RAW}/{market}{interval}/{a}/{a}-{interval}-{m}.zip")]
        if not paths:
            defects.append({"symbol": name, "archive_symbol": a, "rows": 0})
            continue
        k = kline_frame(paths)
        out = os.path.join(outdir, f"{name}.csv")
        k.to_csv(out, index=False)
        chk = load_klines(out)
        assert chk.index.is_unique and len(chk) == len(k), name
        d = kline_defects(name, k, step_s=step) if market != "premium" else premium_defects(name, k, step)
        d["archive_symbol"] = a
        defects.append(d)
    rep = pd.DataFrame(defects)
    rep.to_csv(os.path.join(OUT, f"{market}_{interval}_defects.csv"), index=False)
    print(f"saved+reloaded {len(rep)} {market} {interval} caches in {outdir}")
    return rep


def spot_coverage(http: Http, syms: list[str], check_month: Optional[str] = None) -> pd.DataFrame:
    """Spot coverage by month from the archive listing (one call per spot pair), plus a mapping
    check: for one overlapping month, median |log(perp_close / (spot_close * multiplier))| on
    daily closes. A large value flags a wrong map (ticker reuse, different token)."""
    sm = spot_map(syms)
    sm = sm[sm["listed_spot"]].reset_index(drop=True)
    ml = http.map(lambda a: list_months(http, f"{SPOT_KL}{a}/1d/"), sm["spot_symbol"].tolist(), "list-spot1d")
    sm["spot_first_month"] = [m[0] if m else None for m in ml]
    sm["spot_last_month"] = [m[-1] if m else None for m in ml]
    sm["spot_months"] = [len(m) for m in ml]
    sm["spot_month_list"] = [" ".join(m) for m in ml]
    u = load_universe()
    res = []

    def check(i):
        r = sm.iloc[i]
        pm = set(u.loc[(u["symbol"] == r["symbol"]) & u["alive"], "month"])
        both = sorted(pm & set(ml[i]))
        out = {"symbol": r["symbol"]}
        if not both:
            return out
        picks = [both[0], both[-1]] if len(both) > 1 else [both[0]]
        meds = []
        for m in picks:
            a = r["spot_symbol"]
            sp = raw_get(http, f"{BASE}/spot/monthly/klines/{a}/1d/{a}-1d-{m}.zip", f"{RAW}/spot1d/{a}/{a}-1d-{m}.zip")
            kp = os.path.join(OUT, "klines_1d_um", f"{r['symbol']}.csv")
            if sp is None or not os.path.exists(kp):
                continue
            ks = kline_frame([sp]).set_index("timestamp")["close"] * r["multiplier"]
            kperp = pd.read_csv(kp)
            kperp = kperp[kperp["volume"] > 0].set_index("timestamp")["close"]   # live perp days only
            j = pd.concat([kperp.rename("p"), ks.rename("s")], axis=1).dropna()
            if len(j):
                meds.append(float(np.median(np.abs(np.log(j["p"] / j["s"])))) / BP)
            else:
                meds.append(np.nan)
        out.update({"map_check_months": " ".join(picks), "map_absdev_first_bp": meds[0] if meds else np.nan,
                    "map_absdev_last_bp": meds[-1] if meds else np.nan})
        return out

    res = http.map(check, range(len(sm)), "spot-mapcheck")
    sm = sm.merge(pd.DataFrame(res), on="symbol", how="left")
    path = os.path.join(OUT, "spot_coverage.csv")
    sm.to_csv(path, index=False)
    chk = pd.read_csv(path)
    bad = chk[(chk["map_absdev_first_bp"] > 200) | (chk["map_absdev_last_bp"] > 200)]
    print(f"saved+reloaded spot_coverage.csv: {len(chk)} pairs; mapping flags (>200 bp median dev): "
          f"{bad[['symbol', 'spot_symbol', 'map_absdev_first_bp', 'map_absdev_last_bp']].to_string(index=False)}")
    return sm


def premium_defects(symbol: str, k: pd.DataFrame, step_s: int) -> dict:
    t = k["timestamp"].to_numpy()
    d = np.diff(t)
    return {"symbol": symbol, "rows": len(k),
            "first": pd.Timestamp(t[0], unit="s", tz="UTC"), "last": pd.Timestamp(t[-1], unit="s", tz="UTC"),
            "dup_dropped": k.attrs.get("dup_dropped", 0), "misaligned": int((t % step_s != 0).sum()),
            "gaps": int((d > step_s).sum()), "missing_bars": int(((d[d > step_s] // step_s) - 1).sum()),
            "abs_close_gt_1pct": int((k["close"].abs() > 0.01).sum()),
            "max_abs_close": float(k["close"].abs().max())}


def funding_formula_check(http: Http, sym: str, start: str, end: str) -> dict:
    """Sign/timing check: rebuild F from Binance's 1h premium index with the published rule
    F = P + clamp(I - P, -5 bp, +5 bp) (P = linearly weighted average over the interval,
    approximated here from hourly closes weighted 1..n) and compare with the printed rate at the
    settlement that CLOSES the interval. A positive premium (perp above index) must map to a
    positive rate (longs pay shorts); the best alignment must be at lag 0."""
    fetch_klines_set(http, [(sym, sym)], "premium", "1h", start, end, os.path.join(OUT, "premium_1h"))
    pr = load_klines(os.path.join(OUT, "premium_1h", f"{sym}.csv"))["close"]
    f = load_funding_edge(sym)
    f = f[(f.index >= pd.Timestamp(start + "-01", tz="UTC")) & (f["interval_h"] == 8)]
    out = {"symbol": sym, "window": f"{start}..{end}"}
    for lag_h in (-8, 0, 8):
        hat, act = [], []
        for t, r in f.iterrows():
            w = pr[(pr.index >= t - pd.Timedelta(hours=8 + lag_h)) & (pr.index < t - pd.Timedelta(hours=lag_h))]
            if len(w) < 8:
                continue
            P = float(np.average(w.to_numpy(), weights=np.arange(1, len(w) + 1)))
            hat.append(P + np.clip(FLOOR_8H - P, -0.0005, 0.0005))
            act.append(r["rate"])
        hat, act = np.array(hat), np.array(act)
        out[f"n_lag{lag_h}"] = len(act)
        out[f"corr_lag{lag_h}"] = float(np.corrcoef(hat, act)[0, 1]) if len(act) > 2 else np.nan
        out[f"within1bp_lag{lag_h}"] = float(np.mean(np.abs(hat - act) <= 1e-4)) if len(act) else np.nan
    return out


# ---------------------------------------------------------------- 4. Bybit listing dates
BYBIT = "https://public.bybit.com"


def bybit_listing(http: Http, syms: list[str]) -> pd.DataFrame:
    """First/last daily file per symbol in Bybit's public trade archive (perp: trading/, spot: spot/).

    The first file date is the listing-date proxy (Bybit's API is blocked from the container).
    Perp symbol names are tried as-is; spot names use the multiplier-stripped base + USDT.
    """
    sm = spot_map(syms)

    def first_last(kind: str, s: str):
        body = http.get(f"{BYBIT}/{kind}/{s}/")
        if body is None:
            return None, None, 0
        dates = sorted(re.findall(r'href="[A-Z0-9]+[_-]?(\d{4}-\d{2}(?:-\d{2})?)\.csv\.gz"', body.decode("utf-8", "replace")))
        return (dates[0], dates[-1], len(dates)) if dates else (None, None, 0)

    perp = http.map(lambda s: first_last("trading", s), sm["symbol"].tolist(), "bybit-perp")
    spot_names = [b + "USDT" for b in sm["base"]]
    spot = http.map(lambda s: first_last("spot", s), spot_names, "bybit-spot")
    out = sm.assign(bybit_perp_first=[p[0] for p in perp], bybit_perp_last=[p[1] for p in perp],
                    bybit_perp_files=[p[2] for p in perp], bybit_spot_symbol=spot_names,
                    bybit_spot_first=[p[0] for p in spot], bybit_spot_last=[p[1] for p in spot],
                    bybit_spot_files=[p[2] for p in spot])
    out.to_csv(os.path.join(OUT, "bybit_listing.csv"), index=False)
    chk = pd.read_csv(os.path.join(OUT, "bybit_listing.csv"))
    print(f"saved+reloaded bybit_listing.csv: {len(chk)} symbols, perp found {chk['bybit_perp_first'].notna().sum()}, "
          f"spot found {chk['bybit_spot_first'].notna().sum()}")
    return out


def _minute_last(ts_s: np.ndarray, price: np.ndarray, qty: np.ndarray) -> pd.DataFrame:
    t = pd.DatetimeIndex(pd.to_datetime(ts_s, unit="s", utc=True)).floor("min")
    d = pd.DataFrame({"p": price, "q": qty, "pq": price * qty}, index=t).sort_index()
    g = d.groupby(level=0)
    return pd.DataFrame({"close": g["p"].last(), "vwap": g["pq"].sum() / g["q"].sum(), "n": g.size()})


def bybit_compare(http: Http, syms: list[str], day: str) -> pd.DataFrame:
    """One-day cross-vendor check from trade files (Bybit) and 1m klines (Binance):
    perp price agreement, spot price agreement, perp-minus-spot basis on each venue,
    Binance premium index, and a +-3 min lag scan of 1m returns (clock check)."""
    sm = spot_map(syms).set_index("symbol")
    rows = []
    for s in syms:
        base, mult = sm.loc[s, "base"], int(sm.loc[s, "multiplier"])
        spot_sym = f"{base}USDT"
        p_by = raw_get(http, f"{BYBIT}/trading/{s}/{s}{day}.csv.gz", f"{RAW}/bybit/trading/{s}/{s}{day}.csv.gz")
        s_by = raw_get(http, f"{BYBIT}/spot/{spot_sym}/{spot_sym}_{day}.csv.gz",
                       f"{RAW}/bybit/spot/{spot_sym}/{spot_sym}_{day}.csv.gz")
        bn = {}
        for kind, pre, sym_ in (("perp", "futures/um/daily/klines", s), ("spot", "spot/daily/klines", spot_sym),
                                ("prem", "futures/um/daily/premiumIndexKlines", s)):
            p = raw_get(http, f"{BASE}/{pre}/{sym_}/1m/{sym_}-1m-{day}.zip", f"{RAW}/bn1m_{kind}/{sym_}/{sym_}-1m-{day}.zip")
            if p:
                k = kline_frame([p])
                bn[kind] = k.set_index(pd.DatetimeIndex(pd.to_datetime(k["timestamp"], unit="s", utc=True)))
        if p_by is None or "perp" not in bn:
            rows.append({"symbol": s, "day": day, "note": "missing bybit perp or binance perp"})
            continue
        bp_ = pd.read_csv(p_by, usecols=["timestamp", "size", "price"])
        byp = _minute_last(bp_["timestamp"].to_numpy(float), bp_["price"].to_numpy(float), bp_["size"].to_numpy(float))
        r = {"symbol": s, "day": day, "bybit_perp_trades": len(bp_)}
        bnp = bn["perp"]["close"]
        j = pd.concat([bnp.rename("bn"), byp["close"].rename("by")], axis=1).dropna()
        dlog = np.log(j["by"] / j["bn"]) / BP
        r.update({"perp_minutes": len(j), "perp_diff_med_bp": float(dlog.median()),
                  "perp_absdiff_p50_bp": float(dlog.abs().median()), "perp_absdiff_p95_bp": float(dlog.abs().quantile(.95))})
        rb = np.log(j["bn"]).diff()
        ry = np.log(j["by"]).diff()
        lags = {L: float(rb.corr(ry.shift(-L))) for L in range(-3, 4)}
        r["lag_best_min"] = max(lags, key=lambda L: lags[L])
        r["lag_corr0"] = lags[0]
        if s_by is not None and "spot" in bn:
            sp_ = pd.read_csv(s_by, usecols=["timestamp", "price", "volume"])
            bys = _minute_last(sp_["timestamp"].to_numpy(float) / 1000.0, sp_["price"].to_numpy(float),
                               sp_["volume"].to_numpy(float))
            # perp quotes `mult` units of the base; spot quotes one unit
            js = pd.concat([bn["spot"]["close"].rename("bn_s") * mult, bys["close"].rename("by_s") * mult,
                            bnp.rename("bn_p"), byp["close"].rename("by_p")], axis=1).dropna()
            ds = np.log(js["by_s"] / js["bn_s"]) / BP
            basis_bn = np.log(js["bn_p"] / js["bn_s"]) / BP
            basis_by = np.log(js["by_p"] / js["by_s"]) / BP
            r.update({"spot_minutes": len(js), "spot_absdiff_p50_bp": float(ds.abs().median()),
                      "basis_bn_mean_bp": float(basis_bn.mean()), "basis_by_mean_bp": float(basis_by.mean()),
                      "basis_corr_1m": float(basis_bn.corr(basis_by)),
                      "basis_corr_1h": float(basis_bn.resample("1h").mean().corr(basis_by.resample("1h").mean())),
                      "basis_diff_mean_bp": float((basis_by - basis_bn).mean())})
            if "prem" in bn:
                pr = bn["prem"]["close"] / BP
                r["bn_premidx_mean_bp"] = float(pr.mean())
                r["bn_premidx_vs_bybit_basis_corr_1h"] = float(pr.resample("1h").mean().corr(basis_by.resample("1h").mean()))
        rows.append(r)
    out = pd.DataFrame(rows)
    path = os.path.join(OUT, f"bybit_compare_{day}.csv")
    out.to_csv(path, index=False)
    print(pd.read_csv(path).T.to_string())
    return out


# ---------------------------------------------------------------- 5. bookDepth coverage + one-day sketch
def depth_probe(http: Http, syms: list[str], day: str) -> pd.DataFrame:
    """Coverage of daily USDT-M bookDepth files (listing only) and a one-day cost sketch:
    cumulative notional within the archive's smallest percentage band on each side."""
    rows = []
    for s in syms:
        keys = [k for k in _listing(http, f"data/futures/um/daily/bookDepth/{s}/", False) if k.endswith(".zip")]
        days = sorted(m.group(1) for k in keys if (m := re.search(r"-(\d{4}-\d{2}-\d{2})\.zip$", k)))
        r = {"symbol": s, "files": len(days), "first": days[0] if days else None, "last": days[-1] if days else None}
        if days:
            full = pd.date_range(days[0], days[-1], freq="D").strftime("%Y-%m-%d")
            r["missing_days"] = len(set(full) - set(days))
        p = raw_get(http, f"{BASE}/futures/um/daily/bookDepth/{s}/{s}-bookDepth-{day}.zip",
                    f"{RAW}/bookDepth/{s}/{s}-bookDepth-{day}.zip")
        if p:
            d = read_zip_csv(p)
            d.columns = [str(c).strip() for c in d.columns]
            r["columns"] = "|".join(d.columns)
            r["levels"] = "|".join(str(x) for x in sorted(d["percentage"].unique()))
            r["snapshots"] = int(d["timestamp"].nunique())
            for lvl in sorted(d["percentage"].unique()):
                if abs(lvl) <= 1:
                    v = d.loc[d["percentage"] == lvl, "notional"].astype(float)
                    r[f"notional_{lvl:+g}pct_median_usd"] = float(v.median())
                    r[f"notional_{lvl:+g}pct_p10_usd"] = float(v.quantile(0.10))
        rows.append(r)
    out = pd.DataFrame(rows)
    path = os.path.join(OUT, f"bookdepth_probe_{day}.csv")
    out.to_csv(path, index=False)
    print(pd.read_csv(path).T.to_string())
    return out


# ---------------------------------------------------------------- 6. outcome-blind Gate-1 counts
EXPLORE = ("2020-09-01", "2025-01-01")      # [start, end) ; verdict era = 2025-01-01 .. data end
BP = 1e-4


def fbar_grid(f: pd.DataFrame, grid: pd.DatetimeIndex) -> pd.DataFrame:
    """Trailing-24 h mean of f8 over settlements s with t-24h < s <= t, at each grid time t."""
    s = np.asarray(epoch_seconds(f.index))
    g = np.asarray(epoch_seconds(grid))
    cs = np.concatenate([[0.0], np.cumsum(f["f8"].to_numpy())])
    hi = np.searchsorted(s, g, side="right")
    lo = np.searchsorted(s, g - 86400, side="right")
    n = hi - lo
    with np.errstate(invalid="ignore", divide="ignore"):
        fb = (cs[hi] - cs[lo]) / n
    fb[n == 0] = np.nan
    return pd.DataFrame({"fbar": fb, "n_settle": n}, index=grid)


def episodes(st: pd.DataFrame, thr: float, exit_: float) -> list[dict]:
    """De-clustered episodes on one coin's 8 h grid. Entry: fbar >= thr while in the universe.
    Exit: fbar <= exit_ or fbar missing (data end / delisting). Consecutive states merge."""
    out = []
    fb = st["fbar"].to_numpy()
    inu = st["in_univ"].to_numpy()
    t = st.index
    i, n = 0, len(st)
    while i < n:
        if inu[i] and not np.isnan(fb[i]) and fb[i] >= thr:
            j = i + 1
            while j < n and not np.isnan(fb[j]) and fb[j] > exit_:
                j += 1
            out.append({"start": t[i], "end": t[j] if j < n else t[-1], "start_i": i,
                        "n_bars": j - i, "censored": j >= n or np.isnan(fb[j]) if j < n else True})
            i = j + 1
        else:
            i += 1
    return out


def gate1_counts(top_rank: tuple[int, int] = (3, 50), K: int = 63, n_boot: int = 2000, seed: int = 7):
    u = load_universe()
    pan = load_funding_panel()
    end = pan.index.max().floor("D") + pd.Timedelta(hours=16)
    grid = pd.date_range(pd.Timestamp("2020-09-01", tz="UTC"), end, freq="8h")
    ur = u[u["rank"].notna()]
    rk = {(a, b): float(c) for a, b, c in zip(ur["symbol"], ur["month"], ur["rank"])}
    by_sym = {s: g.sort_index() for s, g in pan.groupby("symbol")}
    lo_r, hi_r = top_rank
    univ_syms = sorted(u.loc[u["rank"].between(lo_r, hi_r), "symbol"].unique())
    missing = [s for s in univ_syms if s not in set(pan["symbol"])]
    states = {}
    for s in univ_syms:
        if s in missing:
            continue
        f = by_sym[s]
        st = fbar_grid(f, grid)
        mon = st.index.strftime("%Y-%m")
        r = pd.Series(np.array([rk.get((s, m), np.nan) for m in mon], dtype=float), index=st.index)
        st["rank"] = r
        st["in_univ"] = r.between(lo_r, hi_r).to_numpy()
        states[s] = st

    res = {"missing_funding_symbols": missing}
    # (a) universe size and dead-zone share by year (coin-settlements of in-universe coins)
    rows = []
    for s, st in states.items():
        f = by_sym[s]
        mon = f.index.strftime("%Y-%m")
        r = np.array([rk.get((s, m), np.nan) for m in mon], dtype=float)
        f = f[(r >= lo_r) & (r <= hi_r) & (f.index >= pd.Timestamp("2020-09-01", tz="UTC"))]
        rows.append(pd.DataFrame({"year": f.index.year, "f8": f["f8"].to_numpy(),
                                  "interval_h": f["interval_h"].to_numpy(), "symbol": s}))
    cs = pd.concat(rows)
    cs["at_floor"] = np.isclose(cs["f8"], BP, atol=1e-9, rtol=0)
    cs["below"] = cs["f8"] < BP - 1e-9
    cs["above"] = cs["f8"] > BP + 1e-9
    uy = u[u["rank"].between(lo_r, hi_r) & (u["month"] >= "2020-09")]
    dz = cs.groupby("year").agg(settlements=("f8", "size"), coins=("symbol", "nunique"),
                                at_floor=("at_floor", "mean"), below_floor=("below", "mean"),
                                above_floor=("above", "mean"),
                                ge5bp=("f8", lambda v: float((v >= 5 * BP).mean())),
                                non8h_share=("interval_h", lambda v: float((v != 8).mean())))
    dz["univ_size_mean_per_month"] = uy.groupby(uy["month"].str[:4].astype(int))["symbol"].size() / \
        uy.groupby(uy["month"].str[:4].astype(int))["month"].nunique()
    dz["distinct_symbols"] = uy.groupby(uy["month"].str[:4].astype(int))["symbol"].nunique()
    res["deadzone_by_year"] = dz

    # (b) coin-days, episodes, months with an episode, by year
    sp = spot_cover()
    out_rows, ep_all = [], []
    for thr in (5, 7, 10, 15):
        for ex in (2, 3):
            eps = []
            cd = []
            for s, st in states.items():
                for e in episodes(st, thr * BP, ex * BP):
                    e["symbol"] = s
                    eps.append(e)
                tail = st[(st["fbar"] >= thr * BP) & st["in_univ"]]
                cd += [(s, d) for d in tail.index.normalize().unique()]
            E = pd.DataFrame(eps)
            E["year"] = E["start"].dt.year
            E["month"] = E["start"].dt.strftime("%Y-%m")
            E["spot_binance"] = [sp[0].get((r.symbol, r.month), False) for r in E.itertuples()]

            def _by(r):
                pf, sf = sp[1].get(r.symbol, (None, None))
                ok_p = isinstance(pf, str) and pd.Timestamp(pf[:10] if len(pf) > 7 else pf + "-01", tz="UTC") <= r.start
                ok_s = isinstance(sf, str) and pd.Timestamp(sf[:10] if len(sf) > 7 else sf + "-01", tz="UTC") \
                    <= r.start - pd.Timedelta(days=90)
                return bool(ok_p and ok_s)
            E["bybit_perp_spot90"] = [_by(r) for r in E.itertuples()]
            CD = pd.DataFrame(cd, columns=["symbol", "day"])
            CD["year"] = pd.DatetimeIndex(CD["day"]).year
            g = E.groupby("year").agg(episodes=("symbol", "size"), months_with_episode=("month", "nunique"),
                                      coins=("symbol", "nunique"), median_bars=("n_bars", "median"),
                                      spot_binance_share=("spot_binance", "mean"),
                                      bybit_ok_share=("bybit_perp_spot90", "mean"))
            g["coin_days"] = CD.groupby("year").size()
            g["thr_bp"], g["exit_bp"] = thr, ex
            out_rows.append(g.reset_index())
            E["thr_bp"], E["exit_bp"] = thr, ex
            ep_all.append(E)
    res["episodes_by_year"] = pd.concat(out_rows, ignore_index=True)
    EP = pd.concat(ep_all, ignore_index=True)
    EP.drop(columns=["start_i"]).to_csv(os.path.join(OUT, "gate1_episodes.csv"), index=False)

    # (c) EXPLORE-ERA ONLY half-life of excess F_bar after entry (chair-authorised statistic)
    ex_end = pd.Timestamp(EXPLORE[1], tz="UTC")
    hl = {}
    for thr in (5, 7, 10):
        paths, emonth = [], []
        for s, st in states.items():
            fb = st["fbar"].to_numpy()
            for e in episodes(st, thr * BP, 2 * BP):
                if e["start"] >= ex_end:
                    continue
                i = e["start_i"]
                x = np.full(K + 1, np.nan)
                seg = fb[i:i + K + 1]
                tt = st.index[i:i + K + 1]
                seg = np.where(tt < ex_end, seg, np.nan)       # never read the verdict era
                x[:len(seg)] = seg - BP
                paths.append(x)
                emonth.append(e["start"].strftime("%Y-%m"))
        X = np.vstack(paths)
        em = np.array(emonth)
        hl[thr] = halflife_with_boot(X, em, n_boot, seed)
    res["halflife"] = hl
    return res


def decay_curve(X: np.ndarray) -> np.ndarray:
    """R(k) = sum_e x_{e,k} / sum_e x_{e,0} over episodes observed at lag k."""
    obs = ~np.isnan(X)
    x0 = X[:, 0]
    num = np.nansum(np.where(obs, X, 0.0), axis=0)
    den = np.array([x0[obs[:, k]].sum() for k in range(X.shape[1])])
    with np.errstate(invalid="ignore", divide="ignore"):
        return num / den


def hl_from_curve(R: np.ndarray) -> float:
    """First lag (in 8 h settlements) where R(k) <= 0.5, linearly interpolated; inf if never."""
    below = np.where(R <= 0.5)[0]
    if len(below) == 0:
        return np.inf
    k = below[0]
    if k == 0:
        return 0.0
    r0, r1 = R[k - 1], R[k]
    return (k - 1) + (r0 - 0.5) / (r0 - r1)


def halflife_with_boot(X: np.ndarray, em: np.ndarray, n_boot: int, seed: int) -> dict:
    R = decay_curve(X)
    hl = hl_from_curve(R)
    ks = np.arange(len(R))
    ok = (R > 0) & np.isfinite(R)
    lam = -np.polyfit(ks[ok], np.log(R[ok]), 1)[0] if ok.sum() > 3 else np.nan
    rng = np.random.default_rng(seed)
    um = np.unique(em)
    idx = {m: np.where(em == m)[0] for m in um}
    boots, boots_fit = [], []
    for _ in range(n_boot):
        pick = rng.choice(um, size=len(um), replace=True)
        rows = np.concatenate([idx[m] for m in pick])
        Rb = decay_curve(X[rows])
        boots.append(hl_from_curve(Rb))
        okb = (Rb > 0) & np.isfinite(Rb)
        boots_fit.append(np.log(2) / -np.polyfit(ks[okb], np.log(Rb[okb]), 1)[0] if okb.sum() > 3 else np.nan)
    b = np.array(boots)
    bf = np.array(boots_fit)
    to_days = 8.0 / 24.0
    return {"episodes": len(X), "months": len(um), "obs_at_K": int((~np.isnan(X[:, -1])).sum()),
            "R": R, "hl_days": hl * to_days,
            # inf = R(k) never fell to 0.5 inside the K-settlement window (right-censored);
            # percentiles use order statistics so an inf upper bound stays inf, never nan
            "hl_days_ci95": (np.percentile(b, 2.5, method="lower") * to_days,
                             np.percentile(b, 97.5, method="higher") * to_days),
            "hl_days_ci90": (np.percentile(b, 5, method="lower") * to_days,
                             np.percentile(b, 95, method="higher") * to_days),
            "boot_median_days": np.percentile(b, 50, method="lower") * to_days,
            "boot_share_under_3d": float(np.mean(b * to_days < 3.0)),
            "boot_share_never": float(np.mean(~np.isfinite(b))),
            "fit_hl_days": (np.log(2) / lam) * to_days if lam and lam > 0 else np.inf,
            "fit_hl_days_ci95": tuple(np.nanpercentile(bf, [2.5, 97.5]) * to_days),
            "x0_median_bp": float(np.median(X[:, 0]) / BP)}


def spot_cover() -> tuple[dict, dict]:
    """Binance: {(perp_symbol, YYYY-MM): True} if the mapped spot pair has an archive file that
    month (and the mapping check passed). Bybit: {perp_symbol: (perp_first, spot_first)}."""
    bn, by = {}, {}
    p = os.path.join(OUT, "spot_coverage.csv")
    if os.path.exists(p):
        c = pd.read_csv(p)
        for r in c.itertuples():
            bad = (r.map_absdev_first_bp > 200) or (r.map_absdev_last_bp > 200)
            if isinstance(r.spot_month_list, str) and not bad:
                for m in r.spot_month_list.split():
                    bn[(r.symbol, m)] = True
    p = os.path.join(OUT, "bybit_listing.csv")
    if os.path.exists(p):
        c = pd.read_csv(p)
        for r in c.itertuples():
            by[r.symbol] = (r.bybit_perp_first, r.bybit_spot_first)
    return bn, by


def print_counts(res: dict):
    pd.set_option("display.width", 200)
    print("missing funding for universe symbols:", res["missing_funding_symbols"])
    print("\n(a) universe size and dead-zone share by year (in-universe coin-settlements, ranks 3-50)")
    print(res["deadzone_by_year"].round(4).to_string())
    print("\n(b) episodes by year (entry thr / de-cluster exit in bp per 8 h)")
    e = res["episodes_by_year"]
    print(e.round(3).to_string(index=False))
    tot = e.groupby(["thr_bp", "exit_bp"]).agg(episodes=("episodes", "sum"), coin_days=("coin_days", "sum"),
                                                months=("months_with_episode", "sum"))
    print(tot.to_string())
    print("\n(c) EXPLORE-ERA half-life of (F_bar - 1 bp) after entry, exit 2 bp de-clustering, month-clustered bootstrap")
    for thr, h in res["halflife"].items():
        R = h["R"]
        print(f"  thr {thr} bp: episodes {h['episodes']} in {h['months']} months, x0 median {h['x0_median_bp']:.1f} bp, "
              f"HL {h['hl_days']:.2f} d (95% {h['hl_days_ci95'][0]:.2f}-{h['hl_days_ci95'][1]:.2f}; "
              f"90% {h['hl_days_ci90'][0]:.2f}-{h['hl_days_ci90'][1]:.2f}; boot median {h['boot_median_days']:.2f}), "
              f"P(boot HL<3d)={h['boot_share_under_3d']:.3f}, P(boot HL>window)={h['boot_share_never']:.3f}, "
              f"obs at k=K {h['obs_at_K']}; "
              f"log-linear fit HL {h['fit_hl_days']:.2f} d (95% {h['fit_hl_days_ci95'][0]:.2f}-{h['fit_hl_days_ci95'][1]:.2f})")
        print("     R(k) at k=0,1,2,3,6,9,15,21,42,63:",
              " ".join(f"{R[k]:.2f}" for k in (0, 1, 2, 3, 6, 9, 15, 21, 42, 63) if k < len(R)))


# ---------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=["universe", "universe-fill", "rank", "funding", "spot", "premium", "bybit", "bybit-compare",
                                     "depth", "counts", "formula-check", "clock-check"])
    ap.add_argument("--day", default="2023-11-08", help="bybit-compare / depth: YYYY-MM-DD")
    ap.add_argument("--symbols", default="", help="comma list; default = ever rank_any <= --top")
    ap.add_argument("--start", default=RANK_START)
    ap.add_argument("--end", default=DATA_END)
    ap.add_argument("--top", type=int, default=120)
    ap.add_argument("--interval", default="1d")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--delay", type=float, default=0.05)
    ap.add_argument("--screen-k", type=int, default=0,
                    help="universe: aggTrades size-rank screen (0 = off, the default; the screen at 200 "
                         "was shown UNSAFE: a rank-58 coin had trade-count rank 318)")
    ap.add_argument("--coverage-only", action="store_true",
                    help="spot: listing-based monthly coverage + perp/spot mapping check, no full klines")
    ap.add_argument("--only-rank", type=int, default=0,
                    help="funding: fetch only symbol-months within 1 month of rank_any <= N (0 = full life)")
    args = ap.parse_args()
    http = Http(workers=min(args.workers, 4), delay=args.delay)
    t0 = time.time()
    if args.kind == "universe":
        build_universe(http, args.start, args.end, screen_k=args.screen_k)
    elif args.kind == "clock-check":
        # Known event: the SEC's X account posted a fake spot-ETF approval at 21:11 UTC on
        # 2024-01-09 (16:11 New York). The largest 1m BTCUSDT perp move that evening must sit
        # in the 21:11 bar if the archive's open-time stamps are UTC.
        p = raw_get(http, f"{BASE}/futures/um/daily/klines/BTCUSDT/1m/BTCUSDT-1m-2024-01-09.zip",
                    f"{RAW}/bn1m_perp/BTCUSDT/BTCUSDT-1m-2024-01-09.zip")
        k = kline_frame([p])
        k.index = pd.to_datetime(k["timestamp"], unit="s", utc=True)
        ev = k.loc["2024-01-09 20:00":"2024-01-09 23:00"]
        rr = np.log(ev["close"] / ev["open"]).abs()
        print(ev.loc["2024-01-09 21:08":"2024-01-09 21:16", ["open", "high", "low", "close", "volume"]].to_string())
        print("largest |1m move| 20:00-23:00 UTC at", rr.idxmax(), f"{rr.max() / BP:.0f} bp; top-3:",
              list(rr.nlargest(3).index.strftime("%H:%M")))
    elif args.kind == "formula-check":
        rows = [funding_formula_check(http, s, args.start, args.end) for s in args.symbols.split(",")]
        print(pd.DataFrame(rows).T.to_string())
    elif args.kind == "rank":
        rerank(args.start, args.end)
    elif args.kind == "universe-fill":
        fill_universe(http, args.start, args.end)
        rerank(args.start, args.end)
    elif args.kind == "depth":
        depth_probe(http, args.symbols.split(","), args.day)
    elif args.kind == "funding":
        syms = args.symbols.split(",") if args.symbols else ever_top(args.top)
        fetch_funding_all(http, syms, args.start, args.end, only_rank=args.only_rank)
    elif args.kind in ("spot", "premium"):
        syms = args.symbols.split(",") if args.symbols else ever_top(args.top)
        if args.kind == "spot" and args.coverage_only:
            spot_coverage(http, syms)
            pairs = []
        elif args.kind == "spot":
            sm = spot_map(syms)
            sm = sm[sm["listed_spot"]]
            pairs = list(zip(sm["symbol"], sm["spot_symbol"]))
            outdir = os.path.join(OUT, f"spot_{args.interval}")
        else:
            pairs = [(s, s) for s in syms]
            outdir = os.path.join(OUT, f"premium_{args.interval}")
        if pairs:
            fetch_klines_set(http, pairs, args.kind, args.interval, args.start, args.end, outdir)
    elif args.kind == "bybit":
        syms = args.symbols.split(",") if args.symbols else ever_top(args.top)
        bybit_listing(http, syms)
    elif args.kind == "bybit-compare":
        bybit_compare(http, args.symbols.split(","), args.day)
    elif args.kind == "counts":
        print_counts(gate1_counts())
    print(f"done in {time.time() - t0:.0f}s, {http.n_req} requests")


if __name__ == "__main__":
    main()
