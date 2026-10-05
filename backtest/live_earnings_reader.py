"""
v0.29-live, Phase B — live earnings reader: reading packets, recorded calls, paper trades, scoring.

Pre-registered protocol (DEVLOG v0.29-live):
1. Every US weekday evening, after the close, a scheduled Claude session runs --prepare. The run date
   is T, a trading day whose close is already in; T1, the previous trading day, is the report date;
   T2 is the session before T1. Every S&P 500 company on the Nasdaq earnings calendar for T1 gets a
   reading packet: actual vs consensus EPS, the T2 -> T reaction (raw, SPY, abnormal = raw - SPY),
   the standardised surprise s1 = (eps - consensus) / raw close(T2), and the earnings press release
   (8-K item 2.02, exhibit 99) from SEC EDGAR as plain text cut to 2,500 words. The T2 -> T window
   holds the reaction to a release on T1 whether it came before the open or after the close.
2. Claude reads each packet against the rubric and calls a direction (UP/DOWN) with a confidence
   (0.50-1.00; 0.50 = no view) and a one-line reason. --record validates the calls, appends them to
   predictions.jsonl (append-only; one call per ticker per report date) and opens a paper trade for
   every call at >= 0.70 confidence: 1 % of the portfolio, 2 % at >= 0.90.
3. --score enters each trade at the first regular-session open AFTER the decision date (adjusted
   open = open * adjclose / close) and ASSERTS that the call was recorded before 09:30 New York time
   on that day: the call cannot have seen its own entry price. Exit: adjusted close of the 20th
   session, the entry session being session 1. Costs: 0.10 % per side on every trade, plus 3 %/yr
   short financing over the sessions held on DOWN trades. Until session 20 a trade is OPEN and its
   exit_date / exit_price hold the latest mark. Every call with confidence > 0.50, traded or not, is
   scored the same way for calibration, and Phase A's model.json, when present, is scored on the
   same events.

Files, in backtest/live_earnings/: sp500.csv, queue/<T>.json, queue_dryrun/<T>.json,
predictions.jsonl, ledger.csv, results.md, model.json (written by Phase A).

Usage:
  python backtest/live_earnings_reader.py --selftest                 # offline, synthetic prices
  python backtest/live_earnings_reader.py --refresh-universe
  python backtest/live_earnings_reader.py --prepare [--date YYYY-MM-DD] [--dry-run]
  python backtest/live_earnings_reader.py --record --date T --predictions calls.json [--dry-run]
  python backtest/live_earnings_reader.py --score [--ledger path/to/ledger.csv]
"""

import argparse
import csv
import html
import json
import math
import os
import re
import sys
import tempfile
import time
from datetime import date, datetime, timedelta, timezone
from datetime import time as dtime
from typing import Optional
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from backtest.fetch_earnings_calendar import HEADERS as NASDAQ_HEADERS, URL as NASDAQ_URL, money  # noqa: E402
from backtest.headline_blind_test import CACHE as PRICE_CACHE, daily  # noqa: E402

DIR = "backtest/live_earnings"
SP500_CSV, PREDICTIONS_JSONL, LEDGER_CSV = "sp500.csv", "predictions.jsonl", "ledger.csv"
RESULTS_MD, MODEL_JSON = "results.md", "model.json"
LEDGER = f"{DIR}/{LEDGER_CSV}"
LEDGER_COLUMNS = ["id", "ticker", "report_date", "decision_date", "direction", "confidence", "size",
                  "recorded_utc", "entry_date", "entry_price", "exit_date", "exit_price", "ret", "net",
                  "pnl_pct", "status"]
RESULT_COLUMNS = ["entry_date", "entry_price", "exit_date", "exit_price", "ret", "net", "pnl_pct"]

WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
WIKI_UA = {"User-Agent": "Mozilla/5.0"}
UNIVERSE_ROWS = (495, 510)
UNIVERSE_STALE_DAYS = 35

SEC_UA = {"User-Agent": "ICTVWAP research bot admin@ictvwap-research.invalid"}   # SEC wants a declared UA
SEC_SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik}.json"
SEC_FILING = "https://www.sec.gov/Archives/edgar/data/{cik}/{acc}/"
SEC_PAUSE = 0.15                 # seconds before every SEC request (fair-access limit is 10/s)
BACKOFF = (2, 4, 8, 16)          # waits after 429 / 5xx / network errors
FILING_LOOKBACK_DAYS = 3         # the 8-K may be filed up to 3 calendar days before T1 ... through T
MAX_WORDS = 2500

NY = ZoneInfo("America/New_York")
OPEN_ET = dtime(9, 30)
CLOSE_READY_ET = dtime(16, 30)   # T's close counts as available once New York passes 16:30
ENTRY_READY_ET = dtime(9, 45)    # a bar dated today is used only after its opening print is in
PRICE_LOOKBACK_DAYS = 20         # calendar days of bars before T for --prepare
SCORE_WINDOW_DAYS = 50           # calendar days after a decision; always holds the 20 sessions needed
FRESH_DAYS = 5                   # price windows ending this close to today are re-downloaded

HOLD = 20                        # sessions held, the entry session counting as session 1
COST_SIDE = 0.0010               # 0.10 % per side
SHORT_FIN_YR = 0.03              # financing on DOWN trades, per year of 252 sessions
GATE = ((0.90, 0.02), (0.70, 0.01))
BUCKETS = ((0.50, 0.60), (0.60, 0.70), (0.70, 0.80), (0.80, 0.90), (0.90, 1.00))

TAG = re.compile(r"""<[A-Za-z/!?](?:[^>"']|"[^"]*"|'[^']*')*>""")   # quoted attributes may hold '>'
BLOCK = re.compile(r"</?(?:p|div|br|tr|li|ul|ol|dl|dt|dd|table|thead|tbody|tfoot|caption|h[1-6]|hr|"
                   r"blockquote|pre|section|article|header|footer|center|title)\b[^>]*>", re.I)
EX99 = re.compile(r"ex(?:h|hibit)?[-_.]?99", re.I)
EX99_1 = re.compile(r"[-_.]?0?1(?!\d)")
TEXT_DOCS = (".htm", ".html", ".txt")


class NoPrices(Exception):
    """Yahoo returned nothing usable for a ticker."""


# ---------------------------------------------------------------------------- small helpers

def norm(sym) -> str:
    """Matching key for Nasdaq and Wikipedia symbols: upper case, '/' and '-' -> '.' (BRK/B, BRK-B -> BRK.B)."""
    return str(sym or "").strip().upper().replace("/", ".").replace("-", ".")


def yahoo_symbol(ticker: str) -> str:
    return norm(ticker).replace(".", "-")


