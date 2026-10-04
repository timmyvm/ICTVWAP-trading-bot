"""
Benchmark: an 80/20 VGS/VAS portfolio (the user's long-term holding) against the
S&P 500, all in AUD — and the hurdle any trading strategy must clear before money
is moved out of it.

Data:
- Yahoo Finance monthly ADJUSTED closes (distributions reinvested) for VGS.AX
  (MSCI World ex-Australia, unhedged), VAS.AX (S&P/ASX 300) and IVV.AX (S&P 500,
  unhedged, i.e. the S&P measured in AUD). Adjusted prices do NOT include
  franking credits, so VAS is understated for an Australian taxpayer.
- FRED DEXUSAL (USD per AUD), to convert the USD-denominated strategy's quarterly
  returns into AUD so the comparison carries the same currency exposure.

80/20 is rebalanced each January (an assumption; a buy-and-drift holder will
differ slightly). The current, incomplete month is dropped.
"""

import json
import os
import sys

import numpy as np
import pandas as pd
import requests

sys.path.insert(0, ".")

CACHE = "backtest/data_cache/local/benchmark"
TICKERS = {"VGS": "VGS.AX", "VAS": "VAS.AX", "S&P 500 (AUD)": "IVV.AX"}
YF = "https://query1.finance.yahoo.com/v8/finance/chart/{t}?range=max&interval=1mo&events=div"
FRED_AUD = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXUSAL&cosd=2020-06-01&coed=2026-10-01"
UA = {"User-Agent": "Mozilla/5.0"}


def fetch(url: str, path: str) -> str:
    os.makedirs(CACHE, exist_ok=True)
    if not os.path.exists(path):
        r = requests.get(url, timeout=60, headers=UA)
        r.raise_for_status()
        open(path, "w").write(r.text)
    return open(path).read()


def monthly_adj(ticker: str) -> pd.Series:
    d = json.loads(fetch(YF.format(t=ticker), f"{CACHE}/yf_{ticker}.json"))["chart"]["result"][0]
    ts = pd.to_datetime(d["timestamp"], unit="s", utc=True).tz_convert("Australia/Sydney")
    adj = d["indicators"]["adjclose"][0]["adjclose"]
    close = d["indicators"]["quote"][0]["close"]
    s = pd.DataFrame({"adj": adj, "close": close}, index=ts.tz_localize(None).to_period("M"))
    s = s[~s.index.duplicated(keep="last")].dropna()
    s = s[s.index < pd.Period(pd.Timestamp.now(), "M")]      # drop the incomplete month
    return s


def stats(r: pd.Series, per_year: int) -> dict:
    eq = (1.0 + r).cumprod()
    yrs = len(r) / per_year
    tot = eq.iloc[-1] - 1.0
    return {"total": tot, "cagr": (1 + tot) ** (1 / yrs) - 1, "maxdd": (eq / eq.cummax() - 1).min(),
            "vol": r.std(ddof=1) * np.sqrt(per_year), "years": yrs}


def portfolio(rets: pd.DataFrame, w: dict) -> pd.Series:
    """Monthly returns of a portfolio rebalanced to weights w every January."""
    out, hold = [], None
    for p, row in rets.iterrows():
        if hold is None or p.month == 1:
            hold = dict(w)
        tot = sum(hold.values())
        r = sum(hold[k] * row[k] for k in hold) / tot
        hold = {k: hold[k] * (1 + row[k]) for k in hold}
        out.append((p, r))
    return pd.Series(dict(out))


