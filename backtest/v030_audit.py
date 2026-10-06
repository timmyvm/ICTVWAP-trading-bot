"""
v0.30-audit — the S/D engine read still-forming 4H/30m bars. Reproduce, fix, re-run (DEVLOG v0.30-audit).

`sd_vwap_experiment.simulate` matched each 5m bar to the 4H/30m bar CONTAINING it
(open-time `searchsorted(..., side="right") - 1`), whose close lies in the future. The fix
(`closed_htf_index`) uses only bars that have closed by the 5m bar's close and asserts it.

  --selftest   mapping checks on synthetic indexes, including a mutation check that the
               legacy line FAILS the closed-bar property
  --repro      v0.23 holdout, legacy matching ("open"): must reproduce the published table
  --corrected  v0.23 holdout, fixed matching ("close"), base and 1.5x costs, judged against
               the five ORIGINAL pre-registered criteria
Holdout window as published: 2021-01-01 -> 2026-08-31 (UTC); the on-disk files now start in
2020 because they were refetched for v0.26, so the window is applied explicitly.
"""

import argparse
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from backtest.data import load_cached_1m  # noqa: E402
from backtest.horizon_harvest import (COMMITTED_FUNDING, HOLDOUT, SDZ, get_signals,  # noqa: E402
                                      load_funding, run_cell)
from backtest.sd_vwap_experiment import atr, closed_htf_index  # noqa: E402

WINDOW = (pd.Timestamp("2021-01-01", tz="UTC"), pd.Timestamp("2026-09-01", tz="UTC"))
HOURS = (4, 12, 24)
CELLS = ("T1", "T2")
# published v0.23 holdout (DEVLOG v0.23-exp), base costs, net on $10k per coin
PUBLISHED_T1_24 = {"ADAUSDT": 8196, "DOGEUSDT": 11129, "SOLUSDT": 10029, "BNBUSDT": 1071,
                   "XRPUSDT": 339, "LINKUSDT": -4217}
PUBLISHED_POOLED = {("T1", 4): -1712, ("T2", 4): -2187, ("T1", 12): 8829, ("T2", 12): 10445,
                    ("T1", 24): 26547, ("T2", 24): 24960}


def selftest() -> None:
    fails = 0

    def check(name: str, ok: bool) -> None:
        nonlocal fails
        fails += 0 if ok else 1
        print(f"{'PASS' if ok else 'FAIL'}  {name}")

    h4 = pd.date_range("2024-01-01", periods=12, freq="4h", tz="UTC")
    m5 = pd.date_range("2024-01-01", periods=12 * 48, freq="5min", tz="UTC")
    w4, w5 = pd.Timedelta(hours=4), pd.Timedelta(minutes=5)
    p = closed_htf_index(h4, w4, m5, w5)
    check("no 4H bar is usable during the first 4 hours", bool((p[:47] == -1).all()))
    check("the 4H bar becomes usable exactly when its last 5m bar closes", p[47] == 0 and p[48] == 0)
    check("every mapped 4H bar closed by the 5m bar's close",
          bool(((h4[p[p >= 0]] + w4) <= (m5[p >= 0] + w5)).all()))
    legacy = h4.searchsorted(m5, side="right") - 1
    leak = (h4[legacy] + w4) > (m5 + w5)
    check(f"mutation: the legacy line maps to an unclosed bar ({100 * leak.mean():.1f}% of 5m bars)",
          bool(leak.mean() > 0.9))
    try:
        bad = np.array(legacy)
        ok = ((h4[bad] + w4) <= (m5 + w5)).all()
        check("mutation: the closed-bar assertion would reject the legacy mapping", not ok)
    except IndexError:
        check("mutation: the closed-bar assertion would reject the legacy mapping", False)
    print(f"\nselftest: {'ALL PASS' if fails == 0 else f'{fails} FAILED'}")
    if fails:
        sys.exit(1)


