# HANDOFF: read this first

Everything the previous sessions knew, written down for the next one. Last updated **2026-10-09**,
at the end of the session that ran v0.22 → v0.34. Every fact here can also be found in `DEVLOG.md`
(newest first, full detail) or `CLAUDE.md` (rules and lessons). This file is the map.

Reading order for a new session:
1. `CLAUDE.md`, which loads automatically: its rules and lessons are binding.
2. This file.
3. The `DEVLOG.md` entry for whatever you touch.

---

## 1. Where things stand

- **What the repo is.** It started as an ICT/VWAP trading bot for Bybit (`main.py`, `strategy/`,
  `execution/`). Since August 2026 it has mostly been a **pre-registered research pipeline**. It tests
  the user's trading ideas against the one thing that matters: the user's real alternative, an
  **80/20 VGS/VAS ETF holding** that returned **+13.8 %/yr in AUD**. Short-term trading gains lose the
  50 % CGT discount, so the **pre-tax hurdle is ~14-15 %/yr**.
- **What the ideas were.** Instagram reels, a friend's method, Telegram signal channels, news,
  earnings, and websites selling bots.
- **The result.** 34 versions in, **nothing has passed**. Every strategy failed its pre-registered
  bar or was withdrawn after an engine audit.
  - The closest to real is **v0.28 post-earnings drift**: +0.48 % over 20 days, t 1.96 against a
    bar of 2.0. As a traded overlay it was mostly market exposure.
  - The previous best, the v0.23 "holdout pass", was a forming-bar lookahead and was withdrawn in
    v0.30-audit.
- **One thing runs unattended:** the **v0.29-live earnings routine**, weekdays at 17:54 New York
  time (§7). **It has never pushed a commit.** It missed its only real event (Constellation Brands,
  STZ, due on the 2026-10-07 run). Check it first; see §7.
- **Git:** branch `claude/profitability-issues-backtest-5urpdh` and `main` are identical. Develop on
  the branch, push, then fast-forward `main` (standing authorization from the user).

---

## 2. The user

- **Location.** Australia: Sydney time (AEST/AEDT), money in AUD. Long-term money is in VGS/VAS.
  Trades crypto on Bybit at VIP0 fees, and has a Vultr VPS that ran the paper bot.
- **What they send:**
  - Instagram reels ("can u try this", "fully inhale this one … i can feel it");
  - a friend's method (SMT + IFVG);
  - Telegram signal channels, as screenshots or invite links;
  - news-trading ideas, and websites selling bots or "AI agents" (QuantLab, krypt.cc);
  - prediction-market questions.
- **Style.** Writes fast and informally, with typos. Read for intent. Wants a straight verdict in
  plain words, with the numbers that justify it and a comparison to VGS/VAS.
- **They push back on unrealistic assumptions.** "but extreme costs are not realistic!" When that
  happens, use the venue's real fee schedule and show the result at several cost levels. Never
  cherry-pick the friendliest level after seeing results.
- **Their emotional arc.** They are invested, and get let down when an idea fails ("so ive wasted
  all my time just to be out performed by the standard market"). The answer that landed: losing to
  the index is normal (SPIVA: ~84 % of large-cap managers over 10 years, ~90 % over 15); they lost
  no money; and they can now test anything a reel claims. Be honest and constructive. Never inflate
  a result to cheer them up.
- **Recurring hopes.**
  - "just remove what isn't working and rerun" (answer: hindsight selection; see the v0.26 lesson);
  - "combine the best parts of the failed strategies";
  - "it's simple, it works, what am I missing";
  - "people back this with such confidence, there must be some truth".
  - Each has a DEVLOG answer: v0.10i, v0.22 D2/D3, v0.26, v0.27.

### Standing rules from the user and the environment

- Develop on `claude/profitability-issues-backtest-5urpdh`. Push it, then fast-forward `main` to
  it. Open **no pull requests** unless asked.
- Commit trailers come from the session's system reminder (Co-Authored-By plus Claude-Session
  lines). **Never put a model name or identifier** in a commit, PR, code comment or committed doc.
