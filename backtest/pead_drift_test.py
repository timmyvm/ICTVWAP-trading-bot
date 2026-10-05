"""
v0.28-exp — Post-earnings drift and the user's confidence gate (DEVLOG v0.28-exp).

Question: after an earnings surprise, does the stock keep drifting in the surprise's direction for
weeks, measured from the first price a non-HFT trader can get; and does the user's rule ("trade 1% of
the portfolio at >= 70% confidence, 2% at >= 90%") make money when a model supplies the confidence?

Data: Nasdaq earnings calendar (backtest/fetch_earnings_calendar.py) and Yahoo daily bars
(backtest/fetch_yahoo_daily.py). Both lack delisted names (survivor universe), so every signal is
measured against the SAME-QUARTER ALL-EVENTS baseline and as a top-minus-bottom spread.

Event timeline (day 0 = report date, the stock's own trading days):
  reaction window  close(-1) -> close(+1)     covers before-open and after-close releases
  entry            open(+2), adjusted = open * adjclose / close
  exit             adjclose of day (+1 + h), h in HORIZONS; primary h = 20
  abnormal         stock return - SPY return over the identical span
Universe at each event, lookahead-free: traded price close(-1) >= $5 and median dollar volume over
days -21..-2 >= $20M (tier 2: >= $100M). Same company twice on one day: keep the higher dollar volume.

Signals: S1 surprise-to-price = (eps - forecast) / traded close(-1)   [PRIMARY]
         S2 reaction = abnormal close(-1) -> close(+1)
         S3 both in the same extreme quintile
Quintile breakpoints come from the PREVIOUS calendar quarter's events.

Usage:
  python backtest/pead_drift_test.py --build      # event table -> data_cache/local/pead_events.csv.gz
  python backtest/pead_drift_test.py --selftest   # must pass before --report
  python backtest/pead_drift_test.py --report
"""

import argparse
import json
import math
import os
import sys
from collections import defaultdict
from typing import Optional

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from backtest.fetch_earnings_calendar import load_events  # noqa: E402
from backtest.fetch_yahoo_daily import VALID, load_daily  # noqa: E402

EVENTS_CACHE = "backtest/data_cache/local/pead_events.csv.gz"
MODEL_OUT = "backtest/live_earnings/model.json"
PILOT_DIR = "backtest/headline_events"
HORIZONS = (5, 10, 20, 40, 60)
H = 20
MIN_PRICE, MIN_DV, TIER2_DV = 5.0, 20e6, 100e6
EXPLORE = (pd.Timestamp("2015-01-01"), pd.Timestamp("2021-12-31"))
HOLDOUT = (pd.Timestamp("2022-01-01"), pd.Timestamp("2026-08-31"))
FULL = (pd.Timestamp("2015-01-01"), pd.Timestamp("2026-08-31"))
COST_SIDE, COST_SIDE_HI = 0.0010, 0.0030
SHORT_FIN = 0.03                       # per year, on short notional
GATE_1, GATE_2 = 0.70, 0.90            # the user's rule: 1% of equity, 2% of equity
SPREAD_BAR = 4 * COST_SIDE             # four legs (long and short, in and out)
TEST_YEARS = range(2018, 2027)
MIN_GATED = 30
BREAK_MOVE = 0.60
QGRID = np.linspace(0.01, 0.99, 99)


# ---------------------------------------------------------------------------- events