def fin(x) -> Optional[float]:
    """Finite float or None (money() returns nan for a blank field; JSON has no nan)."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_utc(s: str) -> datetime:
    dt = datetime.fromisoformat(str(s).strip().replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError(f"timestamp without a timezone: {s!r}")
    return dt.astimezone(timezone.utc)


def entry_open_utc(d: date) -> datetime:
    """09:30 New York time on session d, in UTC (zoneinfo applies EST or EDT)."""
    return datetime.combine(d, OPEN_ET, tzinfo=NY).astimezone(timezone.utc)


def next_weekday(d: date) -> date:
    d += timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def require(cond: bool, msg: str) -> None:
    """An assert that survives python -O."""
    if not cond:
        raise AssertionError(msg)


def gate_size(confidence: float) -> float:
    """Fraction of the portfolio a call trades: >= 0.90 -> 2 %, >= 0.70 -> 1 %, else no trade."""
    for threshold, size in GATE:
        if confidence >= threshold:
            return size
    return 0.0


def cell(x) -> str:
    if x is None:
        return ""
    return format(x, ".10g") if isinstance(x, float) else str(x)


def pc(x: Optional[float], digits: int = 2) -> str:
    return "n/a" if x is None else f"{100 * x:+.{digits}f} %"


# ---------------------------------------------------------------------------- Phase A model

def pct(x: float, q) -> float:
    """Percentile position of x among the quantile cut points q, kept off 0 and 1."""
    q = np.asarray(q, dtype=float)
    return (float(np.searchsorted(q, x, side="right")) + 0.5) / (len(q) + 1)


def model_p_up(model: dict, s1: float, s2: float) -> float:
    """P(UP) from model.json: logistic in p1 = pct(s1), p2 = pct(abnormal reaction) and p1 * p2."""
    b1, b2, b3 = (float(b) for b in np.ravel(model["coef"]))
    p1, p2 = pct(s1, model["s1_quantiles"]), pct(s2, model["s2_quantiles"])
    z = float(model["intercept"]) + b1 * p1 + b2 * p2 + b3 * p1 * p2
    return 1.0 / (1.0 + math.exp(-z)) if z >= 0 else math.exp(z) / (1.0 + math.exp(z))


def model_call(model: dict, s1: float, s2: float) -> tuple[str, float]:
    """(direction, confidence): UP when P(UP) >= 0.5, confidence max(p, 1 - p)."""
    p = model_p_up(model, s1, s2)
    return ("UP", p) if p >= 0.5 else ("DOWN", 1.0 - p)


# ---------------------------------------------------------------------------- network

def http_get(url: str, headers: dict, pause: float = 0.0) -> Optional[requests.Response]:
    """GET; 429 / 5xx / network errors are retried after 2, 4, 8, 16 s. None on another 4xx or at the end."""
    for wait in (0,) + BACKOFF:
        if wait:
            print(f"    retry in {wait}s: {url}", flush=True)
            time.sleep(wait)
        if pause:
            time.sleep(pause)
        try:
            r = requests.get(url, headers=headers, timeout=30)
        except requests.RequestException as e:
            print(f"    {type(e).__name__}: {url}", flush=True)
            continue
        if r.status_code == 200:
            return r
        print(f"    HTTP {r.status_code}: {url}", flush=True)
        if r.status_code != 429 and r.status_code < 500:
            return None
    return None


def sec_get(url: str) -> Optional[requests.Response]:
    return http_get(url, SEC_UA, pause=SEC_PAUSE)


_FETCHED: set = set()


def bars(ticker: str, lo: date, hi: date, today: Optional[date] = None) -> pd.DataFrame:
    """daily() from headline_blind_test, made safe for live use. daily() caches each window forever, so
    a window ending within FRESH_DAYS of today (whose last session may be partial or not yet there)
    is downloaded again, once per process. Raises NoPrices when Yahoo has nothing usable."""
    today = today or datetime.now(NY).date()
    path = f"{PRICE_CACHE}/{ticker}_{lo}_{hi}.json"
    if path not in _FETCHED and hi >= today - timedelta(days=FRESH_DAYS) and os.path.exists(path):
        os.remove(path)
    problem = "no response"
    for wait in (0,) + BACKOFF[:3]:
        time.sleep(wait)
        try:
            df = daily(ticker, lo, hi)
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else 0
            problem = f"HTTP {code}"
            if code != 429 and code < 500:
                break
        except requests.RequestException as e:
            problem = type(e).__name__
        except (KeyError, IndexError, TypeError, ValueError) as e:
            problem = f"unusable response ({type(e).__name__})"
            if os.path.exists(path):
                os.remove(path)
            break
        else:
            _FETCHED.add(path)
            return df
    raise NoPrices(f"Yahoo {ticker} {lo}..{hi}: {problem}")


# ---------------------------------------------------------------------------- HTML

def clean_cell(s: str) -> str:
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(TAG.sub("", s))).strip()


def html_to_text(s: str) -> str:
    """Plain text from an EDGAR HTML document: one line per block element, table cells space-separated."""
    m = re.search(r"<TEXT>(.*?)</TEXT>", s, flags=re.S | re.I)
    if m and s.lstrip()[:10].upper() == "<DOCUMENT>":          # EDGAR's SGML wrapper
        s = m.group(1)
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
    s = re.sub(r"<(script|style|head|ix:header)\b.*?</\1\s*>", " ", s, flags=re.S | re.I)
    s = BLOCK.sub("\n", s)
    s = re.sub(r"</t[dh]\s*>", " ", s, flags=re.I)
    s = html.unescape(TAG.sub("", s)).replace("\u200b", "").replace("\ufeff", "")
    lines = (re.sub(r"\s+", " ", line).strip() for line in s.split("\n"))
    return "\n".join(line for line in lines if line)


def truncate_words(text: str, n: int) -> str:
    out, used = [], 0
    for line in text.split("\n"):
        words = line.split()
        if used + len(words) > n:
            out.append(" ".join(words[: n - used]))
            break
        out.append(line)
        used += len(words)
    return "\n".join(out).strip()


def decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


# ---------------------------------------------------------------------------- universe

def parse_constituents(page: str) -> list:
    """Rows of the Wikipedia table id="constituents": symbol (cell 1), name (cell 2), 10-digit CIK."""
    m = re.search(r'<table\b[^>]*\bid="constituents"[^>]*>(.*?)</table>', page, flags=re.S)
    if not m:
        raise ValueError('no <table id="constituents"> on the page')
    trs = re.findall(r"<tr\b[^>]*>(.*?)</tr>", m.group(1), flags=re.S)
    header = [clean_cell(c) for c in re.findall(r"<th\b[^>]*>(.*?)</th>", trs[0], flags=re.S)] if trs else []
    cik_col = header.index("CIK") if "CIK" in header else None
    rows = []
    for tr in trs:
        cells = [clean_cell(c) for c in re.findall(r"<td\b[^>]*>(.*?)</td>", tr, flags=re.S)]
        if len(cells) < 2:
            continue
        cik = cells[cik_col] if cik_col is not None and cik_col < len(cells) else ""
        if not re.fullmatch(r"\d{10}", cik):
            cik = next((c for c in cells if re.fullmatch(r"\d{10}", c)), "")
        rows.append({"symbol": cells[0], "name": cells[1], "cik": cik})
    return rows


def load_universe(path: str = f"{DIR}/{SP500_CSV}") -> dict:
    """norm(symbol) -> row; read with the csv module so CIKs keep their leading zeros."""
    with open(path, newline="", encoding="utf-8") as f:
        return {norm(r["symbol"]): r for r in csv.DictReader(f)}


def refresh_universe() -> list:
    r = http_get(WIKI_URL, WIKI_UA)
    if r is None:
        sys.exit(f"could not download {WIKI_URL}; {SP500_CSV} left unchanged")
    rows = parse_constituents(r.text)
    require(UNIVERSE_ROWS[0] <= len(rows) <= UNIVERSE_ROWS[1],
            f"{len(rows)} constituents parsed, expected {UNIVERSE_ROWS[0]}-{UNIVERSE_ROWS[1]}")
    bad = [x["symbol"] for x in rows if not re.fullmatch(r"\d{10}", x["cik"])]
    require(not bad, f"rows without a 10-digit CIK: {bad[:10]}")
    keys = [norm(x["symbol"]) for x in rows]
    require(len(set(keys)) == len(keys), "duplicate symbols after norm()")
    stamp = iso_z(datetime.now(timezone.utc))
    os.makedirs(DIR, exist_ok=True)
    path = f"{DIR}/{SP500_CSV}"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["symbol", "name", "cik", "fetched_utc"], lineterminator="\n")
        w.writeheader()
        for x in rows:
            w.writerow({**x, "fetched_utc": stamp})
    back = load_universe(path)
    require(len(back) == len(rows) and all(re.fullmatch(r"\d{10}", x["cik"]) for x in back.values()),
            "sp500.csv did not re-load intact")
    print(f"{len(rows)} S&P 500 constituents -> {path} (fetched {stamp})")
    return rows


# ---------------------------------------------------------------------------- press release (SEC EDGAR)

def pick_8k(sub: dict, t1: date, t: date) -> Optional[dict]:
    """The 8-K / 8-K/A with item 2.02 filed T1-3 days .. T, closest to T1."""
    rec = sub["filings"]["recent"]
    best = None
    for i, form in enumerate(rec["form"]):
        if form not in ("8-K", "8-K/A"):
            continue
        if "2.02" not in [x.strip() for x in str(rec["items"][i]).split(",")]:
            continue
        filed = date.fromisoformat(rec["filingDate"][i])
        if not t1 - timedelta(days=FILING_LOOKBACK_DAYS) <= filed <= t:
            continue
        key = (abs((filed - t1).days), form != "8-K", rec["acceptanceDateTime"][i])
        if best is None or key < best[0]:
            best = (key, {"accession": rec["accessionNumber"][i], "form": form, "filed": str(filed),
                          "accepted": rec["acceptanceDateTime"][i]})
    return best[1] if best else None


def choose_exhibit(names: list) -> tuple[Optional[str], bool]:
    """Exhibit 99 by file name -> (name, is 99.1). /ex-?99/ alone misses Workiva names such as
    'q1fy27exhibit991er.htm', so 'exh99' and 'exhibit99' count too; 991, 99-1, 99_1 are preferred."""
    docs = [n for n in names if n.lower().endswith(TEXT_DOCS) and EX99.search(n)]
    first = [n for n in docs if EX99_1.match(n[EX99.search(n).end():])]
    if first:
        return first[0], True
    return (docs[0], False) if docs else (None, False)


def exhibit_from_index_page(page: str) -> Optional[str]:
    """Fallback: the document whose Type is EX-99.1 (else any EX-99) in the filing's -index.htm table."""
    docs = []
    for tr in re.findall(r"<tr\b[^>]*>(.*?)</tr>", page, flags=re.S | re.I):
        cells = re.findall(r"<td\b[^>]*>(.*?)</td>", tr, flags=re.S | re.I)
        m = re.search(r'href="[^"]*/([^"/]+)"', cells[2]) if len(cells) >= 4 else None
        if m and m.group(1).lower().endswith(TEXT_DOCS):
            docs.append((m.group(1), clean_cell(cells[3]).upper()))
    for want in (r"EX-99\.0?1$", r"EX-99"):
        for name, typ in docs:
            if re.match(want, typ):
                return name
    return None


