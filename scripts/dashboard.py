"""
Read-only web dashboard for the paper-trading forward test.

Serves ONE page (stdlib only, no new dependencies) showing equity, win
rate, per-symbol results, open positions, recent trades, and a bot
heartbeat — so the forward test can be checked from a browser instead of
SSH. Auto-refreshes every 60s.

Security model: read-only, renders only the paper CSV and the bot-log
mtime; no file access beyond that, no actions, no secrets on the page.
Access requires DASHBOARD_TOKEN (set in .env) passed as ?token=... —
the server refuses to start without one. Plain HTTP: fine for paper-
trade numbers; put Caddy in front later if HTTPS is ever wanted.

Run:  python scripts/dashboard.py   (env: DASHBOARD_PORT, default 8080)
"""

import hmac
import html
import logging
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402  (loads .env)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("dashboard")

TOKEN = os.getenv("DASHBOARD_TOKEN", "")
PORT = int(os.getenv("DASHBOARD_PORT", "8080"))
BOT_LOG = "logs/bot.log"


def load_data() -> dict:
    d: dict = {"closed": pd.DataFrame(), "open": pd.DataFrame(),
               "equity": config.PAPER_START_BALANCE, "realized": 0.0}
    try:
        t = pd.read_csv(config.TRADE_LOG_PATH, dtype=str, keep_default_na=False)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return d
    t["qty_f"] = pd.to_numeric(t["qty"], errors="coerce")
    t["pnl_f"] = pd.to_numeric(t["pnl"], errors="coerce")
    dollar = t[t["qty_f"] > 0]
    d["closed"] = dollar[dollar["result"].isin(["STOPPED", "TP_HIT"])].copy()
    d["open"] = dollar[dollar["result"].isin(["PAPER", "OPEN"])].copy()
    d["realized"] = float(d["closed"]["pnl_f"].sum()) if not d["closed"].empty else 0.0
    d["equity"] = config.PAPER_START_BALANCE + d["realized"]
    return d


def sparkline(closed: pd.DataFrame) -> str:
    """Inline SVG of cumulative realized PnL over closed trades."""
    if len(closed) < 2:
        return "<p class='dim'>equity curve appears after a few closed trades</p>"
    cum = closed.sort_values("closed_at")["pnl_f"].cumsum().tolist()
    w, h, pad = 640, 120, 6
    lo, hi = min(min(cum), 0.0), max(max(cum), 0.0)
    span = (hi - lo) or 1.0
    n = len(cum)
    pts = " ".join(
        f"{pad + i * (w - 2 * pad) / (n - 1):.1f},"
        f"{h - pad - (v - lo) / span * (h - 2 * pad):.1f}"
        for i, v in enumerate(cum)
    )
    zero_y = h - pad - (0.0 - lo) / span * (h - 2 * pad)
    color = "#4ade80" if cum[-1] >= 0 else "#f87171"
    return (
        f"<svg viewBox='0 0 {w} {h}' style='width:100%;max-width:{w}px'>"
        f"<line x1='{pad}' y1='{zero_y:.1f}' x2='{w - pad}' y2='{zero_y:.1f}' "
        f"stroke='#3f3f46' stroke-dasharray='4 4'/>"
        f"<polyline points='{pts}' fill='none' stroke='{color}' stroke-width='2'/>"
        f"</svg>"
    )


def heartbeat() -> tuple[str, str]:
    try:
        age = time.time() - os.path.getmtime(BOT_LOG)
    except OSError:
        return "NO LOG", "#f87171"
    if age < 180:
        return f"alive ({int(age)}s ago)", "#4ade80"
    return f"STALE — last log {int(age / 60)} min ago", "#f87171"