def build_events() -> pd.DataFrame:
    ev = load_events()
    ev = ev[ev.eps.notna() & ev.eps_forecast.notna() & (ev.n_ests >= 1)]
    ev = ev[ev.symbol.fillna("").str.match(VALID.pattern)]
    spy = load_daily("SPY")
    spy_adj = spy["adjclose"]
    spy_open = spy["open"] * spy["adjclose"] / spy["close"]
    rows, no_prices = [], 0
    for sym, g in ev.groupby("symbol"):
        px = load_daily(sym)
        if px is None or len(px) < 40:
            no_prices += 1
            continue
        idx = px.index.values
        close, adj, opn = px["close"].values, px["adjclose"].values, px["open"].values
        traded = close * px["split_adj"].values
        dv = close * px["volume"].values
        with np.errstate(divide="ignore", invalid="ignore"):
            adj_open = opn * adj / close
            move = np.abs(adj[1:] / adj[:-1] - 1.0)
        sa = spy_adj.reindex(px.index).values
        so = spy_open.reindex(px.index).values
        for e in g.itertuples(index=False):
            d = np.datetime64(e.date)
            i0 = int(np.searchsorted(idx, d, side="left"))
            if i0 < 22 or i0 + 2 >= len(idx) or idx[i0] - d > np.timedelta64(4, "D"):
                continue
            ent, ent_spy = adj_open[i0 + 2], so[i0 + 2]
            row = {"date": e.date, "symbol": sym, "name": e.name, "eps": e.eps, "eps_forecast": e.eps_forecast,
                   "n_ests": e.n_ests, "surprise_pct": e.surprise_pct, "d0": idx[i0], "entry_date": idx[i0 + 2],
                   "close_m1": traded[i0 - 1], "dollar_vol": float(np.nanmedian(dv[i0 - 21:i0 - 1])),
                   "react": adj[i0 + 1] / adj[i0 - 1] - 1.0, "react_spy": sa[i0 + 1] / sa[i0 - 1] - 1.0,
                   "max_move": float(np.nanmax(move[i0 - 21:min(len(move), i0 + 61)]))}
            for h in HORIZONS:
                j = i0 + 1 + h
                ok = j < len(idx) and ent > 0 and ent_spy > 0
                row[f"ret{h}"] = adj[j] / ent - 1.0 if ok else np.nan
                row[f"abn{h}"] = (adj[j] / ent - 1.0) - (sa[j] / ent_spy - 1.0) if ok else np.nan
                row[f"exit{h}"] = idx[j] if ok else np.datetime64("NaT")
            rows.append(row)
    df = pd.DataFrame(rows)
    df.to_csv(EVENTS_CACHE, index=False, compression="gzip")
    back = load_event_table()
    assert len(back) == len(df), "event table did not re-load to the same length"
    print(f"{len(df)} events from {ev.symbol.nunique()} symbols; {no_prices} symbols without Yahoo data "
          f"(delisted or renamed: the survivor gap)")
    return back


def load_event_table() -> pd.DataFrame:
    df = pd.read_csv(EVENTS_CACHE, dtype={"symbol": str, "name": str}, keep_default_na=False, na_values=[""])
    for c in ["date", "d0", "entry_date"] + [f"exit{h}" for h in HORIZONS]:
        df[c] = pd.to_datetime(df[c])
    return df


def prepare(df: pd.DataFrame, min_dv: float = MIN_DV) -> pd.DataFrame:
    """Universe filter, de-duplication, signals, prior-quarter quintiles."""
    d = df[(df.close_m1 >= MIN_PRICE) & (df.dollar_vol >= min_dv)].copy()
    d = d.sort_values("dollar_vol", ascending=False).drop_duplicates(["d0", "name"]).sort_values(["d0", "symbol"])
    d["s1"] = (d.eps - d.eps_forecast) / d.close_m1
    d["s2"] = d.react - d.react_spy
    d["quarter"] = d.d0.dt.to_period("Q")
    d["week"] = d.d0.dt.to_period("W")
    d["q1"] = quintiles(d, "s1")
    d["q2"] = quintiles(d, "s2")
    return d.reset_index(drop=True)


def quintiles(d: pd.DataFrame, col: str) -> pd.Series:
    """Quintile 1-5 per event using breakpoints from the PREVIOUS quarter only (lookahead-free)."""
    out = pd.Series(np.nan, index=d.index)
    for q in sorted(d.quarter.unique()):
        prev = d.loc[d.quarter == q - 1, col].dropna()
        if len(prev) < 50:
            continue
        br = np.quantile(prev, [0.2, 0.4, 0.6, 0.8])
        cur = d.loc[d.quarter == q, col]
        ok = cur.notna()
        out.loc[cur.index[ok]] = np.searchsorted(br, cur[ok].values, side="right") + 1
    return out


# ---------------------------------------------------------------------------- statistics

