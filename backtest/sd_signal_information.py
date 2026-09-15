"""
v0.22-D2 — Does the supply/demand + structure-shift ENTRY carry information?

v0.22 asked "is the packaged strategy profitable" and answered no. That is not
the same question as "is there anything real in it". This strips the packaging
away entirely — no stop, no target, no position management, no one-trade-at-a-
time thinning — and asks only: after a trigger, does price move in the signal's
direction more than it usually does?

For every trigger the engine produces, the forward return in the signal's
direction is measured at 1 h / 4 h / 12 h / 24 h, then the asset's UNCONDITIONAL
mean forward return over the same horizon and the same direction is subtracted.
What is left is the signal's excess, i.e. the part not explained by drift. The
cost line (0.13 % round trip at Bybit retail) is printed beside it, because an
edge smaller than the fee is real and untradeable at the same time.

Caveat printed with the results: forward windows OVERLAP, so the t-statistics
are inflated by autocorrelation and are indicative, not inferential. A
non-overlapping subsample is reported alongside for that reason.
"""

import argparse
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from backtest.data import load_cached_1m  # noqa: E402
from backtest.sd_vwap_experiment import simulate  # noqa: E402

HORIZONS = {"1h": 12, "4h": 48, "12h": 144, "24h": 288}   # in 5m bars
ROUND_TRIP_PCT = 2 * (0.055 + 0.01)                        # Bybit retail, both legs


def analyse(df1m: pd.DataFrame, label: str, require_zone: bool = True) -> None:
    out = simulate(df1m, signals_only=True, require_zone=require_zone)
    sig, df5 = out["signals"], out["df5"]
    if sig.empty:
        print(f"[{label}] no signals")
        return
    c = df5["close"].to_numpy()
    n = len(c)
    bars = sig["bar"].to_numpy()
    dirs = sig["dir"].to_numpy()

    print(f"[{label}] {len(sig)} signals "
          f"({int((dirs == 1).sum())} long / {int((dirs == -1).sum())} short), "
          f"round-trip cost {ROUND_TRIP_PCT:.3f} % of price")
    print(f"  {'horizon':>7s} {'signal %':>9s} {'uncond %':>9s} {'excess %':>9s} "
          f"{'t(overlap)':>10s} {'t(indep)':>9s} {'hit %':>6s} {'excess/cost':>11s}")

    for name, H in HORIZONS.items():
        ok = bars + H < n
        b, d = bars[ok], dirs[ok]
        if len(b) < 30:
            continue
        fwd = d * (c[b + H] / c[b] - 1.0) * 100.0          # directional, in %

        # unconditional baseline over the same horizon, matched to the signal's
        # long/short mix, so drift cannot be mistaken for skill
        base_all = (c[H:] / c[:-H] - 1.0) * 100.0
        mix = d.mean()                                      # +1 all long, -1 all short
        uncond = mix * base_all.mean()

        excess = fwd - uncond
        t_overlap = excess.mean() / (excess.std(ddof=1) / np.sqrt(len(excess)))
        # independent subsample: keep signals at least H bars apart
        keep, last = [], -10**9
        for i, bi in enumerate(b):
            if bi - last >= H:
                keep.append(i)
                last = bi
        ex_i = excess[keep]
        t_indep = (ex_i.mean() / (ex_i.std(ddof=1) / np.sqrt(len(ex_i)))
                   if len(ex_i) > 5 and ex_i.std(ddof=1) > 0 else np.nan)
        print(f"  {name:>7s} {fwd.mean():9.4f} {uncond:9.4f} {excess.mean():9.4f} "
              f"{t_overlap:10.2f} {t_indep:9.2f} {100 * (fwd > 0).mean():6.1f} "
              f"{excess.mean() / ROUND_TRIP_PCT:11.2f}  (n_indep={len(ex_i)})")
    print()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", default="backtest/data_cache/local/btcusd_1m_2019_2022.csv.gz")
    ap.add_argument("--start", default=None)
    ap.add_argument("--label", default="")
    ap.add_argument("--no-zones", action="store_true",
                    help="D3 ablation: drop the supply/demand stage entirely")
    args = ap.parse_args()
    df = load_cached_1m(args.cache)
    if args.start:
        df = df[df.index >= pd.Timestamp(args.start, tz="America/New_York")]
    label = (args.label or args.cache) + (" NO-ZONES" if args.no_zones else "")
    analyse(df, label, require_zone=not args.no_zones)
    print("Overlapping windows inflate t(overlap); t(indep) uses signals spaced "
          "at least one horizon apart. Excess/cost < 1 means the average move is "
          "smaller than the round trip that would capture it.")


if __name__ == "__main__":
    main()
