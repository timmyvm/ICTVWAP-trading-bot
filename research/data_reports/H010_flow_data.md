# H010 / H012 flow data: Binance USDT-M open interest (metrics) and 1h perp klines

Data engineer B, 2026-10-10. Serves `research/hypotheses/H010_oi_flush_reversal.md` and its
placebo comparison `H012_flushed_vs_unflushed_drops.md`. Script: `backtest/fetch_edge_data_oi.py`.
No forward return, P&L or plot was computed for any era. Verdict-era (2025-01+) work below is limited to
coverage, gaps, row counts, contemporaneous data-alignment checks and the outcome-blind funnel counts.

## 0. What is held, in one paragraph

1h USDT-M perp klines with taker-buy volume for 10 symbols, 2020-01 (or listing) to 2026-09-30, gap-free
after patching. Daily `metrics` (5-minute OI in coin units, OI value, long/short ratios, taker ratio),
consolidated to one parquet per symbol, for BTCUSDT (2020-09-01 to 2026-09-30) and ETH, SOL, XRP,
DOGE, BNB, ADA, LINK, AVAX, DOT (2021-12-01 to 2026-09-30, every listed day). Tier A coverage is
the 8 largest alts only. The rest of ranks 3-40 is NOT held; section 9 gives the command and the
time it needs. The four findings that matter most for the card:
1. **For every symbol except BTCUSDT, the OI archive starts on 2021-12-01**, not 2020-09. The
   alt explore era for OI is therefore 2021-12 to 2024-12. With the card's 90-day history rule,
   the first decision is about 2022-03, which leaves roughly 2.8 explore years.
2. **The metrics stamp convention changed at 2024-03-04 00:00 UTC.** Before that instant, the row
   stamped T is the snapshot at T. From it on, the row stamped T is the snapshot at T+5 min.
   This is measured to the minute (section 4). The consolidated file carries a corrected
   `snap_ts`, and the loader `oi_at()` uses it.
3. **After feed outages the OI ramps from near zero back to the true level over 20-30 minutes**
   (for example BTC 2021-05-22 05:15-05:40, from 2,772 to 28,197 BTC). Raw, each such ramp looks
   like a 24h OI collapse of 100-200%, which is exactly the H010 signal. These rows are flagged
   (`oi_ok`, backward-looking) and excluded by `oi_at()`.
4. **The expanding OI-tail threshold starves the verdict era.** A q that gives about 4 OI-tail
   coin-days per coin-year in the explore era gives far fewer after 2025 (section 7), because the
   2022 crashes dominate the tail of every coin's history.

## 1. Sources (all public bulk archives; the exchange APIs are blocked from the container)

| Dataset | URL pattern | Notes |
|---|---|---|
| 1h perp klines | `https://data.binance.vision/data/futures/um/monthly/klines/<SYM>/1h/<SYM>-1h-YYYY-MM.zip` | 12 columns incl. `taker_buy_volume` (base) and `taker_buy_quote_volume`. Header row from about 2022. **open_time stays in milliseconds through 2026-09 in the um archive** (checked per file; the 2025 microsecond switch is spot-only). |
| 1h perp klines, daily (patch) | `.../futures/um/daily/klines/<SYM>/1h/<SYM>-1h-YYYY-MM-DD.zip` | Used only to fill days missing from truncated monthly zips. |
| metrics (OI etc.) | `https://data.binance.vision/data/futures/um/daily/metrics/<SYM>/<SYM>-metrics-YYYY-MM-DD.zip` | One file per symbol per day, 288 rows of 5 min. Columns `create_time` (string `YYYY-MM-DD HH:MM:SS`, UTC), `symbol`, `sum_open_interest` (coin units), `sum_open_interest_value` (USDT), `count_toptrader_long_short_ratio`, `sum_toptrader_long_short_ratio`, `count_long_short_ratio`, `sum_taker_long_short_vol_ratio`. There is no monthly metrics archive. |
| listings | `https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?prefix=data/futures/um/daily/metrics/<SYM>/` (paginated with `marker`) | Only days present in the listing are requested. Each symbol's listing is saved to `metrics_raw/<SYM>.listing.json`. |
| 5m and 1m perp klines (tests only) | `.../futures/um/monthly/klines/<SYM>/5m/...`, `.../1m/...` | Fetched on the fly for the stamp test and the cross-vendor check; not cached. |
| Bybit perp 1m (second vendor) | `https://public.bybit.com/kline_for_metatrader4/<SYM>/<YYYY>/<SYM>_1_<YYYY-MM-01>_<YYYY-MM-last>.csv.gz` | Columns `YYYY.MM.DD HH:MM, o, h, l, c, v`, no header. 2020/2021 to 2024 only, 23 symbols. **The clock is UTC+3** (section 6). Bybit has no OI archive. |

Downloads used at most 4 concurrent requests (3 for bulk metrics while side checks used 1), a
50 ms per-request delay, retries with exponential backoff on 429/5xx, and atomic writes
(`.part` then rename). Downloaded files were parsed only with `zipfile` and pandas, under
`python3 -I`.

## 2. Coverage

