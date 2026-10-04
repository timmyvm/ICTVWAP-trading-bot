"""
Benchmark the v0.23 candidate (with v0.26 quarterly selection) against the S&P 500
over the identical out-of-sample window, quarter by quarter.

S&P source: FRED series SP500 (daily index level, PRICE ONLY — no dividends).
Dividends are added back as a flat 1.4 %/yr (0.35 %/quarter), roughly the
index's 2021-2026 yield, and stated wherever it matters.

Reports compounded and annualised return, max drawdown on the quarterly series
(quarterly granularity UNDERSTATES true peak-to-trough for both), quarterly
volatility, the correlation between the two, and a 50/50 quarterly-rebalanced
blend — the only way a lower-returning strategy can still earn its place.
"""

import io
import os
import sys

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, ".")
from backtest.coin_selection_walkforward import quarter_matrix  # noqa: E402

FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=SP500&cosd=2020-06-01&coed=2026-10-01"
CACHE = "backtest/data_cache/local/sp500_fred.csv"
DIV_PER_Q = 0.014 / 4


def sp500_quarterly() -> pd.Series:
    if not os.path.exists(CACHE):
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        r = requests.get(FRED, timeout=60)
        r.raise_for_status()
        open(CACHE, "w").write(r.text)
    s = pd.read_csv(CACHE)
    s.columns = ["date", "px"]
    s["date"] = pd.to_datetime(s["date"])
    s["px"] = pd.to_numeric(s["px"], errors="coerce")
    s = s.dropna().set_index("date")["px"]
    q_close = s.groupby(s.index.to_period("Q")).last()
    return q_close.pct_change().dropna() + DIV_PER_Q


def stats(r: pd.Series) -> dict:
    eq = (1.0 + r).cumprod()
    tot = eq.iloc[-1] - 1.0
    yrs = len(r) / 4.0
    dd = (eq / eq.cummax() - 1.0).min()
    return {"total": tot, "cagr": (1.0 + tot) ** (1.0 / yrs) - 1.0, "maxdd": dd,
            "vol_q": r.std(ddof=1), "worst_q": r.min(), "pos_q": (r > 0).mean()}


def main() -> None:
    qs, syms, R, INC, ACT = quarter_matrix()
    k = INC.sum(axis=1)
    sel = pd.Series([R[i, INC[i]].mean() if k[i] else 0.0 for i in range(len(qs))],
                    index=pd.PeriodIndex(qs, freq="Q"))
    allon = pd.Series([R[i, ACT[i]].mean() for i in range(len(qs))], index=sel.index)
    spx = sp500_quarterly()
    common = sel.index.intersection(spx.index)
    sel, allon, spx = sel[common], allon[common], spx[common]
    blend = 0.5 * sel + 0.5 * spx

    print(f"window {common[0]} -> {common[-1]} ({len(common)} quarters); S&P = FRED price index "
          f"+ {100 * DIV_PER_Q * 4:.1f}%/yr dividends")
    print(f"{'':34s} {'total':>8s} {'per yr':>7s} {'max DD':>7s} {'worst q':>8s} {'q vol':>6s} {'q up':>5s}")
    for name, r in (("S&P 500", spx), ("strategy, quarterly selection", sel),
                    ("strategy, all coins always on", allon), ("50/50 S&P + strategy", blend)):
        s = stats(r)
        print(f"{name:34s} {100 * s['total']:+7.1f}% {100 * s['cagr']:+6.1f}% {100 * s['maxdd']:+6.1f}% "
              f"{100 * s['worst_q']:+7.1f}% {100 * s['vol_q']:5.1f}% {100 * s['pos_q']:4.0f}%")
    print(f"\ncorrelation of quarterly returns, strategy vs S&P: {sel.corr(spx):+.2f} "
          f"(all-on {allon.corr(spx):+.2f})")
    down = spx < 0
    print(f"in the {int(down.sum())} quarters the S&P fell: S&P mean {100 * spx[down].mean():+.1f}%, "
          f"strategy mean {100 * sel[down].mean():+.1f}%")
    print("\nper year:")
    for y in sorted(set(common.year)):
        m = common.year == y
        print(f"  {y}: S&P {100 * ((1 + spx[m]).prod() - 1):+6.1f}%   strategy {100 * ((1 + sel[m]).prod() - 1):+6.1f}%"
              f"{'   (partial)' if m.sum() < 4 else ''}")


if __name__ == "__main__":
    main()
