"""
v0.18-exp — Funding carry: plain, timed, leveraged, rotated.

Long spot + short the same coin's USDT-M perp: price risk hedged, P&L =
funding received (shorts RECEIVE positive rates) + basis P&L (spot leg
return minus perp leg return) − costs. Pre-registered cells (DEVLOG):
  1. plain   — always on, per coin, 1x notional
  2. timed   — in while trailing 24h mean funding > 0, else flat
  3. levered — cell 2 at 2x / 3x notional per unit capital
  4. rotated — weekly top-3 by trailing 7-day mean funding (> 0), equal
               weight, hysteresis: keep a holding while it stays top-5
Costs: spot 0.1% + perp 0.055% per leg, entry and exit (0.31% round trip
per slot). Basis from daily closes (spot vs perp) at the same UTC day.
Data: backtest/data_cache/local/carry/{funding,spot1d,um1d}_{SYM}.*
produced by backtest/fetch_binance_archive.py.
"""

import argparse
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, ".")

CARRY_DIR = "backtest/data_cache/local/carry"
UNIVERSE = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT",
            "SOLUSDT", "DOTUSDT", "LINKUSDT", "LTCUSDT", "AVAXUSDT", "ATOMUSDT"]
COST_PER_LEG = 0.001 + 0.00055          # spot + perp, one side
ROUND_TRIP = 2 * COST_PER_LEG           # entry + exit, both legs = 0.31%
TOP_N, KEEP_N = 3, 5


def load_symbol(sym: str) -> pd.DataFrame | None:
    """Daily frame (UTC dates): funding (sum of the day's settlements), spot close, perp close."""
    f_path = f"{CARRY_DIR}/funding_{sym}.csv"
    s_path = f"{CARRY_DIR}/spot1d_{sym}.csv.gz"
    p_path = f"{CARRY_DIR}/um1d_{sym}.csv.gz"
    if not all(os.path.exists(x) for x in (f_path, s_path, p_path)):
        return None
    f = pd.read_csv(f_path)
    f["day"] = pd.to_datetime(f["timestamp"], unit="s", utc=True).dt.normalize()
    funding = f.groupby("day")["rate"].sum()
    daily = {}
    for name, path in (("spot", s_path), ("perp", p_path)):
        k = pd.read_csv(path)
        k["day"] = pd.to_datetime(k["timestamp"], unit="s", utc=True).dt.normalize()
        daily[name] = k.drop_duplicates("day").set_index("day")["close"].astype(float)
    df = pd.concat([funding.rename("funding"), daily["spot"].rename("spot"),
                    daily["perp"].rename("perp")], axis=1).sort_index()
    df = df[df["spot"].notna() & df["perp"].notna()]
    df["funding"] = df["funding"].fillna(0.0)
    # hedged daily P&L before costs, as a fraction of notional held into the day:
    # spot return minus perp return (short) plus the day's funding
    df["hedge"] = df["spot"].pct_change().fillna(0.0) - df["perp"].pct_change().fillna(0.0)
    df["pnl"] = df["hedge"] + df["funding"]
    return df


def stats(daily: pd.Series, label: str, in_market: pd.Series | None = None) -> dict:
    daily = daily.dropna()
    eq = (1 + daily).cumprod()
    years = (daily.index[-1] - daily.index[0]).days / 365.25
    cagr = eq.iloc[-1] ** (1 / years) - 1 if years > 0 else 0.0
    dd = (eq / eq.cummax() - 1).min()
    monthly = eq.resample("ME").last().pct_change().dropna()
    ann = daily.mean() * 365
    vol = daily.std() * np.sqrt(365)
    py = eq.resample("YE").last()
    per_year = (py / py.shift(1).fillna(1.0) - 1).round(3)
    out = {"cell": label, "ann_ret_pct": round(100 * ann, 1), "cagr_pct": round(100 * cagr, 1),
           "sharpe": round(ann / vol, 2) if vol > 0 else 0.0,
           "max_dd_pct": round(-100 * dd, 1), "worst_month_pct": round(100 * monthly.min(), 1),
           "per_year_pct": {d.year: round(100 * v, 1) for d, v in per_year.items()}}
    if in_market is not None:
        out["days_flat_pct"] = round(100 * (1 - in_market.mean()), 1)
    return out


