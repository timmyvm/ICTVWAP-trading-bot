"""
Block private-source material from reaching this PUBLIC repository (v0.35-audit).

Scans the lines a commit would ADD (`git diff --cached`, or a given diff range) for:
  - terms in a local denylist (default backtest/data_cache/local/discord/denylist.txt, gitignored:
    server, channel and member names that must never be committed);
  - Discord snowflake ids (17-20 digit integers), Discord and Discord-CDN links, and links to the
    checkout marketplace the audited server sells through.
It prints only the file, line number and a pattern id, never the matched text, so its own output
leaks nothing (the v0.27 leak-scan convention). Exit status 1 on any hit.

  python3 backtest/privacy_check.py                 # staged changes
  python3 backtest/privacy_check.py --range HEAD~1  # changes since a commit
"""

import argparse
import os
import re
import subprocess
import sys
from typing import List, Tuple

DEFAULT_DENYLIST = "backtest/data_cache/local/discord/denylist.txt"
GENERIC = [
    ("snowflake-id", re.compile(r"(?<![0-9A-Za-z])\d{17,20}(?![0-9A-Za-z])")),
    ("discord-link", re.compile(r"discord(app)?\.(com|gg)/", re.I)),
    ("discord-cdn", re.compile(r"cdn\.discordapp\.com", re.I)),
    ("checkout-link", re.compile(r"whop\.com/", re.I)),
]


def added_lines(diff: str) -> List[Tuple[str, int, str]]:
    """(file, new line number, text) for every added line of a unified diff."""
    out, path, line = [], "", 0
    for raw in diff.splitlines():
        if raw.startswith("+++ "):
            path = raw[6:] if raw.startswith("+++ b/") else raw[4:]
        elif raw.startswith("@@"):
            m = re.search(r"\+(\d+)", raw)
            line = int(m.group(1)) if m else 0
        elif raw.startswith("+") and not raw.startswith("+++"):
            out.append((path, line, raw[1:]))
            line += 1
        elif not raw.startswith("-"):
            line += 1
    return out


SELF = "backtest/privacy_check.py"   # the checker's own source contains its patterns and test fixtures, no exported data


def scan(lines: List[Tuple[str, int, str]], terms: List[str]) -> List[Tuple[str, int, str]]:
    hits = []
    for path, n, text in lines:
        if path == SELF:
            continue
        low = text.lower()
        for i, t in enumerate(terms):
            if t and t in low:
                hits.append((path, n, f"denylist#{i + 1}"))
        for name, rx in GENERIC:
            if rx.search(text):
                hits.append((path, n, name))
    return hits


def load_terms(path: str) -> List[str]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [ln.strip().lower() for ln in f if ln.strip() and not ln.startswith("#")]


def selftest() -> int:
    diff = ("+++ b/x.md\n@@ -0,0 +1,3 @@\n+fine text here\n+a secret name ACME appears\n"
            "+id 123456789012345678 and https://cdn.discordapp.com/a\n")
    hits = scan(added_lines(diff), ["acme"])
    kinds = sorted(h[2] for h in hits)
    ok = kinds == ["denylist#1", "discord-cdn", "discord-link", "snowflake-id"] and all(h[0] == "x.md" for h in hits) \
        and [h[1] for h in hits if h[2] == "denylist#1"] == [2]
    clean = scan(added_lines("+++ b/y.py\n@@ -1,0 +1,1 @@\n+epoch 1790827080 is ten digits\n"), ["acme"])
    print(f"{'PASS' if ok else 'FAIL'}  hits found with line numbers and pattern ids only")
    print(f"{'PASS' if not clean else 'FAIL'}  a 10-digit epoch is not a snowflake id")
    return 0 if ok and not clean else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--range", default=None, help="diff against this commit instead of the index")
    ap.add_argument("--denylist", default=DEFAULT_DENYLIST)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    cmd = ["git", "diff", "--unified=0"] + ([a.range] if a.range else ["--cached"])
    diff = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    terms = load_terms(a.denylist)
    if not terms:
        print(f"WARNING: denylist {a.denylist} missing or empty; only generic patterns checked")
    hits = scan(added_lines(diff), terms)
    for path, n, kind in hits:
        print(f"BLOCK {path}:{n} {kind}")
    print(f"privacy check: {len(hits)} hit(s) in {len(added_lines(diff))} added lines")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
