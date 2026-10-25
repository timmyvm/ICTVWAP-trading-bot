"""Outcome-blind distributions of the proposed regime variables on the EXPLORE quadrant only.

Half-A symbols, bars stamped <= 2024-12-31, funding settlements <= 2024-12-31 23:59 for half-A
symbols. Reports how many days fall in each regime level (state counts, no forward returns).
"""
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[3]
E = REPO / "backtest/data_cache/local/edge"
END = pd.Timestamp("2024-12-31", tz="UTC")

sa = pd.read_csv(REPO / "research/prereg/split_assignment.csv")
A = sa[(sa.half == "A") & (sa.early_days > 0)].symbol.tolist()

C, V = {}, {}
for s in A:
    k = pd.read_csv(E / "klines_1d_um" / f"{s}.csv", usecols=["timestamp", "close", "quote_volume"])
    k.index = pd.to_datetime(k.timestamp, unit="s", utc=True)
    k = k[k.index <= END]
    k.loc[k.quote_volume <= 0, "close"] = np.nan
    C[s], V[s] = k.close, k.quote_volume.where(k.quote_volume > 0)
idx = pd.date_range(pd.Timestamp("2020-01-01", tz="UTC"), END, freq="D")
C = pd.DataFrame(C).reindex(idx); V = pd.DataFrame(V).reindex(idx)
age = C.notna().cumsum().where(C.notna())
liq = V.shift(1).rolling(30, min_periods=20).median().where(age >= 90)
rank = liq.rank(axis=1, ascending=False)
top10 = rank <= 10
top50 = rank <= 50

# MKT_A10: equal-weight daily close-to-close log return of the top-10 half-A coins (PIT), >= 5 names
lr = np.log(C / C.shift(1))
n10 = top10.sum(axis=1)
mkt = lr.where(top10).mean(axis=1).where(n10 >= 5)
print("MKT_A10 first day with >=5 names:", mkt.first_valid_index().date(), " names median", n10[n10 >= 5].median())

yr = pd.Series(idx.year, index=idx)
# R1 trend: sign of 90-day cumulative log return ending at t (needs 90 valid days)
tr = mkt.rolling(90, min_periods=90).sum()
r1 = np.sign(tr)
print("\nR1 trend (share of days up / down / NA) by year")
print(pd.DataFrame({"up": (r1 > 0).groupby(yr).mean(), "down": (r1 < 0).groupby(yr).mean(),
                    "na": r1.isna().groupby(yr).mean()}).round(2).to_string())
# number of trend regime switches (episodes) in explore
sw = (r1.dropna().diff().abs() > 0).sum()
print("R1 switches in explore:", int(sw))

# R2 vol tercile: 30-day realised vol of MKT_A10, percentile vs its own trailing 365 days (t-365..t-1), min 180
rv = mkt.rolling(30, min_periods=25).std() * np.sqrt(365)
def trailing_pct(x, win=365, minp=180):
    vals = x.to_numpy(); out = np.full(len(vals), np.nan)
    for i in range(len(vals)):
        if np.isnan(vals[i]):
            continue
        w = vals[max(0, i - win):i]; w = w[~np.isnan(w)]
        if len(w) >= minp:
            out[i] = (w < vals[i]).mean()
    return pd.Series(out, index=x.index)
p2 = trailing_pct(rv)
r2 = pd.cut(p2, [-0.001, 1 / 3, 2 / 3, 1.001], labels=["low", "mid", "high"])
print("\nR2 vol tercile counts by year")
print(pd.crosstab(yr, r2.astype(str)).to_string())

# R4 liquidity: 30-day mean of total quote volume of the top-10 half-A coins, percentile vs trailing 365 d
tv = V.where(top10).sum(axis=1).where(n10 >= 5)
tv30 = tv.rolling(30, min_periods=25).mean()
p4 = trailing_pct(np.log(tv30))
r4 = pd.cut(p4, [-0.001, 1 / 3, 2 / 3, 1.001], labels=["low", "mid", "high"])
print("\nR4 liquidity tercile counts by year")
print(pd.crosstab(yr, r4.astype(str)).to_string())

# R6 dispersion: cross-sectional sd of 7-day log returns of top-50 half-A coins, percentile vs trailing 365 d
r7 = np.log(C / C.shift(7))
disp = r7.where(top50).std(axis=1).where(top50.sum(axis=1) >= 10)
p6 = trailing_pct(disp)
r6 = pd.cut(p6, [-0.001, 1 / 3, 2 / 3, 1.001], labels=["low", "mid", "high"])
print("\nR6 dispersion tercile counts by year")
print(pd.crosstab(yr, r6.astype(str)).to_string())

# R3 funding: median across half-A top-50 coins with funding of the trailing 7-day mean f8 (bp),
# using settlements strictly before the decision instant (bar close = next 00:00 UTC)
fdir = E / "funding"
have = [s for s in A if (fdir / f"{s}.csv").exists()]
print("\nhalf-A symbols with a funding file:", len(have), "of", len(A))
F = {}
for s in have:
    f = pd.read_csv(fdir / f"{s}.csv")
    t = pd.to_datetime(f.timestamp, unit="ms" if f.timestamp.max() > 1e11 else "s", utc=True)
    f = pd.Series(f.f8.to_numpy() * 1e4, index=t).sort_index()
    f = f[f.index <= END + pd.Timedelta(hours=23, minutes=59)]
    F[s] = f
# decision at the close of day d = (d+1) 00:00 UTC; use settlements with time < d+1 00:00
dec = idx + pd.Timedelta(days=1)
fm = {}
for s, f in F.items():
    cs = f.groupby(f.index.floor("D")).mean()  # daily mean of settlements stamped within day d (all < d+1 00:00)
    cs.index = cs.index.tz_convert("UTC") if cs.index.tz is not None else cs.index.tz_localize("UTC")
    fm[s] = cs.reindex(idx).rolling(7, min_periods=5).mean()
FM = pd.DataFrame(fm).reindex(idx)
cover = FM.notna() & top50.reindex(columns=FM.columns, fill_value=False)
print("mean half-A top-50 coins/day with funding, by year:")
print(cover.sum(axis=1).groupby(yr).mean().round(1).to_string())
med = FM.where(cover).median(axis=1).where(cover.sum(axis=1) >= 5)
print("\nR3 cross-coin median of 7-day mean f8 (bp): quantiles over explore days")
print(med.describe(percentiles=[.05, .1, .25, .33, .5, .67, .75, .9, .95]).round(2).to_string())
lv = pd.cut(med, [-1e9, 0.95, 1.5, 1e9], labels=["below_floor", "floor", "elevated"])
print("\nR3 fixed-threshold level counts by year (below 0.95 bp / 0.95-1.5 / above 1.5)")
print(pd.crosstab(yr, lv.astype(str)).to_string())
