"""
v0.34-exp — "EMT / Exhaustion Mean Theory" (DEVLOG v0.34-exp, pre-registered).

The reel (Cody G, @gstreettradesofficial, 7 Oct 2026; he shows Apex Trader Funding certificates, so
CME futures): 5-minute chart with VWAP and the 9 EMA. When price stretches away from the 9 EMA and
VWAP, wait for a candle that wicks hard and stalls (the exhaustion candle). When the NEXT candle breaks
its low, go short; after a dump, a break of the high, go long. Stop just beyond the wick, target VWAP.
"Do not enter on the exhaustion candle itself. Wait for the break."

His words leave four numbers open; they are fixed here before any result (DEVLOG):
  stretched     the exhaustion candle's extreme is beyond VWAP's 2-sigma band (the session's volume-
                weighted sigma of hlc3 around VWAP, as TradingView draws its VWAP bands) and >= K_EMA ATR
                beyond the 9 EMA (ATR = 14 bars of 5m)
  wicks hard    the wick on the stretched side is >= WICK_SHARE of the candle's range and >= WICK_ATR
                ATR, and the candle makes the most extreme price of the previous LOOKBACK bars
  next candle   only the candle right after it; a stop order at its low (high) for that one bar
  just beyond   stop = the wick's extreme +/- STOP_BUF ATR
Target: VWAP as of the previous bar's close, worked as a resting limit (the order a trader would keep
moving to the line). One position at a time; flat before the session's VWAP resets.

Markets: NQ futures 1m with real volume (Hugging Face mdelcristo/NQ-F_1min_OHLCV_Parquet, 2015-01 ->
2025-07-25; clock and minute alignment verified against HistData NSXUSD, sessions with an unmatched
>0.5% one-minute jump excluded) and BTC/ETH 5m perps (Binance UM, real volume, 2020-01 -> 2026-08).

  --selftest   planted short/long setups exact, no-break case, VWAP reset, truncation guard, brackets
  --funnel     outcome-blind setup counts by year (no P&L is computed)
  --report     the pre-registered primaries, then the labelled secondaries
"""

import argparse
import math
import sys
from dataclasses import dataclass, replace

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from backtest.data import NY_TZ, load_cached_1m  # noqa: E402
from backtest.horizon_harvest import COMMITTED_FUNDING  # noqa: E402
from backtest.sd_vwap_experiment import atr  # noqa: E402

LOCAL = "backtest/data_cache/local"
NQ_PKL = f"{LOCAL}/nq_hf_1m.pkl"
NQ_CFD = f"{LOCAL}/nas100_histdata_1m_2015_2026.csv.gz"
FRESH_FROM = pd.Timestamp("2024-01-01", tz="UTC")
PASS_T, PASS_PF, PASS_N = 2.24, 1.2, 100      # 2.24: Bonferroni over the two primaries


@dataclass(frozen=True)
class Rules:
    k_vwap: float = 2.0
    k_ema: float = 1.0
    wick_share: float = 0.5
    wick_atr: float = 0.4
    lookback: int = 6
    stop_buf: float = 0.1
    ema_n: int = 9
    atr_n: int = 14
    stretch_mode: str = "sd"      # "sd": beyond VWAP +/- k_sd session sigma (TradingView's VWAP bands) | "atr"
    k_sd: float = 2.0
    entry: str = "break"          # "break" (his rule) | "close" (enter at the exhaustion candle's close)
    break_bars: int = 1           # how many candles after the exhaustion candle may trigger the break
    target: str = "vwap"          # "vwap" | "1.5R"
    stretch: bool = True          # False: drop both distance conditions (ablation)


@dataclass(frozen=True)
class Market:
    name: str
    kind: str                     # "futures" | "crypto"
    tick: float                   # futures: price tick; crypto: unused
    anchor_hours: int             # hours added to local time so the session date rolls at the anchor
    tz: str
    warmup_bars: int = 12         # VWAP needs an hour of its own session before setups count
    last_entry_min: int = 16 * 60          # local minutes; no new entries at/after this...
    flat_min: int = 16 * 60 + 55           # ...and flat at this local time
    no_entry_from: int | None = None       # (futures) entries blocked from last_entry_min until the next anchor


