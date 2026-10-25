"""The edge measurement battery.

An *edge*, here, is a signal whose trade-by-trade excess return is large next to the
all-in cost of trading it, that survives a market hedge, and that a null built from
the same signal cannot reproduce. Each function below measures one part of that
sentence. None of them makes a verdict: the pass bars are pre-registered by the chair
and judged by the statistician (docs/EDGE_LAB.md).

Conventions (same as docs/HANDOFF.md section 3):
  * a decision is made at the CLOSE of bar t, the fill is the OPEN of bar t+1, the
    exit is the open h bars later. Nothing earlier than the close of t may feed the
    signal. `truncation_guard` tests that.
  * costs per side: taker 0.055 % + slippage 0.01 %  ->  13 bp round trip. Funding is
    passed in separately as the real settled amount.
  * t-statistics are clustered by calendar week (or month) and trades are
    de-overlapped, because overlapping h-bar windows are not independent samples.
  * the primary statistic is the DRIFT-MATCHED excess, so a long signal in a bull
    market is not credited with the market's own drift. The hedged alpha is the
    second guard.
"""

from __future__ import annotations

import math
from typing import Callable, Optional

import numpy as np
import pandas as pd

TAKER = 0.00055
MAKER = 0.0002
SLIP = 0.0001
BPS = 1e4
ROUND_TRIP_BPS = 2 * (TAKER + SLIP) * BPS  # 13.0 bp, Bybit USDT perp at VIP0


# --------------------------------------------------------------------------- returns
def trade_return(open_: pd.Series, h: int) -> pd.Series:
    """Simple return of a trade decided at the close of bar t and held h bars.

    Enter at open[t+1], exit at open[t+1+h]. The last h+1 rows are NaN.
    """
    if h < 1:
        raise ValueError("h must be >= 1")
    return open_.shift(-(1 + h)) / open_.shift(-1) - 1.0


def non_overlapping_mask(active: np.ndarray, h: int) -> np.ndarray:
    """Greedy: keep a decision only if the previous kept trade has exited by then."""
    keep = np.zeros(active.shape, dtype=bool)
    nxt = 0
    for i in np.flatnonzero(active):
        if i >= nxt:
            keep[i] = True
            nxt = i + h
    return keep


# --------------------------------------------------------------------------- stats
def _cluster_key(idx: pd.DatetimeIndex, freq: str) -> pd.PeriodIndex:
    if idx.tz is not None:
        idx = idx.tz_convert(None)
    return idx.to_period(freq)


def cluster_mean_t(x: pd.Series, freq: str = "W") -> dict:
    """Mean and cluster-robust t of a series indexed by time (clusters = calendar periods)."""
    x = x.dropna()
    n = len(x)
    if n < 3 or not isinstance(x.index, pd.DatetimeIndex):
        return dict(mean=float("nan"), t=float("nan"), n=n, clusters=0)
    m = float(x.mean())
    s = (x - m).groupby(_cluster_key(x.index, freq)).sum()
    g = int(s.size)
    if g < 3:
        return dict(mean=m, t=float("nan"), n=n, clusters=g)
    se = math.sqrt(float((s ** 2).sum())) / n * math.sqrt(g / (g - 1))
    return dict(mean=m, t=(m / se if se > 0 else float("nan")), n=n, clusters=g)


