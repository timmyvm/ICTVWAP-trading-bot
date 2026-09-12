"""
"$10,000 on Jan 1 — what did one year return?" for the EMA-200 3xATR bracket rule.

Each calendar year is simulated INDEPENDENTLY: a fresh start balance on
Jan 1 with the 210-bar warmup taken from the bars immediately before it
(a year with no prior history warms up inside the year, as the original
reference did). This answers the single-year question directly instead
of a compounded multi-year CAGR.

Modes (see backtest/bracket_experiment.simulate):
  open  = the frozen reference — contains the stale-price same-bar
          re-entry lookahead (DEVLOG v0.10i). Printed for scale only;
          NOT an expectation.
  exit  = same-bar re-entry at the exit price — closest to the live bot.
  next  = no same-bar re-entry — fully realizable, conservative.
Costs: Bybit retail taker 0.055 % + 0.01 % slip per side, funding applied
where the committed funding CSV covers the year (2020+); plus a maker
execution variant (0.02 % + 0.01 %) of the "exit" mode.
"""

import argparse
import sys

import pandas as pd

sys.path.insert(0, ".")
from backtest.bracket_experiment import WARMUP, load_funding, simulate  # noqa: E402
from backtest.data import load_cached_1m, resample_ohlcv  # noqa: E402

L = "backtest/data_cache/"
DATASETS = {
    "BTC": ([L + "local/btcusd_1m_2019_2022.csv.gz", L + "local/btcusd_1m_2023_2026.csv.gz"],
            L + "funding_btcusdt_binance.csv"),
    "ETH": ([L + "local/ethusd_1m_2017_2026.csv.gz"], L + "funding_ethusdt_binance.csv"),
}
MODES = ("open", "exit", "next")
MIN_BARS = 24 * 60          # skip a year with fewer than ~60 days of bars


def load_hourly(caches: list[str]) -> pd.DataFrame:
    parts = [resample_ohlcv(load_cached_1m(c), "1h") for c in caches]
    df = pd.concat(parts).sort_index()
    return df[~df.index.duplicated(keep="first")]


def year_slices(df: pd.DataFrame):
    for y in sorted(set(df.index.year)):
        y0 = pd.Timestamp(f"{y}-01-01", tz="America/New_York")
        y1 = pd.Timestamp(f"{y + 1}-01-01", tz="America/New_York")
        pos0, pos1 = df.index.searchsorted(y0), df.index.searchsorted(y1)
        if pos1 - pos0 < MIN_BARS:
            continue
        seg = df.iloc[max(pos0 - WARMUP, 0):pos1]
        yield y, seg, df.index[pos0], df.index[pos1 - 1]


def run(asset: str, start_bal: float, taker: float, slip: float) -> pd.DataFrame:
    caches, fpath = DATASETS[asset]
    df = load_hourly(caches)
    fund = load_funding(fpath)
    print(f"{asset}: {df.index.min()} -> {df.index.max()} ({len(df)} 1H bars)", flush=True)
    rows = []
    for y, seg, first, last in year_slices(df):
        f = fund[(fund.index >= first.tz_convert("UTC")) & (fund.index <= last.tz_convert("UTC"))]
        fund_arg = f if len(f) else None
        rec = {"asset": asset, "year": y, "from": first.date(), "to": last.date(),
               "full_year": bool(first.month == 1 and first.day == 1 and last.month == 12 and last.day == 31),
               "funding": fund_arg is not None}
        for mode in MODES:
            r = simulate(seg, start_bal=start_bal, taker_pct=taker, slip_pct=slip,
                         funding=fund_arg, reentry=mode)
            rec[f"{mode}_net"] = r.get("net", 0.0)
            rec[f"{mode}_win"] = r.get("win_pct", float("nan"))
            rec[f"{mode}_dd"] = r.get("max_dd_pct", float("nan"))
            rec[f"{mode}_n"] = r.get("n", 0)
        r = simulate(seg, start_bal=start_bal, taker_pct=0.02, slip_pct=slip,
                     funding=fund_arg, reentry="exit")
        rec["exit_maker_net"] = r.get("net", 0.0)
        rows.append(rec)
        print(f"  {y} {first.date()}->{last.date()} funding={'y' if rec['funding'] else 'n'}: "
              f"open {rec['open_net']:+8.0f} | exit {rec['exit_net']:+8.0f} "
              f"(win {rec['exit_win']:.1f}%, maxDD {rec['exit_dd']:.1f}%, n={rec['exit_n']}) | "
              f"next {rec['next_net']:+8.0f} | exit@maker {rec['exit_maker_net']:+8.0f}", flush=True)
    return pd.DataFrame(rows)


def summarize(t: pd.DataFrame) -> None:
    for asset, s in t.groupby("asset"):
        full = s[s["full_year"]]
        print(f"{asset}: full calendar years n={len(full)}")
        for mode in ("open", "exit", "next", "exit_maker"):
            col = f"{mode}_net"
            print(f"  {mode:10s} mean {full[col].mean():+8.0f}  median {full[col].median():+8.0f}  "
                  f"best {full[col].max():+8.0f}  worst {full[col].min():+8.0f}  "
                  f"years>0 {(full[col] > 0).sum()}/{len(full)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", default="BTC,ETH")
    ap.add_argument("--start-bal", type=float, default=10_000.0)
    ap.add_argument("--taker", type=float, default=0.055)
    ap.add_argument("--slip", type=float, default=0.01)
    ap.add_argument("--csv", default=None, help="optional path to write the per-year table")
    args = ap.parse_args()
    t = pd.concat([run(a.strip(), args.start_bal, args.taker, args.slip)
                   for a in args.assets.split(",")], ignore_index=True)
    print()
    summarize(t)
    if args.csv:
        t.to_csv(args.csv, index=False)


if __name__ == "__main__":
    main()