NQ = Market("NQ", "futures", 0.25, 6, "America/New_York", last_entry_min=16 * 60, flat_min=16 * 60 + 55)
BTC = Market("BTC", "crypto", 0.0, 0, "UTC", last_entry_min=23 * 60, flat_min=23 * 60 + 55)
ETH = replace(BTC, name="ETH")
NQ_COMMISSION_PTS, NQ_SLIP_TICKS = 0.125, 1      # $2.50/side on $20/pt; one tick on stop-type fills
MAKER, TAKER, SLIP = 0.0002, 0.00055, 0.0001       # Bybit VIP0 crypto, per side


# ----------------------------------------------------------------------------------------------
# bars and indicators
# ----------------------------------------------------------------------------------------------
def to_5m(m1: pd.DataFrame) -> pd.DataFrame:
    utc = m1.tz_convert("UTC") if m1.index.tz is not None else m1.tz_localize("UTC")
    out = utc.resample("5min", label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"})
    return out.dropna(subset=["open"])


def indicators(b: pd.DataFrame, mk: Market, r: Rules) -> pd.DataFrame:
    """Session VWAP (typical price x volume, reset at the market's anchor), EMA, ATR, bar count in
    session. Every value at bar i uses bars <= i only (known at bar i's close)."""
    b = b.copy()
    local = b.index.tz_convert(mk.tz)
    b["session"] = (local + pd.Timedelta(hours=mk.anchor_hours)).normalize().tz_localize(None)
    tp = (b["high"] + b["low"] + b["close"]) / 3.0
    pv = (tp * b["volume"]).groupby(b["session"]).cumsum()
    cv = b["volume"].groupby(b["session"]).cumsum()
    b["vwap"] = (pv / cv.replace(0, np.nan)).to_numpy()
    p2 = (tp * tp * b["volume"]).groupby(b["session"]).cumsum()
    var = (p2 / cv.replace(0, np.nan)).to_numpy() - b["vwap"].to_numpy() ** 2
    b["vsd"] = np.sqrt(np.clip(var, 0.0, None))              # volume-weighted sigma of hlc3 around VWAP
    b["ema"] = b["close"].ewm(span=r.ema_n, adjust=False).mean()
    b["atr"] = atr(b, r.atr_n)
    b["n_in_session"] = b.groupby("session").cumcount()
    b["lmin"] = local.hour * 60 + local.minute
    return b


def setups(b: pd.DataFrame, mk: Market, r: Rules) -> tuple:
    """Boolean arrays: bar i is an exhaustion candle for a short / a long."""
    o, h, low, c = (b[k].to_numpy() for k in ("open", "high", "low", "close"))
    vw, em, a = b["vwap"].to_numpy(), b["ema"].to_numpy(), b["atr"].to_numpy()
    rng = h - low
    up_w = h - np.maximum(o, c)
    dn_w = np.minimum(o, c) - low
    prev_hi = pd.Series(h).shift(1).rolling(r.lookback).max().to_numpy()
    prev_lo = pd.Series(low).shift(1).rolling(r.lookback).min().to_numpy()
    nxt = b["lmin"].to_numpy() + 5                          # the candle that would carry the entry
    if mk.kind == "futures":
        window = (nxt < mk.last_entry_min) | (nxt >= 19 * 60)
    else:
        window = (nxt >= 60) & (nxt < mk.last_entry_min)
    ok = (np.isfinite(vw) & np.isfinite(a) & (a > 0) & (b["n_in_session"].to_numpy() >= mk.warmup_bars) & window)
    with np.errstate(invalid="ignore"):
        short = ok & (up_w >= r.wick_share * rng) & (up_w >= r.wick_atr * a) & (h >= prev_hi)
        long_ = ok & (dn_w >= r.wick_share * rng) & (dn_w >= r.wick_atr * a) & (low <= prev_lo)
        if r.stretch:
            sd = b["vsd"].to_numpy()
            band_s = (h >= vw + r.k_sd * sd) & (sd > 0) if r.stretch_mode == "sd" else (h - vw >= r.k_vwap * a)
            band_l = (low <= vw - r.k_sd * sd) & (sd > 0) if r.stretch_mode == "sd" else (vw - low >= r.k_vwap * a)
            short &= band_s & (h - em >= r.k_ema * a)
            long_ &= band_l & (em - low >= r.k_ema * a)
    both = short & long_
    return short & ~both, long_ & ~both


def entry_allowed(lmin: int, mk: Market) -> bool:
    if mk.kind == "futures":
        return lmin < mk.last_entry_min or lmin >= 18 * 60 + 60
    return 60 <= lmin < mk.last_entry_min


def assert_bracket(side: int, entry: float, stop: float, target: float) -> None:
    if not (side * (entry - stop) > 0 and side * (target - entry) > 0):
        raise AssertionError(f"malformed bracket side={side} entry={entry} stop={stop} target={target}")


# ----------------------------------------------------------------------------------------------
# simulation
# ----------------------------------------------------------------------------------------------
def simulate(b: pd.DataFrame, mk: Market, r: Rules, funding: pd.Series | None = None) -> pd.DataFrame:
    b = indicators(b, mk, r)
    S, L = setups(b, mk, r)
    o, h, low, c = (b[k].to_numpy() for k in ("open", "high", "low", "close"))
    vw, a = b["vwap"].to_numpy(), b["atr"].to_numpy()
    sess = b["session"].to_numpy()
    lmin = b["lmin"].to_numpy()
    idx = b.index
    n = len(b)
    rows = []
    i = 0
    while i < n - 1:
        if not (S[i] or L[i]):
            i += 1
            continue
        d = -1 if S[i] else 1
        ext = h[i] if d == -1 else low[i]
        stop = ext - d * r.stop_buf * a[i]
        trig = low[i] if d == -1 else h[i]
        # the entry candle(s)
        fill_bar, entry = None, None
        if r.entry == "close":
            j = i + 1
            if sess[j] == sess[i] and entry_allowed(lmin[j], mk):
                fill_bar, entry = j, o[j]
        else:
            for j in range(i + 1, min(i + 1 + r.break_bars, n)):
                if sess[j] != sess[i] or not entry_allowed(lmin[j], mk):
                    break
                if (h[j] >= stop) if d == -1 else (low[j] <= stop):
                    if not ((o[j] < trig) if d == -1 else (o[j] > trig)):
                        break                               # the wick was taken out before any break
                if (o[j] <= trig) if d == -1 else (o[j] >= trig):
                    fill_bar, entry = j, o[j]               # gapped through the trigger
                    break
                if (low[j] < trig) if d == -1 else (h[j] > trig):
                    fill_bar, entry = j, trig
                    break
        if fill_bar is None:
            i += 1
            continue
        planned_tgt = vw[i]
        risk = d * (entry - stop)
        if not (risk > 0) or d * (planned_tgt - entry) <= 0:
            i = fill_bar + 1                                 # no room to VWAP (or the stop is inside)
            continue
        if r.target == "1.5R":
            planned_tgt = entry + d * 1.5 * risk
        assert_bracket(d, entry, stop, planned_tgt)
        # manage
        x, exit_px, why = fill_bar, None, None
        while x < n:
            if x > fill_bar and (sess[x] != sess[fill_bar] or lmin[x] == mk.flat_min
                                 or (mk.kind == "futures" and lmin[x] >= mk.flat_min and lmin[x] < 18 * 60)):
                exit_px, why = o[x], "session end"
                break
            if (h[x] >= stop) if d == -1 else (low[x] <= stop):
                gap = (o[x] >= stop) if d == -1 else (o[x] <= stop)
                exit_px, why = (o[x] if gap and x > fill_bar else stop), "stop"
                break
            if x > fill_bar:
                tgt = vw[x - 1] if r.target == "vwap" else planned_tgt
                through = mk.tick if mk.kind == "futures" else 0.0
                if (o[x] <= tgt) if d == -1 else (o[x] >= tgt):
                    exit_px, why = o[x], "target"
                    break
                if (low[x] < tgt - through) if d == -1 else (h[x] > tgt + through):
                    exit_px, why = tgt, "target"
                    break
            x += 1
        if exit_px is None:
            x = n - 1
            exit_px, why = c[x], "data end"
        gross_pts = d * (exit_px - entry)
        if mk.kind == "futures":
            slip = NQ_SLIP_TICKS * mk.tick
            cost_pts = NQ_COMMISSION_PTS * 2 + slip + (0.0 if why == "target" else slip)
            if r.entry == "close":
                cost_pts += 0.0                          # a market entry pays the same tick as a stop entry
            cost_R = cost_pts / risk
        else:
            c_in = TAKER + SLIP
            c_out = MAKER if why == "target" else TAKER + SLIP
            cost_R = (c_in * entry + c_out * exit_px) / risk
        fund_R = 0.0
        if funding is not None:
            due = funding[(funding.index > idx[fill_bar]) & (funding.index <= idx[x])]
            fund_R = float(d * -1 * due.sum() * entry / risk) if len(due) else 0.0
        rows.append({"market": mk.name, "side": d, "ex_time": idx[i], "entry_time": idx[fill_bar],
                     "exit_time": idx[x], "entry": entry, "stop": stop, "planned_target": planned_tgt,
                     "planned_rr": d * (planned_tgt - entry) / risk, "exit": exit_px, "reason": why,
                     "risk": risk, "risk_atr": risk / a[i], "stretch_atr": abs(ext - vw[i]) / a[i], "gross_R": gross_pts / risk, "cost_R": cost_R,
                     "fund_R": fund_R, "net_R": gross_pts / risk - cost_R + fund_R,
                     "lmin_entry": lmin[fill_bar]})
        i = x + 1
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------------------------------
# data
# ----------------------------------------------------------------------------------------------
def load_nq() -> tuple:
    """NQ futures 5m bars, minus sessions with a 1m jump the independent CFD does not show."""
    m1 = pd.read_pickle(NQ_PKL)
    cfd = load_cached_1m(NQ_CFD)
    cfd.index = cfd.index.tz_convert("UTC")
    a_ = np.log(m1["close"]).diff()
    b_ = np.log(cfd["close"]).diff().reindex(a_.index)
    contig = (m1.index.to_series().diff() == pd.Timedelta(minutes=1)).to_numpy()
    bad = ((a_ - b_).abs() > 0.005).to_numpy() & contig & b_.notna().to_numpy()
    sess = (m1.index.tz_convert(NQ.tz) + pd.Timedelta(hours=NQ.anchor_hours)).normalize().tz_localize(None)
    bad_sessions = set(sess[bad])
    b = to_5m(m1)
    bs = (b.index.tz_convert(NQ.tz) + pd.Timedelta(hours=NQ.anchor_hours)).normalize().tz_localize(None)
    keep = ~pd.Index(bs).isin(bad_sessions)
    return b[keep], len(bad_sessions), pd.Index(sess).nunique()


def load_crypto(sym: str) -> tuple:
    df = load_cached_1m(f"{LOCAL}/sdz/um5m_{sym}USDT.csv.gz")
    df.index = df.index.tz_convert("UTC")
    f = pd.read_csv(COMMITTED_FUNDING[f"{sym}USDT"])
    fund = pd.Series(f["rate"].to_numpy(), pd.DatetimeIndex(pd.to_datetime(f["timestamp"], unit="s", utc=True)))
    return df, fund


# ----------------------------------------------------------------------------------------------
# stats
# ----------------------------------------------------------------------------------------------
def cluster_t(x: np.ndarray, groups: np.ndarray) -> tuple:
    n = len(x)
    if n < 3:
        return (float(np.mean(x)) if n else float("nan")), float("nan")
    m = float(np.mean(x))
    dev = pd.Series(x - m).groupby(groups).sum().to_numpy()
    g = len(dev)
    se = math.sqrt(float((dev ** 2).sum()) * g / max(g - 1, 1)) / n
    return m, (m / se if se > 0 else float("nan"))


def summary(t: pd.DataFrame, col: str = "net_R") -> dict:
    if t is None or len(t) == 0:
        return {"n": 0, "win": np.nan, "pf": np.nan, "mean": np.nan, "t": np.nan}
    x = t[col].to_numpy()
    wk = pd.DatetimeIndex(t["entry_time"]).strftime("%G-W%V").to_numpy()
    m, tt = cluster_t(x, wk)
    pos, neg = x[x > 0].sum(), -x[x < 0].sum()
    return {"n": len(x), "win": float((x > 0).mean()), "pf": float(pos / neg) if neg > 0 else np.inf, "mean": m, "t": tt}


def fmt(s: dict) -> str:
    if s["n"] == 0:
        return "n    0"
    return f"n {s['n']:5d}  win {100 * s['win']:5.1f}%  PF {s['pf']:5.2f}  mean {s['mean']:+.3f}R  t {s['t']:+5.2f}"


def verdict(s: dict) -> str:
    ok = s["n"] >= PASS_N and s["pf"] >= PASS_PF and s["mean"] > 0 and s["t"] >= PASS_T
    return ("PASS" if ok else "FAIL") + (f"  [n>={PASS_N} {'yes' if s['n'] >= PASS_N else 'NO'}, PF>={PASS_PF} "
                                         f"{'yes' if s['pf'] >= PASS_PF else 'NO'}, t>={PASS_T} "
                                         f"{'yes' if s['mean'] > 0 and s['t'] >= PASS_T else 'NO'}]")


def fresh(t: pd.DataFrame) -> pd.DataFrame:
    return t[pd.DatetimeIndex(t["entry_time"]) >= FRESH_FROM] if len(t) else t


# ----------------------------------------------------------------------------------------------
# self-tests
# ----------------------------------------------------------------------------------------------
def _synthetic(side: int, breaks: bool = True) -> tuple:
    """One crypto-style UTC day of 5m bars: quiet near 100 with volume, a 6-bar rip (side=-1: up) to
    ~108, an exhaustion candle with a long wick at 13:00, the next candle breaking (or not) its low,
    then a slide back through VWAP. Returns bars and the exhaustion bar's index."""
    idx = pd.date_range("2025-03-03 00:00", periods=288, freq="5min", tz="UTC")
    rng = np.random.default_rng(5)
    base = 100 + np.cumsum(rng.normal(0, 0.02, len(idx)))
    o = base.copy(); c = base + rng.normal(0, 0.02, len(idx))
    h = np.maximum(o, c) + 0.05; low = np.minimum(o, c) - 0.05
    vol = np.full(len(idx), 1000.0)
    s = -side                                                # direction of the stretch
    k = 156                                                  # 13:00 UTC
    lvl = base[k - 7]
    for j in range(6):                                       # the rip
        o[k - 6 + j] = lvl + s * 1.2 * j
        c[k - 6 + j] = lvl + s * 1.2 * (j + 1)
        h[k - 6 + j] = max(o[k - 6 + j], c[k - 6 + j]) + 0.05
        low[k - 6 + j] = min(o[k - 6 + j], c[k - 6 + j]) - 0.05
    top = lvl + s * 7.2
    o[k], c[k] = top, top + s * 0.2                          # exhaustion: small body, long wick beyond
    if s == 1:
        h[k], low[k] = top + 3.0, top - 0.1
    else:
        low[k], h[k] = top - 3.0, top + 0.1
    ex_trig = low[k] if s == 1 else h[k]
    o[k + 1] = c[k]
    if breaks:
        c[k + 1] = ex_trig - s * 0.8
    else:
        c[k + 1] = c[k] + s * 0.05
    h[k + 1] = max(o[k + 1], c[k + 1]) + 0.05
    low[k + 1] = min(o[k + 1], c[k + 1]) - 0.05
    for j in range(k + 2, k + 40):                           # slide back towards and through the start
        o[j] = c[j - 1]
        c[j] = c[j - 1] - s * 0.4
        h[j] = max(o[j], c[j]) + 0.05
        low[j] = min(o[j], c[j]) - 0.05
    for j in range(k + 40, len(idx)):
        o[j] = c[j - 1]; c[j] = c[j - 1] + rng.normal(0, 0.02)
        h[j] = max(o[j], c[j]) + 0.05; low[j] = min(o[j], c[j]) - 0.05
    return pd.DataFrame({"open": o, "high": h, "low": low, "close": c, "volume": vol}, index=idx), k


def selftest() -> None:
    fails = 0

    def check(name: str, ok: bool) -> None:
        nonlocal fails
        fails += 0 if ok else 1
        print(f"{'PASS' if ok else 'FAIL'}  {name}")

    try:
        assert_bracket(-1, 100.0, 99.0, 98.0)
        check("mutation: a short bracket with its stop below entry is rejected", False)
    except AssertionError:
        check("mutation: a short bracket with its stop below entry is rejected", True)
    r = Rules()
    for side, name in ((-1, "short after a rip"), (1, "long after a dump")):
        bars, k = _synthetic(side)
        ind = indicators(bars, BTC, r)
        t = simulate(bars, BTC, r)
        exp_entry = bars["low"].iloc[k] if side == -1 else bars["high"].iloc[k]
        exp_stop = (bars["high"].iloc[k] if side == -1 else bars["low"].iloc[k]) - side * 0.1 * ind["atr"].iloc[k]
        ok = (len(t) == 1 and t["side"].iloc[0] == side and t["ex_time"].iloc[0] == bars.index[k]
              and t["entry_time"].iloc[0] == bars.index[k + 1] and np.isclose(t["entry"].iloc[0], exp_entry)
              and np.isclose(t["stop"].iloc[0], exp_stop) and np.isclose(t["planned_target"].iloc[0], ind["vwap"].iloc[k])
              and t["reason"].iloc[0] == "target")
        if ok:
            xb = bars.index.get_loc(t["exit_time"].iloc[0])
            tgt = ind["vwap"].iloc[xb - 1]
            ok = np.isclose(t["exit"].iloc[0], tgt) or np.isclose(t["exit"].iloc[0], bars["open"].iloc[xb])
        check(f"planted {name}: exhaustion bar, break entry, stop beyond the wick, exit at the previous bar's VWAP", ok)
        if not ok:
            print(t.T if len(t) else "no trades")
    bars, k = _synthetic(-1, breaks=False)
    check("no trade when the next candle does not break the exhaustion candle", len(simulate(bars, BTC, r)) == 0)
    ind = indicators(bars, BTC, r)
    tp0 = (bars["high"].iloc[0] + bars["low"].iloc[0] + bars["close"].iloc[0]) / 3
    check("VWAP starts each session at the first bar's typical price", np.isclose(ind["vwap"].iloc[0], tp0))
    two = pd.concat([bars, bars.set_axis(bars.index + pd.Timedelta(days=1))])
    ind2 = indicators(two, BTC, r)
    check("VWAP resets at the next session's anchor (00:00 UTC for crypto)",
          np.isclose(ind2["vwap"].iloc[288], (two["high"].iloc[288] + two["low"].iloc[288] + two["close"].iloc[288]) / 3))
    bars, k = _synthetic(-1)
    full = simulate(bars, BTC, r)
    cut = simulate(bars.iloc[:k + 2], BTC, r)
    check("truncated right after the entry bar: same exhaustion bar, entry and stop (no lookahead)",
          len(cut) == 1 and cut["entry"].iloc[0] == full["entry"].iloc[0] and cut["stop"].iloc[0] == full["stop"].iloc[0]
          and cut["ex_time"].iloc[0] == full["ex_time"].iloc[0])
    early = simulate(bars, BTC, replace(r, entry="close"))
    check("ablation 'enter on the exhaustion candle': fills at the next bar's open, one bar before the break rule",
          len(early) >= 1 and early["entry_time"].iloc[0] == bars.index[k + 1] and np.isclose(early["entry"].iloc[0], bars["open"].iloc[k + 1]))
    nq_b, _ = _synthetic(-1)
    tn = simulate(nq_b, replace(NQ, warmup_bars=12), r)
    check("futures costs: commission both sides + one tick on the stop entry (target fills pay no slippage)",
          len(tn) == 0 or (tn["reason"].iloc[0] != "target" or np.isclose(tn["cost_R"].iloc[0], (2 * NQ_COMMISSION_PTS + 0.25) / tn["risk"].iloc[0])))
    print(f"\nselftest: {'ALL PASS' if fails == 0 else f'{fails} FAILED'}")
    if fails:
        sys.exit(1)


# ----------------------------------------------------------------------------------------------
# funnel and report
# ----------------------------------------------------------------------------------------------
def funnel() -> None:
    r = Rules()
    nq, nbad, ntot = load_nq()
    print(f"NQ futures 5m bars {len(nq)} ({nq.index.min():%Y-%m-%d} -> {nq.index.max():%Y-%m-%d}); "
          f"sessions excluded for unmatched jumps: {nbad} of {ntot}")
    for name, b, mk in (("NQ", nq, NQ),) + tuple((s, load_crypto(s)[0], BTC if s == "BTC" else ETH) for s in ("BTC", "ETH")):
        ind = indicators(b, mk, r)
        S, L = setups(ind, mk, r)
        yr = ind.index.year
        print(f"{name}: exhaustion candles per year (short + long): "
              + ", ".join(f"{y}: {int(S[yr == y].sum() + L[yr == y].sum())}" for y in sorted(set(yr))))


def report() -> None:
    nq, nbad, ntot = load_nq()
    print(f"NQ futures 5m: {nq.index.min():%Y-%m-%d} -> {nq.index.max():%Y-%m-%d}, {nbad} of {ntot} sessions excluded "
          f"(unmatched >0.5% one-minute jump vs HistData NSXUSD)")
    crypto = {s: load_crypto(s) for s in ("BTC", "ETH")}
    base = Rules()

    def run(r: Rules, which: str = "all") -> dict:
        out = {}
        if which in ("all", "NQ"):
            out["NQ"] = simulate(nq, NQ, r)
        if which in ("all", "crypto"):
            out["BTC/ETH"] = pd.concat([simulate(crypto[s][0], BTC if s == "BTC" else ETH, r, crypto[s][1])
                                        for s in ("BTC", "ETH")], ignore_index=True)
        return out

    prim = run(base)
    for k, t in prim.items():
        t.to_csv(f"{LOCAL}/v034_{k.replace('/', '')}_trades.csv", index=False)
    print("\n" + "=" * 100 + "\nPRIMARY (fresh era 2024-01-01 -> data end; NQ ends 2025-07-25, BTC/ETH 2026-08-31)\n" + "=" * 100)
    res = {}
    for k, t in prim.items():
        f = fresh(t)
        s = summary(f)
        res[k] = s
        print(f"  {k:8s}: {fmt(s)}  -> {verdict(s)}")
        old = t[pd.DatetimeIndex(t["entry_time"]) < FRESH_FROM]
        print(f"            context before 2024: {fmt(summary(old))}")
        print(f"            gross (no costs): {fmt(summary(f, 'gross_R'))}; median cost {f['cost_R'].median():.3f}R; "
              f"median risk {f['risk_atr'].median():.2f} ATR; planned R:R median {f['planned_rr'].median():.2f} "
              f"(share <= 1: {100 * (f['planned_rr'] <= 1).mean():.0f}%; unwinnable, reward <= cost: "
              f"{100 * (f['planned_rr'] <= f['cost_R']).mean():.1f}%)")
        print(f"            exits: {f['reason'].value_counts(normalize=True).mul(100).round(0).to_dict()}")
    print("\nSECONDARY (labelled; cannot rescue a primary)")
    for k, t in prim.items():
        f = fresh(t)
        for side, nm in ((-1, "shorts"), (1, "longs")):
            print(f"  {k:8s} {nm:6s}: {fmt(summary(f[f['side'] == side]))}")
        for y, g in t.groupby(pd.DatetimeIndex(t["entry_time"]).year):
            print(f"  {k:8s} {y}: {fmt(summary(g))}")
    f = fresh(prim["NQ"])
    rth = (f["lmin_entry"] >= 570) & (f["lmin_entry"] < 960)
    print(f"  NQ RTH 09:30-16:00 entries: {fmt(summary(f[rth]))}")
    print(f"  NQ overnight entries      : {fmt(summary(f[~rth]))}")
    variants = [("his 'don't': enter on the exhaustion candle", replace(base, entry="close")),
                ("break allowed within 3 candles", replace(base, break_bars=3)),
                ("no stretch filter (any wick + break)", replace(base, stretch=False)),
                ("fixed 1.5R target instead of VWAP", replace(base, target="1.5R")),
                ("stretch: beyond the 2.5-sigma band", replace(base, k_sd=2.5)),
                ("stretch: beyond the 3-sigma band", replace(base, k_sd=3.0)),
                ("stretch: >= 2 ATR from VWAP instead of bands", replace(base, stretch_mode="atr", k_vwap=2.0)),
                ("wick >= 2/3 of the candle", replace(base, wick_share=2 / 3))]
    for label, r in variants:
        out = run(r)
        print(f"  {label:44s}: " + " | ".join(f"{k} {fmt(summary(fresh(t)))}" for k, t in out.items()))
    print("\n" + "=" * 100 + "\nPRE-REGISTERED VERDICTS\n" + "=" * 100)
    for k, s in res.items():
        print(f"  {k:8s}: {fmt(s)}  -> {verdict(s)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--funnel", action="store_true")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    if a.funnel:
        funnel()
    if a.report:
        report()


if __name__ == "__main__":
    main()
