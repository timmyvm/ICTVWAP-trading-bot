"""
v0.24-exp — Funding-settlement flow test (reason-first; DEVLOG v0.24-exp).

Hypothesis: holders on the PAYING side of perp funding close just before the
settlement instant and reopen after, so the pre-settlement return moves OPPOSITE
to the funding sign and the post-settlement return partially reverses.

The confound: funding is positive most of the time and 00:00 UTC is also the
daily candle open, so a generic hour-of-day effect can masquerade as a funding
effect. The primary statistic is therefore a difference-in-differences,

    DiD = [mean r | top f tercile  -  mean r | bottom f tercile]  at settlement
        - [same funding-sorted spread]                            at other hours

which removes any hour-of-day effect that does not depend on funding. Settlement
times are read from each symbol's funding file, never assumed. Windows are 8 h
apart and at most 1 h long, so events do not overlap.

Conditioning (--fcol): f_prev (primary) = the last rate settled strictly before
the event, knowable in advance. f_next (diagnostic, mild lookahead) = the rate
settled at or after the event, which approximates the predicted rate a live
trader sees in the final hour.
"""

import argparse
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from backtest.data import load_cached_1m  # noqa: E402

WINDOWS = (30, 60)           # minutes
ROUND_TRIP = 0.13            # %, taker 0.055 + slip 0.01, both legs
SDZ = "backtest/data_cache/local/sdz"
EXPLORE = ["BTCUSDT", "ETHUSDT"]
HOLDOUT = ["BNBUSDT", "XRPUSDT", "ADAUSDT", "DOGEUSDT", "SOLUSDT", "LINKUSDT"]
FUNDING_PATH = {"BTCUSDT": "backtest/data_cache/funding_btcusdt_binance.csv",
                "ETHUSDT": "backtest/data_cache/funding_ethusdt_binance.csv"}


def epoch_s(idx) -> np.ndarray:
    """Integer epoch seconds via the subtraction idiom (CLAUDE.md: never astype int64)."""
    d = pd.DatetimeIndex(idx)
    return np.asarray((d - pd.Timestamp(0, tz="UTC")) // pd.Timedelta(seconds=1), dtype=np.int64)


def load_open(sym: str) -> pd.Series:
    df = load_cached_1m(f"{SDZ}/um5m_{sym}.csv.gz")
    s = df["open"].astype(float)
    s.index = pd.DatetimeIndex(s.index).tz_convert("UTC")
    return s[~s.index.duplicated(keep="first")]


def load_funding(sym: str) -> pd.DataFrame:
    f = pd.read_csv(FUNDING_PATH.get(sym, f"{SDZ}/funding_{sym}.csv"))
    ts = pd.to_datetime(f["timestamp"], unit="s", utc=True).dt.round("min")
    out = pd.DataFrame({"ts": ts, "rate": f["rate"].astype(float)}).dropna()
    return out.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)


def build_events(px: pd.Series, fund: pd.DataFrame, w_min: int) -> pd.DataFrame:
    lo = max(px.index.min(), fund["ts"].min()).ceil("h")
    hi = min(px.index.max(), fund["ts"].max()).floor("h")
    T = pd.date_range(lo, hi, freq="h", tz="UTC")
    w = pd.Timedelta(minutes=w_min)
    p0 = px.reindex(T).to_numpy()
    p_pre = px.reindex(T - w).to_numpy()
    p_post = px.reindex(T + w).to_numpy()

    t_s = epoch_s(T)
    f_s = epoch_s(fund["ts"])
    rate = fund["rate"].to_numpy()
    i_prev = np.searchsorted(f_s, t_s, side="left") - 1
    i_next = np.searchsorted(f_s, t_s, side="left")
    f_prev = np.where(i_prev >= 0, rate[np.clip(i_prev, 0, len(rate) - 1)], np.nan)
    f_next = np.where(i_next < len(rate), rate[np.clip(i_next, 0, len(rate) - 1)], np.nan)

    with np.errstate(divide="ignore", invalid="ignore"):
        ev = pd.DataFrame({
            "T": T, "hour": T.hour, "year": T.year,
            "settle": np.isin(t_s, f_s),
            "r_pre": 100.0 * np.log(p0 / p_pre),
            "r_post": 100.0 * np.log(p_post / p0),
            "f_prev": f_prev, "f_next": f_next,
        })
    return ev.replace([np.inf, -np.inf], np.nan).dropna(subset=["r_pre", "r_post", "f_prev", "f_next"])