def press_release(cik: str, t1: date, t: date) -> dict:
    out = {"press_release_url": None, "edgar_accepted_utc": None, "text_words": 0,
           "missing_press_release": True, "press_release_text": ""}
    r = sec_get(SEC_SUBMISSIONS.format(cik=cik))
    if r is None:
        print(f"    CIK {cik}: EDGAR submissions unavailable")
        return out
    try:
        filing = pick_8k(r.json(), t1, t)
    except (ValueError, KeyError, TypeError) as e:
        print(f"    CIK {cik}: unreadable submissions JSON ({type(e).__name__})")
        return out
    if filing is None:
        print(f"    CIK {cik}: no 8-K with item 2.02 filed {t1 - timedelta(days=FILING_LOOKBACK_DAYS)}..{t}")
        return out
    acc = filing["accession"].replace("-", "")
    base = SEC_FILING.format(cik=int(cik), acc=acc)
    r = sec_get(base + "index.json")
    try:
        names = [it["name"] for it in r.json()["directory"]["item"]] if r is not None else []
    except (ValueError, KeyError, TypeError):
        names = []
    doc, is_99_1 = choose_exhibit(names)
    if not is_99_1:
        r = sec_get(f"{base}{filing['accession']}-index.htm")
        doc = (exhibit_from_index_page(r.text) if r is not None else None) or doc
    if doc is None:
        print(f"    CIK {cik}: no exhibit 99 in {filing['accession']}")
        return out
    r = sec_get(base + doc)
    if r is None:
        return out
    text = html_to_text(decode(r.content))
    words = len(text.split())
    out.update(press_release_url=base + doc, edgar_accepted_utc=filing["accepted"], text_words=words,
               missing_press_release=words == 0, press_release_text=truncate_words(text, MAX_WORDS))
    return out


# ---------------------------------------------------------------------------- --prepare

def read_predictions(path: str) -> list:
    if not os.path.exists(path):
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if line.strip():
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError as e:
                    raise ValueError(f"{path} line {n} is not valid JSON: {e}") from e
    return out


def fetch_calendar(d: date) -> tuple[list, str]:
    r = http_get(NASDAQ_URL.format(d=d), NASDAQ_HEADERS)
    if r is None:
        sys.exit(f"Nasdaq earnings calendar for {d} unavailable; no queue written")
    try:
        data = (r.json() or {}).get("data") or {}
    except ValueError:
        sys.exit(f"Nasdaq earnings calendar for {d} is not JSON; no queue written")
    return data.get("rows") or [], str(data.get("asOf") or "")


def build_event(row: dict, u: dict, t: date, t1: date, t2: date, spy_react: float, today: date) -> dict:
    eps, fc, n_ests = fin(money(row.get("eps"))), fin(money(row.get("epsForecast"))), fin(money(row.get("noOfEsts")))
    ev = {"ticker": u["symbol"], "name": row.get("name") or u["name"], "report_date": str(t1),
          "fiscal_quarter": row.get("fiscalQuarterEnding", ""), "eps": eps, "eps_forecast": fc,
          "n_ests": int(n_ests) if n_ests is not None else None, "surprise_pct": fin(money(row.get("surprise"))),
          "close_T2": None, "close_T2_raw": None, "reaction_raw": None, "reaction_spy": spy_react,
          "reaction_abnormal": None, "s1": None, "cik": u["cik"]}
    try:
        df = bars(yahoo_symbol(u["symbol"]), t - timedelta(days=PRICE_LOOKBACK_DAYS), t + timedelta(days=1), today)
    except NoPrices as e:
        print(f"    {u['symbol']}: {e}")
        df = None
    if df is not None and t in df.index and t2 in df.index:
        raw = float(df.at[t, "adjclose"] / df.at[t2, "adjclose"] - 1.0)
        ev.update(close_T2=float(df.at[t2, "adjclose"]), close_T2_raw=float(df.at[t2, "close"]),
                  reaction_raw=raw, reaction_abnormal=raw - spy_react)
        if eps is not None and fc is not None:
            ev["s1"] = (eps - fc) / float(df.at[t2, "close"])
    elif df is not None:
        print(f"    {u['symbol']}: Yahoo has no bar for {t2} or {t}; reaction left empty")
    ev.update(press_release(u["cik"], t1, t))
    return ev


