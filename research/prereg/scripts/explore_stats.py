"""Unconditional explore-quadrant statistics for the P2 power table.

Reads ONLY half-A symbols from research/prereg/split_assignment.csv and ONLY 1d bars stamped
<= 2024-12-31 (the explore quadrant). Computes: coverage counts, unconditional forward-return sd
(single coin, pooled), same-date intra-class correlation, equal-weight index sd, a random-sort
(placebo) quintile long-short spread sd, and the sd of |r|. No return is conditioned on any
signal or state.
"""
import hashlib
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
K = REPO / "backtest/data_cache/local/edge/klines_1d_um"
END = pd.Timestamp("2024-12-31", tz="UTC")
BPS = 1e4

sa = pd.read_csv(REPO / "research/prereg/split_assignment.csv")
A = sa[(sa.half == "A") & (sa.early_days > 0)].symbol.tolist()
assert "BTCUSDT" not in A

opens, qv = {}, {}
for s in A:
    k = pd.read_csv(K / f"{s}.csv", usecols=["timestamp", "open", "quote_volume"])
    t = pd.to_datetime(k.timestamp, unit="s", utc=True)
    k = k.assign(t=t).set_index("t")
    k = k[k.index <= END]                      # explore era only: nothing stamped 2025+ is kept
    assert k.index.max() <= END
    k.loc[k.quote_volume <= 0, "open"] = np.nan  # zombie / suspended days are not live
    opens[s] = k["open"]
    qv[s] = k["quote_volume"].where(k.quote_volume > 0)

O = pd.DataFrame(opens).sort_index()
V = pd.DataFrame(qv).reindex(O.index)
idx = pd.date_range(O.index.min(), END, freq="D", tz="UTC")
O, V = O.reindex(idx), V.reindex(idx)
assert O.index.max() <= END

# history filter: >= 90 live days since first live day (point in time)
live = O.notna()
age = live.cumsum().where(live)
elig90 = age >= 90

# point-in-time liquidity rank WITHIN HALF A: trailing 30-day median quote volume, ending t-1
liq = V.shift(1).rolling(30, min_periods=20).median()
rank = liq.where(elig90).rank(axis=1, ascending=False)
top50 = rank <= 50
top10 = rank <= 10

out = []
def p(*a):
    print(*a); out.append(" ".join(str(x) for x in a))

p("half-A coins with explore days:", len(A))
p("explore calendar days:", len(idx), idx.min().date(), "->", idx.max().date())
p("live coin-days:", int(live.sum().sum()), " with >=90d history:", int(elig90.sum().sum()),
  " in top-50 half-A:", int(top50.sum().sum()))
yr = pd.Series(idx.year, index=idx)
cov = pd.DataFrame({"live": live.sum(1), "elig90": elig90.sum(1), "top50": top50.sum(1)})
p("\nmean coins per day by year (live / >=90d / top50):")
p(cov.groupby(yr).mean().round(1).to_string())
p("\ncoin-days by year (>=90d history):")
p(elig90.sum(1).groupby(yr).sum().to_string())

def fwd(h):
    # trade_return convention: decided at close t (== open t+1), enter open[t+1], exit open[t+1+h]
    return O.shift(-(1 + h)) / O.shift(-1) - 1.0

