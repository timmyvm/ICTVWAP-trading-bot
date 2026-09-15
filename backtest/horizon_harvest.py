"""
v0.23-exp — Harvest the v0.22 entry over the horizon where its edge actually is.

v0.22's entry carries real information (DEVLOG D2: 12/12 cells positive, up to
2.91x the fee on ETH at 24 h; D3: the supply/demand zone roughly doubles
per-signal excess) but the packaging destroyed it — a ~1 %-of-price structural
stop chasing a median 0.6 R VWAP target inside two hours. This keeps the ENTRY
VERBATIM and rebuilds only the exit, the sizing and the position model.

Because per-signal excess (0.04-0.38 % of price) is small against 4-24 h
volatility (2-4 %), hit rates are 49-54 % and this is a portfolio edge, not a
trade-by-trade one. Hence: TIME exits rather than price exits, risk bounded by
POSITION SIZE rather than stop distance, and overlapping positions.

Cells (all reported, none selected — see the DEVLOG pass bar):
  T1  time exit only, flat H hours after entry at that bar's open
  T2  same, plus a wide protective stop at 2 x sigma_H,
      sigma_H = ATR14(5m) * sqrt(H in 5m bars)
  H in {4, 12, 24} hours.

Costs: taker + slippage per side on both legs, scaled by --cost-mult for the
pre-registered 1.5x stress, PLUS perp funding at every 8 h settlement crossed.
Funding is NOT scaled by --cost-mult: it is a market rate, not an execution cost.
"""

import argparse
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from backtest.data import load_cached_1m  # noqa: E402
from backtest.sd_vwap_experiment import ATR_PERIOD, atr, simulate  # noqa: E402

TAKER, SLIP = 0.055, 0.01          # % per side
NOTIONAL_FRAC = 0.20               # of realized equity, per position
MAX_CONCURRENT = 5
START_BAL = 10_000.0
STOP_SIGMAS = 2.0
BARS_PER_HOUR = 12                 # 5m bars


def get_signals(df_base: pd.DataFrame, base: str) -> tuple:
    out = simulate(df_base, signals_only=True, base=base)
    return out["signals"], out["df5"]


def load_funding(path: str, index: pd.DatetimeIndex) -> np.ndarray:
    """Per-5m-bar funding rate: the rate is charged on the bar containing its settlement."""
    rates = np.zeros(len(index))
    if not path:
        return rates
    f = pd.read_csv(path)
    ts = pd.DatetimeIndex(pd.to_datetime(f["timestamp"], unit="s", utc=True)).tz_convert(index.tz)
    pos = index.searchsorted(ts, side="right") - 1
    ok = (pos >= 0) & (pos < len(index))
    np.add.at(rates, pos[ok], f["rate"].to_numpy()[ok])
    return rates