# --------------------------------------------------------------------------- information test
def information_test(
    signal: pd.Series,
    trade_ret: pd.Series,
    *,
    h: int,
    cost_bps: float = ROUND_TRIP_BPS,
    funding_bps: Optional[pd.Series] = None,
    mkt_ret: Optional[pd.Series] = None,
    cluster: str = "W",
    non_overlapping: bool = True,
) -> dict:
    """Measure a directional signal.

    signal       sign is the direction (+1 long, -1 short, 0 flat), indexed like trade_ret.
    trade_ret    from `trade_return(open_, h)`.
    funding_bps  funding paid by a LONG over each window, in bp (positive = long pays).
    mkt_ret      the market's own trade_return over the same windows (e.g. BTC), for the hedge.

    Returns bp per trade. The numbers to read first:
      gross_excess_bps   drift-matched edge per trade, before cost
      cost_ratio         gross_excess_bps / cost_bps   (repo's rule of thumb: viable at >= 3-5)
      t_excess           clustered t of the drift-matched excess
      net_raw_bps        what the account actually earns per trade, after cost and funding
      hedged_alpha_bps   net of the market's own move over the same windows (needs mkt_ret)
      years_positive     share of calendar years whose net_raw mean is > 0
    """
    df = pd.DataFrame({"sig": signal, "ret": trade_ret}).dropna(subset=["ret"])
    d = np.sign(df["sig"].fillna(0.0).to_numpy())
    active = d != 0
    if non_overlapping:
        active = non_overlapping_mask(active, h)
    ret = df["ret"].to_numpy()
    mu = float(np.mean(ret))
    fund = np.zeros(len(df))
    if funding_bps is not None:
        fund = funding_bps.reindex(df.index).fillna(0.0).to_numpy()

    raw = d * ret * BPS
    exc = d * (ret - mu) * BPS
    net_raw = raw - cost_bps - d * fund
    idx = df.index[active]
    s_exc = pd.Series(exc[active], index=idx)
    s_net = pd.Series(net_raw[active], index=idx)

    n = int(active.sum())
    out: dict = dict(n_trades=n, h=h, cost_bps=cost_bps, drift_bps_per_window=mu * BPS)
    if n < 3:
        out.update(gross_excess_bps=float("nan"), t_excess=float("nan"), cost_ratio=float("nan"))
        return out

    te = cluster_mean_t(s_exc, cluster)
    tn = cluster_mean_t(s_net, cluster)
    out.update(
        gross_raw_bps=float(raw[active].mean()),
        gross_excess_bps=te["mean"],
        t_excess=te["t"],
        cost_ratio=te["mean"] / cost_bps if cost_bps else float("nan"),
        net_raw_bps=tn["mean"],
        t_net=tn["t"],
        hit_rate=float((raw[active] > 0).mean()),
        clusters=te["clusters"],
        sd_trade_bps=float(np.std(raw[active], ddof=1)),
        share_long=float((d[active] > 0).mean()),
    )
    yr = s_net.groupby(s_net.index.year).agg(["mean", "size"])
    yr = yr[yr["size"] >= 10]
    out["years_with_10plus_trades"] = int(len(yr))
    out["years_positive"] = float((yr["mean"] > 0).mean()) if len(yr) else float("nan")

    if mkt_ret is not None:
        m = mkt_ret.reindex(df.index).to_numpy()[active]
        y = (d * ret)[active]
        ok = ~np.isnan(m)
        if ok.sum() >= 10 and np.var(m[ok]) > 0:
            xm = d[active][ok] * m[ok]  # the market move the position was exposed to
            beta = float(np.cov(y[ok], xm)[0, 1] / np.var(xm, ddof=1))
            alpha = pd.Series(((y[ok] - beta * xm) * BPS - cost_bps - (d * fund)[active][ok]),
                              index=idx[ok])
            ta = cluster_mean_t(alpha, cluster)
            out.update(beta_to_market=beta, hedged_alpha_bps=ta["mean"], t_hedged_alpha=ta["t"])
    return out