def prepare(t: Optional[date] = None, dry_run: bool = False, now: Optional[datetime] = None) -> dict:
    now = now or datetime.now(timezone.utc)
    now_ny = now.astimezone(NY)
    t = t or now_ny.date()
    if not os.path.exists(f"{DIR}/{SP500_CSV}"):
        sys.exit(f"no {DIR}/{SP500_CSV}: run --refresh-universe first")
    universe = load_universe()
    if not universe:
        sys.exit(f"{DIR}/{SP500_CSV} is empty: run --refresh-universe")
    fetched = parse_utc(next(iter(universe.values()))["fetched_utc"])
    if (now - fetched).days > UNIVERSE_STALE_DAYS:
        print(f"WARNING: S&P 500 list is {(now - fetched).days} days old; run --refresh-universe")
    if t > now_ny.date() or (t == now_ny.date() and now_ny.time() < CLOSE_READY_ET):
        sys.exit(f"{t}: the close is not available yet (New York time {now_ny:%Y-%m-%d %H:%M}); nothing prepared")
    try:
        spy = bars("SPY", t - timedelta(days=PRICE_LOOKBACK_DAYS), t + timedelta(days=1), now_ny.date())
    except NoPrices as e:
        sys.exit(f"cannot load SPY bars to find trading days: {e}")
    if t not in spy.index:
        sys.exit(f"{t} is not a trading day with a close available (no SPY session); nothing prepared")
    sessions = sorted(spy.index)
    i = sessions.index(t)
    if i < 2:
        sys.exit(f"fewer than two sessions before {t} in the SPY bars")
    t1, t2 = sessions[i - 1], sessions[i - 2]
    path = f"{DIR}/{'queue_dryrun' if dry_run else 'queue'}/{t}.json"
    if not dry_run and os.path.exists(path) and any(
            p.get("report_date") == str(t1) for p in read_predictions(f"{DIR}/{PREDICTIONS_JSONL}")):
        sys.exit(f"{path} already has recorded predictions (report date {t1}); refusing to rebuild it")
    spy_react = float(spy.at[t, "adjclose"] / spy.at[t2, "adjclose"] - 1.0)
    cal, asof = fetch_calendar(t1)
    print(f"T {t}, report date T1 {t1}, base T2 {t2}; SPY {pc(spy_react)}; Nasdaq calendar for {t1} "
          f"({asof}): {len(cal)} rows", flush=True)

    events, kept = [], {}
    for row in cal:
        u = universe.get(norm(row.get("symbol")))
        if u is None:
            continue
        if u["cik"] in kept:              # a second share class of the same company (GOOG / GOOGL)
            print(f"  {row.get('symbol')}: same company (CIK {u['cik']}) as {kept[u['cik']]['ticker']}; merged")
            kept[u["cik"]].setdefault("other_share_classes", []).append(u["symbol"])
            continue
        print(f"  building {u['symbol']} ...", flush=True)
        ev = build_event(row, u, t, t1, t2, spy_react, now_ny.date())
        kept[u["cik"]] = ev
        events.append(ev)

    queue = {"date": str(t), "report_date": str(t1), "base_date": str(t2), "built_utc": iso_z(now),
             "calendar_asof": asof, "events": events}
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=1, ensure_ascii=False, allow_nan=False)
    with open(path, encoding="utf-8") as f:
        require(len(json.load(f)["events"]) == len(events), f"{path} did not re-load intact")

    for e in events:
        s1 = "n/a" if e["s1"] is None else f"{e['s1']:+.5f}"
        print(f"  {e['ticker']:6s} s1 {s1:>9s}  abnormal {pc(e['reaction_abnormal']):>9s}  "
              f"words {e['text_words']:5d}{'  MISSING press release' if e['missing_press_release'] else ''}")
    missing = sum(e["missing_press_release"] for e in events)
    print(f"{len(events)} S&P 500 events reported {t1} ({missing} without a press release) -> {path}")
    return queue


# ---------------------------------------------------------------------------- --record

def validate_predictions(preds, queue: dict, recorded: set) -> tuple[list, list]:
    """(errors, clean calls). recorded: {(report_date, norm(ticker))} already in predictions.jsonl."""
    if not isinstance(preds, list):
        return ["the predictions file must hold a JSON list"], []
    events = {norm(e["ticker"]): e for e in queue["events"]}
    errors, clean, seen = [], [], set()
    for i, p in enumerate(preds):
        if not isinstance(p, dict):
            errors.append(f"#{i}: not an object")
            continue
        key, where = norm(p.get("ticker")), f"#{i} {p.get('ticker')}"
        problems = []
        if key not in events:
            problems.append(f"not in the queue for {queue['date']}")
        direction = str(p.get("direction", "")).strip().upper()
        if direction not in ("UP", "DOWN"):
            problems.append(f"direction {p.get('direction')!r} is not UP or DOWN")
        conf = p.get("confidence")
        if isinstance(conf, bool) or not isinstance(conf, (int, float)) or not 0.50 <= conf <= 1.00:
            problems.append(f"confidence {conf!r} is not a number in 0.50-1.00")
        reason = str(p.get("reason") or "").strip()
        if not reason:
            problems.append("empty reason")
        if key in seen:
            problems.append("listed twice in this file")
        if (queue["report_date"], key) in recorded:
            problems.append(f"already recorded for report date {queue['report_date']}")
        seen.add(key)
        if problems:
            errors.extend(f"{where}: {x}" for x in problems)
        else:
            clean.append({"event": events[key], "direction": direction, "confidence": float(conf), "reason": reason})
    return errors, clean


def append_ledger(path: str, rows: list) -> None:
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_COLUMNS, lineterminator="\n")
        if new:
            w.writeheader()
        for r in rows:
            w.writerow({c: cell(r.get(c)) for c in LEDGER_COLUMNS})


def record(t: date, predictions_path: str, dry_run: bool = False, now: Optional[datetime] = None,
           data_dir: str = DIR) -> tuple[list, list]:
    now = now or datetime.now(timezone.utc)
    qpath = f"{data_dir}/queue/{t}.json"
    if not os.path.exists(qpath) and dry_run and os.path.exists(f"{data_dir}/queue_dryrun/{t}.json"):
        qpath = f"{data_dir}/queue_dryrun/{t}.json"
    if not os.path.exists(qpath):
        sys.exit(f"no queue file for {t} ({qpath}); run --prepare first")
    with open(qpath, encoding="utf-8") as f:
        queue = json.load(f)
    require(queue["date"] == str(t), f"{qpath} is for {queue['date']}, not {t}")
    pred_file, ledger_file = f"{data_dir}/{PREDICTIONS_JSONL}", f"{data_dir}/{LEDGER_CSV}"
    recorded = {(p["report_date"], norm(p["ticker"])) for p in read_predictions(pred_file)}
    with open(predictions_path, encoding="utf-8") as f:
        preds = json.load(f)
    errors, clean = validate_predictions(preds, queue, recorded)
    deadline = entry_open_utc(next_weekday(t))
    if now >= deadline:
        msg = f"it is past {iso_z(deadline)}, the earliest possible entry open after {t}"
        if dry_run:
            print(f"WARNING: {msg}")
        else:
            errors.append(msg + "; a call recorded now could see its entry price")
    if errors:
        print(f"REFUSED: {len(errors)} problem(s); nothing written")
        for e in errors:
            print(f"  {e}")
        sys.exit(1)

    stamp, lines, trades = iso_z(now), [], []
    for c in clean:
        ev = c["event"]
        lines.append({"recorded_utc": stamp, "decision_date": str(t), "report_date": queue["report_date"],
                      "ticker": ev["ticker"], "direction": c["direction"], "confidence": c["confidence"],
                      "reason": c["reason"], "eps": ev.get("eps"), "eps_forecast": ev.get("eps_forecast"),
                      "s1": ev.get("s1"), "reaction_abnormal": ev.get("reaction_abnormal"),
                      "press_release_url": ev.get("press_release_url"),
                      "missing_press_release": ev.get("missing_press_release")})
        size = gate_size(c["confidence"])
        if size > 0:
            trades.append({"id": f"{queue['report_date']}_{ev['ticker']}", "ticker": ev["ticker"],
                           "report_date": queue["report_date"], "decision_date": str(t),
                           "direction": c["direction"], "confidence": c["confidence"], "size": size,
                           "recorded_utc": stamp, "status": "PENDING"})
    if dry_run:
        print(f"DRY RUN ({qpath}): would append {len(lines)} line(s) to {pred_file}:")
        for line in lines:
            print("  " + json.dumps(line, ensure_ascii=False))
        print(f"would append {len(trades)} trade(s) to {ledger_file}:")
        for tr in trades:
            print(f"  {tr['id']} {tr['direction']} conf {tr['confidence']:.2f} size {100 * tr['size']:.0f} %")
        return lines, trades
    with open(pred_file, "a", encoding="utf-8") as f:
        for line in lines:
            f.write(json.dumps(line, ensure_ascii=False, allow_nan=False) + "\n")
    if trades:
        append_ledger(ledger_file, trades)
    print(f"recorded {len(lines)} call(s) for {t} (report date {queue['report_date']}) at {stamp}; "
          f"{len(trades)} paper trade(s) opened in {ledger_file}")
    for tr in trades:
        print(f"  {tr['id']} {tr['direction']} conf {tr['confidence']:.2f} size {100 * tr['size']:.0f} %")
    return lines, trades


# ---------------------------------------------------------------------------- --score