def render() -> str:
    d = load_data()
    closed, open_rows = d["closed"], d["open"]
    n = len(closed)
    wins = int((closed["pnl_f"] > 0).sum()) if n else 0
    win_pct = 100.0 * wins / n if n else 0.0
    hb_text, hb_color = heartbeat()
    e = html.escape

    def stat(label, value, sub=""):
        return (f"<div class='card'><div class='dim'>{label}</div>"
                f"<div class='big'>{value}</div><div class='dim'>{sub}</div></div>")

    cards = (
        stat("equity", f"${d['equity']:,.2f}", f"start ${config.PAPER_START_BALANCE:,.0f}")
        + stat("realized pnl", f"${d['realized']:+,.2f}", f"{n} closed trades")
        + stat("win rate", f"{win_pct:.1f}%" if n else "—",
               f"{wins}W / {n - wins}L · target ~58%")
        + stat("bot", f"<span style='color:{hb_color}'>{e(hb_text)}</span>",
               ",".join(config.EMA_BRACKET_SYMBOLS))
    )

    per_sym = ""
    if n and closed["symbol"].nunique() > 1:
        rows = "".join(
            f"<tr><td>{e(s)}</td><td>{len(g)}</td>"
            f"<td>{100 * (g['pnl_f'] > 0).mean():.1f}%</td>"
            f"<td>${g['pnl_f'].sum():+,.2f}</td></tr>"
            for s, g in closed.groupby("symbol")
        )
        per_sym = (f"<h2>per symbol</h2><table><tr><th>symbol</th><th>trades</th>"
                   f"<th>win%</th><th>net</th></tr>{rows}</table>")

    if open_rows.empty:
        open_html = "<p class='dim'>none</p>"
    else:
        open_html = "<table><tr><th>symbol</th><th>dir</th><th>qty</th><th>entry</th><th>SL</th><th>TP</th></tr>" + "".join(
            f"<tr><td>{e(r['symbol'])}</td><td>{e(r['direction'])}</td><td>{e(r['qty'])}</td>"
            f"<td>{e(r['entry'])}</td><td>{e(r['sl'])}</td><td>{e(r['tp'])}</td></tr>"
            for _, r in open_rows.iterrows()
        ) + "</table>"

    if n:
        recent = "<table><tr><th>closed</th><th>symbol</th><th>dir</th><th>entry</th><th>result</th><th>pnl</th></tr>" + "".join(
            f"<tr><td>{e(str(r['closed_at'])[:16])}</td><td>{e(r['symbol'])}</td>"
            f"<td>{e(r['direction'])}</td><td>{e(r['entry'])}</td><td>{e(r['result'])}</td>"
            f"<td style='color:{'#4ade80' if r['pnl_f'] > 0 else '#f87171'}'>{r['pnl_f']:+,.2f}</td></tr>"
            for _, r in closed.sort_values("closed_at").tail(10)[::-1].iterrows()
        ) + "</table>"
    else:
        recent = "<p class='dim'>no closed trades yet — expect ~1/day per symbol</p>"

    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="60"><title>Powell Trades — paper</title>
<style>
 body{{background:#101014;color:#e4e4e7;font:14px/1.5 system-ui,sans-serif;
      margin:0;padding:24px 16px;max-width:720px;margin-inline:auto}}
 h1{{font-size:18px}} h2{{font-size:14px;margin:24px 0 8px;color:#a1a1aa}}
 .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}}
 .card{{background:#18181c;border:1px solid #27272a;border-radius:10px;padding:12px}}
 .big{{font-size:20px;font-weight:600;margin:2px 0}}
 .dim{{color:#71717a;font-size:12px}}
 table{{width:100%;border-collapse:collapse;font-size:13px}}
 th,td{{text-align:left;padding:5px 8px;border-bottom:1px solid #27272a}}
 th{{color:#71717a;font-weight:500}}
</style></head><body>
<h1>Powell Trades — v0.10c EMA-bracket paper test</h1>
<div class="grid">{cards}</div>
<h2>equity curve (realized)</h2>{sparkline(closed)}
{per_sym}
<h2>open positions</h2>{open_html}
<h2>recent closed trades</h2>{recent}
<p class="dim">auto-refreshes every 60s · read-only · paper money</p>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        supplied = (parse_qs(url.query).get("token") or [""])[0]
        if not hmac.compare_digest(supplied, TOKEN):
            self.send_response(403)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"forbidden - append ?token=YOUR_DASHBOARD_TOKEN to the URL")
            return
        try:
            body = render().encode()
        except Exception as exc:  # render must never kill the server
            logger.error("render failed: %s", exc)
            body = f"<h1>dashboard error</h1><pre>{html.escape(str(exc))}</pre>".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        logger.info("%s %s", self.address_string(), fmt % args)


def main():
    if not TOKEN:
        print("DASHBOARD_TOKEN is not set in .env — refusing to serve without auth.\n"
              "Generate one:  python -c \"import secrets; print(secrets.token_hex(16))\"")
        sys.exit(1)
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    logger.info("dashboard on http://0.0.0.0:%d/?token=%s", PORT, TOKEN)
    srv.serve_forever()


if __name__ == "__main__":
    main()
