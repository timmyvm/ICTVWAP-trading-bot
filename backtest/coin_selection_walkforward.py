"""
v0.26-diag — Can the losing coins be identified IN ADVANCE? (DEVLOG v0.26-diag)

Re-scoring the same data after dropping coins that lost is selection on the
outcome and always looks better. The honest question is whether a rule that
only sees the past would have dropped them. Rule (fixed before running): at the
start of each calendar quarter, trade a coin that quarter only if the mean net
return of its trades that CLOSED in the previous four quarters is above zero;
coins with fewer than 50 such trades are traded. Exit time, not entry time,
decides what counts as known — a trade straddling the boundary is not used.

Phase 1 (--build): v0.23 T1 24 h verbatim, overlay off, per coin; trade lists
cached to backtest/data_cache/local/v026_trades/ (gitignored).
Phase 2 (--analyse): equal capital per traded coin, each trade contributing
20 % notional x its net return to its sleeve, re-selected quarterly; compared
with the identical portfolio with every coin always on. OOS 2021-Q1 onward.
"""

import argparse
import glob
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from backtest.data import load_cached_1m  # noqa: E402
from backtest.horizon_harvest import COMMITTED_FUNDING, PERP8, SDZ, get_signals, load_funding, run_cell  # noqa: E402
from backtest.sd_vwap_experiment import atr  # noqa: E402

CACHE = "backtest/data_cache/local/v026_trades"
NOTIONAL = 0.20
LOOKBACK_Q = 4
MIN_TRADES = 50
OOS_START = pd.Period("2021Q1", freq="Q")


def build(sym: str) -> None:
    os.makedirs(CACHE, exist_ok=True)
    fpath = COMMITTED_FUNDING.get(sym, f"{SDZ}/funding_{sym}.csv")
    df = load_cached_1m(f"{SDZ}/um5m_{sym}.csv.gz")
    sig, df5 = get_signals(df, "5m")
    r = run_cell(sig, df5, atr(df5), load_funding(fpath, df5.index), 24,
                 use_stop=False, return_trades=True)
    t = r["trades"][["ts", "exit_ts", "dir", "net", "net_pct"]].copy()
    for c in ("ts", "exit_ts"):
        t[c] = pd.DatetimeIndex(t[c]).tz_convert("UTC")
    t.to_csv(f"{CACHE}/{sym}.csv", index=False)
    print(f"{sym}: {len(t)} trades, {t.ts.min().date()} -> {t.ts.max().date()}, "
          f"total net ${t.net.sum():,.0f}, mean net/trade {t.net_pct.mean():+.4f}%", flush=True)


def load_all() -> dict:
    out = {}
    for p in sorted(glob.glob(f"{CACHE}/*.csv")):
        sym = os.path.basename(p)[:-4]
        t = pd.read_csv(p)
        t["ts"] = pd.to_datetime(t["ts"], utc=True)
        t["exit_ts"] = pd.to_datetime(t["exit_ts"], utc=True)
        t["q"] = t["ts"].dt.tz_localize(None).dt.to_period("Q")
        out[sym] = t
    return out