def spread(df: pd.DataFrame, col: str, fcol: str, q1: float, q2: float) -> tuple:
    top = df.loc[df[fcol] >= q2, col]
    bot = df.loc[df[fcol] <= q1, col]
    if len(top) < 5 or len(bot) < 5:
        return np.nan, np.nan
    s = top.mean() - bot.mean()
    se = np.sqrt(top.var(ddof=1) / len(top) + bot.var(ddof=1) / len(bot))
    return s, se


def did(ev: pd.DataFrame, col: str, fcol: str, q1: float, q2: float) -> tuple:
    s_set, se_set = spread(ev[ev.settle], col, fcol, q1, q2)
    s_base, se_base = spread(ev[~ev.settle], col, fcol, q1, q2)
    d = s_set - s_base
    se = np.sqrt(se_set ** 2 + se_base ** 2)
    return s_set, s_base, d, (d / se if se > 0 else np.nan)


def diff_means(a: pd.Series, b: pd.Series) -> tuple:
    if len(a) < 5 or len(b) < 5:
        return np.nan, np.nan, len(a)
    d = a.mean() - b.mean()
    se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    return d, (d / se if se > 0 else np.nan), len(a)


def analyse(sym: str, fcol: str) -> dict:
    px = load_open(sym)
    fund = load_funding(sym)
    off_hour = int((fund["ts"].dt.minute != 0).sum())
    hours = sorted(fund["ts"].dt.hour.unique().tolist())
    out = {"sym": sym}
    print(f"=== {sym}  bars {px.index.min().date()}->{px.index.max().date()}  "
          f"settlements {len(fund)} at hours {hours}  off-hour stamps {off_hour}  [cond {fcol}]")
    for W in WINDOWS:
        ev = build_events(px, fund, W)
        q1, q2 = ev[fcol].quantile([1 / 3, 2 / 3]).to_numpy()
        st, ba = ev[ev.settle], ev[~ev.settle]
        print(f"  W={W}m  settle n={len(st)}  base n={len(ba)}  tercile cuts f<={100*q1:.4f}% / f>={100*q2:.4f}%")
        for col, pred in (("r_pre", "<0"), ("r_post", ">0")):
            s_set, s_base, d, t = did(ev, col, fcol, q1, q2)
            yrs = []
            for y, g in ev.groupby("year"):
                _, _, dy, _ = did(g, col, fcol, q1, q2)
                if not np.isnan(dy):
                    yrs.append(dy)
            ok = sum(1 for v in yrs if (v < 0 if pred == "<0" else v > 0))
            print(f"    {col:6s} spread@settle {s_set:+.4f}%  spread@base {s_base:+.4f}%  "
                  f"DiD {d:+.4f}%  t {t:+.2f}  (pred {pred})  years matching pred {ok}/{len(yrs)}")
            out[(W, col)] = {"did": d, "t": t, "years_ok": ok, "years": len(yrs)}
        # per settlement hour: an effect at 00:00 only is the daily open, not funding
        parts = []
        for h in sorted(st["hour"].unique()):
            sub = pd.concat([st[st.hour == h], ba])
            _, _, dh, th = did(sub, "r_pre", fcol, q1, q2)
            parts.append(f"{h:02d}h {dh:+.4f}% (t {th:+.2f}, n={int((st.hour == h).sum())})")
        print("    r_pre DiD by settlement hour: " + " | ".join(parts))
        # sharpest single test: negative funding should BUY into settlement
        dn, tn, nn = diff_means(st.loc[st[fcol] < 0, "r_pre"], ba.loc[ba[fcol] < 0, "r_pre"])
        dp, tp, npos = diff_means(st.loc[st[fcol] > 0, "r_pre"], ba.loc[ba[fcol] > 0, "r_pre"])
        print(f"    r_pre settle-minus-base by funding sign: f<0 {dn:+.4f}% (t {tn:+.2f}, n={nn}, pred >0)"
              f" | f>0 {dp:+.4f}% (t {tp:+.2f}, n={npos}, pred <0)")
        # tradeable form: short into settlement when funding is high, long when low
        short_g = -st.loc[st[fcol] >= q2, "r_pre"]
        long_g = st.loc[st[fcol] <= q1, "r_pre"]
        print(f"    tradeable gross at settlement: short-top-tercile {short_g.mean():+.4f}% "
              f"(n={len(short_g)}) | long-bottom-tercile {long_g.mean():+.4f}% (n={len(long_g)}) "
              f"| round trip {ROUND_TRIP:.2f}%")
        out[(W, "trade")] = (short_g.mean(), long_g.mean())
    print()
    return out