| symbol | 1h klines first (UTC open) | last | rows | gaps after patch | days patched from daily | metrics first listed | metrics files held | 5m rows | explore days | verdict days | exact-dup rows dropped | OI = 0 rows | OI ramp rows flagged | rows with oi_ok |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BTCUSDT (Tier B) | 2020-01-01 00 | 2026-09-30 23 | 59160 | 0 | 0 | 2020-09-01 | 2221 | 639014 | 1583 | 638 | 75255 | 473 | 271 | 638270 |
| ETHUSDT (Tier B) | 2020-01-01 00 | 2026-09-30 23 | 59160 | 0 | 0 | 2021-12-01 | 1765 | 508180 | 1127 | 638 | 0 | 208 | 68 | 507904 |
| SOLUSDT | 2020-09-14 07 | 2026-09-30 23 | 52985 | 0 | 5 | 2021-12-01 | 1765 | 508163 | 1127 | 638 | 0 | 197 | 56 | 507910 |
| XRPUSDT | 2020-01-06 08 | 2026-09-30 23 | 59032 | 0 | 5 | 2021-12-01 | 1765 | 508179 | 1127 | 638 | 0 | 196 | 54 | 507929 |
| DOGEUSDT | 2020-07-10 09 | 2026-09-30 23 | 54567 | 0 | 0 | 2021-12-01 | 1765 | 508180 | 1127 | 638 | 0 | 197 | 40 | 507943 |
| BNBUSDT | 2020-02-10 08 | 2026-09-30 23 | 58192 | 0 | 0 | 2021-12-01 | 1765 | 508180 | 1127 | 638 | 0 | 188 | 47 | 507945 |
| ADAUSDT | 2020-01-31 08 | 2026-09-30 23 | 58432 | 0 | 0 | 2021-12-01 | 1765 | 508180 | 1127 | 638 | 0 | 205 | 44 | 507931 |
| LINKUSDT | 2020-01-17 08 | 2026-09-30 23 | 58768 | 0 | 0 | 2021-12-01 | 1765 | 508180 | 1127 | 638 | 0 | 191 | 31 | 507958 |
| AVAXUSDT | 2020-09-23 07 | 2026-09-30 23 | 52769 | 0 | 0 | 2021-12-01 | 1765 | 508121 | 1127 | 638 | 0 | 168 | 26 | 507927 |
| DOTUSDT | 2020-08-22 07 | 2026-09-30 23 | 53537 | 0 | 0 | 2021-12-01 | 1765 | 508180 | 1127 | 638 | 0 | 184 | 26 | 507970 |

Metrics run to 2026-09-30 23:55 (the listing continues to 2026-10-08; days after 2026-09-30 were not
fetched). 5-minute row gaps: BTC 156 gaps / 634 missing rows / 71 short days. Every other symbol
has 10-55 gaps and 140-199 missing rows, and 9-11 short days. The largest gap everywhere is
the market-wide 10.5 h on 2024-02-16/17.