def analyse() -> None:
    trades = load_all()
    syms = [s for s in PERP8 if s in trades]
    first_q = {s: trades[s]["q"].min() for s in syms}
    last_q = max(t["q"].max() for t in trades.values())

    # naive hindsight number, for contrast only
    tot = {s: trades[s]["net"].sum() for s in syms}
    losers = [s for s in syms if tot[s] <= 0]
    print("full-period net per coin ($10k each):",
          ", ".join(f"{s.replace('USDT', '')} {tot[s]:+,.0f}" for s in syms))
    keep = [s for s in syms if s not in losers]
    print(f"HINDSIGHT (drop {', '.join(losers) or 'none'} after seeing them lose): "
          f"avg/coin ${np.mean([tot[s] for s in syms]):,.0f} -> ${np.mean([tot[s] for s in keep]):,.0f}\n")

    rows, excl_count = [], {s: 0 for s in syms}
    q = OOS_START
    while q <= last_q:
        q_start = q.start_time.tz_localize("UTC")
        active = [s for s in syms if first_q[s] <= q]
        sleeve, include = {}, {}
        for s in active:
            t = trades[s]
            sleeve[s] = NOTIONAL * t.loc[t["q"] == q, "net_pct"].sum() / 100.0
            win_lo = (q - LOOKBACK_Q).start_time.tz_localize("UTC")
            past = t.loc[(t["exit_ts"] >= win_lo) & (t["exit_ts"] < q_start), "net_pct"]
            include[s] = len(past) < MIN_TRADES or past.mean() > 0
            if not include[s]:
                excl_count[s] += 1
        sel = [s for s in active if include[s]]
        r_all = float(np.mean([sleeve[s] for s in active])) if active else 0.0
        r_sel = float(np.mean([sleeve[s] for s in sel])) if sel else 0.0
        r_cash = float(np.sum([sleeve[s] for s in sel]) / len(active)) if active else 0.0
        rows.append({"q": str(q), "active": len(active), "dropped": ",".join(
            s.replace("USDT", "") for s in active if not include[s]),
            "all": r_all, "sel": r_sel, "sel_cash": r_cash})
        q += 1

    df = pd.DataFrame(rows)
    print(f"{'quarter':8s} {'act':>3s} {'dropped':22s} {'all coins':>10s} {'selected':>10s} {'sel+cash':>10s}")
    for _, r in df.iterrows():
        print(f"{r.q:8s} {r.active:3d} {r.dropped:22s} {100 * r['all']:+9.2f}% {100 * r.sel:+9.2f}% {100 * r.sel_cash:+9.2f}%")

    def comp(x: pd.Series) -> float:
        return float(np.prod(1.0 + x) - 1.0)

    yrs = len(df) / 4.0
    print()
    for col, name in (("all", "ALL COINS, always on"), ("sel", "SELECTED (capital redistributed)"),
                      ("sel_cash", "SELECTED (excluded coins in cash)")):
        c = comp(df[col])
        print(f"{name:36s} total {100 * c:+7.1f}%  ~{100 * ((1 + c) ** (1 / yrs) - 1):+5.1f}%/yr  "
              f"mean/quarter {100 * df[col].mean():+.2f}%  worst quarter {100 * df[col].min():+.2f}%")
    hit = df[df["dropped"] != ""]
    better = int((hit["sel"] > hit["all"]).sum())
    print(f"\nquarters with at least one exclusion: {len(hit)} of {len(df)}; selection beat all-on in {better}")
    print("quarters each coin was excluded:", ", ".join(f"{s.replace('USDT', '')} {excl_count[s]}" for s in syms))
    verdict = df["sel"].mean() > df["all"].mean() and better > len(hit) / 2
    print("PASS BAR (higher mean/quarter AND better in a majority of exclusion quarters):",
          "PASS" if verdict else "FAIL")


def quarter_matrix() -> tuple:
    """Per OOS quarter: sleeve return per coin, the rule's include mask, the active mask."""
    trades = load_all()
    syms = [s for s in PERP8 if s in trades]
    first_q = {s: trades[s]["q"].min() for s in syms}
    last_q = max(t["q"].max() for t in trades.values())
    qs, R, INC, ACT = [], [], [], []
    q = OOS_START
    while q <= last_q:
        q_start = q.start_time.tz_localize("UTC")
        win_lo = (q - LOOKBACK_Q).start_time.tz_localize("UTC")
        r_row, i_row, a_row = [], [], []
        for s in syms:
            t = trades[s]
            act = first_q[s] <= q
            r_row.append(NOTIONAL * t.loc[t["q"] == q, "net_pct"].sum() / 100.0 if act else 0.0)
            past = t.loc[(t["exit_ts"] >= win_lo) & (t["exit_ts"] < q_start), "net_pct"]
            i_row.append(act and (len(past) < MIN_TRADES or past.mean() > 0))
            a_row.append(act)
        qs.append(str(q)); R.append(r_row); INC.append(i_row); ACT.append(a_row)
        q += 1
    return qs, syms, np.array(R), np.array(INC), np.array(ACT)


