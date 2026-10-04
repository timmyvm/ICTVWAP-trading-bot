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


def _epoch_s(idx) -> np.ndarray:
    """Integer epoch seconds via the subtraction idiom (CLAUDE.md: never astype int64)."""
    d = pd.DatetimeIndex(idx)
    if d.tz is None:
        d = d.tz_localize("UTC")
    return np.asarray((d - pd.Timestamp(0, tz="UTC")) // pd.Timedelta(seconds=1), dtype=np.int64)


def settlement_schedule(path: str, index: pd.DatetimeIndex) -> tuple:
    """
    For every 5m bar: seconds until the next settlement at or after its open, that
    settlement's rate (f_next, mild lookahead — v0.24 diagnostic), the rate settled
    before it (f_prev, lookahead-free), and the bar index whose open IS that
    settlement. Settlement times come from the funding file, never assumed.
    """
    f = pd.read_csv(path)
    ts = pd.to_datetime(f["timestamp"], unit="s", utc=True).dt.round("min")
    s = pd.DataFrame({"t": _epoch_s(ts), "rate": f["rate"].astype(float).to_numpy()})
    s = s.drop_duplicates("t").sort_values("t")
    st, sr = s["t"].to_numpy(), s["rate"].to_numpy()
    bt = _epoch_s(index)
    j = np.searchsorted(st, bt, side="left")
    valid = j < len(st)
    jn = np.clip(j, 0, len(st) - 1)
    secs_to = np.where(valid, st[jn] - bt, 10 ** 9)
    f_next = np.where(valid, sr[jn], np.nan)
    f_prev = np.where(j >= 1, sr[np.clip(j - 1, 0, len(sr) - 1)], np.nan)
    settle_bar = np.where(valid, np.searchsorted(bt, st[jn], side="left"), -1)
    return secs_to, f_next, f_prev, settle_bar


def run_cell(signals: pd.DataFrame, df5: pd.DataFrame, a5: np.ndarray,
             fund: np.ndarray, hours: int, use_stop: bool,
             cost_mult: float = 1.0, settle: tuple | None = None,
             overlay: str | None = None, return_trades: bool = False) -> dict:
    # overlay (v0.25-diag): None = v0.23 verbatim. "next"/"prev" = defer any entry
    # that would fill in the 60 min before a settlement while on the PAYING side of
    # funding (long with f >= 0.01 %, short with f < 0) to the settlement bar's
    # open. "next" conditions on the rate about to be paid (ceiling, mild
    # lookahead), "prev" on the last settled rate (lookahead-free).
    assert overlay in (None, "next", "prev")
    assert overlay is None or settle is not None, "overlay needs a settlement schedule"
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
    deferred: dict[int, list] = {}
    n_deferred = 0
    deferred_skipped = 0

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
                # v0.26: exit time (selection rules may only use CLOSED trades)
                # and net return on notional (size-independent across coins)
                "exit_ts": df5.index[i],
                "net_pct": 100 * net / (p["entry"] * p["qty"]),
            })
        open_pos = still

        # --- entries (fresh signals, plus any the overlay deferred to this bar) ---
        cands = [(d, False) for d in by_bar.get(i, [])] + [(d, True) for d in deferred.pop(i, [])]
        for d, was_deferred in cands:
            if overlay is not None and not was_deferred:
                secs_to, f_nx, f_pv, sbar = settle
                fval = f_nx[i] if overlay == "next" else f_pv[i]
                paying = (d == 1 and fval >= 0.0001) or (d == -1 and fval < 0)
                if 0 < secs_to[i] <= 3600 and paying and sbar[i] > i:
                    deferred.setdefault(int(sbar[i]), []).append(d)
                    n_deferred += 1
                    continue
            if len(open_pos) >= MAX_CONCURRENT:
                skipped_full += 1
                deferred_skipped += 1 if was_deferred else 0
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
    if return_trades:
        return {"n": len(t), "trades": t}
    wins = t[t.net > 0]
    gl = -t.loc[t.net <= 0, "net"].sum()
    t["y"] = t.ts.dt.year
    per_year = {int(y): round(g.net.sum(), 0) for y, g in t.groupby("y")}
    return {
        "n": len(t), "win_pct": round(100 * len(wins) / len(t), 1),
        "net": round(t.net.sum(), 0), "end_bal": round(bal, 0),
        "gross_win": round(wins.net.sum(), 2), "gross_loss": round(gl, 2),
        "pf": round(wins.net.sum() / gl, 2) if gl > 0 else float("inf"),
        "max_dd_pct": round(100 * max_dd, 1),
        "avg_ret_pct": round(t.ret_pct.mean(), 4),
        "funding_total": round(t.funding.sum(), 0),
        "fees_total": round(t.fees.sum(), 0),
        "stop_share_pct": round(100 * (t.reason == "STOP").mean(), 1) if use_stop else 0.0,
        "skipped_full": skipped_full,
        "deferred": n_deferred, "deferred_skipped": deferred_skipped,
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
PERP8 = ["BTCUSDT", "ETHUSDT"] + HOLDOUT
SDZ = "backtest/data_cache/local/sdz"
COMMITTED_FUNDING = {"BTCUSDT": "backtest/data_cache/funding_btcusdt_binance.csv",
                     "ETHUSDT": "backtest/data_cache/funding_ethusdt_binance.csv"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", default="dev", help="'dev', 'holdout', 'perp8', or a comma list")
    ap.add_argument("--hours", default="4,12,24")
    ap.add_argument("--cells", default="T1,T2")
    ap.add_argument("--cost-mult", type=float, default=1.0)
    ap.add_argument("--overlays", default="off",
                    help="v0.25-diag settlement overlay(s), comma list of off/next/prev; "
                         "all run on the SAME signals so only fill timing differs")
    args = ap.parse_args()
    overlays = [None if x == "off" else x for x in args.overlays.split(",")]

    def perp_item(s: str) -> tuple:
        fpath = COMMITTED_FUNDING.get(s, f"{SDZ}/funding_{s}.csv")
        return (s, f"{SDZ}/um5m_{s}.csv.gz", "5m", fpath, None)

    if args.assets == "dev":
        items = [(k, *v) for k, v in ASSETS.items()]
    elif args.assets == "holdout":
        items = [perp_item(s) for s in HOLDOUT]
    elif args.assets == "perp8":
        items = [perp_item(s) for s in PERP8]
    else:
        items = [(k, *ASSETS[k]) if k in ASSETS else perp_item(k)
                 for k in args.assets.split(",")]

    pooled: dict[tuple, float] = {}
    gross: dict[tuple, list] = {}      # key -> [sum gross win, sum gross loss, coins positive, coins]
    for label, path, base, fpath, start in items:
        df = load_cached_1m(path)
        if start:
            df = df[df.index >= pd.Timestamp(start, tz="America/New_York")]
        sig, df5 = get_signals(df, base)
        a5 = atr(df5)
        fund = load_funding(fpath, df5.index)
        settle = settlement_schedule(fpath, df5.index) if any(overlays) else None
        print(f"=== {label}: {len(df5)} 5m bars {df5.index.min().date()} -> "
              f"{df5.index.max().date()}, {len(sig)} signals, "
              f"funding rows applied {int((fund != 0).sum())} "
              f"[x{args.cost_mult:g} costs]", flush=True)
        for cell in args.cells.split(","):
            for hrs in (int(x) for x in args.hours.split(",")):
                for ov in overlays:
                    r = run_cell(sig, df5, a5, fund, hrs, use_stop=(cell == "T2"),
                                 cost_mult=args.cost_mult, settle=settle, overlay=ov)
                    key = (cell, hrs, ov or "off")
                    pooled[key] = pooled.get(key, 0.0) + r.get("net", 0.0)
                    g = gross.setdefault(key, [0.0, 0.0, 0, 0])
                    g[0] += r.get("gross_win", 0.0)
                    g[1] += r.get("gross_loss", 0.0)
                    g[2] += 1 if r.get("net", 0.0) > 0 else 0
                    g[3] += 1
                    print(f"  {cell} {hrs:>2d}h overlay={ov or 'off':4s} ", r, flush=True)
        print(flush=True)
    print("POOLED (the pre-registered criteria):")
    for key, (gw, glo, pos, tot) in sorted(gross.items()):
        cell, hrs, ov = key
        pf = gw / glo if glo > 0 else float("inf")
        print(f"  {cell} {hrs:>2d}h overlay={ov:4s} net {pooled[key]:>9.0f}  pooled_PF {pf:5.3f}  "
              f"assets_net_positive {pos}/{tot}")


if __name__ == "__main__":
    main()
