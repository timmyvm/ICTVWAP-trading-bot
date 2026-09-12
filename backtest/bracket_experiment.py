"""
v0.10c — 3xATR symmetric bracket on 1H EMA-distance extension entries.

THE VALIDATED RULE (DEVLOG v0.10c, validation PASS on unseen BTC 2019-2022):
  d = (close - EMA200) / ATR14 on closed 1H candles
  |d[i-1]| >= 1 -> enter at bar i's open, direction of the extension
  Exit: symmetric bracket at entry +/- 3*ATR14 (signal candle's ATR),
  checked stop-first from the NEXT bar onward (no same-bar exit; an exit
  frees the slot for an entry at that same bar's open). One position at a
  time. 1% equity risk per trade, 10x notional cap. Fill model: entry at
  open slipped by SLIPPAGE, exits at the raw bracket level, and
  (taker + slippage) charged as fees on both legs of every round trip.

This file is the committed reconstruction of the validation script, which
ran from a scratchpad that a container restart wiped. Semantics recovered
VERBATIM from the session transcript (the original heredoc), and this
implementation reproduces the validation output exactly:
  BTC 1H 2019-01 -> 2022-12: 1,508 trades, 58.0% win, net +$36,925,
  per-year +$6,101/+$19,074/+$6,744/+$5,006, longs +$21,669 / shorts
  +$15,256, maxDD 15.6%, Sharpe(365d) 1.68.
strategy/ema_bracket.py (the live module) must stay in lockstep with
simulate() here — backtest/parity_ema_live.py asserts that.
"""

import argparse
import sys
from typing import Optional

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from backtest.data import load_cached_1m, resample_ohlcv  # noqa: E402

EMA_SPAN = 200
ATR_PERIOD = 14
ENTRY_T = 1.0
EXIT_MULT = 3.0
WARMUP = 210