def audit(n_perm: int = 5000, seed: int = 11) -> None:
    """
    Separate selection SKILL from concentration and luck. Concentrating capital in
    fewer coins does not change the expected mean return per coin, only its
    variance, so the fair null is RANDOM selection of the same number of coins
    each quarter, capital redistributed. The rule must beat that distribution.
    """
    qs, syms, R, INC, ACT = quarter_matrix()
    k = INC.sum(axis=1)
    r_all = np.array([R[i, ACT[i]].mean() for i in range(len(qs))])
    r_sel = np.array([R[i, INC[i]].mean() if k[i] else 0.0 for i in range(len(qs))])
    excl = np.array([R[i, ACT[i] & ~INC[i]].mean() if (ACT[i] & ~INC[i]).any() else np.nan
                     for i in range(len(qs))])
    d = r_sel - r_all
    t = d.mean() / (d.std(ddof=1) / np.sqrt(len(d)))
    comp = lambda x: float(np.prod(1.0 + x) - 1.0)
    print(f"OOS quarters {len(qs)}; mean coins selected {k.mean():.1f} of {ACT.sum(axis=1).mean():.1f}")
    print(f"mean per-coin sleeve return/quarter: selected {100 * r_sel.mean():+.2f}%  "
          f"all {100 * r_all.mean():+.2f}%  EXCLUDED {100 * np.nanmean(excl):+.2f}%")
    print(f"excluded coins were net positive in {int((excl > 0).sum())} of {int((~np.isnan(excl)).sum())} quarters")
    print(f"paired (selected - all) per quarter: mean {100 * d.mean():+.2f}%  t {t:+.2f}")
    best = int(np.argmax(d))
    d_lo = np.delete(d, best)
    print(f"without the single best quarter ({qs[best]}, {100 * d[best]:+.2f}%): "
          f"mean {100 * d_lo.mean():+.2f}%  t {d_lo.mean() / (d_lo.std(ddof=1) / np.sqrt(len(d_lo))):+.2f}")
    print(f"quarterly volatility: selected {100 * r_sel.std(ddof=1):.2f}%  all {100 * r_all.std(ddof=1):.2f}%;  "
          f"mean/vol: selected {r_sel.mean() / r_sel.std(ddof=1):.3f}  all {r_all.mean() / r_all.std(ddof=1):.3f}")

    rng = np.random.default_rng(seed)
    perm_tot, perm_mean = np.empty(n_perm), np.empty(n_perm)
    act_idx = [np.flatnonzero(ACT[i]) for i in range(len(qs))]
    for b in range(n_perm):
        rr = np.empty(len(qs))
        for i in range(len(qs)):
            if k[i] == 0:
                rr[i] = 0.0
                continue
            pick = rng.choice(act_idx[i], size=int(k[i]), replace=False)
            rr[i] = R[i, pick].mean()
        perm_tot[b], perm_mean[b] = comp(rr), rr.mean()
    rule_tot = comp(r_sel)
    pct = float((perm_mean < r_sel.mean()).mean())
    print(f"\nRANDOM selection of the same number of coins each quarter, {n_perm} draws:")
    print(f"  compounded total: median {100 * np.median(perm_tot):+.1f}%  "
          f"5-95% [{100 * np.percentile(perm_tot, 5):+.1f}%, {100 * np.percentile(perm_tot, 95):+.1f}%]  "
          f"rule {100 * rule_tot:+.1f}%")
    print(f"  rule's mean/quarter beats {100 * pct:.1f}% of random selections "
          f"(one-sided p = {1 - pct:.3f})")
    print("AUDIT VERDICT:", "SKILL (beats >= 95% of random picks)" if pct >= 0.95
          else "NOT DISTINGUISHABLE FROM LUCK + CONCENTRATION")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", default=None, help="comma list of symbols to (re)build trade lists for")
    ap.add_argument("--analyse", action="store_true")
    ap.add_argument("--audit", action="store_true", help="skill vs luck: permutation test")
    args = ap.parse_args()
    if args.build:
        for s in args.build.split(","):
            build(s.strip())
    if args.analyse:
        analyse()
    if args.audit:
        audit()


if __name__ == "__main__":
    main()