def main() -> None:
    px = {name: monthly_adj(t) for name, t in TICKERS.items()}
    for name, s in px.items():
        r_full = s["adj"].pct_change().dropna()
        breaks = r_full[r_full < -0.5]
        print(f"{name:14s} {s.index[0]} -> {s.index[-1]}  months {len(s)}"
              + (f"  WARNING unadjusted unit break(s) at {', '.join(str(p) for p in breaks.index)}"
                 f" — outside the comparison window only if before 2015-01" if len(breaks) else ""))
    rets = pd.DataFrame({k: v["adj"].pct_change() for k, v in px.items()}).dropna()
    big = rets.abs().max()
    print("largest single-month move INSIDE the comparison window:",
          ", ".join(f"{k} {100 * v:.1f}%" for k, v in big.items()))
    assert (rets.abs() < 0.5).all().all(), "a unit break leaked into the comparison window"
    rets["80/20 VGS/VAS"] = portfolio(rets[["VGS", "VAS"]], {"VGS": 0.8, "VAS": 0.2})

    def table(r: pd.DataFrame, label: str) -> None:
        print(f"\n{label}: {r.index[0]} -> {r.index[-1]}")
        print(f"  {'':16s} {'total':>8s} {'per yr':>7s} {'max DD':>7s} {'vol/yr':>7s}")
        for col in ("80/20 VGS/VAS", "VGS", "VAS", "S&P 500 (AUD)"):
            s = stats(r[col], 12)
            print(f"  {col:16s} {100 * s['total']:+7.1f}% {100 * s['cagr']:+6.1f}% "
                  f"{100 * s['maxdd']:+6.1f}% {100 * s['vol']:6.1f}%")

    table(rets, "FULL COMMON HISTORY (since VGS listed)")
    win = rets[(rets.index >= pd.Period("2021-01", "M")) & (rets.index <= pd.Period("2026-09", "M"))]
    table(win, "STRATEGY WINDOW (same quarters as v0.26)")

    print("\ncalendar-year returns, AUD:")
    yr = (1 + rets).groupby(rets.index.year).prod() - 1
    for y, row in yr.iterrows():
        n = int((rets.index.year == y).sum())
        print(f"  {y}: 80/20 {100 * row['80/20 VGS/VAS']:+6.1f}%   S&P(AUD) {100 * row['S&P 500 (AUD)']:+6.1f}%"
              f"   VAS {100 * row['VAS']:+6.1f}%{'   (partial)' if n < 12 else ''}")

    # strategy in AUD over the same quarters
    try:
        from backtest.coin_selection_walkforward import quarter_matrix
        qs, syms, R, INC, ACT = quarter_matrix()
        k = INC.sum(axis=1)
        sel_usd = pd.Series([R[i, INC[i]].mean() if k[i] else 0.0 for i in range(len(qs))],
                            index=pd.PeriodIndex(qs, freq="Q"))
        fx = pd.read_csv(io_text(fetch(FRED_AUD, f"{CACHE}/fred_dexusal.csv")))
        fx.columns = ["date", "usd_per_aud"]
        fx["date"] = pd.to_datetime(fx["date"])
        fx["usd_per_aud"] = pd.to_numeric(fx["usd_per_aud"], errors="coerce")
        fxq = fx.dropna().set_index("date")["usd_per_aud"].groupby(lambda d: pd.Period(d, "Q")).last()
        aud_factor = (fxq.shift(1) / fxq).reindex(sel_usd.index)       # AUD value of 1 USD, q/q
        sel_aud = (1 + sel_usd) * aud_factor - 1
        portq = (1 + win["80/20 VGS/VAS"]).groupby(lambda p: p.asfreq("Q")).prod() - 1
        common = sel_aud.dropna().index.intersection(portq.index)
        s_s, s_p = stats(sel_aud[common], 4), stats(portq[common], 4)
        print(f"\nSTRATEGY vs YOUR PORTFOLIO, same {len(common)} quarters, both in AUD:")
        print(f"  80/20 VGS/VAS           {100 * s_p['total']:+7.1f}%  {100 * s_p['cagr']:+5.1f}%/yr  "
              f"max DD {100 * s_p['maxdd']:+5.1f}% (quarterly)")
        print(f"  strategy, in AUD        {100 * s_s['total']:+7.1f}%  {100 * s_s['cagr']:+5.1f}%/yr  "
              f"max DD {100 * s_s['maxdd']:+5.1f}% (quarterly)")
        print(f"  AUD/USD moved {fxq[common[0] - 1]:.3f} -> {fxq[common[-1]]:.3f}; "
              f"correlation strategy vs 80/20: {sel_aud[common].corr(portq[common]):+.2f}")
    except (ImportError, FileNotFoundError, KeyError, ValueError, requests.RequestException) as e:
        print(f"\n(strategy comparison skipped: {e})")


def io_text(text: str):
    import io
    return io.StringIO(text)


if __name__ == "__main__":
    main()