def cluster_t(x: np.ndarray, groups: np.ndarray) -> tuple:
    """Mean, cluster-robust t (clusters = report weeks), n, number of clusters."""
    n = len(x)
    if n < 3:
        return float("nan"), float("nan"), n, 0
    m = float(np.mean(x))
    dev = pd.Series(x - m).groupby(groups).sum().values
    g = len(dev)
    se = math.sqrt(float((dev ** 2).sum()) * g / max(g - 1, 1)) / n
    return m, (m / se if se > 0 else float("nan")), n, g


def drift(d: pd.DataFrame, qcol: str, h: int, period: tuple, top=None, bot=None) -> dict:
    s = d[(d.d0 >= period[0]) & (d.d0 <= period[1]) & d[f"abn{h}"].notna()]
    a = s[f"abn{h}"]
    base = a.groupby(s.quarter).transform("mean")
    top_m = (s[qcol] == 5) if top is None else top.reindex(s.index, fill_value=False)
    bot_m = (s[qcol] == 1) if bot is None else bot.reindex(s.index, fill_value=False)
    m_top, t_top, n_top, g = cluster_t((a - base)[top_m].values, s.week[top_m].values)
    m_bot, t_bot, n_bot, _ = cluster_t((a - base)[bot_m].values, s.week[bot_m].values)
    return {"n": len(s), "n_top": n_top, "weeks": g, "top": m_top, "t_top": t_top, "bot": m_bot, "t_bot": t_bot,
            "spread": float(a[top_m].mean() - a[bot_m].mean()), "base": float(a.mean())}


def sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def fit_logit(X: np.ndarray, y: np.ndarray, ridge: float = 1e-6) -> np.ndarray:
    X1 = np.column_stack([np.ones(len(X)), X])
    b = np.zeros(X1.shape[1])
    for _ in range(100):
        p = sigmoid(X1 @ b)
        grad = X1.T @ (y - p) - ridge * b
        hess = (X1 * (p * (1 - p))[:, None]).T @ X1 + ridge * np.eye(len(b))
        step = np.linalg.solve(hess, grad)
        b += step
        if np.abs(step).max() < 1e-9:
            break
    return b


def pct(x, q) -> np.ndarray:
    """Percentile position of x within 99 training quantiles — identical in live_earnings_reader.py."""
    return (np.searchsorted(np.asarray(q), np.asarray(x, dtype=float), side="right") + 0.5) / (len(q) + 1)


def features(s1, s2, q1, q2) -> np.ndarray:
    p1, p2 = pct(s1, q1), pct(s2, q2)
    return np.column_stack([p1, p2, p1 * p2])


def gate_size(conf: np.ndarray) -> np.ndarray:
    return np.where(conf >= GATE_2, 0.02, np.where(conf >= GATE_1, 0.01, 0.0))


def walk_forward(d: pd.DataFrame) -> pd.DataFrame:
    """Model confidence for each test-year event, trained only on events whose EXIT precedes the year."""
    out = []
    for y in TEST_YEARS:
        start, end = pd.Timestamp(f"{y}-01-01"), pd.Timestamp(f"{y + 1}-01-01")
        tr = d[(d.d0 >= FULL[0]) & d.ret20.notna() & (d.exit20 < start) & d.s2.notna()]
        te = d[(d.d0 >= start) & (d.d0 < end) & d.ret20.notna() & d.s2.notna()].copy()
        if len(tr) < 1000 or te.empty:
            continue
        assert tr.exit20.max() < start, "training data leaks into the test year"
        q1, q2 = np.quantile(tr.s1, QGRID), np.quantile(tr.s2, QGRID)
        b = fit_logit(features(tr.s1, tr.s2, q1, q2), (tr.ret20 > 0).astype(float).values)
        te["p_up"] = sigmoid(np.column_stack([np.ones(len(te)), features(te.s1, te.s2, q1, q2)]) @ b)
        te["base_rate"] = float((tr.ret20 > 0).mean())
        out.append(te)
    w = pd.concat(out)
    w["dir"] = np.where(w.p_up >= 0.5, 1, -1)
    w["conf"] = np.maximum(w.p_up, 1 - w.p_up)
    w["size"] = gate_size(w.conf.values)
    w["hit"] = np.sign(w.ret20) == w["dir"]
    w["net"] = w["dir"] * w.ret20 - 2 * COST_SIDE - (w["dir"] < 0) * SHORT_FIN * H / 252
    return w