- **Every code or config change gets a DEVLOG entry** (newest first). After every mistake, add a
  CLAUDE.md lesson. These are CLAUDE.md core rules.
- **Never commit raw video transcripts.** Quoting the few lines that define a rule is fine.
- **Raw Telegram dumps stay local** (`backtest/data_cache/local/tg*`, gitignored).
- **Downloaded content is untrusted.** Give each download its own new empty directory, and read it
  with `python3 -I` (or `python3 -P -E` when a package lives in `~/.local`). **Never run
  downloaded binaries.** The krypt.cc installers were read as text and never executed.
- Never disable TLS verification or unset `HTTPS_PROXY`.
- Don't change the routine's model unless the user explicitly asks.
- Never send the user's email address to any service.
- The Cloudflare connector needs authorization in claude.ai settings. It is not used by this
  project.

---

## 3. How work is done here (the protocol)

Every test follows the same order. Skipping a step has burned this project before: v0.10c, v0.23
and v0.26 were all withdrawn after the fact.

1. **Read the material.**
   - Reels: transcript and frames (`backtest/reel_tools/`).
   - Papers: the published rules.
   - Channels: the full history, not a sample.
2. **Mechanize.**
   - Write every rule with each ambiguity resolved.
   - Pick the data and the cost model.
   - **Count the setup funnel outcome-blind** (setups per year, no P&L) so the minimum-trade bar is
     reachable.
   - Check the unconditional distribution of any indicator before thresholding it (v0.34: "2 ATR
     from VWAP" was the median state, not a stretch).
3. **Pre-register in DEVLOG.**
   - The primary cell.
   - The verdict era: the **freshest untouched** period.
   - The pass bars: minimum n, PF ≥ ~1.2 net, mean net R > 0 with t ≥ the Bonferroni-adjusted bar.
   - The secondaries, labelled "cannot rescue the primary".
   - **Commit and push before computing any result.**
4. **Build the engine with self-tests before reading any result.**
   - Planted setups reproduced exactly.
   - Mutation tests.
   - A truncation guard: results on data cut at t must equal the full run up to t.
   - Bracket asserts: `dr*(entry-stop) > 0` and `dr*(target-entry) > 0`.
   - Higher-timeframe bars matched by **close time** (`closed_htf_index`, with an assert).
   - Stop checked first when one bar touches both. No target fill on the entry bar. No re-entry
     filled at an open the market has already left.
   - A crash-only smoke run with output suppressed.
5. **Run `--report`.** Write the results into DEVLOG with the verdict in the heading, push, and
   fast-forward `main`. Add a CLAUDE.md lesson if something new went wrong.
6. **Answer the user** in plain words. Give the verdict, the reason, the numbers, and the
   comparison to VGS/VAS. Offer the next sensible test, and don't start it unasked.

**Cost models in use.** These are "realistic", and the user agreed:

| Market | Cost per side unless stated | Where |
|---|---|---|
| Bybit USDT perps (crypto) | taker 0.055 % + slippage 0.01 %. Maker 0.02 % for resting limits (limit-entry variants are labelled secondary unless pre-registered). | v0.10–v0.34 (`MAKER, TAKER, SLIP = 0.0002, 0.00055, 0.0001`) |
| Perp funding | real settled rates from the Binance archive, paid or received at each settlement held | v0.10e, v0.18, v0.23, v0.31 |
| NQ futures (CME) | 0.125 pt commission ($2.50 on $20/pt) plus 1 tick (0.25 pt) slippage on stop-type fills. Limit targets fill only on a trade-through, with no slippage. | v0.34 |
| NQ/ES index CFDs | half of a 0.01 % spread, plus 0.01 % slippage on market and stop fills | v0.31 |
| Gold CFD | 0.01 % of price (floor 0.004 %, stress 0.02 %). Signal replays pay the real Dukascopy ask where cached, else that hour's median spread, or a fixed $0.30. | v0.31, v0.33 |
| News minutes (round trip) | EURUSD 2 pips, USDJPY 2 pips, XAUUSD $0.60, NQ 2 index points | v0.32 |
| US stocks (earnings) | 0.10 % per side (stress 0.30 %) plus short financing | v0.28 |

**Statistics conventions.**
- Week-clustered or date-clustered t.
- Bonferroni across the pre-registered primaries.
- Random or drift-matched nulls: the random-walk win rate for a bracket is stop/(stop+target).
- Information tests show excess return beside cost.
- Every report states cost as a share of R (the tight-stop law).
- Report the planned R:R distribution and the "unwinnable" share.

---

## 4. Experiment ledger (v0.1 → v0.34)

<!-- LEDGER -->

---

## 5. Answers given in chat that are not in the DEVLOG

These were research answers, not experiments. The user may refer back to them.

- **"Should I buy a strategy, since only ~10 % of traders beat the S&P?"** (2026-10-04) No.
  - Winners don't persist. SPIVA persistence: of the large US funds in the top quarter in 2022, none
    stayed there for the next two years.
  - A real edge earns more traded than sold, and selling it crowds it.
  - Buffett's $1M index-vs-hedge-funds bet.
  - The bar for any paid strategy: full rules disclosed, audited live broker statements, results from
    after the sale started, and ~15 %/yr pre-tax.
- **QuantLab (quantlab-ai.com) and "+500 %".** The same PF and win rate can be sold as +500 % by
  compounding a backtest at a high risk setting. The money comes from roughly €75 subscriptions and
  broker referral deals.
- **"Should I sell like him if I succeed?"** Sell honestly or not at all.
  - Selling crowds the edge, and a prop firm is often the better route.
  - In Australia, signals or bots for derivatives very likely need an AFSL.
  - Simulated "+500 %" adverts risk misleading-conduct law.
  - The order: pass out of sample, trade it live for 1-2 years with verified records, then decide.
- **News looks predictable** (2026-10-04). Tested with the Tesla Roadster:
  - The unveiling moved from 1 Oct to 15 Oct, and TSLA fell 1.8 % on the confirmation day.
  - Explanations get written after the move; price reacts to news relative to expectations; and a
    person reading news is last in line.
  - This led to v0.27 (blind headline test) and v0.28 (earnings drift).
- **TSA Telegram channel** (v0.33): the real win rate is 86 %, at a losing PF.
  **"Is it the best strategy?"** No.
  - Its best variant (hold to TP4, PF 1.13, t 0.8) is consistent with luck.
  - That variant was chosen after seeing results; it covers 9 months of one regime; it needs a
    response within a minute on ~70 signals a month, some overnight in Sydney.
  - Distinguishing it from luck would take ~2,300 trades.
- **krypt.cc (2026-10-09): no proven edge, and a real security risk.**
  - The site offers free Kalshi and Polymarket bots and a memecoin terminal, plus grey-area tools,
    including "Krypt Larp", which fakes balance dashboards.
  - The Polymarket bot's own research notes:
    - sports markets are priced within ~1 point;
    - the only sports edge is backing 90-99¢ favourites, worth about +1.3¢ a contract, gone once the
      spread exceeds 1.5¢;
    - most of the BTC 15-minute momentum edge vanishes with realistic fills.
  - Risks:
    - unsigned 100 MB+ installers;
    - the Mac instructions disable Gatekeeper;
    - the memecoin bot needs wallet private keys.
  - Access from Australia: Polymarket has been blocked by ACMA since 2025, and Kalshi is US-regulated
    (AU eligibility unverified).
- **KryTrader, the Kalshi bot** (github.com/kryptccgit/KryTrader, read-only, never run):
  - **The "agent council" debate is theatre.**
    - The verdict is hard-wired (`approved = now.traded`).
    - The persuadable members flip to agree 88 % of the time; `OVERRULE_RATE = 0.12` stages dissent
      so the chair can overrule.
    - The lines are random, and the council cannot place or stop a trade.
  - **The real bring-your-own-AI mode is sensible but unproven.**
    - The AI must write a probability before trading, and may only buy when that beats the price by
      a minimum edge after fees.
    - It runs in paper mode first and scores each forecast at settlement.
    - Its README says: "Nothing here has a proven edge. That includes your AI."
  - Offered, not accepted: a paper-mode experiment, built from source on a machine with no real
    accounts.
- **"Can I bet on the Roadster demo on 15 Oct?"** (2026-10-09) Not directly. Prices at the time:

  | Venue | Market | Price |
  |---|---|---|
  | Manifold (play money) | Roadster hovers at a live demo by 31 Oct | 35 % |
  | Manifold (play money) | 0-60 mph under 1 s announced on 15 Oct | 42 % |
  | Kalshi | Roadster deliveries before 2027 | 6-8 % |
  | Polymarket | Delivered by 31 Dec 2026 | 5.5 % |
  | Polymarket | Delivered by end-2027 | 32.5 % |

  - Kalshi's 15,359 open events had none on the demo itself.
  - From Australia, only Manifold is clearly legal (play money).

---

## 6. Data inventory

**Everything under `backtest/data_cache/local/` (~1.2 GB) is gitignored and disappears when the
container is reclaimed.** Re-fetch it with the commands below; each takes minutes, not hours, except
the earnings calendar and Yahoo. Only these are committed:
- `backtest/data_cache/btcusd_1m.csv.gz` (Bitstamp BTC/USD 1m, the old bot's cache);
- `funding_btcusdt_binance.csv` and `funding_ethusdt_binance.csv`;
- `backtest/live_earnings/sp500.csv` and `model.json`;
- `backtest/signal_audits/*.csv`, `backtest/headline_events/*`, `backtest/baselines/*`.

| Dataset | Local path | How to re-fetch | Validation notes |
|---|---|---|---|
| HistData M1 bid, 2015 → 2026-09: EURUSD, USDJPY, XAUUSD, NSXUSD (Nasdaq-100 CFD) | `{eurusd,usdjpy,xauusd}_histdata_1m_2015_2026.csv.gz`, `nas100_histdata_1m_2015_2026.csv.gz` | `pip install histdata`, then for each pair: `python3 backtest/fetch_histdata.py --pair <pair> --years 2015-2025 --current-year 2026 --current-months 1-9 --tz-mode eu --out <path>` | Clock: HistData's "EST" is UTC−5/−4 switching on **EU** DST dates, hence `--tz-mode eu` (the default). Verified by lag scan and by news-minute spikes (08:30 NY CPI/NFP). The bars are Dukascopy's BID (99.97 % of minutes identical). |
| HistData M1 2019 → 2026-09: XAUUSD, UDXUSD (DXY), NSXUSD, SPXUSD | `*_histdata_1m_2019_2026.csv.gz` (`spx500_…`, `nas100_…`) | same, with `--years 2019-2025` | Clock-checked in v0.31: 09:30 NY bars and the NFP minute. |
| Dukascopy XAUUSD bid+ask by day, 2025-12-28 → 2026-10-07 (123 ask days cached) | `duka_raw_gold/` | `backtest.fetch_dukascopy.fetch_day("XAUUSD", day, side, raw_dir, delay=1.0, retries=6)` in a loop (DEVLOG v0.33) | **Throttled** (HTTP 429): use a browser User-Agent, ≥1 s delay and retries. The v0.33 numbers were computed on the cache as frozen; a complete re-fetch shifts them slightly (one cell went from −$564 to −$504 while the fetch was still running). |
| NQ futures 1m with real volume, 2015-01 → 2025-07-25 | `nq_hf_raw/NQ_1min_<year>.parquet` → `nq_hf_1m.pkl` | `pip install pyarrow && python3 backtest/fetch_nq_hf.py --check`: downloads the missing years from Hugging Face `mdelcristo/NQ-F_1min_OHLCV_Parquet`, builds the pickle and re-loads it. Verified on 2026-10-09 to rebuild the v0.34 cache exactly (3,666,547 rows). | MIT licence. The stamps are UTC: volume peaks at 15:59 NY every year. 1m returns correlate 0.88-0.99 with HistData NSXUSD at lag 0 and about 0 at ±1. `emt_experiment.load_nq()` drops sessions with an unmatched >0.5 % one-minute jump (roll and bad-tick defects). |
| Binance USDT-M 5m perps and funding, 2020-01 → 2026-08: BTC, ETH, BNB, XRP, ADA, DOGE, SOL, LINK | `sdz/um5m_<SYM>.csv.gz`, `sdz/funding_<SYM>.csv` | `python3 backtest/fetch_binance_archive.py klines --symbol <SYM> --start 2020-01 --end 2026-08 --interval 5m --market um --out backtest/data_cache/local/sdz/um5m_<SYM>.csv.gz` and `… funding --symbol <SYM> --start 2020-01 --end 2026-08 --out backtest/data_cache/local/sdz/funding_<SYM>.csv` | Untouched coins kept back for a future test: AVAX, DOT, LTC, ATOM, NEAR, TRX. |
| ForexFactory calendar archive, 2007-01 → 2025-04 | `ff_raw/forex_factory_cache.csv` → `ff_usd_events.csv` | `python3 backtest/fetch_ff_calendar.py` (downloads from Hugging Face `Ehsanrs2/Forex_Factory_Calendar` if missing) | **Two defects, both fixed in code.** Rows sharing a release minute are stamped 00:00 (times restored from the official schedule). A stale Tehran +04:30 offset was applied after Sep 2022 (forced to +03:30). |
| Nasdaq earnings calendar, 2014-07 → 2026-10 | `earnings_calendar/` → `earnings_events.csv.gz` | `python3 backtest/fetch_earnings_calendar.py --start 2014-07-01 --end 2026-10-02 --pause 0.2` (it was run as 4 parallel date windows), then `--consolidate` | Actual EPS, consensus, number of estimates, % surprise. |
| Yahoo daily bars for every event symbol plus SPY | `yahoo_daily/` | `python3 backtest/fetch_yahoo_daily.py --pause 0.1` (run twice; the second pass fills gaps) | The close is adjusted for later splits; the script handles it. **IVV.AX has a fake −93 % month at 2011-01**, so check every series over its full history. |
| PEAD event table | `pead_events.csv.gz` | `python3 backtest/pead_drift_test.py --build` | |
| VGS/VAS/IVV benchmark series, FRED SP500 | `benchmark/`, `sp500_fred.csv` | `backtest/benchmark_portfolio.py`, `backtest/benchmark_sp500.py` | AUD, distributions reinvested. |
| Telegram TSA mirrors (@tradesmartacademy, @tsafreetrades) | `tg/*_messages.csv`, `tg_raw/` | `python3 backtest/fetch_tg_channel.py <channel> --out backtest/data_cache/local/tg/<channel>_messages.csv` | Public preview only. Gaps in message ids are deletions or service messages, counted in the summary. |

The old bot's own data (Bybit klines via `pybit`) needs exchange API access and is fetched by
`run_backtest.py --refresh-data`. Other caches named in older DEVLOG entries (Oanda NAS100, Binance
1m ETH, etc.) were lost in earlier container resets. Each entry names its source.

---

## 7. Live: the v0.29 earnings routine

- **What it is.** Every US weekday evening a fresh cloud session reads yesterday's S&P 500 earnings
  releases ("packets": press-release text, the first reaction, context). It writes a direction and a
  confidence for each company, following `backtest/live_earnings/RUBRIC.md`.
- **Paper trades.** Calls at **≥ 0.70** open a paper trade at 1 % of the portfolio; **≥ 0.90**
  opens one at 2 %. This is the user's 70/90 rule, and 0.50 means no view.
- **Results.** The script scores calls and paper trades into `predictions.jsonl`, `ledger.csv` and
  `results.md`.
- **Trigger.** `trig_019f4HV3kS8g9NvP2tpPuoCB`, "Live earnings reader (v0.29-live)". Cron
  `CRON_TZ=America/New_York 54 17 * * 1-5`. A fresh session per fire on the account's default model.
  It works only on the branch and never edits code, RUBRIC.md, CLAUDE.md or DEVLOG.md.
- **Pipeline:**
  1. `--prepare` (T = today in New York; reporters from the previous trading day);
  2. read the packets;
  3. `--record --date T --predictions <file>`, which **must run before 09:30 NY on the next
     weekday** (the script refuses otherwise);
  4. `--score`;
  5. commit and push.
- **State on 2026-10-09:**
  - `predictions.jsonl` holds 3 calls, recorded in-session on 2026-10-05 for the 2026-10-01
    reporters: ACN UP 0.57, NKE DOWN 0.52, MKC DOWN 0.50. No paper trades yet.
  - Run 2026-10-06: 0 events, correct.
  - **Run 2026-10-07: 1 event (STZ, Constellation Brands, reported 10-06; a dry run today rebuilds
    its packet) but nothing was pushed, so the call was missed.** The record deadline has passed.
    Cause unknown: the run log was not visible from the previous session.
  - Run 2026-10-08: 0 events, correct; reported "succeeded" after 68 s.
  - **The routine has never pushed a commit**, so its push path is unproven.
- **First job for the next session:**
  - Check the 2026-10-09 run (reporters of 10-08):
    `git fetch origin claude/profitability-issues-backtest-5urpdh && git log --oneline -5 FETCH_HEAD`.
  - If nothing was pushed although `--prepare --date 2026-10-09 --dry-run` shows events, read that
    run's transcript (claude.ai → Routines) and fix the routine prompt, not the code.
  - Log every finding in the v0.29-live operations notes in DEVLOG.
- **Useful commands:**
  - `python3 backtest/live_earnings_reader.py --prepare --date YYYY-MM-DD --dry-run` writes to the
    gitignored `queue_dryrun/`;
  - `--selftest` runs offline;
  - `--score`;
  - the `get_trigger` / `update_trigger` tools.

---

## 8. Script catalogue

All experiment scripts take `--selftest` (where applicable) and `--report`. Each one's module
docstring holds the full rule and the DEVLOG pointer.

**Current research engines (v0.22+).** Most have `--selftest` and `--report`.

| Script | What it does |
|---|---|
| `backtest/emt_experiment.py` | v0.34 EMT reel: NQ futures and BTC/ETH 5m, VWAP σ-band stretch + 9 EMA, break entry, VWAP limit target. `--selftest --funnel --report` |
| `backtest/signal_audit.py` | Replays a signal channel against real prices. Screenshot CSV mode (`signal_audit.py <csv> [--moves …]`) or channel mode (`--channel messages.csv [--spread duka\|0.30] [--since] [--end] [--detail]`); `--selftest` |
| `backtest/fetch_tg_channel.py` | Public Telegram channel → messages CSV (polite, cached) |
| `backtest/ff_surprise_test.py` | v0.32 ForexFactory surprise test. `--clockcheck --selftest --report` |
| `backtest/fetch_ff_calendar.py` | FF archive → clean USD events (fixes the two defects) |
| `backtest/divergence_experiment.py` | v0.31 gold-vs-DXY (cell B) and SMT+IFVG (cell A) on BTC/ETH and NQ/ES. `--selftest --report [--only]` |
| `backtest/v030_audit.py` | v0.30 lookahead reproduction and fix. `--selftest --repro --corrected --cost-sweep` |
| `backtest/live_earnings_reader.py` | v0.29 live routine (§7) |
| `backtest/pead_drift_test.py` | v0.28 post-earnings drift and the 70 % gate. `--build --selftest --report --diagnostics` |
| `backtest/headline_blind_test.py` | v0.27 blind headline protocol. `--selftest --merge --leakscan --score` |
| `backtest/benchmark_portfolio.py`, `benchmark_sp500.py` | v0.26-a/b: the VGS/VAS hurdle and the S&P comparison |
| `backtest/coin_selection_walkforward.py` | v0.26-diag walk-forward coin selection versus random. `--build --analyse --audit` |
| `backtest/funding_settlement_test.py` | v0.24 funding-settlement flow. `--selftest` |
| `backtest/horizon_harvest.py` | v0.23 horizon harvest of the v0.22 entry (`--overlays`, `--cost-mult`) |
| `backtest/sd_vwap_experiment.py` | v0.22 S/D + structure shift → VWAP engine. Home of `closed_htf_index`, `confirmed_swings`, `structure_bias`, `atr` |
| `backtest/sd_signal_information.py` | Information test (forward return in the signal's direction minus drift, against cost) |

**Earlier engines (v0.10 → v0.21).**
- `bracket_experiment.py`: v0.10c, **withdrawn**.
- `reentry_audit.py`: v0.10i.
- `ema_experiment.py`, `ema_bracket_yearly.py`.
- `trend_portfolio.py`: v0.11.
- `fvg_wick_experiment.py`: v0.12.
- `session_sweep_experiment.py`: v0.14.
- `three_candle_grab_experiment.py`: v0.15.
- `fcr_retest_experiment.py`: v0.16.
- `orb_paper_experiment.py`: v0.16b-d.
- `duka_overlap_check.py`: the two-vendor gate.
- `volume_profile_experiment.py`: v0.17.
- `funding_carry_experiment.py`: v0.18.
- `ema12_open_experiment.py`: v0.19.
- `exit_detector_audit.py`: v0.20.
- `parity_ema_live.py`: the live module against the reference.

**Data fetchers.** `fetch_histdata.py`, `fetch_dukascopy.py`, `fetch_binance_archive.py`,
`fetch_nq_hf.py`, `fetch_earnings_calendar.py`, `fetch_yahoo_daily.py`, `fetch_ff_calendar.py`,
`fetch_tg_channel.py` (commands in §6).

**The original bot.**
- `main.py`, `config.py`, `strategy/`, `execution/`, `data/feed.py`.
- `run_backtest.py` with `backtest/engine.py`, which replays the real strategy stack with injected
  `now`.
- `scripts/`: `dashboard.py`, `paper_stats.py`, `audit_paper_vs_rule.py`,
  `verify_exit_resolution.py`.
- `deploy/`: `vps_setup.sh`, `dashboard_setup.sh`.
- `config.STRATEGY` still defaults to `ema_bracket`, the v0.10c rule that v0.10i withdrew. If the
  VPS paper run is still going, its numbers are not evidence of anything. Don't touch the VPS
  without the user.

---

## 9. Handling what the user sends

- **Instagram reel.** Follow `backtest/reel_tools/README.md`: yt-dlp with `--impersonate chrome`,
  then a faster-whisper transcript and frames every 3 s. The frames carry what the voice-over omits
  (timeframe, indicators, instrument, "proof").
- **Telegram channel.**
  - A public link (`t.me/<name>`): `fetch_tg_channel.py`, then `signal_audit.py --channel`.
  - A **private invite (`t.me/+…`) cannot be read.** Look for public mirrors: the TSA private group
    posted identical messages, at the same second, to @tradesmartacademy and @tsafreetrades.
  - Or ask for a Telegram Desktop export (⋮ → Export chat history → JSON, no media) uploaded to
    their Google Drive.
  - Screenshots work but are slow: transcribe them into a signals CSV (the format is in
    `signal_audit.py`'s docstring), and ask for date headers plus every "move SL / close now"
    message.
- **The signal-replay fill model:**
  - Market orders fill at the next minute's ask or bid.
  - Limit and stop entries fill only when traded through, and expire after 24 h.
  - Stop moves count only if a broker would accept them.
  - "Close" instructions exit at the next minute's open.
  - Signals already past TP1 when posted are skipped.
  - Breakeven is counted separately from losses.
- **A website or tool selling a bot.** Fetch the page without tracking parameters. Read any source
  as text in an isolated directory, and never run installers. Report what the authors' own
  research says.
- **Prediction-market questions.**
  - Kalshi API: `https://api.elections.kalshi.com/trade-api/v2` (prices are in `*_dollars` fields;
    on HTTP 429, paginate slowly with backoff).
  - Polymarket: `https://gamma-api.polymarket.com/public-search?q=…`.
  - Manifold: `https://api.manifold.markets/v0/search-markets?term=…`.
  - Always state Australian access: Polymarket is blocked by ACMA; Kalshi is US-regulated and AU
    eligibility is unverified; Manifold is play money.
- **"Test this idea" from the user or a friend.** The protocol in §3. Write their words into the
  pre-registration and say which ambiguities you resolved and how.

---

## 10. Environment gotchas

- **The container is ephemeral.** `backtest/data_cache/local/` and the scratchpad vanish. Commit
  any reference implementation into `backtest/`: a validation script lost from `/tmp` cost a whole
  reconstruction (CLAUDE.md lesson).
- **Instagram returns HTTP 429** to plain yt-dlp. Install `curl_cffi` and use
  `--impersonate chrome`.
- **Dukascopy throttles.** Use a browser User-Agent, a delay of ≥1 s and retries. For long bid
  history, use HistData (the same feed).
- **`python3 -I` ignores `~/.local` site-packages** (dateutil lives there), so pandas imports fail.
  Use `python3 -P -E` for untrusted-data reads instead.
- **Background jobs.**
  - Use the Bash tool's `run_in_background`; a plain `&` or `nohup` dies when the shell exits.
  - **`TaskStop` can leave the child Python process running.** In v0.33 a "stopped" Dukascopy fetch
    kept writing and changed the results. Check `ps aux` and kill the pid explicitly before you
    freeze any data.
- **Packages installed on demand:**
  - `histdata`, `pyarrow`, `requests`;
  - `yt-dlp`, `curl_cffi`, `faster-whisper`, `av`, `Pillow`.
  - `requirements.txt` holds only the bot's own dependencies.
- **Pandas 2.x pitfalls:**
  - Never `.astype("int64")` a datetime; use epoch subtraction.
  - Write strings into `dtype=str` frames.
  - Re-load every saved artifact through its consumer's loader.
- **Hugging Face downloads** work through the proxy with `curl -L`.
- **GitHub** is reachable only through the MCP tools or `gh api`; scope is this repo plus anything
  attached with `add_repo`. KryTrader was attached read-only and cloned outside the repo; it is gone
  with the container.

---

## 11. Open threads

Each was offered to the user and **not yet accepted**. Don't start any of them unasked.

1. **A maker-entry v0.23 on untouched coins** (AVAX, DOT, LTC, ATOM, NEAR, TRX).
   - Limit entries fill only on trade-through, and misses are counted.
   - Pre-registered with the v0.30 close-time fix.
   - The corrected v0.23 with limit orders on both legs made about 8 %/yr per coin on used data,
     below the hurdle even if it holds.
2. **A forward paper-tracker for the TSA channel** (hold to TP4, rules locked now). It would take
   ~2 years to separate the PF 1.13 from luck.
3. **A Kalshi bring-your-own-AI paper experiment**, scoring forecasts against settlement prices, or
   the same idea on Manifold.
4. **Funding carry or the S/D strategy as a small diversifying add-on** to VGS/VAS: forward paper
   only. Carry came close to the S&P with a fraction of its drawdown in backtest; its real risk is
   the exchange failing.
5. **Monitor the earnings routine** (§7). This one is ongoing, not optional.