**NOT held (cut for time):** the other 222 symbols that were ever in Tier A ranks 3-40 from
2020-09 (232 in total by engineer A's `universe_pit.csv`, 179 for ranks 3-25), Tier C, and
metrics for any delisted symbol. The metrics archive runs at 9-13 files/s under the 4-request
cap. That is about 3 minutes per mature alt, and on the order of 3-5 hours for all of Tier A. The 8
alts held are the largest; DOT left Tier A only in 2024-09..11 and SOL/XRP only in 2022-03 (that
2022-03 exclusion is a universe defect, section 3 #14).

Everything not in this table is NOT held. Period definitions: explore = rows stamped before
2025-01-01, verdict = from 2025-01-01. "Held" metrics files = every day listed in the archive in
range (no listed day failed to download).

**Delisted and collapsed symbols are present in the archive**, so the universe need not be
survivorship-biased, but none were fetched for metrics in this time box. Checked by listing:

| Symbol | metrics days, first to last | 1h kline months, first to last | What the tail of the archive contains |
|---|---|---|---|
| LUNAUSDT | 195, 2021-12-01 to 2024-06-20 | 17, 2021-01 to 2022-05 | Last real day 2022-05-12 (188 rows, partial). Later files hold one row with OI = 0 (for example 2024-02-07). |
| FTTUSDT | 275, 2022-04-15 to 2024-07-15 | 54, 2022-04 to 2026-09 | Kline months continue after the perp stopped trading. |
| SRMUSDT | 377, 2021-12-01 to 2023-06-16 | 45, 2020-09 to 2024-05 | |
| ANCUSDT | 68, 2022-03-08 to 2022-06-08 | 3, 2022-03 to 2022-05 | |
| WAVESUSDT | 945, 2021-12-01 to 2024-07-15 | 74, 2020-08 to 2026-09 | 2025-06 file: 720 bars, volume 0, trades 0, constant close 1.3355 (filler). |
| FTMUSDT | 1196, 2021-12-01 to 2025-03-10 | 73, 2020-09 to 2026-09 | 2025-06 file: 720 bars, volume 0, trades 0, constant close 0.7702 (filler). |
| MATICUSDT / POLUSDT | 1038, 2021-12-01 to 2025-01-22 / 756 from 2024-09-13 | 48, 2020-10 to 2024-09 / from 2024-09 | Ticker migration: two symbols, overlapping. |
| RNDRUSDT | 637, 2023-02-03 to 2025-06-29 | 18, 2023-02 to 2024-07 | Metrics run about 11 months past the last kline month. |
| EOSUSDT | 1332, 2021-12-01 to 2026-05-05 | 65, 2020-01 to 2025-05 | Metrics run about 12 months past the last kline month. |

Consequences: (a) never infer "alive" from file presence. Cut each symbol at its last kline bar
with volume > 0. Engineer A's universe applies an `alive` test (volume > 0 on the day before the
month), which handles this. (b) Metrics files that outlive the klines must be ignored.
Joining on kline hours does this automatically.

## 3. Defects found and how each is handled

| # | Defect | Where | Handling |
|---|---|---|---|
| 1 | OI archive starts 2021-12-01 for all symbols checked except BTCUSDT (2020-09-01): ETH, SOL, XRP, DOGE, ADA, LINK, AVAX, DOT, BNB, LTC, SRM, WAVES, MATIC, FTM, EOS, LUNA | listing | Reported; explore era for alt OI is 2021-12 to 2024-12. Cannot be fixed from this archive. |
| 2 | Stamp convention switch at 2024-03-04 00:00 UTC (snapshot at T before, at T+5 min after) | all symbols tested (BTC, ETH, SOL), same instant | `snap_ts` column; `oi_at()` and the OI-vs-volume check use it. The true-time window [2024-03-03 23:55, 00:00) has no row. |
| 3 | Exact duplicate rows: every row of a file appears twice | BTCUSDT files 2020-09-01 to 2021-05-20 (262 files, 75,255 rows) | Exact duplicates dropped and counted. No conflicting duplicates (same stamp, different values) in any symbol. |
| 4 | OI = 0 rows | BTC 473, ETH 208, SOL 197, XRP 196 (others in coverage table). Market-wide on 2022-03-07/08 (117 rows) and intermittently on 2024-07-09 to 2024-07-15, plus scattered single rows (2023-06-06, 2023-11-20, 2024-08-12, 2025-01-08, 2025-04-11/15, 2025-07-21) | `oi_ok = False`; never used. |
| 5 | Post-outage OI ramp (feed restarts from a partial aggregate) | BTC 271 rows, ETH 68, SOL 56, XRP 54 flagged | Backward-looking rule in `oi_validity()`: after a zero or a gap of more than 30 min, rows stay flagged until a 5-minute change is within 3%. This also flags one good row after each isolated zero (conservative). No row met the 40% spike rule outside a ramp. |
| 6 | OI flicker between two levels about 3% apart, for hours | 2024-06-22/23, seen in ETH and SOL (e.g. ETH 973k vs 1,004k coins alternating every few rows) | NOT flagged (below the spike threshold). It produces the only OI-change-greater-than-volume hours outside outages (section 5). Engines should treat 2024-06-22 to 2024-06-23 as suspect for 2h OI changes (the completion condition). |
| 7 | 5-minute row gaps | BTC 156 gaps, 634 missing rows, largest 10.5 h (market-wide 2024-02-16 13:30 to 2024-02-17 00:00); ETH 10 gaps / 140 rows; SOL 14 gaps; 71 BTC days and 9 ETH days have fewer than 288 rows | Not filled. `oi_at()` returns NaN when the latest valid snapshot is more than 30 min old, so a decision bar inside a gap has no OI. |
| 8 | Taker ratio and top-trader ratios missing | all symbols: `sum_taker_long_short_vol_ratio` empty 2021-12-31 to 2022-05-11 (about 37k rows per symbol); top-trader ratios empty for most of 2022 (91,733 rows per symbol) | Not filled. The card's optional taker-imbalance confirmation should use kline `taker_buy_base`, which is complete. The L/S-ratio fields have no 2022. |
| 9 | Truncated monthly 1h kline zips | SOLUSDT and XRPUSDT: 2022-02-26 to 2022-02-28 and 2022-04-01 to 2022-04-02 missing (120 hours each); BTC and the others complete | Patched from the same vendor's daily 1h files (`patch_klines_1h`, recorded in `um1h/<SYM>.patched.json`). 0 gaps after the patch. No interpolation. |
| 10 | Market-wide zero-volume hour | 2024-10-28 20:00 UTC, every symbol | Kept as is (one bar). It is the only hour where OI change exceeds volume in BTC. |
| 11 | Post-delisting filler bars and metrics files | see section 2 | Cut at the last bar with volume > 0; ignore metrics outside kline coverage. |
| 12 | Coin-unit OI rises mechanically in a death spiral | LUNA 2022-05-12: coin OI 86M to 256M while price collapsed | Not a data error, a property of the variable. A collapsing coin shows rising coin-unit OI, so it falls in the H012 placebo group, not the flush group. Reported as a threat (section 8). |
| 13 | Bybit MT4 clock is UTC+3, unstated | all 10 symbol-months compared | Re-stamped by the measured offset before any comparison (section 6). |
| 14 | **Engineer A's universe (not my file): 2022-03 has 88 alive symbols of 137**, against 134-142 in the neighbouring months. SOL and XRP are among the 49 marked not alive. Cause, inferred: the monthly 1d kline zips for 2022-02 are truncated (2022-02-26..28 missing, as in defect 9), so the `alive` test on 2022-02-28 fails. | `universe_pit.csv`, month 2022-03 | Not touched. Reported to the chair and A. The fix is the same daily-file patch. In the counts below, SOL and XRP lose 2022-03 from Tier A. |
| 15 | 1h moves larger than 25% | DOGE 10 bars (2021-01-29 pump), AVAX/SOL/XRP 3, others 0-2 (2020-03-12, 2021-05-19, 2025-03-02 ADA +29%) | All checked against known market events; kept. No zero or negative prices, no high/low inconsistency, taker buy never exceeds volume. |

Units: `sum_open_interest` is in coin units. `sum_open_interest_value / sum_open_interest` matches the 1h
kline price at the snapshot within a median 1.4 bp (BTC) and 2.6 bp (ETH), so the value column is
coin OI times a mark price. No row in any held metrics file is stamped off the 5-minute grid. No
row's stamp falls outside its file's day. No rows carry another symbol.

## 4. Timestamp convention of the metrics rows (what time does a row describe?)

Two independent tests, both purely contemporaneous (no returns):

**(a) Taker-ratio identity.** `sum_taker_long_short_vol_ratio` should equal buy/sell taker volume of
one 5-minute window, computable from the 5m klines (`taker_buy_base / (volume - taker_buy_base)`).
For every day of BTC from 2020-09 to 2026-09 (`stampscan`), I compared it with the window [T-5, T)
("end" convention) and with [T, T+5) ("start" convention). The table gives medians of daily values:

| Period (BTC) | exact-match share, end | exact-match share, start | corr, end | corr, start |
|---|---|---|---|---|
| 2020-09 to 2021-12-30 | 1.000 | 0.000 | 1.000 | 0.007 |
| 2021-12-31 to 2022-05-11 | (ratio missing) | | | |
| 2022-05-12 to 2024-03-03 | 0.833 | 0.000 | 1.000 | 0.051 |
| 2024-03-04 to 2025-07-30 | 0.000 | 0.743 | 0.095 | 1.000 |
| 2025-07-31 to 2026-09-30 | 0.000 | 0.128 | 0.115 | 0.999 |

The switch is a single instant. On 2024-03-03 23:55 the row still matches [23:50, 23:55). The
row stamped 2024-03-04 00:00 matches [00:00, 00:05). ETH and SOL switch on the same day. The
exact-match share falls in late 2025 while the correlation stays at 0.999. That is rounding in
the file, not a further shift.

**(b) OI change against traded volume, minute resolution** (`stamp1m`, BTC). Correlation of
|ln OI_T - ln OI_{T-5m}| with log 1m volume summed over the 5-minute window ending at T + o:

| o (min) | 2021-03 | 2022-06 | 2023-06 | 2024-01 | 2024-04 | 2024-08 |
|---|---|---|---|---|---|---|
| -5 | 0.294 | 0.352 | 0.346 | 0.368 | 0.302 | 0.325 |
| -1 | 0.506 | 0.512 | 0.542 | 0.526 | 0.349 | 0.361 |
| **0** | **0.534** | **0.534** | **0.570** | **0.551** | 0.365 | 0.382 |
| +1 | 0.511 | 0.518 | 0.560 | 0.537 | 0.404 | 0.425 |
| +4 | 0.374 | 0.427 | 0.458 | 0.448 | 0.529 | 0.546 |
| **+5** | 0.327 | 0.396 | 0.419 | 0.416 | **0.556** | **0.572** |
| +6 | 0.302 | 0.378 | 0.396 | 0.398 | 0.543 | 0.556 |

OI follows the taker ratio: before the switch, the snapshot stamped T is taken at T. After it,
the snapshot is taken at T+5 min. The 5-minute coarse version (`stampcheck`) agrees in every
month tested, including 2025-04 and 2026-03.

**Clock.** The 1h/5m kline stamps are UTC open times. The largest 5m BTC volume bar opens at 12:30
UTC on CPI day 2022-07-13 (08:30 New York, EDT) and at 13:30 UTC on 2022-11-10 (08:30, EST)
(`clockcheck`). The metrics clock is tied to the klines by the exact taker-ratio identity in
(a), so it is UTC as well.

**Confidence: high.** The taker identity is exact (correlation 1.000 on one side and about 0.05-0.1
on the other, every day) and the OI result peaks at the same offset to the minute. Residual
uncertainty: (i) I tested the switch date on three symbols, not all. (ii) Publication
latency (when a snapshot became available live) is not observable in an archive.

**Consequence for the card.** The card reads "the latest row stamped at or before t - 5 min".
On raw stamps that gives a snapshot at t-5 min before 2024-03-04 and at t after it, which is
an era-dependent lag. `oi_at(met, times, lag="5min")` applies the rule to `snap_ts`, so the
snapshot is always taken at or before t-5 min. An engine that uses the raw stamp with no lag would read
OI 5 minutes into the future in the whole 2024-03 to 2026-09 period, including the entire verdict era.

## 5. OI changes versus traded volume (Giagkiozis and Said 2024)

Share of hours where |OI_t - OI_{t-1h}| in coin units exceeds that hour's perp volume in coin
units. Snapshots are taken exactly at the hour (`snap_ts`) and the volume is the 1h kline of
(t-1h, t]. `oivol`, %:

| symbol | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|
| BTCUSDT | 0 | 0 | 0 | 0 | 0.011 | 0 | 0 |
| ETHUSDT | | 0 | 0 | 0 | 0.148 | 0 | 0 |
| SOLUSDT | | 0 | 0 | 0 | 0.057 | 0 | 0 |
| XRPUSDT | | 0 | 0.034 | 0 | 0.011 | 0 | 0 |
| DOGEUSDT | | 0 | 0.011 | 0 | 0.228 | 0 | 0 |
| BNBUSDT | | 0 | 0.034 | 0 | 0.011 | 0 | 0 |
| ADAUSDT | | 0 | 0 | 0 | 0.011 | 0 | 0 |
| LINKUSDT | | 0 | 0 | 0 | 0.011 | 0 | 0 |
| AVAXUSDT | | 0 | 0 | 0 | 0.011 | 0 | 0 |
| DOTUSDT | | 0 | 0 | 0 | 0.011 | 0 | 0 |

(2021 for the alts is December only; 0.011% = 1 hour of about 8,760.) The median hourly
|dOI|/volume is 2.0-3.9% and its 99th percentile is 10-18% (BTC, ETH, SOL; full table in
`h010_checks/oi_vs_volume.csv`).

The Binance archive does not show the anomaly at hourly resolution: at most 0.23% of hours
(DOGE 2024, 20 hours). I traced the BTC, ETH and SOL cases: the 2024 hours are the market-wide
zero-volume hour (2024-10-28 21:00) and the 2024-06-22/23 OI flicker (defect 6). The 1-3 hours in
BNB/XRP/DOGE 2022 and the remaining DOGE 2024 hours were not traced. The median ratio is what one
expects when most volume is turnover between existing positions. This does not refute the paper. It
measured other venues and windows, and one-sided feed errors (defects 4-6) are what remain here.

## 6. Cross-vendor: Binance USDT-M vs Bybit USDT perp

Bybit offers no OI archive, so only prices can be compared. Source: Bybit MT4 1m exports, against
Binance um 1m (clock) and 1h (comparison). Months were chosen for flush events: May 2021,
LUNA (2022-05), FTX (2022-11), 2024-08-05. SOL and XRP have no Bybit file for 2021-05.

**Clock.** I scanned the 1m log-close RMS difference over Bybit shifts of -14 h to +14 h in 30-minute steps,
then refined to the minute. The best offset is **+180 min in all 10 symbol-months**, including
November (no DST switch). The RMS at the best offset is 1.4-12 bp (SOL 2022-11: 128 bp, the FTX
dislocation below), against 10-27 bp at plus or minus 1 min, 72-326 bp at plus or minus 60 min, and 126-516 bp unshifted. So Bybit's MT4 stamps are UTC+3, constant. Comparing them unshifted
gives a 1h-return correlation of about 0 (first run, discarded).

After re-stamping:

| Symbol | Month | 1h close abs diff, median / p99 (bp) | 1h return corr | 24h log-return abs diff, median / p99 (bp) | hours with abs R24 >= 5%: Binance / Bybit / disagree | max 1m abs diff (bp), at |
|---|---|---|---|---|---|---|
| BTC | 2021-05 | 4.1 / 15.2 | 0.9990 | 5.3 / 20.1 | 225 / 224 / 5 | 806, 2021-05-19 13:19 |
| BTC | 2022-05 | 1.7 / 7.6 | 0.9992 | 2.3 / 9.6 | 109 / 108 / 1 | 60 |
| BTC | 2022-11 | 1.8 / 9.3 | 0.9991 | 2.8 / 14.3 | 79 / 78 / 3 | 66 |
| BTC | 2024-08 | 1.0 / 4.1 | 0.9998 | 1.2 / 4.6 | 86 / 86 / 0 | 21 |
| SOL | 2022-05 | 2.0 / 10.7 | 0.9996 | 3.0 / 13.8 | 309 / 308 / 1 | 129 |
| SOL | **2022-11** | 4.7 / **763.8** | **0.9743** | 6.4 / **1022.9** | 334 / 334 / 6 | **2,295, 2022-11-09 21:22** |
| SOL | 2024-08 | 1.4 / 5.9 | 0.9997 | 1.9 / 7.9 | 182 / 182 / 0 | 28 |
| XRP | 2022-05 | 2.4 / 10.0 | 0.9994 | 2.7 / 14.4 | 182 / 181 / 1 | 51 |
| XRP | 2022-11 | 2.6 / 14.4 | 0.9989 | 2.8 / 16.5 | 204 / 203 / 1 | 90 |
| XRP | 2024-08 | 1.7 / 6.2 | 0.9995 | 1.8 / 8.8 | 124 / 125 / 1 | 32 |

In normal months the vendors agree to a few bp at the hourly close, and the card's 5% move flag
disagrees in 0-6 hours a month. That is the quote stream. **The exception is the flush itself:**
in the FTX collapse, Bybit's SOLUSDT perp traded 8-13% below Binance's at eight hourly closes
from 2022-11-09 17:00 to 2022-11-10 04:00 (`bybit_top_divergence.csv`). Binance printed
9.99 at 21:00 when Bybit printed 8.73. Bybit volume was 25-70% of Binance's in those hours. That is a
venue-specific dislocation in exactly the state H010 trades. A reversal measured on one venue's
prints in such an episode may be that venue's, not the market's (section 8).

## 7. Outcome-blind funnel counts (H010 / H012)

Definitions follow the card exactly. Decision bars are every 1h close t (UTC).
`P_t` = close of the bar ending at t. `OI_t` = `oi_at(lag=5min)`: the latest valid snapshot taken
at or before t-5 min, NaN if older than 30 min. `dOI = ln OI_t/OI_{t-24h}`, `R = ln P_t/P_{t-24h}`.
`sigma` = std of 1h log returns over the 720 hours ending at t-24h (at least 600 present), times sqrt(24).
OI-tail rank = share of the coin's own dOI values at hours up to t-24h that are at or below
dOI_t (expanding, at least 90 days = 2,160 hourly values). Tail: rank <= q. Big move:
|R| >= max(k sigma, 5%). Completion: `ln OI_t/OI_{t-2h} >= (2/24) dOI_t`. Placebo groups (H012):
big move with OI NOT in the tail. Variants: any sign; falling only; OI held or grew (dOI >= 0).
q is calibrated on the explore era only, by log-interpolation on a grid, so that the OI condition
alone gives 2, 4 or 8 coin-days per coin-year. Units: coin-days are distinct (coin, UTC date of t);
distinct dates are distinct UTC dates; events are entries after a 24h per-coin cooling period.
Nothing after t is read anywhere.

**Scope: Tier A = the 8 held alts** (SOL, XRP, DOGE, BNB, ADA, LINK, AVAX, DOT), masked hour by
hour to ranks 3-40 using engineer A's `universe_pit.csv` (`rank` of month m, computed from the 30 days
before m with at least 90 days of history). These numbers are for the top of Tier A only. The full
Tier A (232 symbols ever) will have more coin-days but not proportionally more distinct dates.
Eligible coin-years (all of: Tier A that hour, OI rank defined, sigma defined): 2022 6.50,
2023 7.99, 2024 7.77, 2025 7.99, 2026 6.00 (to 2026-09-30). Explore era 22.26 coin-years
(first eligible hour 2022-03), verdict era 13.99.