def null_shift_p(
    signal: pd.Series,
    trade_ret: pd.Series,
    *,
    h: int,
    n_shifts: int = 300,
    seed: int = 0,
    min_shift: Optional[int] = None,
    non_overlapping: bool = True,
) -> dict:
    """Circular-shift null: slide the SAME signal against the returns.

    Keeps the signal's frequency, clustering and autocorrelation, destroys its timing.
    p = share of shifted signals whose |mean drift-matched excess| >= the observed one.
    """
    sig = signal.reindex(trade_ret.index).fillna(0.0).to_numpy()
    ret = trade_ret.to_numpy()
    valid = ~np.isnan(ret)
    mu = float(np.nanmean(ret))
    d0 = np.sign(sig)

    def stat(d: np.ndarray) -> float:
        a = d != 0
        if non_overlapping:
            a = non_overlapping_mask(a, h)
        a = a & valid
        if a.sum() < 3:
            return float("nan")
        return float(np.mean(d[a] * (ret[a] - mu)))

    obs = stat(d0)
    n = len(d0)
    lo = min_shift if min_shift is not None else max(5 * h, n // 20)
    if not (0 < lo < n - lo):
        raise ValueError("series too short for the requested minimum shift")
    rng = np.random.default_rng(seed)
    null = np.array([stat(np.roll(d0, int(s))) for s in rng.integers(lo, n - lo, n_shifts)])
    null = null[~np.isnan(null)]
    p = (1 + float(np.sum(np.abs(null) >= abs(obs)))) / (1 + len(null))
    return dict(observed_bps=obs * BPS, null_mean_bps=float(null.mean() * BPS),
                null_sd_bps=float(null.std(ddof=1) * BPS), p_value=p, n_null=int(len(null)))


# --------------------------------------------------------------------------- cross-section
def cross_sectional_ls(
    signal: pd.DataFrame,
    trade_ret: pd.DataFrame,
    *,
    q: float = 0.2,
    cost_bps_per_leg: float = ROUND_TRIP_BPS,
    min_names: int = 10,
) -> pd.DataFrame:
    """Dollar-neutral long-short on a panel (rows = rebalance times, columns = coins).

    Long the top q of `signal`, short the bottom q, equal weight, held for the window in
    `trade_ret`. Cost assumes FULL turnover at every rebalance (both legs, round trip):
    2 x cost_bps_per_leg. That is conservative on purpose. Short-borrow/funding is not
    modelled here; add the real funding in the caller if the legs are perps.
    Rows must already be spaced at the holding period (the test is de-overlapped by you).
    """
    rows = []
    for t in signal.index.intersection(trade_ret.index):
        s = signal.loc[t]
        r = trade_ret.loc[t]
        ok = s.notna() & r.notna()
        if ok.sum() < min_names:
            continue
        s, r = s[ok], r[ok]
        k = max(1, int(round(q * len(s))))
        order = s.sort_values()
        short, long = r[order.index[:k]].mean(), r[order.index[-k:]].mean()
        gross = (long - short) * BPS
        rows.append((t, gross, gross - 2 * cost_bps_per_leg, int(ok.sum()), long * BPS, short * BPS))
    return pd.DataFrame(rows, columns=["t", "gross_bps", "net_bps", "n_names", "long_bps", "short_bps"]
                        ).set_index("t")


def plateau_score(grid: pd.DataFrame | pd.Series) -> dict:
    """Is the best cell an island or a plateau?

    grid: net mean bp per trade by parameter values (2-D DataFrame, or a Series for one
    parameter). Reports the share of the best cell's neighbours (8-neighbourhood) that
    have the same sign and at least half its magnitude. A real edge degrades smoothly;
    an overfit one is a single lucky cell.
    """
    g = grid.to_frame().T if isinstance(grid, pd.Series) else grid
    a = g.to_numpy(dtype=float)
    if np.isnan(a).all():
        return dict(best=float("nan"), neighbours=0, share_similar=float("nan"))
    i, j = np.unravel_index(np.nanargmax(np.abs(a)), a.shape)
    best = a[i, j]
    nb = []
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            if (di or dj) and 0 <= i + di < a.shape[0] and 0 <= j + dj < a.shape[1]:
                v = a[i + di, j + dj]
                if not np.isnan(v):
                    nb.append(v)
    similar = [v for v in nb if np.sign(v) == np.sign(best) and abs(v) >= 0.5 * abs(best)]
    return dict(best=float(best), neighbours=len(nb),
                share_similar=(len(similar) / len(nb) if nb else float("nan")))


# --------------------------------------------------------------------------- lookahead guard
def truncation_guard(
    signal_fn: Callable[[pd.DataFrame], pd.Series],
    data: pd.DataFrame,
    cut_fracs=(0.5, 0.7, 0.9),
    tail: int = 50,
) -> list[float]:
    """Lookahead test (HANDOFF protocol step 4): the signal computed on data cut at t must
    equal the signal from the full run at t.

    Returns the list of cut fractions that FAILED. Empty = no lookahead found at those cuts.
    Anything normalised with full-sample statistics, resampled by bar OPEN, or built from
    shift(-k) fails here.
    """
    full = signal_fn(data)
    bad = []
    for f in cut_fracs:
        k = int(len(data) * f)
        part = signal_fn(data.iloc[:k])
        ix = part.index[-tail:]
        a = part.loc[ix].to_numpy(dtype=float)
        b = full.reindex(ix).to_numpy(dtype=float)
        if not np.allclose(a, b, equal_nan=True, rtol=1e-9, atol=1e-12):
            bad.append(f)
    return bad


def screen(res: dict, *, ratio_min: float = 3.0, t_min: float = 2.0, n_min: int = 60) -> list[str]:
    """Gate 0, cheap and applied on the EXPLORE era only. Returns the reasons it fails.

    Not a verdict: a pass only earns a pre-registration, a fail ends the idea. The
    ratio comes from the repo's own cost literature (expected move >= 3-5x round trip).
    """
    why = []
    if res.get("n_trades", 0) < n_min:
        why.append(f"n {res.get('n_trades', 0)} < {n_min}")
    if not (res.get("cost_ratio", float("nan")) >= ratio_min):
        why.append(f"cost ratio {res.get('cost_ratio', float('nan')):.2f} < {ratio_min}")
    if not (res.get("t_excess", float("nan")) >= t_min):
        why.append(f"t {res.get('t_excess', float('nan')):.2f} < {t_min}")
    return why