def final_model(d: pd.DataFrame) -> dict:
    tr = d[(d.d0 >= FULL[0]) & d.ret20.notna() & d.s2.notna()]
    q1, q2 = np.quantile(tr.s1, QGRID), np.quantile(tr.s2, QGRID)
    b = fit_logit(features(tr.s1, tr.s2, q1, q2), (tr.ret20 > 0).astype(float).values)
    return {"version": "v0.28", "target": "stock up over 20 sessions from the day+2 open",
            "features": ["pct(s1)", "pct(s2)", "pct(s1)*pct(s2)"], "intercept": float(b[0]),
            "coef": [float(v) for v in b[1:]], "s1_quantiles": [float(v) for v in q1],
            "s2_quantiles": [float(v) for v in q2], "n_train": int(len(tr)),
            "train_last_exit": str(tr.exit20.max().date()), "up_rate": float((tr.ret20 > 0).mean())}


# ---------------------------------------------------------------------------- sleeve simulation

class Prices:
    """Adjusted open/close paths per symbol, loaded once."""

    def __init__(self) -> None:
        self.cache = {}

    def get(self, sym: str) -> pd.DataFrame:
        if sym not in self.cache:
            px = load_daily(sym)
            px["adj_open"] = px["open"] * px["adjclose"] / px["close"]
            self.cache[sym] = px[["adj_open", "adjclose"]]
        return self.cache[sym]


def simulate(trades: pd.DataFrame, prices: Prices, cost_side: float, h: int = H) -> dict:
    """Calendar-time overlay: each trade puts size x equity into the stock at the entry open."""
    sched = defaultdict(list)
    for i, tr in enumerate(trades.itertuples(index=False)):
        px = prices.get(tr.symbol)
        k0 = px.index.searchsorted(tr.entry_date)
        path = px.iloc[k0:k0 + h]
        if len(path) < h or path.index[0] != tr.entry_date:
            continue
        rets = np.empty(h)
        rets[0] = path.adjclose.iloc[0] / path.adj_open.iloc[0] - 1.0
        rets[1:] = path.adjclose.values[1:] / path.adjclose.values[:-1] - 1.0
        for k, day in enumerate(path.index):
            sched[day].append((i, k, rets[k], tr.direction, tr.size))
    if not sched:
        return {"trades": 0}
    eq, notional, curve, expo = 1.0, {}, [], []
    for day in sorted(sched):
        pnl = 0.0
        for i, k, r, sgn, size in sched[day]:
            if k == 0:
                notional[i] = size * eq
                pnl -= cost_side * notional[i]
            pnl += sgn * notional[i] * r
            if sgn < 0:
                pnl -= SHORT_FIN / 252 * notional[i]
            notional[i] *= 1.0 + r
            if k == h - 1:
                pnl -= cost_side * notional[i]
        expo.append(sum(notional.values()) / eq)
        for i, k, *_ in sched[day]:
            if k == h - 1:
                del notional[i]
        eq += pnl
        curve.append((day, eq))
    c = pd.Series(dict(curve))
    yrs = (c.index[-1] - c.index[0]).days / 365.25
    monthly = c.resample("ME").last().pct_change().dropna()
    return {"trades": len(trades), "cagr": c.iloc[-1] ** (1 / yrs) - 1 if yrs > 0 else float("nan"),
            "total": c.iloc[-1] - 1, "maxdd": float((c / c.cummax() - 1).min()),
            "worst_month": float(monthly.min()) if len(monthly) else float("nan"),
            "mean_expo": float(np.mean(expo)), "max_expo": float(np.max(expo)), "years": yrs}


def sleeve_trades(rows: pd.DataFrame, direction: int, size: float) -> pd.DataFrame:
    t = rows[["symbol", "entry_date"]].copy()
    t["direction"], t["size"] = direction, size
    return t


# ---------------------------------------------------------------------------- self-tests

