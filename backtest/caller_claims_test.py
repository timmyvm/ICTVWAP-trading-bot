"""
v0.37-exp — the Discord caller's explicit statistical claims, tested on QQQ history (DEVLOG v0.37-exp).

  H1  "No-news Mondays pump" (80 %, "99 % chance"): Mondays with no high-impact US release 08:00-10:30 ET
  H2  "OPEX week: favour bearish Wed-Fri" (90 %): Wednesday open -> monthly-expiry close
  H3  "Classic 1300": on down mornings the session low prints 12:50-13:29 ET and the close is above 13:30
  H4  "Month-end candles close to the top": last session of the month, close in the top quarter of its range;
      and his trade, 13:00 -> close on that session
  H5  "Lower VIX is bullish": VIX opening below its prior close -> QQQ open -> close
  H6  Same-calendar-date "odds" (the inferred method of his paid indicator): >= 7 of the previous 10 years
      up (down) on this calendar date -> call this session up (down), close to close
  C1  His same-day gain claims that name a QQQ contract, against the best gain any entry/exit pair allowed
      that session (Black-Scholes on the underlying, entry at sigma x1, exit at sigma x1.5)
  C2  "No losses" records against his own stop-outs in the frozen alert table (descriptive)

Verdict per H: SUPPORTED when the observed rate reaches the claimed rate minus 10 points AND beats the
matching base rate at one-sided p < 0.05 / 6 (H4b, H5: the difference has Welch t >= 2.64, the same level).

Data (local, gitignored): Yahoo QQQ and ^VIX daily (fetch_yahoo_intraday.py), HistData NSXUSD 1m, the
ForexFactory USD high-impact calendar (to 2025-03), and for C1/C2 the v0.35 trade table and claims list.
Aggregates only are printed (the repository is public).

  python3 backtest/caller_claims_test.py --selftest
  python3 backtest/caller_claims_test.py --report
"""

import argparse
import json
import math
import os
import re
import sys
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
LOCAL = "backtest/data_cache/local"
NY = "America/New_York"
P_BAR = 0.05 / 6
T_BAR = 2.64                                   # two-sided-normal equivalent of one-sided p 0.05/6
MARGIN = 0.10
H_CLAIMED = {"H1": 0.80, "H2": 0.90, "H3": 0.50, "H4a": 0.50, "H6": 0.70}
ERA_START = date(2015, 1, 1)
CALLER_ERA = date(2024, 12, 1)


# ---------------------------------------------------------------------------------------------------
# statistics
# ---------------------------------------------------------------------------------------------------
def phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def two_prop_p(k1: int, n1: int, k2: int, n2: int) -> float:
    """One-sided p that rate 1 exceeds rate 2 (pooled z)."""
    if min(n1, n2) == 0:
        return float("nan")
    p = (k1 + k2) / (n1 + n2)
    se = math.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    return 1.0 - phi((k1 / n1 - k2 / n2) / se) if se > 0 else float("nan")


def expected_rate_p(hits: np.ndarray, base: np.ndarray) -> float:
    """One-sided p that hits exceed their per-trial expected rates (normal approximation)."""
    var = float((base * (1 - base)).sum())
    return 1.0 - phi((float(hits.sum()) - float(base.sum())) / math.sqrt(var)) if var > 0 else float("nan")