def run_cell(signals: pd.DataFrame, df5: pd.DataFrame, a5: np.ndarray,
             fund: np.ndarray, hours: int, use_stop: bool,
             cost_mult: float = 1.0) -> dict:
    o = df5["open"].to_numpy()
    h = df5["high"].to_numpy()
    low = df5["low"].to_numpy()
    c = df5["close"].to_numpy()
    n = len(df5)
    H = hours * BARS_PER_HOUR

    slip = (SLIP * cost_mult) / 100.0
    cost = ((TAKER + SLIP) * cost_mult) / 100.0

    by_bar: dict[int, list] = {}
    for b, d in zip(signals["bar"].to_numpy(), signals["dir"].to_numpy()):
        by_bar.setdefault(int(b), []).append(int(d))

    bal = START_BAL
    peak, max_dd = START_BAL, 0.0
    open_pos: list[dict] = []
    trades: list[dict] = []
    skipped_full = 0

    for i in range(ATR_PERIOD + 1, n):
        # --- funding on everything held into this bar ---
        if fund[i] != 0.0 and open_pos:
            for p in open_pos:
                p["funding"] += -p["dir"] * p["qty"] * o[i] * fund[i]

        # --- exits (stop first, then the time exit) ---
        still: list[dict] = []
        for p in open_pos:
            px = reason = None
            if use_stop:
                hit = low[i] <= p["stop"] if p["dir"] == 1 else h[i] >= p["stop"]
                if hit and i > p["bar"]:
                    px, reason = p["stop"], "STOP"
            if px is None and i >= p["bar"] + H:
                px, reason = o[i], "TIME"
            if px is None:
                still.append(p)
                continue
            gross = p["dir"] * (px - p["entry"]) * p["qty"]
            fees = (p["entry"] + px) * p["qty"] * cost
            net = gross + p["funding"] - fees
            bal += net
            trades.append({
                "ts": df5.index[p["bar"]], "dir": "LONG" if p["dir"] == 1 else "SHORT",
                "net": net, "reason": reason, "funding": p["funding"], "fees": fees,
                "ret_pct": 100 * p["dir"] * (px / p["entry"] - 1.0),
                "bars": i - p["bar"],
            })
        open_pos = still

        # --- entries ---
        for d in by_bar.get(i, []):
            if len(open_pos) >= MAX_CONCURRENT:
                skipped_full += 1
                continue
            if i + 1 >= n or np.isnan(a5[i]) or a5[i] <= 0 or bal <= 0:
                continue
            e = o[i] * (1 + d * slip)
            qty = (bal * NOTIONAL_FRAC) / e
            sigma = a5[i - 1] * np.sqrt(H) if not np.isnan(a5[i - 1]) else np.nan
            stop = e - d * STOP_SIGMAS * sigma if use_stop and not np.isnan(sigma) else np.nan
            if use_stop and (np.isnan(stop) or d * (e - stop) <= 0):
                continue
            open_pos.append({"bar": i, "dir": d, "entry": e, "qty": qty,
                             "stop": stop, "funding": 0.0})

        # --- mark to market ---
        m2m = bal + sum(p["dir"] * (c[i] - p["entry"]) * p["qty"] + p["funding"]
                        for p in open_pos)
        peak = max(peak, m2m)
        max_dd = max(max_dd, (peak - m2m) / peak if peak > 0 else 0.0)

    t = pd.DataFrame(trades)
    if t.empty:
        return {"n": 0}
    wins = t[t.net > 0]
    gl = -t.loc[t.net <= 0, "net"].sum()
    t["y"] = t.ts.dt.year
    per_year = {int(y): round(g.net.sum(), 0) for y, g in t.groupby("y")}
    return {
        "n": len(t), "win_pct": round(100 * len(wins) / len(t), 1),
        "net": round(t.net.sum(), 0), "end_bal": round(bal, 0),
        "pf": round(wins.net.sum() / gl, 2) if gl > 0 else float("inf"),
        "max_dd_pct": round(100 * max_dd, 1),
        "avg_ret_pct": round(t.ret_pct.mean(), 4),
        "funding_total": round(t.funding.sum(), 0),
        "fees_total": round(t.fees.sum(), 0),
        "stop_share_pct": round(100 * (t.reason == "STOP").mean(), 1) if use_stop else 0.0,
        "skipped_full": skipped_full,
        "per_year": per_year,
        "years_positive": f"{sum(1 for v in per_year.values() if v > 0)}/{len(per_year)}",
    }


ASSETS = {
    # development (D2/D3 measured these — in-sample, can disqualify not validate)
    "BTC 2019-22": ("backtest/data_cache/local/btcusd_1m_2019_2022.csv.gz", "1m",
                    "backtest/data_cache/funding_btcusdt_binance.csv", None),
    "BTC 2023-26": ("backtest/data_cache/local/btcusd_1m_2023_2026.csv.gz", "1m",
                    "backtest/data_cache/funding_btcusdt_binance.csv", None),
    "ETH 2018-26": ("backtest/data_cache/local/ethusd_1m_2017_2026.csv.gz", "1m",
                    "backtest/data_cache/funding_ethusdt_binance.csv", "2018-01-01"),
}
HOLDOUT = ["BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "SOLUSDT", "LINKUSDT"]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", default="dev", help="'dev', 'holdout', or a comma list")
    ap.add_argument("--hours", default="4,12,24")
    ap.add_argument("--cells", default="T1,T2")
    ap.add_argument("--cost-mult", type=float, default=1.0)
    args = ap.parse_args()

    if args.assets == "dev":
        items = [(k, *v) for k, v in ASSETS.items()]
    elif args.assets == "holdout":
        items = [(s, f"backtest/data_cache/local/sdz/um5m_{s}.csv.gz", "5m",
                  f"backtest/data_cache/local/sdz/funding_{s}.csv", None) for s in HOLDOUT]
    else:
        items = [(k, *ASSETS[k]) for k in args.assets.split(",")]

    pooled: dict[tuple, float] = {}
    for label, path, base, fpath, start in items:
        df = load_cached_1m(path)
        if start:
            df = df[df.index >= pd.Timestamp(start, tz="America/New_York")]
        sig, df5 = get_signals(df, base)
        a5 = atr(df5)
        fund = load_funding(fpath, df5.index)
        print(f"=== {label}: {len(df5)} 5m bars {df5.index.min().date()} -> "
              f"{df5.index.max().date()}, {len(sig)} signals, "
              f"funding rows applied {int((fund != 0).sum())} "
              f"[x{args.cost_mult:g} costs]", flush=True)
        for cell in args.cells.split(","):
            for hrs in (int(x) for x in args.hours.split(",")):
                r = run_cell(sig, df5, a5, fund, hrs, use_stop=(cell == "T2"),
                             cost_mult=args.cost_mult)
                pooled[(cell, hrs)] = pooled.get((cell, hrs), 0.0) + r.get("net", 0.0)
                print(f"  {cell} {hrs:>2d}h ", r, flush=True)
        print(flush=True)
    print("pooled net by cell/horizon:",
          {f"{c} {h}h": round(v, 0) for (c, h), v in sorted(pooled.items())})


if __name__ == "__main__":
    main()
