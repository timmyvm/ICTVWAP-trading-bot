# HANDOFF: read this first

Everything the previous sessions knew, written down for the next one. Last updated **2026-10-09**,
at the end of the long session that ran v0.16d → v0.34. Everything here is also in `DEVLOG.md`
(newest first, full detail) or `CLAUDE.md` (rules and lessons). Three things live only here: the chat
answers (§5), the data re-fetch commands (§6) and the environment notes (§10). This file is the map.

Reading order for a new session:
1. `CLAUDE.md`, which loads automatically: its rules and lessons are binding.
2. This file.
3. The `DEVLOG.md` entry for whatever you touch.

---

## 1. Where things stand

- **What the repo is.** It started as an ICT/VWAP trading bot for Bybit (`main.py`, `strategy/`,
  `execution/`). Since August 2026 it has mostly been a **pre-registered research pipeline**. It tests
  the user's trading ideas against the one thing that matters: the user's real alternative, an
  **80/20 VGS/VAS ETF holding**. In AUD it returned **+12.1 %/yr over 2015-2026** and **+13.8 %/yr
  over 2021-Q1 → 2026-Q3** (v0.26-b). Short-term trading gains lose the 50 % CGT discount, so the
  **pre-tax hurdle is ~14-15 %/yr**.
- **What the ideas were.** Instagram reels, a friend's method, Telegram signal channels, news,
  earnings, and websites selling bots.
- **The result.** 34 versions in, **no trading signal has passed**. Every directional strategy failed
  its pre-registered bar or was withdrawn after an engine audit.
  - The closest to real is **v0.28 post-earnings drift**: +0.48 % over 20 days, t 1.96 against a
    bar of 2.0. As a traded overlay it was mostly market exposure.
  - The previous best, the v0.23 "holdout pass", was a forming-bar lookahead and was withdrawn in
    v0.30-audit.
  - **One non-directional exception.** v0.18 **funding carry** (long spot, short the same coin's
    perp, collect funding) passed its pre-registered bar on plain BTC and ETH: +11.6 / +13.6 %/yr on
    notional, maxDD ~2 %. Realistically that is ~10-14 %/yr on capital, still under the hurdle. Its
    risk is the exchange failing (FTX), which no backtest shows. It was never built: it needs spot
    and perp legs plus margin management.
- **One thing runs unattended:** the **v0.29-live earnings routine**, weekdays at 17:54 New York
  time (§7). **It has never pushed a commit.** It missed its only real event (Constellation Brands,
  STZ, due on the 2026-10-07 run). Check it first; see §7.
- **Git:** branch `claude/profitability-issues-backtest-5urpdh` and `main` are identical. Develop on
  the branch, push, then fast-forward `main` (standing authorization from the user).

**First minutes of a new session:**

```bash
git fetch origin claude/profitability-issues-backtest-5urpdh main && git log --oneline -8 FETCH_HEAD
pip install -q -r requirements.txt requests histdata pyarrow   # the bot's deps + research extras
# 1. did the earnings routine record anything? (§7)
git log --oneline -5 origin/claude/profitability-issues-backtest-5urpdh -- backtest/live_earnings
python3 backtest/live_earnings_reader.py --selftest
# 2. nothing under backtest/data_cache/local/ survives a container reset:
#    re-fetch only what the next task needs (§6)
```

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
- **Recurring hopes, and where the DEVLOG answers each:**
  - "just remove what isn't working and rerun": hindsight selection, v0.26-diag and its CLAUDE.md
    lesson;
  - "combine it with all the best parts of the failed strategy": v0.25-diag;
  - "it's simple, it works, what am I missing" (about the ORB "hidden gem"): the era, v0.16d;
  - "people back this with such confidence, there must be some truth": the v0.22 D2/D3 information
    test, later withdrawn by v0.30;
  - "news is so predictable": v0.27 and v0.32, where the move is priced before you can trade.

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

## 4. Experiment ledger (v0.1 → v0.36)

