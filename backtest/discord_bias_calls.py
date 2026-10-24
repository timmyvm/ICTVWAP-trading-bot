"""
v0.35-audit Addendum A5 — the caller's pre-market bias calls, extracted blind and double-coded (DEVLOG).

Inputs and outputs are local and gitignored (the repository is public):
  backtest/data_cache/local/discord/v035_config.json   {"analysis": "<path to the analysis-channel export>", "caller": ...}
  backtest/data_cache/local/discord/v036/bias_days.jsonl     one line per session: day number + pre-open posts
  backtest/data_cache/local/discord/v036/bias_daymap.json    day number -> NY session date (read only when scoring)
  backtest/data_cache/local/discord/v036/biasA.jsonl, biasB.jsonl   two independent label passes
  backtest/data_cache/local/discord/v036/bias_frozen.jsonl   agreed labels (+ sha256 printed for the DEVLOG)

Session assignment (New York time): a post before 09:30 belongs to that weekday's session; a post at or after
16:00, or on a weekend, belongs to the next weekday's session; posts between 09:30 and 16:00 are intraday and
excluded. A post edited after its session's 09:30 open is excluded (counted). Dates never reach the labellers.

Rubric (the labellers get this text verbatim):
  BULL         the posts state or clearly imply an up session or a preference for calls/longs today, without an
               equally weighted opposite case ("bias bullish", "looking for calls", "favor upside",
               "bullish above X" with no bearish branch)
  BEAR         the mirror image
  CONDITIONAL  if/then plans for both directions with no stated lean ("above X calls, below Y puts"), or a lean
               explicitly suspended ("no bias until X breaks")
  NEUTRAL      explicitly no trade, chop, no bias, or sitting out
  NONE         no directional content: levels without a direction, news reminders, greetings, images only
  When the lean changes across the pre-open posts, the LAST lean counts.

  python3 backtest/discord_bias_calls.py --prepass
  python3 backtest/discord_bias_calls.py --freeze
  python3 backtest/discord_bias_calls.py --selftest
"""

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from datetime import date, datetime, time, timedelta
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

LOCAL = "backtest/data_cache/local/discord"
CONFIG = f"{LOCAL}/v035_config.json"
OUT = f"{LOCAL}/v036"
NY = ZoneInfo("America/New_York")
OPEN_T, CLOSE_T = time(9, 30), time(16, 0)
LABELS = ("BULL", "BEAR", "CONDITIONAL", "NEUTRAL", "NONE")


def parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def next_weekday(d: date) -> date:
    d += timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def session_of(t_utc: datetime) -> Optional[date]:
    """The session a post speaks to, or None for an intraday post."""
    t = t_utc.astimezone(NY)
    d = t.date()
    if d.weekday() >= 5:
        return next_weekday(d)
    if t.time() < OPEN_T:
        return d
    if t.time() >= CLOSE_T:
        return next_weekday(d)
    return None


def session_open(d: date) -> datetime:
    return datetime.combine(d, OPEN_T, tzinfo=NY)