def synthetic_events(seed: int, plant: float) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for q in pd.period_range("2015Q1", "2026Q2", freq="Q"):
        n = 600
        days = pd.to_datetime(rng.integers(q.start_time.value // 10**9, q.end_time.value // 10**9 - 86400 * 20, n),
                              unit="s").normalize()
        rows.append(pd.DataFrame({"d0": days, "s1": rng.normal(0, 1, n), "s2": rng.normal(0, 0.05, n)}))
    d = pd.concat(rows, ignore_index=True)
    d["quarter"], d["week"] = d.d0.dt.to_period("Q"), d.d0.dt.to_period("W")
    d["q1"], d["q2"] = quintiles(d, "s1"), quintiles(d, "s2")
    d["abn20"] = rng.normal(0, 0.08, len(d)) + plant * (d.q1 == 5)
    return d


def selftest() -> None:
    fails = 0

    def check(name: str, ok: bool, detail: str = "") -> None:
        nonlocal fails
        fails += 0 if ok else 1
        print(f"{'PASS' if ok else 'FAIL'}  {name} {detail}")

    r = drift(synthetic_events(1, 0.01), "q1", 20, HOLDOUT)
    check("planted +1% drift is recovered", r["top"] > 0.005 and r["t_top"] > 2, f"(top {100 * r['top']:+.2f}%, t {r['t_top']:.1f})")
    nulls = [drift(synthetic_events(s, 0.0), "q1", 20, HOLDOUT)["t_top"] for s in range(2, 22)]
    clean = sum(abs(t) < 2 for t in nulls)
    check("null (no plant) stays inside |t| < 2", clean >= 17, f"({clean} of 20 seeds)")
    rng = np.random.default_rng(5)
    X = rng.uniform(0, 1, (20000, 3))
    true = np.array([-0.3, 1.2, -0.8, 0.5])
    y = (rng.uniform(0, 1, 20000) < sigmoid(np.column_stack([np.ones(20000), X]) @ true)).astype(float)
    b = fit_logit(X, y)
    check("logistic fit recovers known coefficients", np.abs(b - true).max() < 0.15, f"({np.round(b, 2)})")
    check("gate thresholds", list(gate_size(np.array([0.5, 0.69, 0.70, 0.89, 0.90, 0.99]))) == [0, 0, .01, .01, .02, .02])
    syn = synthetic_events(3, 0.0)
    for q in sorted(syn.quarter.unique())[1:4]:
        prev = syn.loc[syn.quarter == q - 1, "s1"]
        br = np.quantile(prev, [0.2, 0.4, 0.6, 0.8])
        cur = syn[syn.quarter == q]
        ok = (np.searchsorted(br, cur.s1.values, side="right") + 1 == cur.q1.values).all()
        check(f"quintiles for {q} use {q - 1} breakpoints only", bool(ok))
    if os.path.exists(EVENTS_CACHE):
        d = prepare(load_event_table())
        msft = d[(d.symbol == "MSFT") & (d.date == "2026-07-29")]
        check("known event MSFT 2026-07-29 reaction > +12%", len(msft) == 1 and msft.react.iloc[0] > 0.12,
              f"({100 * msft.react.iloc[0]:+.1f}%)" if len(msft) else "(missing)")
        nke = d[(d.symbol == "NKE") & (d.date == "2026-10-01")]
        check("known event NKE 2026-10-01 reaction about -4.3%", len(nke) == 1 and abs(nke.react.iloc[0] + 0.043) < 0.006,
              f"({100 * nke.react.iloc[0]:+.1f}%)" if len(nke) else "(missing)")
        check("entry is strictly after the reaction window", bool((d.entry_date > d.d0).all()))
        rng = np.random.default_rng(9)
        planted = d.copy()
        planted["abn20"] = rng.normal(0, 0.08, len(d)) + 0.01 * (d.q1 == 5)
        planted.loc[d.abn20.isna(), "abn20"] = np.nan
        r = drift(planted, "q1", 20, HOLDOUT)
        check("planted +1% drift on the REAL event structure is recovered", r["top"] > 0.005 and r["t_top"] > 2,
              f"(top {100 * r['top']:+.2f}%, t {r['t_top']:.1f})")
    else:
        print("SKIP  real-data checks (run --build first)")
    print(f"\nselftest: {'ALL PASS' if fails == 0 else f'{fails} FAILED'}")
    if fails:
        sys.exit(1)


# ---------------------------------------------------------------------------- report

def fmt(r: dict) -> str:
    return (f"n {r['n']:6d}  top {100 * r['top']:+.2f}% (t {r['t_top']:+.1f}, {r['n_top']} ev)  "
            f"bottom {100 * r['bot']:+.2f}% (t {r['t_bot']:+.1f})  spread {100 * r['spread']:+.2f}%")


def pilot(prices: Prices) -> None:
    ev = {e["ticker"]: e for e in json.load(open(f"{PILOT_DIR}/events.json"))}
    pr = json.load(open(f"{PILOT_DIR}/predictions.json"))
    rows = []
    for p in pr:
        e = ev[p["ticker"]]
        px = prices.get(p["ticker"])
        i0 = px.index.searchsorted(pd.Timestamp(e["release_date_et"]))
        if i0 + 1 + H >= len(px):
            continue
        ret = px.adjclose.iloc[i0 + 1 + H] / px.adj_open.iloc[i0 + 2] - 1
        sgn = 1 if p["direction"] == "UP" else -1
        rows.append((p["ticker"], p["confidence"], sgn, ret, np.sign(ret) == sgn))
    t = pd.DataFrame(rows, columns=["ticker", "conf", "dir", "ret20", "hit"])
    hi = t[t.conf >= GATE_1]
    print(f"\nPILOT (labelled; v0.27 calls were made for the reaction, scored here on the 20-session drift "
          f"from the day+2 open): {len(t)} events with complete windows; direction right {int(t.hit.sum())} of {len(t)}; "
          f"confidence >= 70%: {int(hi.hit.sum())} of {len(hi)}, mean signed return "
          f"{100 * (hi.dir * hi.ret20).mean():+.2f}%")


def report() -> None:
    d = prepare(load_event_table())
    d2 = prepare(load_event_table(), TIER2_DV)
    yearly = d.groupby(d.d0.dt.year).size()
    print(f"liquid events: {len(d)} ({d.symbol.nunique()} symbols); per year: "
          + ", ".join(f"{y}:{n}" for y, n in yearly.items()))
    print(f"events with a >{int(100 * BREAK_MOVE)}% one-day move in the window: {int((d.max_move > BREAK_MOVE).sum())}")

    print(f"\n=== PRIMARY: S1 surprise, h = {H}, holdout {HOLDOUT[0].date()} -> {HOLDOUT[1].date()} ===")
    p = drift(d, "q1", H, HOLDOUT)
    print(fmt(p))
    passed = p["top"] > 0 and p["t_top"] >= 2.0 and p["spread"] >= SPREAD_BAR
    print(f"pass bar: top > 0 with t >= 2.0 AND spread >= {100 * SPREAD_BAR:.2f}% -> {'PASS' if passed else 'FAIL'}")

    print("\n=== SECONDARY (labelled; cannot rescue the primary) ===")
    print("S1 explore 2015-2021 :", fmt(drift(d, "q1", H, EXPLORE)))
    print("S1 full 2015-2026    :", fmt(drift(d, "q1", H, FULL)))
    print("S2 reaction, holdout :", fmt(drift(d, "q2", H, HOLDOUT)))
    both_top, both_bot = (d.q1 == 5) & (d.q2 == 5), (d.q1 == 1) & (d.q2 == 1)
    print("S3 both, holdout     :", fmt(drift(d, "q1", H, HOLDOUT, both_top, both_bot)))
    for h in HORIZONS:
        print(f"S1 holdout h={h:2d}      :", fmt(drift(d, "q1", h, HOLDOUT)))
    print("S1 holdout $100M tier:", fmt(drift(d2, "q1", H, HOLDOUT)))
    clean = d[d.max_move <= BREAK_MOVE]
    print("S1 holdout, no >60% day:", fmt(drift(clean, "q1", H, HOLDOUT)))

    print("\n=== CONFIDENCE GATE (the user's rule; model confidence, walk-forward 2018-2026) ===")
    w = walk_forward(d)
    print(f"test events {len(w)}; model p_up range {w.p_up.min():.3f} - {w.p_up.max():.3f}; "
          f"confidence >= 70%: {int((w.conf >= GATE_1).sum())}; >= 90%: {int((w.conf >= GATE_2).sum())}")
    bins = [0, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70, 1.0]
    cal = w.groupby(pd.cut(w.p_up, bins), observed=True).agg(n=("ret20", "size"), p=("p_up", "mean"),
                                                            up=("ret20", lambda x: float((x > 0).mean())))
    print("calibration (predicted p_up vs realised up-rate):")
    for b_, r_ in cal.iterrows():
        print(f"  {str(b_):14s} n {int(r_.n):6d}  predicted {r_.p:.3f}  realised {r_.up:.3f}")
    y = (w.ret20 > 0).astype(float)
    print(f"Brier: model {((w.p_up - y) ** 2).mean():.4f} vs base-rate {((w.base_rate - y) ** 2).mean():.4f}")
    g = w[w["size"] > 0]
    prices = Prices()
    if len(g) < MIN_GATED:
        print(f"VERDICT: {len(g)} gated trades (< {MIN_GATED}): honest confidence rarely reaches 70%; the rule barely trades")
    if len(g):
        print(f"gated trades {len(g)}: hit {int(g.hit.sum())} of {len(g)} ({100 * g.hit.mean():.0f}%), "
              f"mean net {100 * g.net.mean():+.2f}% per trade")
        s = simulate(g.assign(direction=g["dir"]), prices, COST_SIDE)
        print(f"  overlay: {100 * s['cagr']:+.2f}%/yr of portfolio, max DD {100 * s['maxdd']:.2f}%, "
              f"mean exposure {100 * s['mean_expo']:.1f}%")
    top10 = []
    for q in sorted(w.quarter.unique()):
        prev = w.loc[w.quarter == q - 1, "conf"]
        if len(prev) < 100:
            continue
        thr = np.quantile(prev, 0.9)
        top10.append(w[(w.quarter == q) & (w.conf >= thr)])
    t10 = pd.concat(top10)
    print(f"DIAGNOSTIC top-10% most confident per quarter (prior-quarter threshold): {len(t10)} trades, "
          f"hit {100 * t10.hit.mean():.1f}%, mean net {100 * t10.net.mean():+.2f}%/trade")
    s = simulate(t10.assign(direction=t10["dir"], size=0.01), prices, COST_SIDE)
    print(f"  at 1% each: {100 * s['cagr']:+.2f}%/yr, max DD {100 * s['maxdd']:.2f}%, mean exposure {100 * s['mean_expo']:.0f}%")

    print("\n=== DRIFT SLEEVES (1% per trade, overlay on the core portfolio) ===")
    for label, period in (("holdout", HOLDOUT), ("full", FULL)):
        s_ = d[(d.d0 >= period[0]) & (d.d0 <= period[1]) & d.ret20.notna()]
        longs = sleeve_trades(s_[s_.q1 == 5], 1, 0.01)
        shorts = sleeve_trades(s_[s_.q1 == 1], -1, 0.01)
        for name, tr in (("long top quintile", longs), ("long-short", pd.concat([longs, shorts]))):
            for cost in (COST_SIDE, COST_SIDE_HI):
                r = simulate(tr, prices, cost)
                print(f"  {label:7s} {name:17s} cost {100 * cost:.2f}%/side: {r['trades']} trades, "
                      f"{100 * r['cagr']:+.2f}%/yr, max DD {100 * r['maxdd']:.1f}%, worst month "
                      f"{100 * r['worst_month']:+.1f}%, exposure mean {100 * r['mean_expo']:.0f}% max {100 * r['max_expo']:.0f}%")

    pilot(prices)
    m = final_model(d)
    os.makedirs(os.path.dirname(MODEL_OUT), exist_ok=True)
    json.dump(m, open(MODEL_OUT, "w"), indent=1)
    print(f"\nfinal model (all events with exits to {m['train_last_exit']}, n {m['n_train']}) -> {MODEL_OUT}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.build:
        build_events()
    if a.selftest:
        selftest()
    if a.report:
        report()


if __name__ == "__main__":
    main()