def welch_t(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 3 or len(b) < 3:
        return float("nan")
    se = math.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    return (a.mean() - b.mean()) / se if se > 0 else float("nan")


def wilson(k: int, n: int) -> Tuple[float, float]:
    if n == 0:
        return float("nan"), float("nan")
    z, p = 1.96, k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return c - h, c + h


def verdict(rate: float, claimed: float, p: float) -> str:
    return "SUPPORTED" if rate >= claimed - MARGIN and p < P_BAR else "NOT SUPPORTED"


# ---------------------------------------------------------------------------------------------------
# calendar helpers
# ---------------------------------------------------------------------------------------------------
def opex_day(year: int, month: int, sessions: pd.DatetimeIndex) -> Optional[pd.Timestamp]:
    """Third Friday, or the previous session when that Friday is a market holiday."""
    d = date(year, month, 15)
    third_friday = d + timedelta(days=(4 - d.weekday()) % 7)
    prior = sessions[sessions.date <= third_friday]
    return prior[-1] if len(prior) else None


def month_ends(sessions: pd.DatetimeIndex) -> pd.DatetimeIndex:
    s = pd.Series(sessions, index=sessions)
    return pd.DatetimeIndex(s.groupby([sessions.year, sessions.month]).max().to_numpy())


def same_date_session(sessions: pd.DatetimeIndex, year: int, month: int, day: int) -> Optional[pd.Timestamp]:
    """First session on or after (year, month, day); 29 Feb falls back to 1 Mar in other years."""
    try:
        d = date(year, month, day)
    except ValueError:
        d = date(year, 3, 1)
    after = sessions[sessions.date >= d]
    return after[0] if len(after) and (after[0].date() - d).days <= 4 else None


# ---------------------------------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------------------------------
def load_daily(sym: str) -> pd.DataFrame:
    from backtest.fetch_yahoo_intraday import load
    d = load(sym, "1d")
    assert d is not None, f"fetch {sym} daily first"
    d.index = pd.DatetimeIndex(d.index.tz_localize(None).normalize())
    return d[~d.index.duplicated(keep="last")].sort_index()


def sanity(d: pd.DataFrame, name: str) -> None:
    r = np.log(d["c"]).diff().abs()
    big = r[r > 0.15]
    assert (d["h"] >= d["l"]).all(), f"{name}: high below low"
    print(f"  {name}: {len(d)} sessions {d.index[0].date()} -> {d.index[-1].date()}; "
          f"close-to-close moves above 15 %: {len(big)}")


def load_nsx_sessions(lo: str = "2014-12-01", hi: str = "2026-10-31") -> Dict[date, pd.DataFrame]:
    raw = pd.read_csv(f"{LOCAL}/nas100_histdata_1m_2015_2026.csv.gz", usecols=["timestamp", "open", "high", "low", "close"])
    t0, t1 = int(pd.Timestamp(lo, tz="UTC").timestamp()), int(pd.Timestamp(hi, tz="UTC").timestamp())
    raw = raw[(raw["timestamp"] >= t0) & (raw["timestamp"] < t1)]
    idx = pd.DatetimeIndex(pd.to_datetime(raw["timestamp"].to_numpy(), unit="s", utc=True)).tz_convert(NY)
    df = pd.DataFrame({"o": raw["open"].to_numpy(), "h": raw["high"].to_numpy(), "l": raw["low"].to_numpy(),
                       "c": raw["close"].to_numpy()}, index=idx)
    df = df[(df.index.time >= time(9, 30)) & (df.index.time < time(16, 0))]
    return {d: g for d, g in df.groupby(df.index.date) if len(g) >= 370}


def news_mondays(lo: date, hi: date) -> set:
    ff = pd.read_csv(f"{LOCAL}/ff_usd_events.csv")
    t = pd.to_datetime(ff["timestamp"], unit="s", utc=True).dt.tz_convert(NY)
    hm = t.dt.hour * 60 + t.dt.minute
    m = (t.dt.weekday == 0) & (hm >= 8 * 60) & (hm <= 10 * 60 + 30)
    return {x for x in t[m].dt.date if lo <= x <= hi}


# ---------------------------------------------------------------------------------------------------
# hypotheses (each returns a dict of aggregates)
# ---------------------------------------------------------------------------------------------------
def h1(q: pd.DataFrame, news: set, lo: date, hi: date) -> dict:
    s = q[(q.index.date >= lo) & (q.index.date <= hi)].copy()
    s["oc_up"] = s["c"] > s["o"]
    s["cc_up"] = s["c"] > s["c"].shift(1)
    mon = s[(s.index.weekday == 0)]
    quiet = mon[[d.date() not in news for d in mon.index]]
    rest = s[~s.index.isin(quiet.index)]
    k1, n1, k2, n2 = int(quiet["oc_up"].sum()), len(quiet), int(rest["oc_up"].sum()), len(rest)
    return {"n": n1, "rate": k1 / n1, "base": k2 / n2, "p": two_prop_p(k1, n1, k2, n2), "ci": wilson(k1, n1),
            "cc_rate": float(quiet["cc_up"].mean()), "n_news": len(mon) - n1}


def h2(q: pd.DataFrame, lo: date, hi: date) -> dict:
    s = q[(q.index.date >= lo) & (q.index.date <= hi)]
    sess = s.index
    rows = []
    for (y, wk), g in s.groupby([sess.isocalendar().year, sess.isocalendar().week]):
        g_idx = g.index
        mid = g_idx[g_idx.weekday >= 2]
        if len(mid) < 2:
            continue
        ox = opex_day(g_idx[0].year, g_idx[0].month, sess)
        if ox is None:
            continue
        is_opex = ox in set(g_idx) and ox.weekday() >= 2
        end = ox if is_opex else mid[-1]
        if not is_opex and mid[-1].weekday() != 4:
            continue
        rows.append({"opex": is_opex, "down": float(g.loc[end, "c"]) < float(g.loc[mid[0], "o"]),
                     "ret": math.log(float(g.loc[end, "c"]) / float(g.loc[mid[0], "o"]))})
    w = pd.DataFrame(rows)
    o, n = w[w["opex"]], w[~w["opex"]]
    k1, n1, k2, n2 = int(o["down"].sum()), len(o), int(n["down"].sum()), len(n)
    return {"n": n1, "rate": k1 / n1, "base": k2 / n2, "p": two_prop_p(k1, n1, k2, n2), "ci": wilson(k1, n1),
            "mean_ret": float(o["ret"].mean()), "base_ret": float(n["ret"].mean())}


def h3(nsx: Dict[date, pd.DataFrame], lo: date, hi: date) -> dict:
    down, up = [], []
    for d, g in nsx.items():
        if not (lo <= d <= hi) or g.index[-1].time() < time(15, 59):
            continue
        o = float(g["o"].iloc[0])
        noon = g[g.index.time <= time(11, 59)]["c"].iloc[-1]
        low_t = g["l"].idxmin().time()
        in_win = time(12, 50) <= low_t <= time(13, 29)
        c1330 = g[g.index.time <= time(13, 29)]["c"].iloc[-1]
        hit = in_win and float(g["c"].iloc[-1]) > float(c1330)
        (down if noon < o else up).append((hit, in_win))
    dn, upa = np.array(down), np.array(up)
    k1, n1, k2, n2 = int(dn[:, 0].sum()), len(dn), int(upa[:, 0].sum()), len(upa)
    return {"n": n1, "rate": k1 / n1, "base": k2 / n2, "p": two_prop_p(k1, n1, k2, n2), "ci": wilson(k1, n1),
            "low_in_window": float(dn[:, 1].mean()), "uniform": 40 / 390}


def h4(q: pd.DataFrame, nsx: Dict[date, pd.DataFrame], lo: date, hi: date) -> dict:
    s = q[(q.index.date >= lo) & (q.index.date <= hi)].copy()
    rng = (s["h"] - s["l"]).replace(0, np.nan)
    s["top"] = ((s["c"] - s["l"]) / rng) >= 0.75
    eom = set(month_ends(s.index))
    e, r = s[s.index.isin(eom)], s[~s.index.isin(eom)]
    k1, n1, k2, n2 = int(e["top"].sum()), len(e), int(r["top"].sum()), len(r)
    pm_e, pm_r = [], []
    for d, g in nsx.items():
        if not (lo <= d <= hi) or g.index[-1].time() < time(15, 59):
            continue
        a = g[g.index.time <= time(12, 59)]["c"]
        if not len(a):
            continue
        x = math.log(float(g["c"].iloc[-1]) / float(a.iloc[-1]))
        (pm_e if pd.Timestamp(d) in eom else pm_r).append(x)
    a_, b_ = np.array(pm_e), np.array(pm_r)
    return {"n": n1, "rate": k1 / n1, "base": k2 / n2, "p": two_prop_p(k1, n1, k2, n2), "ci": wilson(k1, n1),
            "pm_n": len(a_), "pm_mean": float(a_.mean()), "pm_base": float(b_.mean()), "pm_t": welch_t(a_, b_)}


def h5(q: pd.DataFrame, vix: pd.DataFrame, lo: date, hi: date) -> dict:
    s = q[(q.index.date >= lo) & (q.index.date <= hi)].copy()
    v = vix.reindex(s.index)
    s["vix_down_open"] = v["o"] < vix["c"].shift(1).reindex(s.index)
    s = s[v["o"].notna()]
    s["oc"] = np.log(s["c"] / s["o"])
    a, b = s[s["vix_down_open"]]["oc"].to_numpy(), s[~s["vix_down_open"]]["oc"].to_numpy()
    return {"n": len(a), "n_other": len(b), "mean": float(a.mean()), "base_mean": float(b.mean()), "t": welch_t(a, b),
            "hit": float((a > 0).mean()), "base_hit": float((b > 0).mean())}


def h6(q: pd.DataFrame, lo: date, hi: date) -> dict:
    sess = q.index
    up = (q["c"] > q["c"].shift(1))
    ret = np.log(q["c"] / q["c"].shift(1))
    hits, base, signed = [], [], []
    for d in sess[(sess.date >= lo) & (sess.date <= hi)]:
        past = [same_date_session(sess, d.year - k, d.month, d.day) for k in range(1, 11)]
        past = [p for p in past if p is not None and not pd.isna(up.get(p))]
        if len(past) < 10:
            continue
        odds_up = float(np.mean([bool(up[p]) for p in past]))
        if 0.3 < odds_up < 0.7:
            continue
        call_up = odds_up >= 0.7
        prior = up[(sess < d) & (sess >= d - pd.Timedelta(days=3653))]
        p_up = float(prior.mean())
        hits.append(bool(up[d]) == call_up)
        base.append(p_up if call_up else 1 - p_up)
        signed.append(float(ret[d]) * (1 if call_up else -1))
    h, b, sg = np.array(hits), np.array(base), np.array(signed)
    t = float(sg.mean() / (sg.std(ddof=1) / math.sqrt(len(sg)))) if len(sg) > 2 else float("nan")
    return {"n": len(h), "rate": float(h.mean()), "base": float(b.mean()), "p": expected_rate_p(h, b),
            "ci": wilson(int(h.sum()), len(h)), "signed_mean": float(sg.mean()), "signed_t": t}


# ---------------------------------------------------------------------------------------------------
# C1: same-day gain claims that name a QQQ contract
# ---------------------------------------------------------------------------------------------------
def best_gain(bars: pd.DataFrame, cp: str, k: float, sigma: float, close_ts: pd.Timestamp) -> float:
    """The largest exit/entry - 1 over any entry minute t1 <= exit minute t2 in the session: entry priced at
    the bar's unfavourable extreme with sigma, exit at the favourable extreme with 1.5 x sigma."""
    from backtest.options_signal_fallback import bs, t_mid
    t = t_mid(bars.index, close_ts)
    fav, unf = (bars["h"], bars["l"]) if cp == "C" else (bars["l"], bars["h"])
    entry = np.maximum(bs(cp, unf, k, t, sigma), 0.01)
    exit_ = bs(cp, fav, k, t, 1.5 * sigma)
    run_min = np.minimum.accumulate(entry)
    return float(np.max(exit_ / run_min)) - 1.0


def claim_session(posted_utc: str, paraphrase: str, sessions: List[date]) -> Optional[date]:
    m = re.search(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", paraphrase)
    if m:
        d = date(int(m.group(3)), int(m.group(1)), int(m.group(2)))
        return d if d in sessions else None
    t = pd.Timestamp(posted_utc).tz_convert(NY)
    d = t.date()
    if t.time() < time(9, 30) or d not in sessions:
        prior = [s for s in sessions if s < d or (s == d and t.time() >= time(9, 30))]
        return prior[-1] if prior else None
    return d


def claimed_gain(numbers: List[float]) -> Optional[float]:
    """A pair of small prices -> exit/entry - 1; otherwise the largest % figure."""
    small = [x for x in numbers if 0 < x < 10]
    if len(small) >= 2:
        return small[1] / small[0] - 1.0
    pct = [x for x in numbers if x >= 10]
    return max(pct) / 100.0 if pct else None


# ---------------------------------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------------------------------
def fmt_rate(name: str, r: dict, claimed: float) -> str:
    lo_, hi_ = r["ci"]
    return (f"  {name:4s} n {r['n']:4d}  rate {100 * r['rate']:5.1f}% (95% CI {100 * lo_:.0f}-{100 * hi_:.0f}%)  "
            f"claimed {100 * claimed:.0f}%  base {100 * r['base']:5.1f}%  p {r['p']:.4f}  -> {verdict(r['rate'], claimed, r['p'])}")


def report() -> int:
    q, vix = load_daily("QQQ"), load_daily("^VIX")
    print("=" * 100 + "\nDATA\n" + "=" * 100)
    sanity(q, "QQQ daily")
    sanity(vix, "VIX daily")
    nsx = load_nsx_sessions()
    print(f"  NSXUSD full sessions: {len(nsx)}, {min(nsx)} -> {max(nsx)}")
    end_q, end_n = q.index[-1].date(), max(nsx)
    ff_end = date(2025, 3, 31)
    news = news_mondays(ERA_START, ff_end)
    print(f"  high-impact news Mondays (08:00-10:30 ET), {ERA_START} -> {ff_end}: {len(news)}")

    print("\n" + "=" * 100 + "\nCLAIMS H1-H6 (primary: full span; context: the caller's era from 2024-12)\n" + "=" * 100)
    out = {}
    for era, lo, cap in (("full", ERA_START, None), ("caller", CALLER_ERA, None)):
        print(f"--- {era} span")
        r1 = h1(q, news if era == "full" else set(), lo, ff_end if era == "full" else end_q)
        if era == "caller":
            print(f"  H1   (no calendar after 2025-03: every Monday counts as no-news here) n {r1['n']}, "
                  f"open->close up {100 * r1['rate']:.1f}% vs other sessions {100 * r1['base']:.1f}%")
        else:
            print(fmt_rate("H1", r1, H_CLAIMED["H1"]) + f"   (news Mondays excluded {r1['n_news']}; "
                  f"close-to-close up {100 * r1['cc_rate']:.1f}%)")
        r2 = h2(q, lo, end_q)
        print(fmt_rate("H2", r2, H_CLAIMED["H2"]) + f"   (mean Wed->expiry {1e4 * r2['mean_ret']:+.0f} bp vs "
              f"{1e4 * r2['base_ret']:+.0f} bp in other weeks' Wed->Fri)")
        r3 = h3(nsx, lo, end_n)
        print(fmt_rate("H3", r3, H_CLAIMED["H3"]) + f"   (low in 12:50-13:29 alone {100 * r3['low_in_window']:.1f}%, "
              f"uniform {100 * r3['uniform']:.1f}%)")
        r4 = h4(q, nsx, lo, min(end_q, end_n))
        print(fmt_rate("H4a", r4, H_CLAIMED["H4a"]))
        print(f"  H4b  13:00 -> close on month-end sessions: n {r4['pm_n']}, mean {1e4 * r4['pm_mean']:+.1f} bp vs "
              f"{1e4 * r4['pm_base']:+.1f} bp on other sessions, Welch t {r4['pm_t']:+.2f} -> "
              f"{'SUPPORTED' if r4['pm_t'] >= T_BAR else 'NOT SUPPORTED'}")
        r5 = h5(q, vix, lo, end_q)
        print(f"  H5   VIX opens below its prior close: n {r5['n']} (other {r5['n_other']}); QQQ open->close "
              f"{1e4 * r5['mean']:+.1f} bp vs {1e4 * r5['base_mean']:+.1f} bp, Welch t {r5['t']:+.2f}; up "
              f"{100 * r5['hit']:.1f}% vs {100 * r5['base_hit']:.1f}% -> {'SUPPORTED' if r5['t'] >= T_BAR else 'NOT SUPPORTED'}")
        r6 = h6(q, max(lo, date(2016, 1, 1)), end_q)
        print(fmt_rate("H6", r6, H_CLAIMED["H6"]) + f"   (signed close-to-close {1e4 * r6['signed_mean']:+.1f} bp, "
              f"t {r6['signed_t']:+.2f})")
        out[era] = (r1, r2, r3, r4, r5, r6)

    print("\n" + "=" * 100 + "\nC1: same-day gain claims naming a QQQ contract vs the best possible modelled gain\n" + "=" * 100)
    from backtest.options_signal_fallback import Underlying
    ub = Underlying()
    sessions = ub.sessions()
    claims = [json.loads(x) for x in open(f"{LOCAL}/discord/v036/claims.jsonl", encoding="utf-8") if x.strip()]
    sig = sigma_by_month()
    n_ok, n_imp, skipped, ratios = 0, 0, {}, []
    for c in claims:
        if c["type"] != "trade_gain" or not c.get("contract"):
            continue
        legs = re.findall(r"(\d+(?:\.\d+)?)([cp])", c["contract"].lower())
        g = claimed_gain([float(x) for x in c["numbers"]])
        d = claim_session(c["posted_utc"], c["paraphrase"], sessions)
        if not legs or g is None or d is None:
            skipped["unparsed or no session"] = skipped.get("unparsed or no session", 0) + 1
            continue
        b = ub.day(d)
        if b is None:
            skipped["no underlying bars"] = skipped.get("no underlying bars", 0) + 1
            continue
        s0 = float(b["o"].iloc[0])
        legs = [(float(k), cp.upper()) for k, cp in legs if abs(float(k) / s0 - 1) <= 0.03]
        if not legs:
            skipped["not a QQQ strike that day"] = skipped.get("not a QQQ strike that day", 0) + 1
            continue
        sigma = nearest(sig, d.strftime("%Y-%m"))
        bound = max(best_gain(b, cp, k, sigma, ub.close_ts[d]) for k, cp in legs)
        n_ok += 1
        n_imp += (1 + g) > 1.2 * (1 + bound)
        ratios.append((1 + g) / (1 + bound))
    print(f"  checked {n_ok}; above 1.2 x the best possible gain: {n_imp}; skipped {skipped}")
    if ratios:
        print(f"  (1 + claim) / (1 + best possible): median {np.median(ratios):.2f}, max {max(ratios):.2f}")

    print("\n" + "=" * 100 + "\nC2: 'no losses' records vs his own stop-outs in the alert table (descriptive)\n" + "=" * 100)
    trades = [json.loads(x) for x in open(f"{LOCAL}/discord/v035/trades_frozen.jsonl", encoding="utf-8") if x.strip()]
    fb = f"{LOCAL}/discord/v035/fallback_per_trade.csv"
    a1 = pd.read_csv(fb) if os.path.exists(fb) else pd.DataFrame()
    for label, lo, hi in (("'no losses this year' (said 2025-11-20)", date(2025, 1, 1), date(2025, 11, 20)),
                          ("'no losses in seven months' (said 2026-09-04)", date(2026, 2, 4), date(2026, 9, 4))):
        tw = [t for t in trades if lo <= date.fromisoformat(t["date"]) <= hi]
        stops = sum(any(e["type"] == "STOPPED" for e in t["events"]) for t in tw)
        against = 0
        if len(a1):
            w = a1[(a1["status"] == "ok") & a1["date"].between(lo.isoformat(), hi.isoformat())]
            against = int((w["r"] < 0).sum())
        print(f"  {label}: tracked trades {len(tw)}; with his own 'stopped' post {stops}; "
              f"QQQ moved against him over his hold {against}")
    v = out["full"]
    print("\n" + "=" * 100 + "\nVERDICTS (full span)\n" + "=" * 100)
    for name, r in zip(("H1", "H2", "H3", "H4a", "H6"), (v[0], v[1], v[2], v[3], v[5])):
        print(f"  {name}: {verdict(r['rate'], H_CLAIMED[name], r['p'])}")
    print(f"  H4b: {'SUPPORTED' if v[3]['pm_t'] >= T_BAR else 'NOT SUPPORTED'}")
    print(f"  H5: {'SUPPORTED' if v[4]['t'] >= T_BAR else 'NOT SUPPORTED'}")
    print("CLAIMS_REPORT_DONE")
    return 0


def sigma_by_month() -> Dict[str, float]:
    """The v0.35 Addendum A3 month medians of the sigma solved from his stated entries."""
    from backtest.options_signal_fallback import Underlying, solve_sigma, t_mid, typical
    from backtest.options_signal_audit import NY as _NY
    ub = Underlying()
    out: Dict[str, List[float]] = {}
    for x in open(f"{LOCAL}/discord/v035/trades_frozen.jsonl", encoding="utf-8"):
        t = json.loads(x)
        if not t.get("stated_entry"):
            continue
        d = date.fromisoformat(t["date"])
        b = ub.day(d)
        if b is None:
            continue
        st = pd.Timestamp(t.get("stated_entry_utc") or t["announce_utc"]).tz_convert(_NY).floor("min")
        if st not in b.index:
            continue
        s = float(typical(b.loc[[st]]).iloc[0])
        sv = solve_sigma(t["cp"], s, t["strike"], float(t_mid(pd.DatetimeIndex([st]), ub.close_ts[d])[0]),
                         float(t["stated_entry"]))
        if sv is not None:
            out.setdefault(t["date"][:7], []).append(sv)
    return {m: float(np.median(v)) for m, v in out.items()}


def nearest(med: Dict[str, float], m: str) -> float:
    if m in med:
        return med[m]
    key = lambda x: abs((int(x[:4]) * 12 + int(x[5:])) - (int(m[:4]) * 12 + int(m[5:])))
    return med[min(med, key=key)]


# ---------------------------------------------------------------------------------------------------
# self-tests
# ---------------------------------------------------------------------------------------------------
def selftest() -> int:
    ok = True

    def check(name: str, cond: bool) -> None:
        nonlocal ok
        ok &= bool(cond)
        print(f"{'PASS' if cond else 'FAIL'}  {name}")

    bdays = pd.bdate_range("2025-01-01", "2025-12-31")
    sessions = bdays[~bdays.isin([pd.Timestamp("2025-04-18")])]            # Good Friday closed
    check("OPEX = third Friday", opex_day(2025, 3, sessions) == pd.Timestamp("2025-03-21"))
    check("OPEX on a holiday -> the previous session", opex_day(2025, 4, sessions) == pd.Timestamp("2025-04-17"))
    me = month_ends(sessions)
    check("month-end = last session of the month", pd.Timestamp("2025-01-31") in set(me) and pd.Timestamp("2025-02-28") in set(me))
    check("same date on a weekend -> next session", same_date_session(sessions, 2025, 3, 1) == pd.Timestamp("2025-03-03"))
    check("29 Feb in a non-leap year -> 1 Mar", same_date_session(sessions, 2025, 2, 29) == pd.Timestamp("2025-03-03"))
    check("two-proportion p: equal rates -> 0.5", abs(two_prop_p(50, 100, 50, 100) - 0.5) < 1e-12)
    check("two-proportion p: 80/100 vs 50/100 -> tiny", two_prop_p(80, 100, 50, 100) < 1e-5)
    check("verdict needs both the level and the p", verdict(0.71, 0.80, 0.001) == "SUPPORTED"
          and verdict(0.69, 0.80, 0.001) == "NOT SUPPORTED" and verdict(0.95, 0.80, 0.2) == "NOT SUPPORTED")
    check("claimed gain from a price pair", abs(claimed_gain([0.44, 2.22]) - (2.22 / 0.44 - 1)) < 1e-12)
    check("claimed gain from a % figure", abs(claimed_gain([250]) - 2.5) < 1e-12)
    sess = [date(2025, 9, 5), date(2025, 9, 8), date(2025, 9, 9)]
    check("a pre-open claim refers to the previous session",
          claim_session("2025-09-09T12:00:00+00:00", "x", sess) == date(2025, 9, 8))
    check("an explicit m/d/yyyy date wins", claim_session("2025-09-09T12:00:00+00:00", "9/5/2025 calls", sess) == date(2025, 9, 5))
    idx = pd.date_range("2025-09-08 09:30", "2025-09-08 15:59", freq="1min", tz=NY)
    path = 500 + np.sin(np.linspace(0, 6, len(idx)))
    b = pd.DataFrame({"o": path, "h": path + 0.05, "l": path - 0.05, "c": path}, index=idx)
    from backtest.options_signal_fallback import bs, t_mid
    close = pd.Timestamp("2025-09-08 16:00", tz=NY)
    g = best_gain(b, "C", 500.0, 0.10, close)
    t = t_mid(b.index, close)
    any_pair = float(bs("C", b["h"].iloc[60:61], 500.0, t[60:61], 0.15)[0] / max(bs("C", b["l"].iloc[10:11], 500.0, t[10:11], 0.10)[0], 0.01)) - 1
    check("best possible gain >= the gain of any entry/exit pair", g >= any_pair - 1e-12)
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.report:
        return report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