def outcome(ticker: str, decision: date, recorded_utc: str, now: datetime) -> Optional[dict]:
    """The 20-session outcome of a call decided on `decision`: None until the entry session exists.
    Raises AssertionError if the call was not recorded before that session's 09:30 New York open."""
    now_ny = now.astimezone(NY)
    today = now_ny.date()
    hi = min(today + timedelta(days=1), decision + timedelta(days=SCORE_WINDOW_DAYS))
    df = bars(yahoo_symbol(ticker), decision, hi, today)
    sessions = [d for d in sorted(df.index) if d > decision and (d < today or now_ny.time() >= ENTRY_READY_ET)]
    if not sessions:
        return None
    entry = sessions[0]
    opened = entry_open_utc(entry)
    require(parse_utc(recorded_utc) < opened,
            f"LOOKAHEAD: {ticker} (decided {decision}) recorded {recorded_utc}, not before the {entry} open "
            f"{iso_z(opened)}")
    held = sessions[:HOLD]
    entry_px = float(df.at[entry, "open"] * df.at[entry, "adjclose"] / df.at[entry, "close"])
    exit_px = float(df.at[held[-1], "adjclose"])
    return {"entry_date": entry, "entry_price": entry_px, "exit_date": held[-1], "exit_price": exit_px,
            "raw": exit_px / entry_px - 1.0, "n_sessions": len(held),
            "status": "CLOSED" if len(held) == HOLD else "OPEN"}


def trade_return(raw: float, direction: str, n_sessions: int) -> tuple[float, float]:
    """(ret, net) for a call: costs 0.10 % per side, plus 3 %/yr financing over the sessions held if DOWN."""
    ret = raw if direction == "UP" else -raw
    costs = 2 * COST_SIDE + (SHORT_FIN_YR * n_sessions / 252 if direction == "DOWN" else 0.0)
    return ret, ret - costs


def hit(raw: float, direction: str) -> bool:
    """The move went the called way (before costs)."""
    return raw > 0 if direction == "UP" else raw < 0


def bucket_label(i: int) -> str:
    lo, hi = BUCKETS[i]
    return f"[{lo:.2f}-{hi:.2f}{']' if i == len(BUCKETS) - 1 else ')'}"


def bucket_stats(items: list) -> list:
    """items: (confidence, direction, outcome or None). One row per bucket plus 'all'; hit = the
    20-session move went the called way (before costs); hit rate and mean net over CLOSED calls only."""
    table = [{"bucket": bucket_label(i), "closed": 0, "open": 0, "pending": 0, "hits": 0, "nets": []}
             for i in range(len(BUCKETS))] + [{"bucket": "all", "closed": 0, "open": 0, "pending": 0,
                                               "hits": 0, "nets": []}]
    for conf, direction, o in items:
        i = next((k for k, (lo, hi) in enumerate(BUCKETS)
                  if lo <= conf < hi or (k == len(BUCKETS) - 1 and conf == hi)), None)
        for row in ([table[i]] if i is not None else []) + [table[-1]]:
            if o is None:
                row["pending"] += 1
            elif o["status"] == "OPEN":
                row["open"] += 1
            else:
                row["closed"] += 1
                row["hits"] += int(hit(o["raw"], direction))
                row["nets"].append(trade_return(o["raw"], direction, o["n_sessions"])[1])
    for row in table:
        row["hit_rate"] = row["hits"] / row["closed"] if row["closed"] else None
        row["mean_net"] = float(np.mean(row["nets"])) if row["nets"] else None
    return table


def read_ledger(path: str) -> list:
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_ledger(path: str, rows: list) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LEDGER_COLUMNS, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({c: cell(r.get(c)) for c in LEDGER_COLUMNS})
    os.replace(tmp, path)


def stats_table(table: list, title: str) -> list:
    out = [f"| {title} | closed | open | pending | hit rate | mean net |", "|---|---:|---:|---:|---:|---:|"]
    for r in table:
        rate = "n/a" if r["hit_rate"] is None else f"{100 * r['hit_rate']:.0f} % ({r['hits']}/{r['closed']})"
        out.append(f"| {r['bucket']} | {r['closed']} | {r['open']} | {r['pending']} | {rate} | {pc(r['mean_net'])} |")
    return out


