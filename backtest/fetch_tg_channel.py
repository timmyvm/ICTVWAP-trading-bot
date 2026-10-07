"""
Public Telegram channel -> CSV of its messages (id, UTC time, kind, text), via the public web preview
https://t.me/s/<channel>?before=<id>. Only PUBLIC channels have this preview; a private invite link
(t.me/+...) shows a join page and nothing else.

Polite by design: one page (~20 messages) per --delay seconds, every page cached in --raw-dir so a
re-run only fetches what is missing. Gaps in message ids are kept (the CSV lists every id the preview
returned); ids that never appear were deleted or are service messages, and are counted in the summary.

  python3 backtest/fetch_tg_channel.py tradesmartacademy --out backtest/data_cache/local/tg/tradesmartacademy_messages.csv
"""

import argparse
import html
import os
import re
import sys
import time

import pandas as pd
import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36"}


def parse_page(s: str) -> list:
    out = []
    for b in re.split(r'<div class="tgme_widget_message_wrap', s)[1:]:
        mid = re.search(r'data-post="[^/]+/(\d+)"', b)
        dt = re.search(r'<time datetime="([^"]+)"', b)
        if not mid or not dt:
            continue
        txt = re.search(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', b, re.S)
        t = ""
        if txt:
            t = re.sub(r"<br\s*/?>", "\n", txt.group(1))
            t = html.unescape(re.sub(r"<[^>]+>", "", t)).strip()
        kind = ("photo" if "tgme_widget_message_photo" in b else
                "voice" if "tgme_widget_message_voice" in b else
                "video" if "tgme_widget_message_video" in b else "text")
        out.append({"id": int(mid.group(1)), "utc": pd.Timestamp(dt.group(1)).tz_convert("UTC"),
                    "kind": kind, "text": t})
    return out


def fetch(channel: str, raw_dir: str, delay: float, stop_before: str | None) -> pd.DataFrame:
    os.makedirs(raw_dir, exist_ok=True)
    sess = requests.Session()
    sess.headers.update(HEADERS)
    rows, before = [], None
    stop_ts = pd.Timestamp(stop_before, tz="UTC") if stop_before else None
    while True:
        key = os.path.join(raw_dir, f"{channel}_{before or 'latest'}.html")
        if os.path.exists(key) and before is not None:
            s = open(key, encoding="utf-8").read()
        else:
            url = f"https://t.me/s/{channel}" + (f"?before={before}" if before else "")
            for k in range(6):
                time.sleep(delay)
                r = sess.get(url, timeout=30)
                if r.status_code == 429:
                    time.sleep(30 * (k + 1))
                    continue
                r.raise_for_status()
                break
            s = r.text
            with open(key, "w", encoding="utf-8") as f:
                f.write(s)
        page = parse_page(s)
        if not page:
            break
        rows.extend(page)
        low = min(p["id"] for p in page)
        if low <= 1 or (stop_ts is not None and min(p["utc"] for p in page) < stop_ts):
            break
        before = low
        if len(rows) % 500 < 20:
            print(f"  {channel}: {len(rows)} messages, back to {min(p['utc'] for p in page):%Y-%m-%d}", flush=True)
    df = pd.DataFrame(rows).drop_duplicates("id").sort_values("id").reset_index(drop=True)
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("channel")
    ap.add_argument("--out", required=True)
    ap.add_argument("--raw-dir", default="backtest/data_cache/local/tg_raw")
    ap.add_argument("--delay", type=float, default=1.5)
    ap.add_argument("--since", default=None, help="stop once messages are older than this UTC date")
    a = ap.parse_args()
    df = fetch(a.channel, a.raw_dir, a.delay, a.since)
    df.to_csv(a.out, index=False)
    back = pd.read_csv(a.out)
    span = back["id"].max() - back["id"].min() + 1
    print(f"saved+reloaded {a.out}: {len(back)} messages, ids {back['id'].min()}-{back['id'].max()} "
          f"({span - len(back)} ids absent: deleted or service messages), {back['utc'].min()} -> {back['utc'].max()}")
    print("TG_DONE")


if __name__ == "__main__":
    sys.exit(main())