res = {}
for h in (1, 7, 30):
    R = fwd(h)
    for uname, U in (("elig90", elig90), ("top50A", top50)):
        x = R.where(U)
        v = x.stack().to_numpy() * BPS
        v = v[np.isfinite(v)]
        lo, hi = np.percentile(v, [0.5, 99.5])
        vw = np.clip(v, lo, hi)
        mad = 1.4826 * np.median(np.abs(v - np.median(v)))
        kurt = float(pd.Series(v).kurt())
        # intra-class (same-date) correlation, one-way ANOVA estimator on dates
        g = x.stack()
        g = g[np.isfinite(g)] * BPS
        d = g.groupby(level=0)
        m_i = d.size(); mean_i = d.mean(); N = len(g); k_ = len(m_i)
        grand = g.mean()
        ssb = float((m_i * (mean_i - grand) ** 2).sum()); ssw = float(((g - mean_i.reindex(g.index.get_level_values(0)).to_numpy()) ** 2).sum())
        msb = ssb / (k_ - 1); msw = ssw / (N - k_)
        m0 = (N - (m_i ** 2).sum() / N) / (k_ - 1)
        icc = (msb - msw) / (msb + (m0 - 1) * msw)
        # winsorised icc
        gw = g.clip(lo, hi); dw = gw.groupby(level=0); mw = dw.mean(); gr = gw.mean()
        ssbw = float((m_i * (mw - gr) ** 2).sum()); ssww = float(((gw - mw.reindex(gw.index.get_level_values(0)).to_numpy()) ** 2).sum())
        iccw = ((ssbw / (k_ - 1)) - ssww / (N - k_)) / ((ssbw / (k_ - 1)) + (m0 - 1) * ssww / (N - k_))
        absv = np.abs(v)
        res[(h, uname)] = dict(n=len(v), sd=v.std(ddof=1), sd_wins=vw.std(ddof=1), sd_mad=mad, kurt=kurt,
                               icc=icc, icc_wins=iccw, mean_abs=absv.mean(), sd_abs=absv.std(ddof=1))
    # equal-weight top-10 half-A index, non-overlapping h windows
    ew = R.where(top10).mean(axis=1)
    ew = ew[ew.index >= pd.Timestamp("2020-03-01", tz="UTC")]
    ew_no = ew.iloc[::h].dropna() * BPS
    res[(h, "EW10_index")] = dict(n=len(ew_no), sd=ew_no.std(ddof=1))
    ew50 = R.where(top50).mean(axis=1)
    ew50_no = ew50[ew50.index >= pd.Timestamp("2020-03-01", tz="UTC")].iloc[::h].dropna() * BPS
    res[(h, "EW50_index")] = dict(n=len(ew50_no), sd=ew50_no.std(ddof=1))

    # random-sort (placebo) quintile spread within top50A, rebalanced every h days (non-overlapping)
    rows = []
    for t in R.index[::h]:
        r = R.loc[t].where(top50.loc[t]).dropna()
        if len(r) < 10:
            continue
        key = pd.Series({s: int(hashlib.sha256(f"{s}|{t.date()}".encode()).hexdigest(), 16) for s in r.index})
        order = key.sort_values().index
        q = max(1, int(round(0.2 * len(r))))
        rows.append((t, (r[order[-q:]].mean() - r[order[:q]].mean()) * BPS, len(r)))
    sp = pd.DataFrame(rows, columns=["t", "spread", "n"]).set_index("t")
    res[(h, "random_quintile_spread")] = dict(n=len(sp), sd=sp.spread.std(ddof=1), names_med=sp.n.median())

    # half-A split into two random sub-halves (hash parity): correlation of their EW top50 returns
    sub = np.array([int(hashlib.sha256(("sub" + s).encode()).hexdigest(), 16) % 2 for s in R.columns]) == 0
    e1 = R.loc[:, sub].where(top50.loc[:, sub]).mean(axis=1)
    e2 = R.loc[:, ~sub].where(top50.loc[:, ~sub]).mean(axis=1)
    j = pd.concat([e1, e2], axis=1).dropna().iloc[::h]
    j = j[j.index >= pd.Timestamp("2020-07-01", tz="UTC")]
    res[(h, "subhalf_EW_corr")] = dict(n=len(j), corr=float(j.corr().iloc[0, 1]))

p("\nUNCONDITIONAL STATS (bp), explore quadrant only")
for k_, v in res.items():
    p(k_, {a: (round(b, 3) if isinstance(b, float) else b) for a, b in v.items()})

# date-window counts in explore (top50A with >= 10 names, from first such date)
n10 = top50.sum(1)
first10 = n10[n10 >= 10].index.min()
p("\nfirst date with >= 10 eligible top-50 half-A coins:", first10.date())
win = idx[idx >= first10]
p("explore days from that date:", len(win), " weeks:", len(pd.PeriodIndex(win.tz_convert(None), freq="W").unique()),
  " months:", len(pd.PeriodIndex(win.tz_convert(None), freq="M").unique()))
p("mean top-50 names per day from that date:", round(float(n10[n10.index >= first10].mean()), 1))

# coins with >= 365 days of history by year (for long-lookback cells)
age365 = age >= 365
p("\nmean coins/day with >=365d history (and top50 liquidity) by year:")
p((age365 & top50).sum(1).groupby(yr).mean().round(1).to_string())
age750 = age >= 750
p("mean coins/day with >=750d history by year:")
p((age750 & top50).sum(1).groupby(yr).mean().round(1).to_string())

Path(sys.argv[1]).write_text("\n".join(out))
