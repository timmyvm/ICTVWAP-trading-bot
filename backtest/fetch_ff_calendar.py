"""
ForexFactory calendar archive -> clean USD high-impact events with exact UTC release times (v0.32-exp).

Source: the Hugging Face dataset Ehsanrs2/Forex_Factory_Calendar, file forex_factory_cache.csv
(83,427 rows, 2007-01 -> 2025-04-07; columns DateTime, Currency, Impact, Event, Actual, Forecast,
Previous, Detail). Two scraper defects, both found by checking release times that are public facts
(payrolls/CPI/claims 08:30 ET, ISM 10:00 ET, FOMC 14:00 ET, consumer credit 15:00 ET):

1. Rows that share a release minute with the row above them on ForexFactory (payrolls, the
   unemployment rate and earnings all at 08:30) lost their time: the archive stamps them 00:00:00
   local. Their release time is restored from the official US release schedule (SCHEDULE_ET). The
   table is checked against the same events' rows whose time survived (consistency() prints the share
   that match, by event). Philly Fed is left out: it moved from 10:00 to 08:30 inside the window, so its
   timeless rows are dropped.
2. Timestamps carry Tehran offsets, and the +04:30 summer offset is still attached after Iran
   abolished daylight saving (last period ended 21 Sep 2022). The wall clock is right and the label
   is not: from 22 Sep 2022 every row is read at +03:30.

Rows stamped 23:59:59 are all-day/tentative and are dropped. The output is re-loaded through
load_events() before the script reports success (CLAUDE.md: validate the saved artifact).

  python3 backtest/fetch_ff_calendar.py            # download if missing, clean, save, re-load
"""

import os
import re
import sys
import urllib.request

import numpy as np
import pandas as pd

URL = "https://huggingface.co/datasets/Ehsanrs2/Forex_Factory_Calendar/resolve/main/forex_factory_cache.csv"
RAW = "backtest/data_cache/local/ff_raw/forex_factory_cache.csv"
OUT = "backtest/data_cache/local/ff_usd_events.csv"
IRAN_NO_DST_FROM = pd.Timestamp("2022-09-22")
NY = "America/New_York"
SCHEDULE_ET = {   # official release times (New York), stable over 2015-2025 for these events
    "ADP Non-Farm Employment Change": "08:15",
    "Non-Farm Employment Change": "08:30", "Unemployment Rate": "08:30", "Average Hourly Earnings m/m": "08:30",
    "CPI m/m": "08:30", "CPI y/y": "08:30", "Core CPI m/m": "08:30", "PPI m/m": "08:30", "Core PPI m/m": "08:30",
    "Retail Sales m/m": "08:30", "Core Retail Sales m/m": "08:30", "Unemployment Claims": "08:30",
    "Advance GDP q/q": "08:30", "Prelim GDP q/q": "08:30", "Final GDP q/q": "08:30",
    "Core Durable Goods Orders m/m": "08:30", "Durable Goods Orders m/m": "08:30",
    "Core PCE Price Index m/m": "08:30", "Personal Spending m/m": "08:30", "Building Permits": "08:30",
    "Housing Starts": "08:30", "Trade Balance": "08:30", "Empire State Manufacturing Index": "08:30",
    "Employment Cost Index q/q": "08:30", "Prelim Unit Labor Costs q/q": "08:30",
    "Flash Manufacturing PMI": "09:45", "Flash Services PMI": "09:45", "Final Manufacturing PMI": "09:45",
    "Chicago PMI": "09:45",
    "ISM Manufacturing PMI": "10:00", "ISM Services PMI": "10:00", "CB Consumer Confidence": "10:00",
    "JOLTS Job Openings": "10:00", "Prelim UoM Consumer Sentiment": "10:00", "Revised UoM Consumer Sentiment": "10:00",
    "New Home Sales": "10:00", "Existing Home Sales": "10:00", "Pending Home Sales m/m": "10:00",
    "Crude Oil Inventories": "10:30",
    "Federal Funds Rate": "14:00", "FOMC Statement": "14:00",
}

EFFECT = {
    "'Actual' greater than 'Forecast' is good for currency": 1,
    "'Actual' less than 'Forecast' is good for currency": -1,
    "More hawkish than expected is good for currency": 1,
}
MULT = {"K": 1e3, "M": 1e6, "B": 1e9, "T": 1e12}


def parse_value(s: object) -> float:
    """'275K' -> 275000, '-0.1%' -> -0.1, '2.73T' -> 2.73e12; ranges, '<0.25%' and blanks -> NaN."""
    if not isinstance(s, str):
        return float("nan")
    s = s.strip()
    if not s or "|" in s or s[0] in "<>":
        return float("nan")
    mult = 1.0
    if s.endswith("%"):
        s = s[:-1]
    elif s[-1] in MULT:
        mult, s = MULT[s[-1]], s[:-1]
    try:
        return float(s) * mult
    except ValueError:
        return float("nan")