Newest first, as in DEVLOG. "Withdrawn" means a later engine audit showed the result was an
artifact. Numbers are net of costs unless marked gross. R = multiples of the stop distance.

| Version · date | What was tested (source) | Verdict | Key numbers | Script |
|---|---|---|---|---|
| v0.36-catalogue-1 · 10-11 | **Strategy catalogue, phase 1**: 226 probe records (130 groups), explore/sealed split fixed in code, 304-cell P2 grid, power table, pre-registration. | Design only, no probe run | T1 102 / T2 27 / T3 21 / parked 51 probes. Sealed set confirms only market-neutral 1-3 day forms; 129 of 304 cells descriptive only; one batch of at most 5 opens at t 2.576. Coin halves correlate 0.94, so the coin split does not protect directional signals. | `docs/CATALOGUE.md`, `research/prereg/P2_*`, `backtest/edge_lab/split.py` |
| v0.36-catalogue-0 · 10-10 | **Strategy catalogue, phase 0**: 144 sourced cards from nine families, decomposed into primitives (user's pivot: learn what published strategies rely on, then combine by mechanism). | Catalogue only, no test run | 64 A / 52 B / 28 C; P1 55, P5 17, P4 16, P8 16; 86 cards testable on our data; 53 cards hold a recalled-not-re-fetched claim. No trials spent (71). | `docs/CATALOGUE.md`, `research/catalogue/` |
| v0.35-gate1 · 10-10 | **Edge lab batch 1, H001 tail-funding carry rotation and H010 post-flush reversal** (scout cards, not user ideas). | **Shelved, untestable** (no verdict era opened) | H001: explore half-life > 21 days at 7 bp over 768 episodes, but 69 % in 2021 and only ~8 of 82 verdict-era episodes have a spot hedge (93 % of 2026 tail episodes are perp-only). H010: ~15 verdict-era coin-days on 5 dates; needs ~517 independent events, history has ~100-150. | `research/data_reports/`, `fetch_edge_data_*.py` |
| v0.35-gate0 · 10-10 | **Edge lab batch 1 scouting**: 7 cards (carry, forced flow, cross-sectional momentum), written blind. | 5 shelved on power at card stage (H002, H011, H020, H021; H012 folded into H010), 2 advanced | Predicted gross 50-110 bp, minimum detectable edge 79-200 bp. | `research/hypotheses/` |
| v0.35-infra · 10-10 | Edge lab harness and agent team (chair + 5). | infra | 8 self-tests pass; planted 30 bp edge recovered as 30.5 bp. | `backtest/edge_lab/`, `.claude/agents/` |
| v0.34-exp · 10-09 | **EMT "Exhaustion Mean Theory"** (reel, Cody G). 5m: price stretched beyond the VWAP 2σ band and ≥1 ATR from the 9 EMA, an exhaustion wick, entry on the next candle's break, stop beyond the wick, target VWAP. NQ futures and BTC/ETH. | **FAIL** both | NQ 2024+: n 1,000, PF 1.03, +0.018R, t 0.39. NQ 2015-23: PF 0.87, t −4.45. BTC/ETH: n 4,099, PF 0.56, −0.402R; a gross +0.064R (t 2.48) eaten by 0.36R of fees. | `emt_experiment.py` |
| v0.33-audit · 10-07 | **TSA Telegram gold signals** (the user's private channel, read through 2 public mirrors). 674 signals from Jan-Oct 2026 replayed on real bid/ask, following every "move SL / close" message. | Win rate real, **loses** | TP1 (as advertised): 86 % win, PF 0.80, t −2.2. TP4: 60 %, PF 1.13, t 0.8, against a 57 % random null. A quarter off at each TP: PF 0.99. At a $0.30 spread: 0.90 / 1.18 / 1.07. | `signal_audit.py`, `fetch_tg_channel.py` |
| v0.32-exp · 10-07 | **ForexFactory surprises** (user idea). EURUSD traded in the surprise direction from release +1 min to +60 min, \|S\| ≥ 1. | **FAIL** | Holdout 2021-25: n 132, +1.09 bp, t 0.60, hit 49.2 %. The first-minute reaction is t 7-12, so the news is priced before a retail fill. | `ff_surprise_test.py`, `fetch_ff_calendar.py` |
| v0.31-exp · 10-07 | **(B) gold-vs-DXY reel** (itstomtrades): a DXY 2σ push that gold ignores, then trade gold on the DXY pullback; M1, 2R. **(A) The friend's SMT + IFVG**: H4 → M15 on BTC/ETH and NQ/ES. | **FAIL** ×3 | Gold: n 1,719, PF 0.60, −0.319R, t −9.07, and PF 0.94 even at zero cost. BTC/ETH: n 37, PF 0.73. NQ/ES: n 28, PF 0.98. Both pairs fall under the n 60 bar at about 10 setups a year. | `divergence_experiment.py` |
| v0.30-audit · 10-06 | **Lookahead audit of the S/D engine.** 4H/30m bars were matched by OPEN time, so 97.9 % of 5m decisions read a still-forming 4H bar. Fixed with `closed_htf_index` plus an assert, then v0.22-D2, v0.23, v0.25 and v0.26 were re-run unchanged against their original bars. | **audit: v0.23 PASS and v0.26 "skill" WITHDRAWN** | v0.23 T1 24 h: +$26,547 (5/6 coins, PF 1.085) became +$11,581 (3/6, PF 1.036, −$1,316 at 1.5× costs). v0.26: always-on +29.6 % became −1.3 %, and selection beats only 93.6 % of random picks (p 0.064). D2: significant cells fell from 16/32 to 3/32. In AUD the strategy is +5.4 %/yr against the 80/20's +13.8 %. Cost sweep: even maker fills on both legs give ≈ 8 %/yr per coin. | `v030_audit.py`, `sd_vwap_experiment.py` |
| v0.29-live · 10-05 | **Live earnings reading** with the user's 70/90 rule (§7) | live, pre-registered | 3 calls so far, all below 0.70, so no trades. Evaluation starts at ≥ 100 gated trades. | `live_earnings_reader.py` |
| v0.28-exp · 10-05 | **Post-earnings drift plus the user's confidence gate** (user idea). Long the top surprise quintile from the day +2 open for 20 sessions; a logistic gate trades at ≥ 70 % / ≥ 90 %. US stocks 2014-26, holdout 2022-01 → 2026-08. | **FAIL** (t 1.96 vs 2.0); the gate never trades | +0.484 % over 20 days, t 1.964 (5,403 events). Against SPY: +0.318 % (t 1.00); SPY-hedged: +0.098 %/trade. The honest P(up) never exceeded 0.612, so the gate made 0 trades. The long sleeve's +13.2 %/yr came with 91 % average exposure (SPY: +12.2 %). | `pead_drift_test.py` |
| v0.27-exp · 10-04 | **Blind headline test** (user idea): read 20 earnings releases without prices and call the next-session move | **FAIL** by one call | 14/20 against a bar of 15 (p 0.058); Brier 0.199. From the next open: 9/20, because a median 77 % of the move was already in the opening gap. | `headline_blind_test.py` |
| v0.26-b · 10-04 | **The real hurdle**: the user's 80/20 VGS/VAS, in AUD | benchmark | 80/20: +12.1 %/yr over 2015-26 (maxDD −17.1 %), +13.8 %/yr over 2021-Q1 → 2026-Q3. The S&P 500 in AUD: +15.0 / +16.7 %. The after-tax hurdle for trading profits is ≈ 14-15 %/yr pre-tax. | `benchmark_portfolio.py` |
| v0.26-a · 10-04 | The v0.23 candidate against the S&P 500 | benchmark, corrected by v0.30 | S&P +14.7 %/yr. Strategy published at +8.9 %/yr, corrected to +3.7 %/yr. | `benchmark_sp500.py` |
| v0.26-diag · 10-04 | **"Just remove what isn't working and rerun"** (user). Walk-forward coin selection using only trades already closed. | PASS at the time, **withdrawn by v0.30** | Dropping the losers in hindsight gives +56 % per coin and proves nothing. The mechanical rule beat 97.1 % of random picks, 93.6 % after the fix. | `coin_selection_walkforward.py` |
| v0.25-diag · 10-04 | **"Combine it with the best parts of the failed strategy"** (user): a settlement-timing overlay on the v0.23 harvest | diagnostic; its base was withdrawn | About 4-7 bp per deferred trade; best paired t 1.84. | `horizon_harvest.py --overlays` |
| v0.24-exp · 10-04 | **Funding-settlement flow**, a reason-first idea (from an IG reel on how quants find ideas): pre-settlement returns should oppose the funding sign | **FAIL**, killed by cost | The primary (`f_prev`) peaked at t −1.70. The effect is 1-5 bp against a 13 bp round trip. | `funding_settlement_test.py` |
| v0.23-exp · 09-15 | **Horizon harvest** of the v0.22 entry: hold 4, 12 or 24 h; holdout on 6 alt perps | 24 h PASS, **withdrawn by v0.30** | Published T1 24 h: +$26,547, 5/6 coins, PF 1.085. Corrected: +$11,581, 3/6, PF 1.036. | `horizon_harvest.py` |
| v0.22-exp · 09-14 | **The user's S/D rule**: 4H bias, an opposite 30m pullback into a supply/demand zone, a 5m structure shift, target VWAP. BTC and ETH. | **FAIL** everywhere | PF 0.59 / 0.31 / 0.62; 0 of 17 years positive. The VWAP target was unwinnable for 14-30 % of trades, and D1 (a 2R target) loses too. The D2/D3 "information" was withdrawn by v0.30 (1 h excess +0.053 % → +0.001 %). | `sd_vwap_experiment.py`, `sd_signal_information.py` |
| v0.21 · 09-13 | Paper brackets resolve on the 1m price path instead of one mark per 60 s (user: "fix it all") | infra | The point check had missed 6-10 % of stop touches, flattering paper results by $486-2,188 per $10k. | `scripts/verify_exit_resolution.py` |
| v0.20-diag · 09-13 | The live exit detector against the backtest's, same entries | diagnostic | Live vs backtest: −$928 to −$2,669 per $10k over 4-8 years. Recommendation C was withdrawn by v0.21: the exchange holds the bracket. | `exit_detector_audit.py` |
| v0.16d-exp · 09-12 | ORB ATR cell on the fresh era 2020-06 → 2026-08, plus one refinement (a 10 % ATR stop) | **FAIL**; the ORB family is closed | Fresh era: n 1,537, PF 0.90, −$4,830, 1 of 5 years positive. Two-vendor gate on the same 320 trades: Oanda PF 1.42 vs Dukascopy PF 1.23. | `orb_paper_experiment.py`, `duka_overlap_check.py` |
| v0.10i-a · 09-12 | "$10k for one year" table for the EMA bracket | diagnostic | With realistic re-entry: BTC −$833/yr (2 of 7 years positive), ETH +$669/yr. | `ema_bracket_yearly.py` |
| v0.19-exp · 09-12 | **QuantLab reel**: first 5-min candle vs the 12 EMA, EMA trailing stop; NAS100 | **FAIL** (2× cost stress) | At 1× costs the holdout PF was 1.19, all of it from 2019. At 2× costs PF was 0.87 / 0.96. The reel claimed 57 % wins and PF 1.29; the test got 30 %. | `ema12_open_experiment.py` |
| v0.18-exp · 09-12 | **Funding carry**: long spot, short the same coin's perp | **PASS** for plain BTC and ETH; the timed and 3× variants FAIL | Plain BTC +11.6 %/yr, maxDD 2.3 %. Plain ETH +13.6 %/yr, maxDD 1.8 %. Never built. | `funding_carry_experiment.py` |
| v0.10i · 09-12 | Re-entry semantics audit of the v0.10c reference engine | **audit: v0.10c WITHDRAWN** | BTC 2019-22 went from 58.0 % / PF 1.18 / Sharpe 1.68 to 52.7 % / 0.99 / 0.01 under realistic re-entry. The same collapse appears in all 7 datasets. | `reentry_audit.py` |
| v0.10g, v0.10h · 09-12 | The reversed rule; streak conditioning; a cooldown after each loss (Rule A) | diagnostic; v0.10h withdrawn | The "32 % after a loss" streak effect was the same artifact. | `bracket_experiment.py` |
| Paper run · 09-12 | Week-1 audit of the VPS paper run | diagnostic | 8 closed, 1 win, −6.6 %, consistent with an artifact-free ~52 %. | `scripts/audit_paper_vs_rule.py` |
| v0.10f, v0.10e, v0.10d · 09-08 → 12 | Bracket validation on ETH, with real funding, and across NAS100/XAU/WTICO/SPX500 | PASS at the time, **withdrawn by v0.10i** | "The effect travels" (PF 1.09-1.23 in every market) was the engine's signature. | `bracket_experiment.py` |
| docs · 09-12 | `docs/failure_path.md`: why every reel strategy dies | docs | Location ≠ information, and stops below the cost floor. Its "survivor" section was withdrawn by v0.10i. | — |
| v0.17-exp · 09-12 | **IG reel**: fixed-range volume-profile POC pullback; BTC 1H | **FAIL**, and not because of costs | Explore: n 337, PF 0.78. Holdout: n 455, PF 0.86. | `volume_profile_experiment.py` |
| v0.16c · 09-12 | ORB ATR cell at 2-4× costs | **FAIL** at 2× | Holdout PF 1.44 at 1×, 1.14 at 2×, 0.90 at 3×. Explore turns negative at 2×. | `orb_paper_experiment.py` |
| v0.16b-exp · 09-12 | **Published ORB** (Zarattini & Aziz 2023), both cells; NAS100 1m | A FAIL; B passed the holdout, later retired (v0.16c/d) | B holdout: n 567, PF 1.44, +$14,100. | `orb_paper_experiment.py` |
| v0.16-exp · 09-12 | **IG reel**: first-candle-range breakout + retest, 1:3; NAS100 1m | **FAIL** | Explore: n 341, 23.2 % wins against a 25 % null, PF 0.67. Costs were 0.72R per trade. | `fcr_retest_experiment.py` |
| v0.13b-d · 09-07 → 10 | VPS deployment, multi-symbol paper trading, web dashboard | infra | — | `deploy/`, `scripts/` |
| v0.15-exp · 09-07 | **ComLucro** 2/3-candle liquidity-grab reversal (YouTube); BTC 1H | **FAIL** | Explore: n 831, PF 0.74. Holdout: n 778, PF 0.85. Every hit rate sits on its random-walk null. | `three_candle_grab_experiment.py` |
| v0.14-exp, v0.14b · 09-07 | **"Wake up at 9am NY" reel**: Asia/London sweep → 1m FVG, 1:2; v0.14b uses the reactor's DOL targets. NAS100 1m. | **FAIL** | n 2,350, 32.0 / 32.6 % wins against a 33.3 % null, PF 0.78 / 0.80. v0.14b: PF 0.88. | `session_sweep_experiment.py` |
| v0.13 · 09-03 | v0.10c wired into the bot as the paper strategy (`STRATEGY=ema_bracket`) | infra | Parity 85/85 against the reference. | `strategy/ema_bracket.py`, `parity_ema_live.py` |
| v0.12 → v0.12e · 09-02/03 | **The user's FVG-wick 0.3:1** on gold 5m; the "80 % IRL" reading; session filters; the 8am AEST open | **FAIL** in every reading | v0.12: 20.8 % wins against a 23.1 % breakeven. v0.12c: 57.8-59.2 % wins at PF 0.36. Best session: 62.7 % against a 79.9 % breakeven. −100 % everywhere. | `fvg_wick_experiment.py` |
| v0.10c · 09-01 | 3×ATR symmetric bracket after the 1H close is ≥1 ATR from EMA200; BTC | PASS → **withdrawn (v0.10i)** | Claimed: 1,508 trades, 58.0 %, +$36,925, Sharpe 1.68. Artifact-free: ~52 %, PF ~1.0. | `bracket_experiment.py` |
| v0.11 · 09-01 | Diversified daily time-series momentum (from the literature) | **FAIL** | Holdout Sharpe −0.21. | `trend_portfolio.py` |
| v0.10b · 09-01 | The EMA-distance rule on XAU / WTICO / SPX500 | mixed. WTICO trend was parked, never killed | WTICO holdout PF 1.33-1.47, maxDD 33-36 %. Needs post-2020, roll-aware data. | `ema_experiment.py` |
| v0.10-exp · 08-18 | **The user's 1H EMA200-distance** trend/revert rule; BTC and NAS100 | **FAIL** | BTC explore PF 1.31-1.44, holdout 0.83-0.90. | `ema_experiment.py` |
| v0.9 · 08-17 | The ICT rejection-block family on its home instrument, NAS100 1m 2015-20 | **FAIL**; the ICT family is concluded | Clean: n 43, 30.2 % wins, PF 0.72. | `run_backtest.py` |
| v0.8 · 07-22 | v0.3 and v0.3+FVG over 3.55 years of BTC | **FAIL**, shelved | 118 trades, −49.6 %; 53 trades, −31.9 %. | `run_backtest.py` |
| v0.5 → v0.7.2 · 07-22 | ICT 2022 mentorship packs: D1 anchor + M15 MSS, R1-R3, the 2022-model FVG entry | **FAIL** | 7-14 trades per 180 days, PF 0.26-0.87. | `run_backtest.py` |
| v0.4 → v0.4.2 · 07-21/22 | Trend gate and fee-aware TP floor | **FAIL**, reverted | — | `run_backtest.py` |
| v0.3 · 07-21 | Rulebook-faithful execution model | baseline | 180 days: 22 trades, PF 0.71, −5.6 %. v0.8 showed this was regime luck. | `run_backtest.py` |
| v0.2 · 07-21 | The 16-bug audit of the original bot | infra | The original ICT logic could never fire. | — |
| v0.1 | The original Powell Trades bot | **FAIL** | −45.1 % over 60 days. | — |

### What the ledger teaches (the short version)

1. **Location is not information.** Entries at a drawn level (FVG, sweep, POC, first-candle range,
   SMT) win at exactly the random-walk rate for their bracket (stop/(stop+target)). See v0.14-v0.17,
   v0.31 and `docs/failure_path.md`.
2. **The tight-stop cost law.** A stop or target below the cost floor kills a strategy whatever the
   signal: v0.12, v0.16, v0.16c, v0.31 NQ/ES, v0.34 crypto. Always report cost as a share of R.
3. **The best numbers were engine artifacts:**
   - v0.10c: same-bar re-entry filled at a stale open;
   - v0.23 and v0.26: the forming higher-timeframe bar;
   - v0.16: a target with a flipped sign;
   - v0.9: a fill through a gap.
   A result that is uniformly strong across unrelated markets is a reason to audit the engine.
4. **The era is the variable.** ORB and v0.19 lived in 2015-2020 and in single years; both died
   after 2020. Test the freshest untouched data first.
5. **News is priced in under a minute.** Reactions are huge (t 7-12), and what follows from a
   tradable price is a coin flip (v0.27, v0.32).
6. **Data can carry the result.** The same 320 ORB trades scored PF 1.42 on Oanda and 1.23 on
   Dukascopy. Calendars and vendor clocks lie until checked (v0.16d, v0.32).
7. **Marketing math.** Compounding a thin edge at high risk produces "+500 %" (QuantLab). A TP1
   win rate sells while the account bleeds (TSA).

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
- **QuantLab (quantlab-ai.com) and "+500 %"** (2026-10-06). It is all backtest, with no verified
  live record.
  - Their NAS100 bot's +506 % (2019-26) at PF 1.24 and 56 % wins is about 0.1R per trade,
    compounded over ~1,780 trades at 1 % risk. That works out to ~26 %/yr with a −27 % drawdown, and
    it was reproduced.
  - The headline is a risk setting: +150 % at 0.5 % risk, +2,900 % at 2 %.
  - It is fragile: a live PF of 1.10 gives +103 %, and 1.00 gives −7 %. That is what happened to
    the ORB.
  - Income: a €75/month subscription plus a broker partnership (Vantage) that pays on client volume.
    Only the 3 bots that tested well are shown.
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
| **Edge lab (v0.35)**: PIT universe (700 symbols), funding (418 symbols, 756,648 settlements), spot coverage and perp-to-spot mapping, Bybit listing dates, 1h klines + 5-min OI for 10 symbols | `edge/` under `data_cache/local/` | `pip install pytz`, then the commands in `research/data_reports/H001_carry_data.md` and `H010_flow_data.md` (`fetch_edge_data_funding.py`, `fetch_edge_data_oi.py`) | Archive keeps zombie rows after delistings (146 symbols); OI starts 2021-12 except BTC; OI stamp convention changes 2024-03-04; Bybit archive has no funding or USDT premium history. ~865 MB. |
| Telegram TSA mirrors (@tradesmartacademy, @tsafreetrades) | `tg/*_messages.csv`, `tg_raw/` | `python3 backtest/fetch_tg_channel.py <channel> --out backtest/data_cache/local/tg/<channel>_messages.csv` | Public preview only. Gaps in message ids are deletions or service messages, counted in the summary. |

**Older caches that the pre-v0.22 scripts expect** were lost in earlier container resets and are not
on disk now. Rebuild one before re-running its script, then reproduce a published number first.
- `btcusd_1m_2019_2022.csv.gz` and `btcusd_1m_2023_2026.csv.gz` (v0.10c, v0.15, v0.17, v0.20, v0.22):
  Bitstamp spot BTC/USD 1m.
  - The exact download source was never written down. The committed `btcusd_1m.csv.gz` is the same
    vendor for a 180-day window.
  - Binance spot (`fetch_binance_archive.py klines --symbol BTCUSDT`) is a substitute from a
    different vendor, so expect small differences.
- `ethusd_1m_2017_2026.csv.gz`:
  `python3 backtest/fetch_binance_archive.py klines --symbol ETHUSDT --start 2017-08 --end 2026-08 --out backtest/data_cache/local/ethusd_1m_2017_2026.csv.gz`.
- `nas100_1m_2015_2020.csv.gz` (v0.9, v0.14, v0.16, v0.19), `xau_5m_2006_2020.csv.gz` (v0.12), and
  the ~17-instrument daily panel (v0.11, under `local/daily/`): Oanda data from the GitHub archive
  FutureSharks/financial-data.
  - The UTC stamps were verified through the DST drift of the 09:30 ET volume spike, with about
    89 % minute coverage.
  - HistData/Dukascopy NSXUSD is the documented alternative for NAS100 (the v0.16d two-vendor
    check).
- The old bot's own data (Bybit klines via `pybit`) needs exchange API access:
  `run_backtest.py --refresh-data`.

---

## 7. Live: the v0.29 earnings routine

- **What it is.** Every US weekday evening a fresh cloud session reads yesterday's S&P 500 earnings
  releases ("packets": press-release text, the first reaction, context). It writes a direction and a
  confidence for each company, following `backtest/live_earnings/RUBRIC.md`.
- **Paper trades.** Calls at **≥ 0.70** open a paper trade at 1 % of the portfolio; **≥ 0.90**
  opens one at 2 %. This is the user's 70/90 rule, and 0.50 means no view.
  - Entry at the first session's open after T; exit at the 20th session's close.
  - Costs: 0.10 % per side, plus 3 %/yr financing on DOWN calls.
  - The v0.28 anchor in RUBRIC.md: the numbers alone justify about 0.60 at most, so trades should
    be rare.
- **Pre-registered evaluation, once there are ≥ 100 gated trades:**
  - mean net return > 0 with t ≥ 2.0, clustered by week;
  - the ≥ 0.70 bucket must hit ≥ 60 %, or the reading is declared overconfident;
  - the reader is compared against `model.json` on the same events.
- **Results.** Every call goes to `predictions.jsonl`. Paper trades go to `ledger.csv` and scores to
  `results.md`. Neither of those two files exists yet, because no call has reached 0.70.
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

Each script's module docstring holds the full rule and its DEVLOG pointer, and `--help` lists the
flags. Most engines from v0.24 on have a `--selftest`, and the table lists each one's modes. Older
ones take `--cache/--explore-end`-style arguments and default to the `local/` cache paths in §6.

**Edge lab (v0.35).** `docs/EDGE_LAB.md` is the protocol for the chair + five-agent team
(`/edge-lab <family|next>`, agents in `.claude/agents/`, artifacts in `research/`). The shared
harness is `backtest/edge_lab/` (`python3 -m backtest.edge_lab.selftest`): `measure.py` (information
test, nulls, hedged alpha, truncation guard), `power.py`, `ledger.py` (pre-registration check,
one-shot holdout, total trial count, deflated Sharpe). Nothing has been run through it yet.

**Strategy catalogue (v0.36).** `docs/CATALOGUE.md` is the protocol for learning what published
strategies rely on; cards are in `research/catalogue/` (`INDEX.md` is generated by `build_index.py`).
Phases 0 and 1 are done (cards, probe library, split in `backtest/edge_lab/split.py`, P2 pre-registration in
`research/prereg/`). Phases 2-4 (primitive probes on the explore quadrant, combination search, one sealed batch)
have not started: build preconditions are listed in P2 section 3 and 16.

**Current research engines (v0.22+).**

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
- `config.STRATEGY` still defaults to `ema_bracket`, the v0.10c rule that v0.10i withdrew. Its
  artifact-free expectation is ~52 % wins at PF ~1.0.
- **The VPS paper run.** `deploy/vps_setup.sh` installs the `powelltrades` systemd service with
  `PAPER_TRADE=true`, `BYBIT_TESTNET=false` (mainnet data) and no API keys.
  - `deploy/dashboard_setup.sh` adds the `powelltrades-dash` read-only dashboard on port 8080, which
    needs `DASHBOARD_TOKEN`.
  - v0.10f told the user to set `EMA_BRACKET_SYMBOLS=BTCUSDT,XAUTUSDT,ETHUSDT`.
  - The only recorded paper statistics are week 1: 8 closed, 1 win, −6.6 %.
  - Paper brackets resolve on the 1m path since v0.21 (2026-09-13). That was the last change to
    any bot code.
  - **Whether it is still running is unknown from the repo.** Its numbers are a free measurement,
    not evidence. Don't touch the VPS without the user.

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
6. **A forward paper tracker for tail-funding episodes** (H001): log every perp episode with
   trailing-24h funding >= 7 bp, whether a Bybit/Binance spot hedge exists, the funding actually
   paid and the basis. New data accrues out of sample, so it resolves what the archive cannot.
   Offered 2026-10-10, not accepted. Builds on thread 4.
7. **Catalogue phase 2 build**: data patches (1d gaps, half-A funding), loader guard that enforces the
   split, the probe engine with self-tests, auditor stage A, then `log_catalogue_explore` and the 304-cell
   run. Offered 2026-10-11; the user has not yet said go.