def score(ledger_path: str = LEDGER, now: Optional[datetime] = None) -> dict:
    """Price the ledger in place, score every call for calibration (and model.json if present) and write
    results.md. predictions.jsonl, model.json and results.md live beside the ledger."""
    now = now or datetime.now(timezone.utc)
    data_dir = os.path.dirname(os.path.abspath(ledger_path))
    rows = read_ledger(ledger_path)
    print(f"scoring {len(rows)} paper trade(s) in {ledger_path}", flush=True)
    for row in rows:
        try:
            o = outcome(row["ticker"], date.fromisoformat(row["decision_date"]), row["recorded_utc"], now)
        except NoPrices as e:
            print(f"  {row['id']}: {e}; left as {row['status']}")
            continue
        if o is None:
            row.update({c: "" for c in RESULT_COLUMNS}, status="PENDING")
        else:
            ret, net = trade_return(o["raw"], row["direction"], o["n_sessions"])
            row.update(entry_date=str(o["entry_date"]), entry_price=o["entry_price"], exit_date=str(o["exit_date"]),
                       exit_price=o["exit_price"], ret=ret, net=net, pnl_pct=float(row["size"]) * net,
                       status=o["status"])
        line = f"  {row['id']:22s} {row['direction']:4s} {float(row['confidence']):.2f}  {row['status']:7s}"
        if row["status"] != "PENDING":
            line += (f" entry {row['entry_date']} @ {float(row['entry_price']):.2f}  "
                     f"{'exit' if row['status'] == 'CLOSED' else 'mark'} {row['exit_date']} @ "
                     f"{float(row['exit_price']):.2f}  net {pc(float(row['net']))}")
        print(line)
    if rows:
        write_ledger(ledger_path, rows)
        back = read_ledger(ledger_path)
        require([b["id"] for b in back] == [r["id"] for r in rows]
                and [b["status"] for b in back] == [r["status"] for r in rows], "ledger did not re-load intact")

    preds = read_predictions(os.path.join(data_dir, PREDICTIONS_JSONL))
    scored, unpriced = [], 0
    for p in preds:
        try:
            o = outcome(p["ticker"], date.fromisoformat(p["decision_date"]), p["recorded_utc"], now)
        except NoPrices as e:
            print(f"  prediction {p['report_date']} {p['ticker']}: {e}")
            unpriced += 1
            continue
        scored.append((p, o))
    calib = bucket_stats([(float(p["confidence"]), p["direction"], o) for p, o in scored
                          if float(p["confidence"]) > 0.50])

    model, msec = None, None
    model_path = os.path.join(data_dir, MODEL_JSON)
    if os.path.exists(model_path):
        with open(model_path, encoding="utf-8") as f:
            model = json.load(f)
        calls = [(p, o, model_call(model, float(p["s1"]), float(p["reaction_abnormal"])))
                 for p, o in scored if fin(p.get("s1")) is not None and fin(p.get("reaction_abnormal")) is not None]
        h2h = [(p, o, m) for p, o, m in calls
               if float(p["confidence"]) > 0.50 and o is not None and o["status"] == "CLOSED"]
        msec = {"n": len(calls), "skipped": len(scored) - len(calls),
                "table": bucket_stats([(m[1], m[0], o) for p, o, m in calls]),
                "h2h_n": len(h2h),
                "h2h_claude": sum(hit(o["raw"], p["direction"]) for p, o, m in h2h),
                "h2h_model": sum(hit(o["raw"], m[0]) for p, o, m in h2h),
                "h2h_agree": sum(p["direction"] == m[0] for p, o, m in h2h)}

    status = [r["status"] for r in rows]
    totals = {"predictions": len(preds), "with_view": sum(float(p["confidence"]) > 0.50 for p in preds),
              "trades": len(rows), "pending": status.count("PENDING"), "open": status.count("OPEN"),
              "closed": status.count("CLOSED"),
              "pnl_closed": sum(float(r["pnl_pct"]) for r in rows if r["status"] == "CLOSED"),
              "pnl_marked": sum(float(r["pnl_pct"]) for r in rows if r["status"] in ("OPEN", "CLOSED"))}

    md = ["# v0.29-live — live earnings reader: results", "",
          f"Scored {now.astimezone(NY):%Y-%m-%d %H:%M} New York time by "
          "`python backtest/live_earnings_reader.py --score`. Every call is scored from the first regular-session "
          f"open after its decision date (adjusted open) to the adjusted close of the {HOLD}th session; costs "
          f"{100 * COST_SIDE:.2f} % per side plus {100 * SHORT_FIN_YR:.0f} %/yr short financing on DOWN calls. "
          "Hit = the move went the called way, before costs; hit rates and means use closed calls only.", "",
          "## Counts", "",
          "| predictions | with a view (> 0.50) | trades | pending | open | closed |",
          "|---:|---:|---:|---:|---:|---:|",
          f"| {totals['predictions']} | {totals['with_view']} | {totals['trades']} | {totals['pending']} | "
          f"{totals['open']} | {totals['closed']} |", ""]
    if unpriced:
        md += [f"{unpriced} prediction(s) could not be priced this run.", ""]
    md += ["## Calibration: every call with confidence > 0.50, traded or not", ""] + stats_table(calib, "confidence")
    md += ["", f"## Paper trades (confidence >= {GATE[1][0]:.2f}: {100 * GATE[1][1]:.0f} % of the portfolio; "
           f">= {GATE[0][0]:.2f}: {100 * GATE[0][1]:.0f} %)", "",
           f"Total pnl_pct (size x net, share of the portfolio): closed {pc(totals['pnl_closed'], 3)}; "
           f"including open marks {pc(totals['pnl_marked'], 3)}.", ""]
    if rows:
        md += ["| id | call | conf | size | entry | exit / mark | net | pnl_pct | status |",
               "|---|---|---:|---:|---|---|---:|---:|---|"]
        for r in rows:
            head = f"| {r['id']} | {r['direction']} | {float(r['confidence']):.2f} | {100 * float(r['size']):.0f} % |"
            if r["status"] == "PENDING":
                md.append(f"{head} | | | | PENDING |")
            else:
                md.append(f"{head} {r['entry_date']} @ {float(r['entry_price']):.2f} | {r['exit_date']} @ "
                          f"{float(r['exit_price']):.2f} | {pc(float(r['net']))} | {pc(float(r['pnl_pct']), 3)} | "
                          f"{r['status']} |")
    md += ["", "## Model (model.json) on the same events", ""]
    if msec is None:
        md.append("model.json not found: Phase A has not written it yet.")
    else:
        md += [f"Model calls on {msec['n']} recorded events ({msec['skipped']} skipped: no s1 or reaction).", ""]
        md += stats_table(msec["table"], "model confidence")
        md += ["", f"Head to head on closed events where Claude had a view: Claude {msec['h2h_claude']} of "
               f"{msec['h2h_n']}, model {msec['h2h_model']} of {msec['h2h_n']}; same direction on "
               f"{msec['h2h_agree']} of {msec['h2h_n']}."]
    results_path = os.path.join(data_dir, RESULTS_MD)
    with open(results_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    print(f"{totals['trades']} trade(s): {totals['pending']} pending, {totals['open']} open, {totals['closed']} "
          f"closed; pnl closed {pc(totals['pnl_closed'], 3)}, with open marks {pc(totals['pnl_marked'], 3)}; "
          f"{len(preds)} prediction(s) -> {results_path}")
    return {"ledger": rows, "calibration": calib, "model": msec, "totals": totals}


# ---------------------------------------------------------------------------- --selftest

def _synthetic_bars() -> dict:
    """Sessions 2026-01-02 .. 2026-02-27 without the MLK (01-19) and Presidents' Day (02-16) holidays.
    Flat filler prices; the sessions the hand computations use are set explicitly."""
    holidays = {date(2026, 1, 19), date(2026, 2, 16)}
    sessions = [d for d in (date(2026, 1, 2) + timedelta(days=k) for k in range(57))
                if d.weekday() < 5 and d not in holidays]
    base = {"AAA": 50.0, "BBB": 80.0, "CCC": 20.0, "DDD": 40.0, "EEE": 30.0, "FFF": 60.0, "GGG": 25.0, "HHH": 10.0}
    out = {t: pd.DataFrame({"open": p, "close": p, "adjclose": p}, index=sessions) for t, p in base.items()}
    entry, exit_ = date(2026, 1, 8), date(2026, 2, 5)          # session 1 and session 20 after 2026-01-07
    out["AAA"].loc[entry, ["open", "close", "adjclose"]] = [50.00, 51.00, 50.49]   # adj open 50 * 0.99 = 49.50
    out["AAA"].loc[exit_, "adjclose"] = 54.45                                      # 54.45 / 49.50 = +10 %
    out["BBB"].loc[entry, ["open", "close", "adjclose"]] = [80.00, 82.00, 80.36]   # adj open 80 * 0.98 = 78.40
    out["BBB"].loc[exit_, "adjclose"] = 70.56                                      # 70.56 / 78.40 = -10 %
    out["DDD"].loc[date(2026, 2, 27), "adjclose"] = 38.0                           # mark after 5 sessions: -5 %
    out["FFF"].loc[exit_, "adjclose"] = 57.0                                       # -5 %
    out["GGG"].loc[exit_, "adjclose"] = 26.0                                       # +4 %
    out["HHH"].loc[exit_, "adjclose"] = 11.0                                       # +10 %
    return out


_TOY_MODEL = {"intercept": -0.1, "coef": [2.0, -1.0, 0.5],
              "s1_quantiles": [1.0, 2.0, 3.0], "s2_quantiles": [1.0, 2.0, 3.0]}


def _close(a, b, tol: float = 1e-9) -> bool:
    return a is not None and b is not None and abs(float(a) - float(b)) <= tol


def _selftest_units(check) -> None:
    check("gate 0.69 -> no trade", gate_size(0.69) == 0.0)
    check("gate 0.70 -> 1 %", gate_size(0.70) == 0.01)
    check("gate 0.89 -> 1 %", gate_size(0.89) == 0.01)
    check("gate 0.90 -> 2 %", gate_size(0.90) == 0.02)
    check("gate 1.00 -> 2 %", gate_size(1.00) == 0.02)
    check("norm: BRK/B, brk-b, BF-B",
          (norm("BRK/B"), norm(" brk-b "), norm("BF-B")) == ("BRK.B", "BRK.B", "BF.B"))
    check("yahoo symbol BRK.B -> BRK-B", yahoo_symbol("BRK.B") == "BRK-B")
    q = [1.0, 2.0, 3.0]
    check("pct below / tie / above", (pct(0.5, q), pct(2.0, q), pct(9.0, q)) == (0.125, 0.625, 0.875))
    # p1 0.625, p2 0.125: z = -0.1 + 1.25 - 0.125 + 0.5 * 0.078125 = 1.0640625 -> 1 / (1 + e^-z) = 0.743466...
    check("model p_up (p1 0.625, p2 0.125)", _close(model_p_up(_TOY_MODEL, 2.0, 0.5), 0.7434661285929933, 1e-12))
    d, c = model_call(_TOY_MODEL, 2.0, 0.5)
    check("model call UP at 0.7435", d == "UP" and _close(c, 0.7434661285929933, 1e-12))
    # p1 0.125, p2 0.875: z = -0.1 + 0.25 - 0.875 + 0.5 * 0.109375 = -0.6703125 -> p_up 0.338427 -> DOWN 0.661573
    d, c = model_call(_TOY_MODEL, 0.5, 9.0)
    check("model call DOWN at 0.6616", d == "DOWN" and _close(c, 0.6615731296489828, 1e-12))
    check("entry open 2026-01-08 = 14:30Z (EST)",
          entry_open_utc(date(2026, 1, 8)) == datetime(2026, 1, 8, 14, 30, tzinfo=timezone.utc))
    check("entry open 2026-07-02 = 13:30Z (EDT)",
          entry_open_utc(date(2026, 7, 2)) == datetime(2026, 7, 2, 13, 30, tzinfo=timezone.utc))

    page = ('<table class="wikitable" id="constituents"><tbody>'
            '<tr><th>Symbol</th><th>Security</th><th>CIK</th></tr>'
            '<tr><td><a href="x" data-mw=\'{"a":">"}\'>BRK.B</a><!-- DO NOT CHANGE. YOU\'VE BEEN WARNED! --></td>'
            '<td>Berkshire &amp; Co</td><td>0001067983</td></tr></tbody></table>')
    got = parse_constituents(page)
    check("wikipedia row: comment, quoted '>', entity",
          got == [{"symbol": "BRK.B", "name": "Berkshire & Co", "cik": "0001067983"}], str(got))
    doc = ("<DOCUMENT>\n<TYPE>EX-99.1\n<TEXT>\n<html><head><title>Document</title><style>p{x:1}</style></head>"
           "<body><p>Revenue&nbsp;rose <b>5%</b></p><table><tr><td>$</td><td>1,234</td></tr></table>"
           "<script>var a</script></body></html>\n</TEXT>\n</DOCUMENT>")
    got = html_to_text(doc)
    check("html to text", got == "Revenue rose 5%\n$ 1,234", repr(got))
    check("truncate to 3 words", truncate_words("a b\nc d\ne", 3) == "a b\nc")
    check("exhibit: Workiva 'exhibit991'",
          choose_exhibit(["nke-20261001.htm", "q1fy27exhibit991er.htm", "R1.htm"]) == ("q1fy27exhibit991er.htm", True))
    check("exhibit: prefers 99.1 over 99.2",
          choose_exhibit(["d1dex992.htm", "d1dex991.htm"]) == ("d1dex991.htm", True)
          and choose_exhibit(["ex99-2.htm", "ex99_1.htm"]) == ("ex99_1.htm", True))
    check("exhibit: 99.2 alone is not preferred; 99.10 is not 99.1",
          choose_exhibit(["ex99-2.htm"]) == ("ex99-2.htm", False)
          and choose_exhibit(["ex99-10.htm"]) == ("ex99-10.htm", False))
    idx = ('<tr><td>1</td><td>8-K</td><td><a href="/ix?doc=/Archives/x/main.htm">main.htm</a></td><td>8-K</td></tr>'
           '<tr><td>2</td><td>PR</td><td><a href="/Archives/x/pressrel.htm">pressrel.htm</a></td><td>EX-99.1</td></tr>')
    check("exhibit from the index page's Type column", exhibit_from_index_page(idx) == "pressrel.htm")
    sub = {"filings": {"recent": {
        "form": ["10-Q", "8-K", "8-K", "8-K/A", "8-K"],
        "items": ["", "5.02,9.01", "2.02,9.01", "2.02", "2.02,9.01"],
        "filingDate": ["2026-10-02", "2026-10-01", "2026-10-01", "2026-10-02", "2026-09-20"],
        "acceptanceDateTime": ["a", "b", "2026-10-01T20:15:15.000Z", "d", "e"],
        "accessionNumber": ["n0", "n1", "n2", "n3", "n4"]}}}
    check("8-K with item 2.02 closest to T1",
          (pick_8k(sub, date(2026, 10, 1), date(2026, 10, 2)) or {}).get("accession") == "n2")
    check("8-K outside the window -> None", pick_8k(sub, date(2026, 8, 3), date(2026, 8, 4)) is None)


def _selftest_record(check, tmp: str) -> None:
    ev = {"eps": 1.0, "eps_forecast": 0.9, "s1": 0.002, "reaction_abnormal": -0.01,
          "press_release_url": "u", "missing_press_release": False}
    queue = {"date": "2026-01-07", "report_date": "2026-01-06",
             "events": [dict(ev, ticker=x) for x in ("AAA", "BBB", "FFF", "BRK.B")]}
    os.makedirs(f"{tmp}/queue")
    with open(f"{tmp}/queue/2026-01-07.json", "w") as f:
        json.dump(queue, f)
    bad = [{"ticker": "AAA", "direction": "UP", "confidence": 1.2, "reason": "x"},     # range + already recorded
           {"ticker": "BBB", "direction": "FLAT", "confidence": 0.7, "reason": "x"},
           {"ticker": "FFF", "direction": "UP", "confidence": 0.7, "reason": " "},
           {"ticker": "ZZZ", "direction": "UP", "confidence": 0.7, "reason": "x"},
           {"ticker": "brk-b", "direction": "down", "confidence": 0.5, "reason": "x"},  # the good one
           {"ticker": "BRK/B", "direction": "UP", "confidence": 0.6, "reason": "x"}]    # same ticker twice
    errs, ok = validate_predictions(bad, queue, {("2026-01-06", "AAA")})
    check("validation: 6 problems in 5 rows, BRK.B accepted",
          len(errs) == 6 and [c["event"]["ticker"] for c in ok] == ["BRK.B"], "; ".join(errs))

    calls = [{"ticker": "AAA", "direction": "UP", "confidence": 0.90, "reason": "beat and raise"},
             {"ticker": "BBB", "direction": "DOWN", "confidence": 0.69, "reason": "guide cut"},
             {"ticker": "FFF", "direction": "UP", "confidence": 0.70, "reason": "margin beat"}]
    with open(f"{tmp}/calls.json", "w") as f:
        json.dump(calls, f)
    with open(f"{tmp}/late.json", "w") as f:
        json.dump([{"ticker": "BRK.B", "direction": "UP", "confidence": 0.8, "reason": "x"}], f)
    evening = datetime(2026, 1, 7, 23, 0, tzinfo=timezone.utc)
    pred_file, ledger_file = f"{tmp}/{PREDICTIONS_JSONL}", f"{tmp}/{LEDGER_CSV}"
    record(date(2026, 1, 7), f"{tmp}/calls.json", dry_run=True, now=evening, data_dir=tmp)
    check("record --dry-run writes nothing", not os.path.exists(pred_file) and not os.path.exists(ledger_file))
    record(date(2026, 1, 7), f"{tmp}/calls.json", now=evening, data_dir=tmp)
    led = [(r["id"], r["size"], r["status"]) for r in read_ledger(ledger_file)]
    check("record: 3 calls; trades AAA 2 % (0.90), FFF 1 % (0.70), none for BBB (0.69)",
          len(read_predictions(pred_file)) == 3
          and led == [("2026-01-06_AAA", "0.02", "PENDING"), ("2026-01-06_FFF", "0.01", "PENDING")], str(led))
    for label, calls_file, when in (("duplicate calls refused", "calls.json", evening),
                                    ("call after the next 09:30 ET open refused", "late.json",
                                     datetime(2026, 1, 8, 14, 31, tzinfo=timezone.utc))):
        try:
            record(date(2026, 1, 7), f"{tmp}/{calls_file}", now=when, data_dir=tmp)
            check(label, False, "no refusal")
        except SystemExit:
            check(label, len(read_predictions(pred_file)) == 3)


def _ledger_row(ticker: str, decision: str, direction: str, conf: float, recorded: str) -> dict:
    return {"id": f"x_{ticker}", "ticker": ticker, "report_date": "x", "decision_date": decision,
            "direction": direction, "confidence": conf, "size": gate_size(conf), "recorded_utc": recorded,
            "status": "PENDING"}


def _selftest_score(check, tmp: str) -> None:
    sdir = f"{tmp}/score"
    os.makedirs(sdir)
    good = [_ledger_row("AAA", "2026-01-07", "UP", 0.92, "2026-01-07T23:00:00Z"),
            _ledger_row("BBB", "2026-01-07", "DOWN", 0.75, "2026-01-08T14:29:00Z"),   # 09:29 EST, a minute early
            _ledger_row("DDD", "2026-02-20", "DOWN", 0.80, "2026-02-20T22:00:00Z"),
            _ledger_row("EEE", "2026-02-27", "UP", 0.70, "2026-02-27T22:00:00Z")]
    write_ledger(f"{sdir}/{LEDGER_CSV}", good)
    inputs = {"AAA": (2.0, 0.5), "BBB": (0.5, 9.0), "DDD": (0.5, 9.0), "EEE": (2.0, 0.5), "FFF": (2.0, 0.5),
              "GGG": (2.0, 0.5), "HHH": (None, 0.1)}               # toy model: (2.0, 0.5) -> UP, (0.5, 9.0) -> DOWN
    preds = good + [_ledger_row("FFF", "2026-01-07", "UP", 0.60, "2026-01-07T23:00:00Z"),
                    _ledger_row("GGG", "2026-01-07", "UP", 0.50, "2026-01-07T23:00:00Z"),
                    _ledger_row("HHH", "2026-01-07", "UP", 0.55, "2026-01-07T23:00:00Z")]
    with open(f"{sdir}/{PREDICTIONS_JSONL}", "w") as f:
        for p in preds:
            s1, s2 = inputs[p["ticker"]]
            f.write(json.dumps(dict(p, reason="r", s1=s1, reaction_abnormal=s2)) + "\n")
    with open(f"{sdir}/{MODEL_JSON}", "w") as f:
        json.dump(_TOY_MODEL, f)
    after = datetime(2026, 3, 2, 22, 0, tzinfo=timezone.utc)
    try:
        res = score(f"{sdir}/{LEDGER_CSV}", now=after)
    except AssertionError as err:                     # e.g. 09:29 ET judged to be after the open
        check("score the hand-computed ledger", False, str(err))
        return
    by = {r["ticker"]: r for r in res["ledger"]}
    a, b, dd, e = by["AAA"], by["BBB"], by["DDD"], by["EEE"]
    check("AAA UP: entry 2026-01-08 @ 49.50 (adjusted open), exit 2026-02-05 @ 54.45 (session 20)",
          (a["entry_date"], a["exit_date"], a["status"]) == ("2026-01-08", "2026-02-05", "CLOSED")
          and _close(a["entry_price"], 49.50) and _close(a["exit_price"], 54.45), str(a))
    check("AAA UP: ret +10 %, net +9.8 %, pnl_pct 0.02 x 0.098 = 0.00196",
          _close(a["ret"], 0.10) and _close(a["net"], 0.098) and _close(a["pnl_pct"], 0.00196), str(a))
    check("BBB DOWN: entry 78.40, exit 70.56, ret +10 %",
          _close(b["entry_price"], 78.40) and _close(b["exit_price"], 70.56) and _close(b["ret"], 0.10)
          and b["status"] == "CLOSED", str(b))
    # 0.10 - 0.002 - 0.03 * 20 / 252 = 0.0956190476...; x 0.01
    check("BBB DOWN: net 0.0956190476 (fees + 20/252 yr financing), pnl_pct 0.000956190476",
          _close(b["net"], 0.0956190476190476, 1e-12) and _close(b["pnl_pct"], 0.000956190476190476, 1e-12), str(b))
    # 0.05 - 0.002 - 0.03 * 5 / 252 = 0.0474047619...
    check("DDD DOWN: OPEN, marked 2026-02-27 @ 38 after 5 sessions, net 0.0474047619",
          (dd["status"], dd["entry_date"], dd["exit_date"]) == ("OPEN", "2026-02-23", "2026-02-27")
          and _close(dd["exit_price"], 38.0) and _close(dd["net"], 0.0474047619047619, 1e-12)
          and _close(dd["pnl_pct"], 0.000474047619047619, 1e-12), str(dd))
    check("EEE: PENDING until a session after its decision exists", (e["status"], e["entry_date"]) == ("PENDING", ""))
    back = {r["ticker"]: r for r in read_ledger(f"{sdir}/{LEDGER_CSV}")}
    check("ledger re-loads with the same numbers", _close(back["BBB"]["net"], b["net"])
          and _close(back["AAA"]["pnl_pct"], 0.00196) and back["DDD"]["status"] == "OPEN")
    cal = {r["bucket"]: r for r in res["calibration"]}
    check("calibration: the 0.50 call excluded; closed 4, hits 3, open 1, pending 1",
          tuple(cal["all"][k] for k in ("closed", "hits", "open", "pending")) == (4, 3, 1, 1), str(cal["all"]))
    check("calibration buckets", (cal["[0.50-0.60)"]["hits"], cal["[0.60-0.70)"]["hits"], cal["[0.70-0.80)"]["hits"],
                                  cal["[0.80-0.90)"]["open"], cal["[0.90-1.00]"]["hits"]) == (1, 0, 1, 1, 1)
          and _close(cal["[0.60-0.70)"]["mean_net"], -0.052))
    m = res["model"]
    check("model: 6 events (HHH has no s1), closed 4, hits 3 (FFF missed)",
          m is not None and (m["n"], m["skipped"], m["table"][-1]["closed"], m["table"][-1]["hits"]) == (6, 1, 4, 3),
          str(m and m["table"][-1]))
    check("results.md written", os.path.exists(f"{sdir}/{RESULTS_MD}"))

    # a call recorded one minute AFTER its entry open must stop the scoring
    bad_dir = f"{tmp}/lookahead"
    os.makedirs(bad_dir)
    late = _ledger_row("CCC", "2026-01-07", "UP", 0.95, "2026-01-08T14:31:00Z")
    write_ledger(f"{bad_dir}/{LEDGER_CSV}", good[:1] + [late])
    label = "call recorded 09:31 ET on its entry day trips the lookahead assertion"
    try:
        score(f"{bad_dir}/{LEDGER_CSV}", now=after)
        check(label, False, "no assertion")
    except AssertionError as err:
        check(label, "LOOKAHEAD" in str(err), str(err))


def selftest() -> None:
    """Offline: synthetic sessions and prices replace Yahoo; every file goes to a temporary directory."""
    global bars
    outcomes = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        outcomes.append(bool(ok))
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"   [{detail}]" if detail and not ok else ""))

    _selftest_units(check)
    synth = _synthetic_bars()

    def fake_bars(ticker: str, lo: date, hi: date, today: Optional[date] = None) -> pd.DataFrame:
        df = synth[ticker]
        return df[[lo <= x < hi for x in df.index]]          # Yahoo's window: period1 <= session < period2

    real_bars, bars = bars, fake_bars
    try:
        with tempfile.TemporaryDirectory() as tmp:
            _selftest_record(check, tmp)
            _selftest_score(check, tmp)
    finally:
        bars = real_bars
    failed = outcomes.count(False)
    print(f"selftest: {len(outcomes) - failed} passed, {failed} failed")
    if failed:
        sys.exit(1)


