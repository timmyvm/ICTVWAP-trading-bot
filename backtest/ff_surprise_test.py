"""
v0.32-exp — ForexFactory macro surprises: is any of the move still tradeable after the release?
(DEVLOG v0.32-exp, pre-registered.)

The user's idea: use ForexFactory's calendar (actual vs forecast) to predict the market. The first
minute's reaction to a surprise is fast and well known; the question is whether anything is left
from the first price a trader could actually get (CLAUDE.md, v0.27 lesson: score from the first
tradeable price, not the reaction).

Events: USD high-impact releases with numeric actual and forecast and a "usual effect" sign
(backtest/fetch_ff_calendar.py). Surprise z = (actual - forecast) / a robust scale of the same
event's last 36 PRIOR surprises (80th percentile of |surprise| / 1.2816; >= 12 prior). Releases at
the same minute are combined: S = mean of effect x z, so S > 0 is good for the dollar.

  --clockcheck  market check of the event times (EURUSD spikes at the release minute) and of
                HistData's clock (08:30 New York peak by month); no drift is measured here
  --selftest    planted drift recovered, a planted first-minute jump NOT counted, z prior-only, parsing
  --report      the pre-registered primary, then the labelled secondaries
"""

import argparse
import math
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from backtest.data import NY_TZ, load_cached_1m  # noqa: E402
from backtest.fetch_ff_calendar import OUT as EVENTS_FILE  # noqa: E402
from backtest.fetch_ff_calendar import load_events, parse_value, to_utc  # noqa: E402

LOCAL = "backtest/data_cache/local"
# market: (file, sign of the move when the surprise is GOOD for the dollar (0 = no fixed sign),
#          round-trip cost in price units at news time)
MARKETS = {
    "EURUSD": (f"{LOCAL}/eurusd_histdata_1m_2015_2026.csv.gz", -1, 0.0002),   # 2 pips
    "USDJPY": (f"{LOCAL}/usdjpy_histdata_1m_2015_2026.csv.gz", 1, 0.02),      # 2 pips
    "XAUUSD": (f"{LOCAL}/xauusd_histdata_1m_2015_2026.csv.gz", -1, 0.60),     # $0.60/oz
    "NQ": (f"{LOCAL}/nas100_histdata_1m_2015_2026.csv.gz", 0, 2.0),           # 2 index points
}
DEV = (pd.Timestamp("2015-01-01", tz="UTC"), pd.Timestamp("2021-01-01", tz="UTC"))
HOLDOUT = (pd.Timestamp("2021-01-01", tz="UTC"), pd.Timestamp("2025-04-08", tz="UTC"))
MIN_PRIOR = 12
Z_WINDOW = 36                                   # robust scale over the last 36 prior releases
Z_MIN = 1.0
ENTRY_MIN, HOLD_MIN = 1, 60                      # primary: enter 1 minute after, hold 60 minutes
ENTRIES, HOLDS = (1, 5), (15, 60, "close")       # secondary grid; "close" = 16:00 New York
PRICE_TOL = pd.Timedelta(minutes=5)
PASS_T = 2.0
FAMILY = {
    "jobs": ("Non-Farm Employment Change", "Unemployment Rate", "Average Hourly Earnings m/m",
             "ADP Non-Farm Employment Change", "Unemployment Claims", "JOLTS Job Openings",
             "Employment Cost Index q/q"),
    "inflation": ("CPI m/m", "CPI y/y", "Core CPI m/m", "PPI m/m", "Core PPI m/m", "Core PCE Price Index m/m"),
    "fed": ("Federal Funds Rate",),
    "oil": ("Crude Oil Inventories",),
}


def family_of(names: list) -> str:
    fams = {f for f, evs in FAMILY.items() for n in names if n in evs}
    if not fams:
        return "growth"
    return fams.pop() if len(fams) == 1 else "mixed"


