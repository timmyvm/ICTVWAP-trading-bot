"""
v0.11 — Diversified daily time-series-momentum portfolio (TSMOM).

The literature-standard construction (Moskowitz/Ooi/Pedersen 2012 family):
per instrument, go long when its trailing L-day return is positive, short
when negative; size every instrument to an equal volatility budget so no
single market dominates; hold for weeks; costs are tiny at daily turnover.

Grid (pre-registered, exploration only): L in {90, 180, 252} days.
Sizing: notional_i = equity * (GROSS_BUDGET / N_active) / sigma_ann_i,
sigma = 20d EWMA of daily returns annualized, floored at 5%; gross capped.
Rebalance: on signal flip, plus monthly vol-resize. Cost per side on traded
notional: taker 0.002% + slippage 0.005%.

Survivor rule: exploration Sharpe >= 0.3 AND maxDD < 40% -> one holdout run.
"""

import argparse
import glob
import os

import numpy as np
import pandas as pd

GROSS_BUDGET = 2.0     # target gross exposure multiple when all instruments active
GROSS_CAP = 3.0
VOL_FLOOR_ANN = 0.05
COST_PER_SIDE = 0.00007  # 0.002% taker + 0.005% slippage
RESIZE = "M"             # monthly vol-resize


def load_panel(daily_dir: str) -> pd.DataFrame:
    frames = {}
    for f in sorted(glob.glob(os.path.join(daily_dir, "*.csv"))):
        name = os.path.basename(f)[:-4]
        d = pd.read_csv(f, parse_dates=["date"]).set_index("date")
        frames[name] = d["close"]
    panel = pd.DataFrame(frames).sort_index()
    # weekends/holidays: keep rows where at least 3 instruments traded
    panel = panel[panel.notna().sum(axis=1) >= 3]
    # limit forward-fill to 5 sessions so dead feeds don't fake prices
    return panel.ffill(limit=5)


def simulate(panel: pd.DataFrame, lookback: int, start_bal: float = 10_000.0) -> dict:
    rets = panel.pct_change()
    mom = panel.pct_change(lookback)
    vol_ann = rets.ewm(span=20).std() * np.sqrt(252)
    vol_ann = vol_ann.clip(lower=VOL_FLOOR_ANN)

    dates = panel.index
    equity = start_bal
    notional = pd.Series(0.0, index=panel.columns)  # signed $ positions
    curve = []
    trades_cost = 0.0
    last_resize_month = None

    for i in range(1, len(dates)):
        dt = dates[i]
        r = rets.iloc[i].fillna(0.0)
        # 1) mark to market with yesterday's positions
        pnl = float((notional * r).sum())
        equity += pnl

        # 2) desired book from yesterday's information (no lookahead)
        sig = np.sign(mom.iloc[i - 1])
        v = vol_ann.iloc[i - 1]
        active = sig.replace(0, np.nan).dropna().index.intersection(v.dropna().index)
        # instruments need full lookback history
        active = [a for a in active if not np.isnan(mom.iloc[i - 1][a])]
        target = pd.Series(0.0, index=panel.columns)
        if active:
            per = equity * (GROSS_BUDGET / len(active))
            for a in active:
                target[a] = sig[a] * per / v[a] * 0.10  # 10% ann vol unit
            gross = target.abs().sum()
            if gross > equity * GROSS_CAP:
                target *= equity * GROSS_CAP / gross

        # 3) trade on signal flips always; full resize monthly
        month = (dt.year, dt.month)
        do_resize = month != last_resize_month
        flip = np.sign(target) != np.sign(notional)
        new_book = notional.copy()
        new_book[flip] = target[flip]
        if do_resize:
            new_book = target.copy()
            last_resize_month = month
        traded = (new_book - notional).abs().sum()
        cost = traded * COST_PER_SIDE
        equity -= cost
        trades_cost += cost
        notional = new_book

        curve.append((dt, equity))

    eq = pd.Series(dict(curve))
    daily = eq.pct_change().dropna()
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = (eq.iloc[-1] / eq.iloc[0]) ** (1 / years) - 1
    sharpe = daily.mean() / daily.std() * np.sqrt(252) if daily.std() > 0 else 0.0
    dd = (eq / eq.cummax() - 1).min()
    per_year = eq.resample("YE").last().pct_change().dropna()
    first_year = eq.resample("YE").last().iloc[0] / start_bal - 1
    py = {eq.index[0].year: round(100 * first_year, 1)}
    py.update({d.year: round(100 * v, 1) for d, v in per_year.items()})
    return {
        "lookback": lookback,
        "end_bal": round(eq.iloc[-1], 0),
        "cagr_pct": round(100 * cagr, 2),
        "sharpe": round(sharpe, 2),
        "max_dd_pct": round(-100 * dd, 1),
        "costs": round(trades_cost, 0),
        "per_year_pct": py,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--daily-dir", default="backtest/data_cache/local/daily")
    ap.add_argument("--explore-end", default="2013-01-01")
    args = ap.parse_args()

    panel = load_panel(args.daily_dir)
    print(f"panel: {panel.shape[1]} instruments, {panel.index.min().date()} -> {panel.index.max().date()}, {len(panel)} days")
    cut = pd.Timestamp(args.explore_end)
    explore, holdout = panel[panel.index < cut], panel[panel.index >= cut]

    survivors = []
    for L in (90, 180, 252):
        r = simulate(explore, L)
        print(f"EXPLORE L={L}: {r}")
        if r["sharpe"] >= 0.3 and r["max_dd_pct"] < 40:
            survivors.append(L)
    print(f"\nsurvivors -> holdout: {survivors or 'NONE'}\n")
    for L in survivors:
        r = simulate(holdout, L)
        print(f"HOLDOUT L={L}: {r}")


if __name__ == "__main__":
    main()