# ---------------------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description="v0.29-live Phase B: live earnings reader")
    ap.add_argument("--selftest", action="store_true", help="offline test on synthetic prices")
    ap.add_argument("--refresh-universe", action="store_true", help="download the S&P 500 list to sp500.csv")
    ap.add_argument("--prepare", action="store_true", help="build reading packets for T into queue/<T>.json")
    ap.add_argument("--record", action="store_true", help="record calls for T and open paper trades")
    ap.add_argument("--score", action="store_true", help="price the ledger and write results.md")
    ap.add_argument("--date", type=date.fromisoformat, help="T, YYYY-MM-DD (--prepare default: today in New York)")
    ap.add_argument("--predictions", help="JSON list of {ticker, direction, confidence, reason}")
    ap.add_argument("--dry-run", action="store_true", help="--prepare: write queue_dryrun/; --record: write nothing")
    ap.add_argument("--ledger", help="ledger to score; predictions.jsonl, model.json and results.md beside it")
    a = ap.parse_args()
    if a.record and (a.date is None or not a.predictions):
        ap.error("--record needs --date and --predictions")
    predictions = os.path.abspath(a.predictions) if a.predictions else None
    ledger = os.path.abspath(a.ledger) if a.ledger else os.path.join(ROOT, LEDGER)
    os.chdir(ROOT)                    # every data path, and daily()'s price cache, is relative to the repo root
    if not (a.selftest or a.refresh_universe or a.prepare or a.record or a.score):
        ap.print_help()
        return
    if a.selftest:
        selftest()
    if a.refresh_universe:
        refresh_universe()
    if a.prepare:
        prepare(a.date, a.dry_run)
    if a.record:
        record(a.date, predictions, a.dry_run)
    if a.score:
        score(ledger)


if __name__ == "__main__":
    main()