# ----------------------------------------------------------------------------------------------
# surprises
# ----------------------------------------------------------------------------------------------
def robust_scale(prior: np.ndarray) -> float:
    """sigma estimate from the 80th percentile of |surprise| (Q80/1.2816 = sigma for a normal).
    Robust to the 2020 outliers (payrolls missed by millions) that would inflate an RMS for years."""
    return float(np.quantile(np.abs(prior), 0.80) / 1.2816)


def add_z(ev: pd.DataFrame, min_prior: int = MIN_PRIOR, window: int = Z_WINDOW) -> pd.DataFrame:
    """z = surprise / robust scale of the same event's last `window` strictly earlier surprises
    (at least min_prior of them; z undefined when the scale is 0)."""
    ev = ev[ev["actual"].notna() & ev["forecast"].notna() & (ev["effect"] != 0)].copy()
    ev = ev.sort_values(["event", "utc"]).reset_index(drop=True)
    ev["surprise"] = ev["actual"] - ev["forecast"]
    z = np.full(len(ev), np.nan)
    for _, g in ev.groupby("event", sort=False):
        s = g["surprise"].to_numpy()
        for j, row in enumerate(g.index):
            if j < min_prior:
                continue
            sc = robust_scale(s[max(0, j - window):j])
            if sc > 0:
                z[row] = s[j] / sc
    ev["z"] = z
    ev["sz"] = ev["effect"] * ev["z"]
    return ev.sort_values("utc").reset_index(drop=True)


def releases(ev: pd.DataFrame) -> pd.DataFrame:
    """One row per release minute: S = mean of effect x z over its events with a valid z."""
    ok = ev[ev["z"].notna()]
    rel = ok.groupby("utc").agg(S=("sz", "mean"), n_events=("sz", "size"),
                                events=("event", lambda s: "|".join(sorted(s)))).reset_index()
    rel["family"] = rel["events"].str.split("|").map(family_of)
    return rel


# ----------------------------------------------------------------------------------------------
# prices
# ----------------------------------------------------------------------------------------------
class Prices:
    """price_at(t): the open of the bar starting at t, else the last close before t within 5 min."""

    def __init__(self, df: pd.DataFrame):
        utc = df.index.tz_convert("UTC")
        self.idx = utc
        self.o = df["open"].to_numpy()
        self.c = df["close"].to_numpy()

    def at(self, ts: pd.DatetimeIndex) -> np.ndarray:
        ts = pd.DatetimeIndex(ts)
        pos = self.idx.searchsorted(ts, side="left")
        out = np.full(len(ts), np.nan)
        ok = pos < len(self.idx)
        exact = ok.copy()
        exact[ok] = self.idx[pos[ok]] == ts[ok]
        out[exact] = self.o[pos[exact]]
        prev = pos - 1
        use = ~exact & (prev >= 0)
        good = use.copy()
        good[use] = (ts[use] - self.idx[prev[use]]) <= PRICE_TOL
        out[good] = self.c[prev[good]]
        return out


def ny_close(ts: pd.DatetimeIndex) -> pd.DatetimeIndex:
    ny = pd.DatetimeIndex(ts).tz_convert(NY_TZ)
    return (ny.normalize() + pd.Timedelta(hours=16)).tz_convert("UTC")


def measure(rel: pd.DataFrame, px: Prices, sign: int, cost_abs: float) -> pd.DataFrame:
    """Per release: the first-minute reaction and every entry/hold cell, signed by the surprise
    (dollar-good x the market's sign) and by the reaction (momentum)."""
    t0 = pd.DatetimeIndex(rel["utc"])
    m = pd.Timedelta(minutes=1)
    out = rel.copy()
    p_pre, p_1 = px.at(t0 - m), px.at(t0 + m)
    out["reaction"] = np.log(p_1 / p_pre)
    out["dir_surprise"] = sign * np.sign(out["S"]) if sign != 0 else 0.0
    out["dir_momentum"] = np.sign(out["reaction"]).fillna(0.0)
    for k in ENTRIES:
        pe = px.at(t0 + k * m)
        out[f"cost_e{k}"] = cost_abs / pe
        for h in HOLDS:
            tx = ny_close(t0) if h == "close" else t0 + (k + h) * m
            r = np.log(px.at(tx) / pe)
            if h == "close":
                r = np.where(tx > t0 + k * m, r, np.nan)
            out[f"r_e{k}_{h}"] = r
    out["date"] = pd.DatetimeIndex(out["utc"]).tz_convert(NY_TZ).strftime("%Y-%m-%d")
    return out