def run_holdout(htf_match: str, cost_mults: tuple) -> dict:
    out = {}
    for sym in HOLDOUT:
        df = load_cached_1m(f"{SDZ}/um5m_{sym}.csv.gz")
        df = df[(df.index >= WINDOW[0]) & (df.index < WINDOW[1])]
        sig, df5 = get_signals(df, "5m", htf_match=htf_match)
        a5 = atr(df5)
        fund = load_funding(COMMITTED_FUNDING.get(sym, f"{SDZ}/funding_{sym}.csv"), df5.index)
        print(f"{sym}: {len(df5)} 5m bars {df5.index.min().date()} -> {df5.index.max().date()}, "
              f"{len(sig)} signals [{htf_match}]", flush=True)
        for cm in cost_mults:
            for cell in CELLS:
                for h in HOURS:
                    r = run_cell(sig, df5, a5, fund, h, use_stop=(cell == "T2"), cost_mult=cm)
                    out[(sym, cell, h, cm)] = r
        out[(sym, "n_signals")] = len(sig)
    return out


def pooled(res: dict, cell: str, h: int, cm: float) -> tuple:
    net = sum(res[(s, cell, h, cm)].get("net", 0.0) for s in HOLDOUT)
    gw = sum(res[(s, cell, h, cm)].get("gross_win", 0.0) for s in HOLDOUT)
    gl = sum(res[(s, cell, h, cm)].get("gross_loss", 0.0) for s in HOLDOUT)
    pos = sum(1 for s in HOLDOUT if res[(s, cell, h, cm)].get("net", 0.0) > 0)
    return float(net), (gw / gl if gl > 0 else float("inf")), pos


def report(res: dict, label: str, cost_mults: tuple) -> None:
    print(f"\n=== {label} ===")
    print("per coin, T1 24h base costs: " + ", ".join(
        f"{s.replace('USDT', '')} {res[(s, 'T1', 24, 1.0)].get('net', 0):+,.0f} "
        f"(PF {res[(s, 'T1', 24, 1.0)].get('pf', float('nan'))}, n {res[(s, 'n_signals')]})" for s in HOLDOUT))
    for cm in cost_mults:
        for cell in CELLS:
            for h in HOURS:
                net, pf, pos = pooled(res, cell, h, cm)
                pub = PUBLISHED_POOLED.get((cell, h)) if cm == 1.0 else None
                print(f"  x{cm:g} {cell} {h:>2d}h: pooled net {net:+9,.0f}  PF {pf:.3f}  coins+ {pos}/6"
                      + (f"   (published {pub:+,})" if pub is not None else ""))


def verdict(res: dict) -> None:
    print("\nFIVE ORIGINAL CRITERIA (24h cells; criterion 4 = development, re-checked separately):")
    for cell in CELLS:
        net, pf, pos = pooled(res, cell, 24, 1.0)
        net15, _, _ = pooled(res, cell, 24, 1.5)
        c = [net > 0, pos >= 4, pf >= 1.05, None, net15 > 0]
        marks = ["yes" if x else ("n/a" if x is None else "NO") for x in c]
        print(f"  {cell} 24h: (1) pooled net>0 {marks[0]} [{net:+,.0f}]  (2) >=4/6 coins {marks[1]} [{pos}/6]  "
              f"(3) PF>=1.05 {marks[2]} [{pf:.3f}]  (4) dev {marks[3]}  (5) net>0 at 1.5x {marks[4]} [{net15:+,.0f}]")
        print(f"    -> {'PASS on 1,2,3,5' if all(x for x in c if x is not None) else 'FAIL'}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--repro", action="store_true")
    ap.add_argument("--corrected", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
    if a.repro:
        res = run_holdout("open", (1.0,))
        report(res, "REPRODUCTION with the legacy (lookahead) matching", (1.0,))
        print("published T1 24h per coin: " + ", ".join(f"{s.replace('USDT', '')} {v:+,}" for s, v in PUBLISHED_T1_24.items()))
    if a.corrected:
        res = run_holdout("close", (1.0, 1.5))
        report(res, "CORRECTED (closed-bar matching)", (1.0, 1.5))
        verdict(res)


if __name__ == "__main__":
    main()
