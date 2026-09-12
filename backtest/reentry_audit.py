"""
Re-entry semantics audit of the bracket reference engine.

The frozen reference re-enters at bar i's OPEN after an exit inside bar i —
a price from before the exit move (stale). This driver loads each dataset
once and runs every combination of re-entry semantics x Rule A, so the
size of the artifact and the survival of the streak effect can be read
side by side. Costs: Bybit retail for crypto, futures-CFD for the rest.
"""

import sys

import pandas as pd

sys.path.insert(0, ".")
from backtest.bracket_experiment import simulate  # noqa: E402
from backtest.data import load_cached_1m, resample_ohlcv  # noqa: E402

L = "backtest/data_cache/local/"
DATASETS = [
    ("BTC 2019-22", L + "btcusd_1m_2019_2022.csv.gz", None, 0.055, 0.01),
    ("BTC 2023-26", L + "btcusd_1m_2023_2026.csv.gz", None, 0.055, 0.01),
    ("ETH 2018-26", L + "ethusd_1m_2017_2026.csv.gz", "2018-01-01", 0.055, 0.01),
    ("NAS100 15-20", L + "nas100_1m_2015_2020.csv.gz", None, 0.002, 0.005),
    ("XAU 06-20", L + "xau_usd_1h_2005_2020.csv.gz", None, 0.002, 0.005),
    ("WTICO 05-20", L + "wtico_usd_1h_2005_2020.csv.gz", None, 0.002, 0.005),
    ("SPX500 05-20", L + "spx500_usd_1h_2005_2020.csv.gz", None, 0.002, 0.005),
]
CONFIGS = [("open", False), ("exit", False), ("next", False),
           ("open", True), ("exit", True), ("next", True)]


def main():
    print(f"{'dataset':13s} {'reentry':7s} {'ruleA':5s} {'n':>5s} {'win%':>5s} {'PF':>5s} "
          f"{'Sharpe':>6s} {'maxDD':>6s} {'CAGR%':>7s} {'yrs+':>5s}")
    for name, cache, start, taker, slip in DATASETS:
        df = resample_ohlcv(load_cached_1m(cache), "1h")
        if start:
            df = df[df.index >= pd.Timestamp(start, tz="America/New_York")]
        for reentry, rule_a in CONFIGS:
            r = simulate(df, taker_pct=taker, slip_pct=slip,
                         reentry=reentry, skip_after_loss=rule_a)
            yrs = r["per_year"]
            pos = sum(1 for v in yrs.values() if v > 0)
            print(f"{name:13s} {reentry:7s} {str(rule_a):5s} {r['n']:5d} {r['win_pct']:5.1f} "
                  f"{r['pf']:5.2f} {r['sharpe']:6.2f} {r['max_dd_pct']:6.1f} {r['cagr_pct']:7.1f} "
                  f"{pos:2d}/{len(yrs):<2d}", flush=True)
        print(flush=True)


if __name__ == "__main__":
    main()