def cluster_t(x: np.ndarray, groups: np.ndarray) -> tuple:
    n = len(x)
    if n < 3:
        return float("nan"), float("nan"), n
    mu = float(np.mean(x))
    dev = pd.Series(x - mu).groupby(groups).sum().to_numpy()
    g = len(dev)
    se = math.sqrt(float((dev ** 2).sum()) * g / max(g - 1, 1)) / n
    return mu, (mu / se if se > 0 else float("nan")), n


def cell(m: pd.DataFrame, k: int, h, direction: str = "surprise", z_min: float = Z_MIN,
         net: bool = True) -> dict:
    d = m[f"dir_{direction}"].to_numpy(dtype=float)
    r = m[f"r_e{k}_{h}"].to_numpy(dtype=float)
    keep = (np.abs(m["S"].to_numpy()) >= z_min) & np.isfinite(r) & (d != 0)
    x = d[keep] * r[keep] - (m[f"cost_e{k}"].to_numpy()[keep] if net else 0.0)
    mu, t, n = cluster_t(x, m["date"].to_numpy()[keep])
    return {"n": n, "mean_bp": mu * 1e4, "t": t, "hit": float((x > 0).mean()) if n else float("nan")}


def fmt(c: dict) -> str:
    return f"n {c['n']:4d}  mean {c['mean_bp']:+7.2f} bp  t {c['t']:+5.2f}  hit {100 * c['hit']:4.1f}%"


def in_era(m: pd.DataFrame, era: tuple) -> pd.DataFrame:
    u = pd.DatetimeIndex(m["utc"])
    return m[(u >= era[0]) & (u < era[1])]


# ----------------------------------------------------------------------------------------------
# clock check (before any drift is read)
# ----------------------------------------------------------------------------------------------
def clockcheck() -> None:
    ev = load_events(EVENTS_FILE)
    ev = ev[(ev["utc"] >= DEV[0]) & (ev["utc"] < HOLDOUT[1])]
    eur = load_cached_1m(MARKETS["EURUSD"][0])
    px = Prices(eur)
    r1 = pd.Series(np.log(eur["close"].to_numpy() / eur["open"].to_numpy()), index=px.idx).abs()
    print("HistData EURUSD/USDJPY clock: NY minute with the largest mean |1m move|, by year")
    for name in ("EURUSD", "USDJPY"):
        df = eur if name == "EURUSD" else load_cached_1m(MARKETS[name][0])
        a = pd.Series(np.log(df["close"].to_numpy() / df["open"].to_numpy()), index=df.index).abs()
        a = a[df.index.weekday < 5]
        mod = a.index.hour * 60 + a.index.minute
        for y, g in a.groupby(a.index.year):
            prof = g.groupby(mod[a.index.year == y]).mean()
            top = int(prof.idxmax())
            print(f"  {name} {y}: peak {top // 60:02d}:{top % 60:02d}  08:30 is {prof.get(510, np.nan) / prof.median():4.1f}x "
                  f"the median minute, 07:30 {prof.get(450, np.nan) / prof.median():4.1f}x, 09:30 {prof.get(570, np.nan) / prof.median():4.1f}x")
    print("\nEvent times vs EURUSD: share of release minutes whose |1m move| is the largest in +-30 min, "
          "and the same for the minute one hour earlier / later (a clock error would move the spike there)")
    mins = ev.groupby("utc").agg(src=("time_source", lambda s: "schedule" if (s == "canonical").all() else "archive"),
                                 names=("event", lambda s: "|".join(sorted(set(s))))).reset_index()
    rows = []
    for _, r in mins.iterrows():
        t0 = r["utc"]
        lo, hi = t0 - pd.Timedelta(minutes=90), t0 + pd.Timedelta(minutes=91)
        w = r1[(r1.index >= lo) & (r1.index < hi)]
        if len(w) < 120:
            continue
        def is_max(t):
            win = w[(w.index >= t - pd.Timedelta(minutes=30)) & (w.index <= t + pd.Timedelta(minutes=30))]
            return bool(len(win) and t in win.index and win[t] >= win.max())
        rows.append((t0.year, r["src"], is_max(t0), is_max(t0 - pd.Timedelta(hours=1)), is_max(t0 + pd.Timedelta(hours=1))))
    tab = pd.DataFrame(rows, columns=["year", "src", "at", "minus1h", "plus1h"])
    out = tab.groupby(["year", "src"])[["at", "minus1h", "plus1h"]].mean().mul(100).round(0)
    out["n"] = tab.groupby(["year", "src"]).size()
    print(out.to_string())