def cell_plain(df: pd.DataFrame, label: str) -> dict:
    pnl = df["pnl"].copy()
    pnl.iloc[0] -= COST_PER_LEG            # entry
    pnl.iloc[-1] -= COST_PER_LEG           # exit
    return stats(pnl, label)


def cell_timed(df: pd.DataFrame, label: str, lev: float = 1.0) -> dict:
    # decision at 00:00 UTC each day from the trailing 24h (3 settlements)
    # mean funding known at that instant -> yesterday's daily sum / 3
    signal = (df["funding"].shift(1) / 3.0) > 0
    in_mkt = signal.astype(float)
    pnl = df["pnl"] * in_mkt
    switches = in_mkt.diff().abs().fillna(in_mkt)   # 1 on entry and on exit
    pnl = pnl - switches * COST_PER_LEG
    return stats(pnl * lev, label, in_market=in_mkt)


def cell_rotated(frames: dict[str, pd.DataFrame], label: str) -> dict:
    fund = pd.DataFrame({s: d["funding"] for s, d in frames.items()}).sort_index()
    pnl_tbl = pd.DataFrame({s: d["pnl"] for s, d in frames.items()}).reindex(fund.index)
    avail = pd.DataFrame({s: d["pnl"].notna() for s, d in frames.items()}).reindex(fund.index).fillna(False)
    score = fund.rolling(7, min_periods=7).mean().shift(1)   # trailing 7d, known at 00:00
    held: list[str] = []
    daily = []
    turnover = 0
    for day in fund.index:
        if day.weekday() == 0:                                   # Monday rebalance
            sc = score.loc[day].where(avail.loc[day]).dropna()
            ranked = sc[sc > 0].sort_values(ascending=False)
            top5 = list(ranked.index[:KEEP_N])
            keep = [s for s in held if s in top5]
            for s in ranked.index[:TOP_N]:
                if len(keep) >= TOP_N:
                    break
                if s not in keep:
                    keep.append(s)
            changed = len(set(held) ^ set(keep))
            turnover += changed
            cost = changed * COST_PER_LEG / max(TOP_N, 1)       # one leg per slot changed
            held = keep
        else:
            cost = 0.0
        if held:
            w = 1.0 / TOP_N
            day_pnl = sum(w * (pnl_tbl.at[day, s] if not np.isnan(pnl_tbl.at[day, s]) else 0.0)
                          for s in held)
        else:
            day_pnl = 0.0
        daily.append((day, day_pnl - cost))
    ser = pd.Series(dict(daily))
    out = stats(ser, label, in_market=(ser != 0).astype(float))
    out["slot_changes_per_year"] = round(turnover / ((ser.index[-1] - ser.index[0]).days / 365.25), 1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2020-01-01")
    args = ap.parse_args()
    start = pd.Timestamp(args.start, tz="UTC")

    frames = {}
    for sym in UNIVERSE:
        df = load_symbol(sym)
        if df is None:
            print(f"{sym}: data missing — skipped")
            continue
        frames[sym] = df[df.index >= start]
        print(f"{sym}: {frames[sym].index.min().date()} -> {frames[sym].index.max().date()} "
              f"({len(frames[sym])} days), mean funding {100 * frames[sym]['funding'].mean() * 365:+.1f}%/yr")
    print()
    for sym in ("BTCUSDT", "ETHUSDT"):
        if sym in frames:
            print(cell_plain(frames[sym], f"1 plain {sym}"))
            print(cell_timed(frames[sym], f"2 timed {sym}"))
            print(cell_timed(frames[sym], f"3 timed {sym} 2x", lev=2.0))
            print(cell_timed(frames[sym], f"3 timed {sym} 3x", lev=3.0))
            print()
    print("--- per-coin plain carry (annualized on notional) ---")
    for sym, df in frames.items():
        r = cell_plain(df, sym)
        print(f"  {sym:9s} ann {r['ann_ret_pct']:+6.1f}%  maxDD {r['max_dd_pct']:5.1f}%  worst month {r['worst_month_pct']:+5.1f}%")
    print()
    print(cell_rotated(frames, "4 rotated top-3 weekly"))


if __name__ == "__main__":
    main()
