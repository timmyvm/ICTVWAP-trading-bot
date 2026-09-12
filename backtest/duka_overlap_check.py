"""
v0.16d source-consistency gate: Dukascopy USATECHIDXUSD vs the FutureSharks/
Oanda NAS100 cache on their overlap (2019-01-01 -> 2020-05-14, consumed data).

Pre-registered gate (DEVLOG v0.16d-exp): on common 1H bars the closes must
agree within 0.05 % RMS, and Cell B (v0.16b ATR-stop ORB) run on each
source over the overlap must agree in the sign of net and within +/-25 %
on trade count and on net. A failed gate voids the fresh-era verdict.
"""

import argparse
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from backtest.data import load_cached_1m, resample_ohlcv  # noqa: E402
from backtest.orb_paper_experiment import simulate  # noqa: E402

NY = "America/New_York"


def within(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol * max(abs(a), abs(b), 1e-9)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="backtest/data_cache/local/nas100_1m_2015_2020.csv.gz")
    ap.add_argument("--new", default="backtest/data_cache/local/nas100_duka_1m_2019_2026.csv.gz")
    ap.add_argument("--start", default="2019-01-01")
    ap.add_argument("--end", default="2020-05-14")
    args = ap.parse_args()
    lo, hi = pd.Timestamp(args.start, tz=NY), pd.Timestamp(args.end, tz=NY)

    ref = load_cached_1m(args.ref)
    new = load_cached_1m(args.new)
    ref = ref[(ref.index >= lo) & (ref.index < hi)]
    new = new[(new.index >= lo) & (new.index < hi)]
    print(f"ref {ref.index.min()} -> {ref.index.max()} ({len(ref)} 1m rows)")
    print(f"new {new.index.min()} -> {new.index.max()} ({len(new)} 1m rows)")

    # 1) price agreement on common 1H bars
    r1h, n1h = resample_ohlcv(ref, "1h"), resample_ohlcv(new, "1h")
    common = r1h.index.intersection(n1h.index)
    rel = (n1h.loc[common, "close"] / r1h.loc[common, "close"] - 1.0)
    rms = float(np.sqrt((rel ** 2).mean()))
    print(f"common 1H bars {len(common)} (ref-only {len(r1h.index.difference(n1h.index))}, "
          f"new-only {len(n1h.index.difference(r1h.index))}); close diff mean {100 * rel.mean():+.4f} %, "
          f"RMS {100 * rms:.4f} %, max |diff| {100 * rel.abs().max():.3f} %")
    # session coverage: 09:30 NY bars per source
    for name, d in (("ref", ref), ("new", new)):
        mod = d.index.hour * 60 + d.index.minute
        print(f"  {name}: 09:30 bars {(mod == 570).sum()}, session 1m bars {((mod >= 570) & (mod < 960)).sum()}")

    # 2) Cell B on each source over the overlap
    res = {}
    for name, d in (("ref", ref), ("new", new)):
        res[name] = simulate(d, "atr")
        r = res[name]
        print(f"  Cell B on {name}: n={r['n']} win={r['win_pct']} PF={r['pf']} net={r['net']:+.0f} "
              f"maxDD={r['max_dd_pct']} per_year={r['per_year']}")

    a, b = res["ref"], res["new"]
    checks = {
        "close RMS < 0.05 %": rms < 0.0005,
        "same sign of net": np.sign(a["net"]) == np.sign(b["net"]),
        "trade count within 25 %": within(a["n"], b["n"], 0.25),
        "net within 25 %": within(a["net"], b["net"], 0.25),
    }
    for k, v in checks.items():
        print(f"  [{'PASS' if v else 'FAIL'}] {k}")
    print("GATE:", "PASS" if all(checks.values()) else "FAIL")


if __name__ == "__main__":
    main()