# ----------------------------------------------------------------------------------------------
# self-tests
# ----------------------------------------------------------------------------------------------
def selftest() -> None:
    fails = 0

    def check(name: str, ok: bool) -> None:
        nonlocal fails
        fails += 0 if ok else 1
        print(f"{'PASS' if ok else 'FAIL'}  {name}")

    check("parse '275K', '-0.1%', '2.73T', '<0.25%', '1.2|0.3'",
          parse_value("275K") == 275000 and parse_value("-0.1%") == -0.1 and parse_value("2.73T") == 2.73e12
          and math.isnan(parse_value("<0.25%")) and math.isnan(parse_value("1.2|0.3")))
    raw = pd.Series(["2023-07-12T16:00:00+04:30", "2019-06-07T17:00:00+04:30", "2016-01-08T17:00:00+03:30"])
    u, _ = to_utc(raw)
    check("Tehran offsets: post-2022 +04:30 read as +03:30; real DST and standard time kept",
          list(u.dt.strftime("%Y-%m-%d %H:%M")) == ["2023-07-12 12:30", "2019-06-07 12:30", "2016-01-08 13:30"])
    from backtest.fetch_ff_calendar import clean
    fake = pd.DataFrame({"DateTime": ["2024-03-08T00:00:00+03:30", "2024-03-08T17:00:00+03:30"],
                         "Currency": ["USD", "USD"], "Impact": ["High Impact Expected"] * 2,
                         "Event": ["Non-Farm Employment Change", "Average Hourly Earnings m/m"],
                         "Actual": ["275K", "0.1%"], "Forecast": ["198K", "0.2%"], "Previous": [None, None],
                         "Detail": ["Usual Effect: 'Actual' greater than 'Forecast' is good for currency;"] * 2})
    c = clean(fake)
    check("a timeless payrolls row gets 08:30 New York (13:30 UTC before the US switch)",
          set(c["utc"].dt.strftime("%H:%M")) == {"13:30"})

    rng = np.random.default_rng(3)
    times = pd.date_range("2016-01-04 13:30", periods=40, freq="7D", tz="UTC")
    ev = pd.DataFrame({"utc": times, "event": "X", "actual": rng.normal(0, 1, 40), "forecast": 0.0, "effect": 1})
    z1 = add_z(ev)
    ev2 = ev.copy()
    ev2.loc[39, "actual"] = 1e6
    z2 = add_z(ev2)
    check("z uses prior surprises only (changing the last release leaves earlier z unchanged)",
          bool(np.allclose(z1["z"].iloc[:39], z2["z"].iloc[:39], equal_nan=True)))
    check("no z before 12 prior releases", bool(z1["z"].iloc[:12].isna().all() and z1["z"].iloc[12:].notna().all()))
    ones = pd.DataFrame({"utc": times, "event": "Y", "actual": np.r_[np.tile([1.0, -1.0], 10), 1000.0,
                                                                       np.tile([1.0, -1.0], 10)[:19]],
                         "forecast": 0.0, "effect": 1})
    zo = add_z(ones)
    check("one 1000-sigma outlier does not shrink the next release's z (robust scale)",
          bool(abs(abs(zo["z"].iloc[21]) - 1.2816) < 1e-9))

    # synthetic EURUSD minutes with planted behaviour after each release
    idx = pd.date_range("2016-01-04 00:00", "2016-10-30 00:00", freq="1min", tz="UTC")
    p = 1.10 * np.exp(np.cumsum(rng.normal(0, 1e-5, len(idx))))
    df = pd.DataFrame({"open": p, "high": p, "low": p, "close": p, "volume": 0.0}, index=idx.tz_convert(NY_TZ))
    z1 = z1.iloc[12:].copy()
    z1["S"] = np.where(np.arange(len(z1)) % 2 == 0, 2.0, -2.0)
    rel = z1[["utc", "S"]].assign(n_events=1, events="X", family="growth")
    drift = 20e-4                                               # 20 bp over the hour after entry
    jump = 30e-4                                                # 30 bp in the release minute
    pl = df.copy()
    pos = pl.index.tz_convert("UTC")
    for _, r in rel.iterrows():
        d = -np.sign(r["S"])                                    # dollar-good -> EURUSD down
        i0 = pos.get_loc(r["utc"])
        f = np.ones(len(pl))
        f[i0 + 1:] *= np.exp(d * jump)                         # the jump completes by t0+1
        ramp = np.clip((np.arange(len(pl)) - (i0 + 1)) / 60.0, 0, 1)
        f *= np.exp(d * drift * ramp)                           # then a 60-minute drift
        for col in ("open", "high", "low", "close"):
            pl[col] = pl[col].to_numpy() * f
    m = measure(rel, Prices(pl), -1, 0.0)
    c1 = cell(m, 1, 60, net=False)
    check(f"planted 20 bp post-entry drift is recovered ({c1['mean_bp']:+.1f} bp)", abs(c1["mean_bp"] - 20) < 2)
    sr = float(np.mean(np.sign(m["S"]) * -1 * m["reaction"])) * 1e4
    check(f"planted 30 bp first-minute jump shows in the reaction ({sr:+.1f} bp) and NOT in the trade", abs(sr - 30) < 3)
    pl2 = df.copy()
    for _, r in rel.iterrows():
        d = -np.sign(r["S"])
        i0 = pos.get_loc(r["utc"])
        f = np.ones(len(pl2))
        f[i0 + 1:] *= np.exp(d * jump)
        for col in ("open", "high", "low", "close"):
            pl2[col] = pl2[col].to_numpy() * f
    m2 = measure(rel, Prices(pl2), -1, 0.0)
    c2 = cell(m2, 1, 60, net=False)
    check(f"jump-only market: the tradeable drift is ~0 ({c2['mean_bp']:+.2f} bp)", abs(c2["mean_bp"]) < 1.5)
    m3 = measure(rel, Prices(pl), -1, 0.0002)
    c3 = cell(m3, 1, 60, net=True)
    check("2-pip round trip is subtracted (net = gross - 0.0002/price)", abs((c1["mean_bp"] - c3["mean_bp"]) - 0.0002 / 1.1 * 1e4) < 0.3)
    print(f"\nselftest: {'ALL PASS' if fails == 0 else f'{fails} FAILED'}")
    if fails:
        sys.exit(1)