def rel(t_utc: datetime, d: date) -> str:
    mins = int((session_open(d) - t_utc.astimezone(NY)).total_seconds() // 60)
    return f"-{mins // 60:02d}:{mins % 60:02d}"


def prepass() -> int:
    cfg = json.load(open(CONFIG, encoding="utf-8"))
    raw = json.load(open(cfg["analysis"], encoding="utf-8"))
    msgs = [m for m in raw["messages"] if m["author"]["name"] == cfg["caller"]]
    assert len(raw["messages"]) == raw.get("messageCount", len(raw["messages"])), "export is incomplete"
    days: Dict[date, List[dict]] = {}
    counts = Counter()
    for m in msgs:
        t = parse_ts(m["timestamp"])
        d = session_of(t)
        if d is None:
            counts["intraday"] += 1
            continue
        if m.get("timestampEdited") and parse_ts(m["timestampEdited"]) >= session_open(d):
            counts["edited after the open"] += 1
            continue
        counts["pre-open"] += 1
        days.setdefault(d, []).append({"t": t, "text": m["content"], "attach": len(m.get("attachments") or [])})
    os.makedirs(OUT, exist_ok=True)
    daymap = {}
    with open(f"{OUT}/bias_days.jsonl", "w", encoding="utf-8") as f:
        for k, d in enumerate(sorted(days), 1):
            daymap[k] = d.isoformat()
            posts = [{"rel": rel(p["t"], d), "text": p["text"], "attach": p["attach"]}
                     for p in sorted(days[d], key=lambda p: p["t"])]
            f.write(json.dumps({"day": k, "posts": posts}, ensure_ascii=False) + "\n")
    json.dump(daymap, open(f"{OUT}/bias_daymap.json", "w"), indent=0)
    print(f"caller posts {len(msgs)}: {dict(counts)}; sessions with pre-open posts {len(days)}")
    return 0


def load_labels(path: str) -> Dict[int, str]:
    out = {}
    for line in open(path, encoding="utf-8"):
        if line.strip():
            r = json.loads(line)
            lab = str(r["label"]).upper()
            assert lab in LABELS, f"{path}: bad label {lab}"
            out[int(r["day"])] = lab
    return out


def agree(a: Dict[int, str], b: Dict[int, str]) -> Tuple[Dict[int, str], Counter]:
    frozen, c = {}, Counter()
    for k in sorted(set(a) | set(b)):
        la, lb = a.get(k), b.get(k)
        if la is None or lb is None:
            c["missing in one pass"] += 1
        elif la == lb:
            frozen[k] = la
            c["agreed"] += 1
        else:
            c["disagreed (excluded)"] += 1
    return frozen, c


def freeze() -> int:
    days = [json.loads(x)["day"] for x in open(f"{OUT}/bias_days.jsonl", encoding="utf-8") if x.strip()]
    a, b = load_labels(f"{OUT}/biasA.jsonl"), load_labels(f"{OUT}/biasB.jsonl")
    print(f"sessions {len(days)}, pass A {len(a)}, pass B {len(b)}")
    both = [k for k in days if k in a and k in b]
    print(f"agreement {100 * sum(a[k] == b[k] for k in both) / max(len(both), 1):.1f}% over {len(both)} sessions")
    print("pass A:", dict(Counter(a.values())), " pass B:", dict(Counter(b.values())))
    frozen, c = agree(a, b)
    print(dict(c), " agreed labels:", dict(Counter(frozen.values())))
    path = f"{OUT}/bias_frozen.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for k in sorted(frozen):
            f.write(json.dumps({"day": k, "label": frozen[k]}) + "\n")
    print("sha256", hashlib.sha256(open(path, "rb").read()).hexdigest())
    return 0


def selftest() -> int:
    ok = True

    def check(name: str, cond: bool) -> None:
        nonlocal ok
        ok &= bool(cond)
        print(f"{'PASS' if cond else 'FAIL'}  {name}")

    u = lambda s: datetime.fromisoformat(s).replace(tzinfo=NY).astimezone(ZoneInfo("UTC"))
    check("pre-open post -> same session", session_of(u("2025-03-04T08:15:00")) == date(2025, 3, 4))
    check("intraday post -> excluded", session_of(u("2025-03-04T09:30:00")) is None)
    check("after the close -> next weekday", session_of(u("2025-03-04T16:00:00")) == date(2025, 3, 5))
    check("Friday evening -> Monday", session_of(u("2025-03-07T18:00:00")) == date(2025, 3, 10))
    check("Sunday -> Monday", session_of(u("2025-03-09T20:00:00")) == date(2025, 3, 10))
    check("offset to the open", rel(u("2025-03-04T08:15:00"), date(2025, 3, 4)) == "-01:15")
    fr, c = agree({1: "BULL", 2: "BEAR", 3: "NONE"}, {1: "BULL", 2: "BULL", 4: "BEAR"})
    check("only agreed labels are frozen", fr == {1: "BULL"} and c["disagreed (excluded)"] == 1
          and c["missing in one pass"] == 2)
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prepass", action="store_true")
    ap.add_argument("--freeze", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.prepass:
        return prepass()
    if a.freeze:
        return freeze()
    return 0


if __name__ == "__main__":
    sys.exit(main())