q calibration (explore era, Tier A, OI condition alone):

| q | OI-tail coin-days | per coin-year |
|---|---|---|
| 0.0010 | 29 | 1.30 |
| 0.0020 | 49 | 2.20 |
| 0.0030 | 80 | 3.59 |
| 0.0040 | 111 | 4.99 |
| 0.0050 | 131 | 5.88 |
| 0.0075 | 193 | 8.67 |
| 0.0100 | 267 | 11.99 |

The picks by log-interpolation are **q = 0.00181 (2/coin-year), 0.00330 (4), 0.00690 (8)**.
Cells below are **coin-days / distinct UTC dates**. "S3 events" are entries after the 24h per-coin cooling.
S1 = OI tail; S2 = S1 and big move; S3 = S2 and completion (split by the sign of R);
P = placebo, a big move with OI not in the tail. P_down = the same, falling only (H012's group);
P_oi_up = a big move with dOI >= 0.

**Summary (Tier A, 8 alts), explore / verdict:**

| q target | k | S1 OI tail | S2 + big move | S3 + completion | S3 R<0 | S3 R>0 | S3 events | Placebo (big move, no tail) | Placebo, falling |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 2 | 46/30 ; 23/11 | 28/17 ; 20/9 | 25/15 ; 16/8 | 19/11 ; 11/4 | 7/5 ; 5/4 | 21 ; 14 | 1505/517 ; 980/302 | 717/213 ; 488/131 |
| 2 | 3 | 46/30 ; 23/11 | 19/11 ; 16/6 | 16/9 ; 13/5 | 13/7 ; 9/2 | 3/2 ; 4/3 | 12 ; 11 | 507/224 ; 298/122 | 244/76 ; 151/45 |
| 4 | 2 | 87/49 ; 28/13 | 58/30 ; 23/10 | 47/25 ; 20/9 | 35/20 ; 12/4 | 14/7 ; 8/5 | 35 ; 17 | 1497/517 ; 978/302 | 708/213 ; 487/131 |
| 4 | 3 | 87/49 ; 28/13 | 37/19 ; 18/6 | 30/16 ; 15/5 | 23/11 ; 10/2 | 7/5 ; 5/3 | 21 ; 12 | 498/221 ; 297/122 | 237/73 ; 150/45 |
| 8 | 2 | 176/101 ; 52/29 | 94/46 ; 34/17 | 81/40 ; 29/14 | 62/32 ; 16/6 | 22/10 ; 13/8 | 63 ; 24 | 1481/515 ; 976/302 | 692/210 ; 487/131 |
| 8 | 3 | 176/101 ; 52/29 | 53/29 ; 25/10 | 42/23 ; 21/8 | 31/17 ; 13/3 | 11/6 ; 8/5 | 32 ; 17 | 492/220 ; 293/120 | 232/71 ; 150/44 |

(A coin-day can hold both an R<0 and an R>0 qualifying hour, so the two S3 splits can sum to more than S3.)

**By calendar year, q target 4, k = 2** (coin-days / distinct dates):

| year | S1 | S2 | S3 | S3 R<0 | S3 R>0 | S3 events | P not tail | P falling | P dOI>=0 |
|---|---|---|---|---|---|---|---|---|---|
| 2022 (from Mar) | 29 / 19 | 16 / 7 | 13 / 6 | 6 / 3 | 7 / 3 | 10 | 447 / 144 | 263 / 68 | 282 / 129 |
| 2023 | 36 / 21 | 28 / 15 | 23 / 12 | 19 / 10 | 5 / 3 | 15 | 518 / 188 | 211 / 75 | 294 / 158 |
| 2024 | 22 / 9 | 14 / 8 | 11 / 7 | 10 / 7 | 2 / 1 | 10 | 532 / 185 | 234 / 70 | 320 / 160 |
| 2025 | 24 / 9 | 20 / 7 | 17 / 6 | 12 / 4 | 5 / 2 | 15 | 545 / 166 | 284 / 72 | 366 / 146 |
| 2026 (to Sep) | 4 / 4 | 3 / 3 | 3 / 3 | 0 / 0 | 3 / 3 | 2 | 433 / 136 | 203 / 59 | 303 / 119 |

Full tables for every (q, k) by year: `backtest/data_cache/local/edge/h010_checks/funnel_counts_tierA.csv`
(also hours and coin counts).

**Tier B control (BTC, ETH; no mask; BTC from 2020-12, ETH from 2022-03)**, q target 4
(q = 0.00381), k = 2, explore / verdict: S1 29/29 ; 8/6, S2 20/20 ; 7/5, S3 16/16 ; 5/4,
placebo 467/341 ; 212/148. BTC/ETH flushes cluster on the same dates, as the card predicted.
`funnel_counts_tierB.csv`.

Reading the counts (no outcomes involved):
- **Rate.** At q target 4, k = 2, the 8 largest alts give S3 = 47 coin-days on 25 distinct dates in
  2.8 explore years (2.1 per coin-year, 9 dates a year), and 20 on 9 dates in the 1.75-year verdict era.
  That is the card's 1-2 entries per coin-year. Date clustering is about 1.9 coins per date in the explore era
  and 2.2 in the verdict era.
- **Verdict starvation.** The OI tail alone gives 3.9 coin-days per coin-year in the explore era
  (by calibration) but 2.0 in the verdict era (28 / 14.0). At target 8 it is 7.9 against 3.7.
  2026 has 4 tail coin-days in 6 coin-years.
- **Verdict-era S3 at k = 3 is 15 coin-days on 5 dates, and the long-flush (R<0) leg is 10 on 2 dates.**
  On these 8 coins the verdict era cannot resolve a +100 bp claim. Full Tier A raises the coin-day count but not the
  date count by much, because flushes are market-wide.
- **The completion condition removes only 10-20% of S2**, not the half the card assumed. Most
  qualifying 24h windows have already stopped losing OI at the decision bar.
- **Placebo size.** The placebo group is 25-50 times larger than S2 in coin-days, so H012's comparison
  has ample control days. Its falling subset (H012's large fallers) is about 70 dates a year
  at k = 2 and about 25 at k = 3 for these 8 coins. The H012 rule needs 6 or more fallers in a 3-60
  universe on one day; it cannot be counted on 8 coins and needs the full universe.

## 8. Threats to the card found in the data

1. **Era length.** Alt OI starts 2021-12-01. With 90 days of history needed, the explore era for
   Tier A is about 2022-03 to 2024-12. The card's power arithmetic assumed 2020-09 to 2026-08.
2. **Event starvation in the verdict era** (section 7). An expanding tail anchored on 2022 yields
   few qualifying OI collapses after 2025. If q is set from the explore era, the verdict era can
   fail on count alone (CLAUDE.md, v0.31 lesson). A rolling window (for example 365 days) instead
   of an expanding history is a pre-registration choice for the statistician. It is not tested here.
3. **Fake flushes from the feed.** Defects 4-6 create exactly the H010 signature (a sudden deep
   OI fall followed by a "completed" rebuild). They are flagged here, but any engine that bypasses
   `oi_at()` and reads raw `oi` will trade them.
4. **Death-spiral coins are not OI collapses in coin units** (LUNA). The survivorship worry in the
   card is real, but it lands in the H012 placebo group, not the flush group. H012's falsifier 4
   (USD vs coin units) is the right check. The USD column `oi_value` is held for it.
5. **Venue-specific prints in flushes** (SOL, FTX week). Expect the measured reversal in extreme
   episodes to depend on the vendor. Bybit OI is not available to cross-check the state variable
   itself.
6. **Stamp switch** (section 4): any engine reading the raw stamp looks 5 min ahead for the whole
   verdict era.
7. **Coverage.** Only 8 Tier A coins hold OI. These are the largest alts, the least likely to
   reverse according to the card's own source (Zaremba et al.). The counts below are for them, and
   the full Tier A will have more events per year but not more distinct dates in proportion.

## 9. Rebuild commands (container is ephemeral; `backtest/data_cache/local/` is gitignored)

`pip install pyarrow` first (parquet). All commands from the repo root. Times measured here while
another engineer was downloading in parallel.

```
# 1h perp klines (about 10 s per symbol; truncated monthly zips are patched from daily files automatically)
python3 -I backtest/fetch_edge_data_oi.py klines --symbols BTCUSDT,ETHUSDT,SOLUSDT,XRPUSDT,DOGEUSDT,BNBUSDT,ADAUSDT,LINKUSDT,AVAXUSDT,DOTUSDT --start 2020-01 --end 2026-09

# metrics zips (about 9-13 files/s at 4 workers, so about 3 min per alt from 2021-12, 4 min for BTC from 2020-09)
python3 -I backtest/fetch_edge_data_oi.py metrics --symbols BTCUSDT --start 2020-09-01 --end 2026-09-30
python3 -I backtest/fetch_edge_data_oi.py metrics --symbols ETHUSDT,SOLUSDT,XRPUSDT,DOGEUSDT,BNBUSDT,ADAUSDT,LINKUSDT,AVAXUSDT,DOTUSDT --start 2021-01-01 --end 2026-09-30
# one parquet per symbol with snap_ts and oi_ok (re-loaded through load_metrics before it reports)
python3 -I backtest/fetch_edge_data_oi.py consolidate --symbols BTCUSDT,ETHUSDT,SOLUSDT,XRPUSDT,DOGEUSDT,BNBUSDT,ADAUSDT,LINKUSDT,AVAXUSDT,DOTUSDT

# extend to the rest of Tier A once engineer A's universe_pit.csv exists (prints the symbol list)
python3 -I backtest/fetch_edge_data_oi.py symbols --tier A
python3 -I backtest/fetch_edge_data_oi.py klines --symbols $(python3 -I backtest/fetch_edge_data_oi.py symbols --tier A) --start 2020-01 --end 2026-09
python3 -I backtest/fetch_edge_data_oi.py metrics --symbols $(python3 -I backtest/fetch_edge_data_oi.py symbols --tier A) --start 2021-01-01 --end 2026-09-30
python3 -I backtest/fetch_edge_data_oi.py consolidate --symbols ALL

# checks (outputs in backtest/data_cache/local/edge/h010_checks/)
python3 -I backtest/fetch_edge_data_oi.py coverage --symbols ALL
python3 -I backtest/fetch_edge_data_oi.py validate --symbols ALL
python3 -I backtest/fetch_edge_data_oi.py clockcheck
python3 -I backtest/fetch_edge_data_oi.py stampscan --symbols BTCUSDT --start 2020-09 --end 2026-09
python3 -I backtest/fetch_edge_data_oi.py stampscan --symbols ETHUSDT --start 2024-02 --end 2024-03
python3 -I backtest/fetch_edge_data_oi.py stamp1m --symbols BTCUSDT --months 2021-03,2022-06,2023-06,2024-01,2024-04,2024-08
python3 -I backtest/fetch_edge_data_oi.py stampcheck --symbols BTCUSDT --months 2020-10,2021-05,2022-06,2023-03,2024-08,2025-04,2026-03
python3 -I backtest/fetch_edge_data_oi.py oivol --symbols ALL
python3 -I backtest/fetch_edge_data_oi.py bybit --symbols BTCUSDT,SOLUSDT,XRPUSDT --months 2021-05,2022-05,2022-11,2024-08
# outcome-blind counts (Tier A uses universe_pit.csv ranks 3-40 when present; Tier B = BTC/ETH, no mask)
python3 -I backtest/fetch_edge_data_oi.py counts --tier A
python3 -I backtest/fetch_edge_data_oi.py counts --tier B --symbols BTCUSDT,ETHUSDT
```

Layout: `backtest/data_cache/local/edge/um1h/<SYM>.csv.gz` (+ `.patched.json`),
`edge/metrics_raw/<SYM>/*.zip` (+ `<SYM>.listing.json`), `edge/metrics/<SYM>.parquet`
(+ `.consolidate.json`), `edge/h010_checks/*.csv|json`, `edge/logs/`.

## 10. Consumer loaders (import from `backtest.fetch_edge_data_oi`)

- `load_um1h(sym)`: UTC index = bar OPEN time. Columns open, high, low, close, volume,
  quote_volume, trades, taker_buy_base, taker_buy_quote. The bar closes at index + 1h. Match
  decisions by close time (CLAUDE.md lesson).
- `load_metrics(sym)`: UTC index = raw stamp. `snap_ts` = measured snapshot time. `oi_ok` = validity
  flag. Raw values otherwise, nothing filled.
- `oi_at(met, times, lag="5min", max_age="30min", col="oi")`: the point-in-time accessor. It uses
  `snap_ts` and `oi_ok` and returns NaN in gaps.

Every artifact was re-loaded through these loaders after it was written (the fetch and consolidate
steps call them and print row counts, ranges and uniqueness). The counts in section 7 were computed
from the re-loaded files.