# ----------------------------------------------------------------------------------------------
# report
# ----------------------------------------------------------------------------------------------
def report() -> None:
    ev = add_z(load_events(EVENTS_FILE))
    rel = releases(ev)
    rel = rel[(rel["utc"] >= DEV[0]) & (rel["utc"] < HOLDOUT[1])].reset_index(drop=True)
    print(f"release minutes with a valid z, 2015-01 -> 2025-04: {len(rel)}; |S| >= {Z_MIN}: "
          f"{int((rel['S'].abs() >= Z_MIN).sum())} (holdout {int(((rel['S'].abs() >= Z_MIN) & (rel['utc'] >= HOLDOUT[0])).sum())})")
    res = {}
    for name, (path, sign, cost) in MARKETS.items():
        m = measure(rel, Prices(load_cached_1m(path)), sign, cost)
        m.to_csv(f"{LOCAL}/v032_{name}_releases.csv", index=False)
        res[name] = m
    eur = res["EURUSD"]
    ho, dv = in_era(eur, HOLDOUT), in_era(eur, DEV)
    prim = cell(ho, ENTRY_MIN, HOLD_MIN)
    ok = prim["mean_bp"] > 0 and prim["t"] >= PASS_T
    print("\n" + "=" * 96 + "\nPRIMARY: EURUSD, |S| >= 1, trade the surprise direction from 1 minute after the "
          "release, hold 60 min,\n2-pip round trip, holdout 2021-01 -> 2025-04\n" + "=" * 96)
    print(f"  {fmt(prim)}  -> {'PASS' if ok else 'FAIL'} (needs mean > 0 and date-clustered t >= {PASS_T})")
    g = cell(ho, ENTRY_MIN, HOLD_MIN, net=False)
    print(f"  gross (no cost): {fmt(g)};  development 2015-2020 net: {fmt(cell(dv, ENTRY_MIN, HOLD_MIN))}")

    print("\nSECONDARY (labelled; cannot rescue the primary)")
    for era_name, era in (("holdout", HOLDOUT), ("dev 2015-20", DEV)):
        print(f"\n  first-minute reaction in the surprise direction ({era_name}), bp:")
        for name, m in res.items():
            if MARKETS[name][1] == 0:
                continue
            e = in_era(m, era)
            keep = e["S"].abs() >= Z_MIN
            x = (e["dir_surprise"] * e["reaction"])[keep].to_numpy()
            mu, t, n = cluster_t(x[np.isfinite(x)], e["date"][keep].to_numpy()[np.isfinite(x)])
            print(f"    {name}: n {n}  mean {mu * 1e4:+.2f} bp  t {t:+.2f}")
    for direction in ("surprise", "momentum"):
        print(f"\n  tradeable drift, direction = {direction}, holdout, net of costs:")
        for name, m in res.items():
            if direction == "surprise" and MARKETS[name][1] == 0:
                continue
            e = in_era(m, HOLDOUT)
            for k in ENTRIES:
                parts = [f"+{h}{'m' if h != 'close' else ''}: {cell(e, k, h, direction)['mean_bp']:+6.2f} bp "
                         f"(t {cell(e, k, h, direction)['t']:+5.2f})" for h in HOLDS]
                print(f"    {name:6s} entry +{k}m  " + "  ".join(parts))
    print("\n  EURUSD primary cell by |S| bucket, family and year (holdout, net):")
    for lo, hi in ((1, 2), (2, 99)):
        b = ho[(ho["S"].abs() >= lo) & (ho["S"].abs() < hi)]
        print(f"    |S| {lo}-{hi if hi < 99 else 'inf'}: {fmt(cell(b, 1, 60))}")
    for fam in ("jobs", "inflation", "growth", "fed", "oil", "mixed"):
        print(f"    {fam:9s}: {fmt(cell(ho[ho['family'] == fam], 1, 60))}")
    for y in range(2015, 2026):
        e = eur[pd.DatetimeIndex(eur["utc"]).year == y]
        print(f"    {y}: {fmt(cell(e, 1, 60))}")
    print("\n  EURUSD fade (against the first-minute reaction), holdout, entry +1m: " +
          "  ".join(f"+{h}: {-cell(ho, 1, h, 'momentum', net=False)['mean_bp'] - 1e4 * ho['cost_e1'].mean():+6.2f} bp"
                    for h in HOLDS))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clockcheck", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.clockcheck:
        clockcheck()
    if a.selftest:
        selftest()
    if a.report:
        report()


if __name__ == "__main__":
    main()