def to_utc(raw: pd.Series) -> tuple:
    """(UTC timestamps, wall-clock times) with the post-2022 Tehran offset repaired."""
    wall = pd.to_datetime(raw.str[:19], format="%Y-%m-%dT%H:%M:%S")
    sign = np.where(raw.str[19] == "-", -1, 1)
    off = pd.to_timedelta(raw.str[20:22].astype(int), unit="h") + pd.to_timedelta(raw.str[23:25].astype(int), unit="m")
    off = off * sign
    off = off.where(wall < IRAN_NO_DST_FROM, pd.Timedelta(hours=3, minutes=30))
    return (wall - off).dt.tz_localize("UTC"), wall


def clean(df: pd.DataFrame) -> pd.DataFrame:
    usd = df[(df["Currency"] == "USD") & (df["Impact"] == "High Impact Expected")].copy()
    utc, wall = to_utc(usd["DateTime"])
    usd["utc"], usd["wall"] = utc, wall
    t = wall.dt.strftime("%H:%M:%S")
    usd = usd[t != "23:59:59"].copy()
    usd["time_known"] = (usd["wall"].dt.strftime("%H:%M:%S") != "00:00:00")
    usd["actual"] = usd["Actual"].map(parse_value)
    usd["forecast"] = usd["Forecast"].map(parse_value)
    eff = usd["Detail"].fillna("").str.extract(r"Usual Effect: ([^;|]*)")[0].str.strip()
    usd["effect"] = eff.map(EFFECT).fillna(0).astype(int)

    # timeless rows get the official New York release time for their event
    fill = ~usd["time_known"] & usd["Event"].isin(SCHEDULE_ET)
    day = usd.loc[fill, "wall"].dt.strftime("%Y-%m-%d")
    hhmm = usd.loc[fill, "Event"].map(SCHEDULE_ET)
    usd.loc[fill, "utc"] = pd.to_datetime(day + " " + hhmm).dt.tz_localize(NY).dt.tz_convert("UTC")
    usd["time_source"] = np.where(usd["time_known"], "archive", np.where(fill, "canonical", "unknown"))
    usd = usd[usd["time_source"] != "unknown"]
    out = usd[["utc", "Event", "actual", "forecast", "effect", "time_source"]].rename(columns={"Event": "event"})
    return out.sort_values(["utc", "event"]).reset_index(drop=True)


def consistency(ev: pd.DataFrame, since: str = "2015-01-01") -> pd.DataFrame:
    """For rows whose time survived: the share that sit at the schedule time, by event."""
    k = ev[(ev["time_source"] == "archive") & (ev["utc"] >= pd.Timestamp(since, tz="UTC"))
           & ev["event"].isin(SCHEDULE_ET)].copy()
    k["hm"] = k["utc"].dt.tz_convert(NY).dt.strftime("%H:%M")
    k["ok"] = k["hm"] == k["event"].map(SCHEDULE_ET)
    return k.groupby("event")["ok"].agg(["count", "mean"]).sort_values("count", ascending=False)


def epoch_s(ts: pd.Series) -> np.ndarray:
    """CLAUDE.md: the subtraction idiom, never astype(int64)."""
    return np.asarray((pd.DatetimeIndex(ts) - pd.Timestamp(0, tz="UTC")) // pd.Timedelta(seconds=1), dtype=np.int64)


def load_events(path: str = OUT) -> pd.DataFrame:
    ev = pd.read_csv(path)
    ev["utc"] = pd.to_datetime(ev["timestamp"], unit="s", utc=True)
    return ev.drop(columns=["timestamp"])


def main() -> None:
    if not os.path.exists(RAW):
        os.makedirs(os.path.dirname(RAW), exist_ok=True)
        urllib.request.urlretrieve(URL, RAW)
    df = pd.read_csv(RAW, dtype=str)
    ev = clean(df)
    dump = ev.copy()
    dump.insert(0, "timestamp", epoch_s(dump["utc"]))
    dump.drop(columns=["utc"]).to_csv(OUT, index=False)
    back = load_events(OUT)
    assert len(back) == len(ev) and (back["utc"].values == ev["utc"].values).all(), "saved file does not round-trip"
    cons = consistency(back)
    print("schedule table vs rows whose time survived (2015+): share at the table time, by event")
    for name, r in cons.iterrows():
        print(f"  {name:34s} {int(r['count']):4d} rows  {100 * r['mean']:5.1f}%")
    print(f"saved+reloaded {OUT}: {len(back)} USD high-impact rows, {back['utc'].min()} -> {back['utc'].max()}; "
          f"time from archive {int((back.time_source == 'archive').sum())}, canonical {int((back.time_source == 'canonical').sum())}")
    nm = back["actual"].notna() & back["forecast"].notna() & (back["effect"] != 0)
    print(f"rows with numeric actual, forecast and a usual-effect sign: {int(nm.sum())}")
    print("FF_EVENTS_DONE")


if __name__ == "__main__":
    sys.exit(main())