def selftest() -> None:
    """
    Plant a known effect in synthetic data and confirm the DiD recovers it with
    the right sign, then confirm it reports ~nothing when nothing is planted.
    Also plants a funding-INDEPENDENT dip into 00:00 UTC — the confound — and
    checks the DiD is not fooled by it.
    """
    rng = np.random.default_rng(7)
    idx = pd.date_range("2021-01-01", "2023-01-01", freq="5min", tz="UTC", inclusive="left")
    fts = pd.date_range("2021-01-01", "2023-01-01", freq="8h", tz="UTC", inclusive="left")
    rates = rng.normal(0.0001, 0.00015, len(fts))          # ~75 % positive, like crypto
    fund = pd.DataFrame({"ts": fts, "rate": rates})
    base_ret = rng.normal(0, 0.0012, len(idx))             # ~0.12 % per 5m bar

    def run(plant: str) -> tuple:
        r = base_ret.copy()
        t_s, f_s = epoch_s(idx), epoch_s(fts)
        for k, ts in enumerate(f_s):
            j = int(np.searchsorted(t_s, ts))               # bar starting at settlement
            if j < 12:
                continue
            fprev = rates[k - 1] if k > 0 else 0.0
            if plant == "funding":                          # sell into settlement when f > 0
                r[j - 12:j] += -0.15 / 100 * np.sign(fprev) / 12
            if plant == "confound" and fts[k].hour == 0:    # dip into 00:00 regardless of f
                r[j - 12:j] += -0.15 / 100 / 12
        px = pd.Series(100.0 * np.exp(np.cumsum(r)), index=idx)
        ev = build_events(px, fund, 60)
        q1, q2 = ev["f_prev"].quantile([1 / 3, 2 / 3]).to_numpy()
        _, _, d, t = did(ev, "r_pre", "f_prev", q1, q2)
        return d, t

    cases = [("none", "|t| < 2.5"), ("funding", "DiD < 0, t < -3"), ("confound", "|t| < 2.5")]
    ok_all = True
    for plant, want in cases:
        d, t = run(plant)
        ok = (abs(t) < 2.5) if plant != "funding" else (d < 0 and t < -3)
        ok_all &= ok
        print(f"  selftest plant={plant:9s} DiD {d:+.4f}%  t {t:+.2f}  want {want}  -> {'PASS' if ok else 'FAIL'}")
    print("SELFTEST", "PASSED" if ok_all else "FAILED")
    if not ok_all:
        sys.exit(1)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", default="explore", help="'explore', 'holdout', 'all' or a comma list")
    ap.add_argument("--fcol", choices=["f_prev", "f_next"], default="f_prev")
    ap.add_argument("--selftest", action="store_true", help="planted-effect check on synthetic data")
    args = ap.parse_args()
    if args.selftest:
        selftest()
        return
    groups = {"explore": EXPLORE, "holdout": HOLDOUT, "all": EXPLORE + HOLDOUT}
    syms = groups.get(args.assets, args.assets.split(","))
    res = [analyse(s, args.fcol) for s in syms]
    print("SUMMARY (pre-window DiD, prediction < 0):")
    for W in WINDOWS:
        row = [f"{r['sym']} {r[(W, 'r_pre')]['did']:+.4f} (t {r[(W, 'r_pre')]['t']:+.2f})" for r in res]
        neg = sum(1 for r in res if r[(W, "r_pre")]["did"] < 0)
        print(f"  W={W}m  negative in {neg}/{len(res)}:  " + "  ".join(row))


if __name__ == "__main__":
    main()