def indicators(df1h: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """(atr14, d) arrays for a 1H frame — the shared math with the live module."""
    close = df1h["close"]
    ema = close.ewm(span=EMA_SPAN, adjust=False).mean().to_numpy()
    tr = pd.concat([
        df1h["high"] - df1h["low"],
        (df1h["high"] - close.shift()).abs(),
        (df1h["low"] - close.shift()).abs(),
    ], axis=1).max(axis=1)
    atr = tr.rolling(ATR_PERIOD).mean().to_numpy()
    d = (close.to_numpy() - ema) / np.where(atr > 0, atr, np.nan)
    return atr, d


def simulate(df1h: pd.DataFrame,
             taker_pct: float = 0.055, slip_pct: float = 0.01,
             risk_pct: float = 1.0, max_lev: float = 10.0,
             start_bal: float = 10_000.0,
             return_trades: bool = False,
             funding: Optional[pd.Series] = None,
             reverse: bool = False,
             skip_after_loss: bool = False,
             reentry: str = "open") -> dict:
    # reentry: how a same-bar re-entry after an exit on bar i is priced.
    #   "open" = frozen reference: fill at o[i] (a price from BEFORE the exit
    #            move — a stale-price artifact, kept as the reference default)
    #   "exit" = fill at the exit price (post-move; closest to the live bot)
    #   "next" = no same-bar re-entry; earliest entry is bar i+1's open
    assert reentry in ("open", "exit", "next")
    # reverse=True fades the extension instead of following it (diagnostic
    # only — the mirror image of the validated rule; never the default).
    side = -1 if reverse else 1
    cooldown = False  # v0.10h Rule A state
    exited_px: Optional[float] = None  # exit price if a position closed on this bar
    o = df1h["open"].to_numpy()
    h = df1h["high"].to_numpy()
    l = df1h["low"].to_numpy()
    c = df1h["close"].to_numpy()
    idx = df1h.index
    atr, d = indicators(df1h)

    # v0.10e: per-bar funding rate (0 outside settlement bars). Positions
    # carried INTO a settlement bar accrue -dir*qty*open*rate; the accrual
    # folds into that trade's net at close. funding=None => rates all zero
    # and behavior is bit-identical to the frozen reference.
    rate_arr = np.zeros(len(df1h))
    if funding is not None:
        rate_arr = funding.reindex(idx.tz_convert("UTC")).fillna(0.0).to_numpy()

    taker = taker_pct / 100.0
    slip = slip_pct / 100.0

    bal = start_bal
    pos: Optional[tuple] = None  # (dr, entry, stop, tp, qty, entry_ts)
    pos_funding = 0.0
    fund_by_dir = {"LONG": 0.0, "SHORT": 0.0}
    trades = []
    entries = []  # every entry event, incl. one left unresolved at data end
    eq_curve = []

    for i in range(WARMUP, len(df1h)):
        exited_px = None
        # 0) funding settlement for the position carried into this bar
        if pos is not None and rate_arr[i] != 0.0:
            cf = -pos[0] * pos[4] * o[i] * rate_arr[i]
            pos_funding += cf
            fund_by_dir["LONG" if pos[0] > 0 else "SHORT"] += cf

        # 1) bracket check for positions opened on EARLIER bars (stop-first,
        #    raw-level fills; an exit here frees the slot for step 2's entry)
        if pos is not None:
            dr, e, st, tg, q, ets = pos
            hit_st = l[i] <= st if dr > 0 else h[i] >= st
            hit_tg = h[i] >= tg if dr > 0 else l[i] <= tg
            px = st if hit_st else (tg if hit_tg else None)
            if px is not None:
                net = dr * (px - e) * q - (e + px) * q * (taker + slip) + pos_funding
                bal += net
                trades.append({"ts": idx[i], "i": i, "entry_ts": ets,
                               "dir": "LONG" if dr > 0 else "SHORT",
                               "entry": e, "exit": px, "net": net,
                               "funding": pos_funding,
                               "reason": "STOP" if hit_st else "TP"})
                pos = None
                pos_funding = 0.0
                exited_px = px
                if skip_after_loss and net <= 0:
                    cooldown = True

        # 2) entry at this bar's open from the PREVIOUS bar's signal
        if pos is None and not np.isnan(d[i - 1]) and abs(d[i - 1]) >= ENTRY_T:
            if cooldown:
                cooldown = False  # v0.10h Rule A: skip one signal after a loss
            elif exited_px is not None and reentry == "next":
                pass  # no same-bar re-entry
            else:
                dr = side * (1 if d[i - 1] >= ENTRY_T else -1)
                base_px = exited_px if (exited_px is not None and reentry == "exit") else o[i]
                e = base_px * (1 + dr * slip)
                a = atr[i - 1]
                q = min(bal * (risk_pct / 100.0) / (EXIT_MULT * a), bal * max_lev / e)
                if q > 0:
                    st_, tg_ = e - dr * EXIT_MULT * a, e + dr * EXIT_MULT * a
                    pos = (dr, e, st_, tg_, q, idx[i - 1])
                    pos_funding = 0.0
                    entries.append({"i": i, "signal_ts": idx[i - 1],
                                    "dir": "LONG" if dr > 0 else "SHORT",
                                    "entry": e, "stop": st_, "tp": tg_})

        # 3) mark-to-market equity tracking (incl. accrued funding carry)
        m2m = bal + (pos[0] * (c[i] - pos[1]) * pos[4] + pos_funding if pos else 0.0)
        eq_curve.append((idx[i], m2m))

    t = pd.DataFrame(trades)
    if t.empty:
        return {"n": 0}
    if return_trades:
        return {"n": len(t), "trades": t, "entries": pd.DataFrame(entries)}

    wins = (t["net"] > 0).sum()
    gw = t.loc[t["net"] > 0, "net"].sum()
    gl = -t.loc[t["net"] <= 0, "net"].sum()
    t["year"] = pd.to_datetime(t["ts"], utc=True).dt.year
    per_year = t.groupby("year")["net"].sum().round(0).to_dict()
    by_dir = t.groupby("dir")["net"].sum().round(0).to_dict()

    eq = pd.Series(dict(eq_curve))
    dailyy = eq.resample("1D").last().dropna()
    r = dailyy.pct_change().dropna()
    sharpe = r.mean() / r.std() * np.sqrt(365) if r.std() > 0 else 0.0
    dd = (eq / eq.cummax() - 1).min()
    monthly = dailyy.resample("ME").last().pct_change().dropna()
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = (eq.iloc[-1] / start_bal) ** (1 / years) - 1 if years > 0 else 0.0

    out = {
        "n": int(len(t)), "win_pct": round(100 * wins / len(t), 1),
        "net": round(t["net"].sum(), 0), "end_bal": round(bal, 0),
        "pf": round(gw / gl, 2) if gl > 0 else float("inf"),
        "max_dd_pct": round(-100 * float(dd), 1),
        "sharpe": round(float(sharpe), 2), "cagr_pct": round(100 * cagr, 1),
        "pos_months_pct": round(100 * (monthly > 0).mean(), 0),
        "worst_month_pct": round(100 * monthly.min(), 1),
        "by_dir": by_dir, "per_year": per_year,
    }
    if funding is not None:
        out["funding_total"] = round(t["funding"].sum(), 0)
        out["funding_by_dir"] = {k: round(v, 0) for k, v in fund_by_dir.items()}
    return out


def load_funding(path: str) -> pd.Series:
    """timestamp(epoch s),rate -> UTC-indexed rate series for simulate()."""
    f = pd.read_csv(path)
    ts = pd.to_datetime(f["timestamp"], unit="s", utc=True)
    return pd.Series(f["rate"].to_numpy(), index=pd.DatetimeIndex(ts))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="backtest/data_cache/local/btcusd_1m_2019_2022.csv.gz")
    ap.add_argument("--start", default=None, help="ISO date lower bound (optional)")
    ap.add_argument("--end", default=None, help="ISO date upper bound (optional)")
    ap.add_argument("--taker", type=float, default=0.055, help="taker fee %% per side")
    ap.add_argument("--slip", type=float, default=0.01, help="slippage %% per side")
    ap.add_argument("--funding", default=None,
                    help="funding CSV (timestamp,rate) to apply; omit for none")
    ap.add_argument("--label", default="", help="printed with the result line")
    ap.add_argument("--reverse", action="store_true", help="diagnostic: fade the extension")
    ap.add_argument("--skip-after-loss", action="store_true",
                    help="v0.10h Rule A: skip the next signal after a losing trade")
    args = ap.parse_args()

    df1h = resample_ohlcv(load_cached_1m(args.cache), "1h")
    if args.start:
        df1h = df1h[df1h.index >= pd.Timestamp(args.start, tz="America/New_York")]
    if args.end:
        df1h = df1h[df1h.index < pd.Timestamp(args.end, tz="America/New_York")]
    fund = load_funding(args.funding) if args.funding else None
    tag = f"[{args.label}] " if args.label else ""
    print(f"{tag}{df1h.index.min()} -> {df1h.index.max()} ({len(df1h)} bars)")
    print(tag, simulate(df1h, taker_pct=args.taker, slip_pct=args.slip, funding=fund,
                        reverse=args.reverse, skip_after_loss=args.skip_after_loss))


if __name__ == "__main__":
    main()
