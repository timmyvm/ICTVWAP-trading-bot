# H001 data report: tail-funding cash-and-carry (Gate 1)

Data engineer A, 2026-10-10. Card: `research/hypotheses/H001_tail_funding_cash_and_carry_rotation.md`.
Eras (chair): explore 2020-09 .. 2024-12, verdict 2025-01 .. data end (2026-09). Nothing in this
report reads a forward return, a P&L or a price path in the verdict era. Verdict-era numbers below
are coverage, gaps, row counts and the funding-state counts the chair asked for. The half-life is
computed on explore-era data only, and paths are cut at 2024-12-31 23:59 UTC.

Script: `backtest/fetch_edge_data_funding.py` (extends `fetch_binance_archive.py`; reuses its
`BASE`, `KLINE_COLS`, `months`, `epoch_seconds`). Data: `backtest/data_cache/local/edge/` (gitignored).

## 1. Sources

| Source | URL pattern | Used for |
|---|---|---|
| Binance bucket listing | `https://s3-ap-northeast-1.amazonaws.com/data.binance.vision?prefix=<p>&delimiter=/&marker=<m>` | symbol lists, month lists, aggTrades sizes, bookDepth day lists |
| USDT-M 1d klines | `https://data.binance.vision/data/futures/um/monthly/klines/<S>/1d/<S>-1d-<YYYY-MM>.zip` | turnover rank, liveness (zombie) mask |
| USDT-M funding | `.../futures/um/monthly/fundingRate/<S>/<S>-fundingRate-<YYYY-MM>.zip` | f, interval, f8 |
| USDT-M premium index | `.../futures/um/monthly/premiumIndexKlines/<S>/1h/...` and `daily/.../1m/` | sign/timing check, cross-vendor |
| Spot klines | `.../spot/monthly/klines/<S>/1d/...` (listing per pair, 1-2 files per pair) | spot coverage by month, perp-to-spot mapping check |
| USDT-M bookDepth | `.../futures/um/daily/bookDepth/<S>/<S>-bookDepth-<YYYY-MM-DD>.zip` | coverage, one-day depth sketch |
| Bybit archive | `https://public.bybit.com/{trading,spot,premium_index,spot_index}/` | Bybit listing dates, one-day trade-level comparison |

The `metrics` and `bookDepth` datasets exist only under `daily/`, not `monthly/` (USDT-M monthly
holds aggTrades, bookTicker, fundingRate, indexPriceKlines, klines, markPriceKlines,
premiumIndexKlines, trades).

## 2. What is held (all under `backtest/data_cache/local/edge/`)

| Artifact | Content | Size / coverage | Loader (re-load verified) |
|---|---|---|---|
| `universe_pit.csv` | one row per (symbol, month) traded at the month's start: `symbol, month, first_month, last_month, listed_spot, spot_symbol, multiplier, alive, hist_days, n_days30, turnover_med30, rank_any, rank, in_universe_3_50` | 20,557 rows, 700 symbols, 2020-02..2026-09; 3,515 in-universe (rank 3-50) rows | `fetch_edge_data_funding.load_universe()` |
| `universe_symbols.csv` | every USDT-M archive symbol: quote, base, multiplier, exclusion reason, first/last archive month, spot pair, `listed_spot` (ever in the spot archive) | 1,056 symbols | pandas |
| `universe_excluded.csv` | excluded symbols by reason | 7 reasons | pandas |
| `klines_1d_um/<S>.csv` | USDT-M 1d bars (open-time epoch s; o/h/l/c, volume, quote_volume, trades) | 712 kept symbols (+27 TradFi files left from before re-classification), every archive month 2019-12..2026-09 | `load_klines()` |
| `klines_1d_um_defects.csv`, `aggtrades_sizes.csv` | per-symbol full-history scan; monthly aggTrades zip sizes | 711 / 19,931 rows | pandas |
| `funding/<S>.csv` | `timestamp, rate, interval_h, interval_file, interval_derived, f8, calc_offset_ms` | 418 symbols, 756,648 settlements, 2020-01-01..2026-09-30 | `load_funding_edge(S)`; also `bracket_experiment.load_funding` (timestamp, rate) |
| `funding_panel.csv.gz` | long panel `timestamp, symbol, rate, interval_h, f8` | same | `load_funding_panel()` |
| `funding_defects.csv` | per-symbol funding defects and at-floor share by year | 418 rows | pandas |
| `spot_coverage.csv` | per ever-top-60 perp: spot pair, spot months (monthly coverage), perp/spot mapping check | 333 pairs | pandas (`spot_cover()`) |
| `bybit_listing.csv` | first/last Bybit perp and spot trade file per symbol | 848 symbols | pandas |
| `gate1_episodes.csv` | every de-clustered episode (start, end, bars, coin, spot flags) per (threshold, exit) | 6,240 rows | pandas |
| `premium_1h/{BTCUSDT,ORDIUSDT}.csv` | 1h premium index 2024-01..03 (formula check only) | 2,184 rows each | `load_klines()` |
| `bybit_compare_<day>.csv`, `bookdepth_probe_2024-03-08.csv` | cross-vendor and depth probes | 2 + 2 + 6 rows | pandas |
| `raw/` | every downloaded zip/gz (resume cache; `.404` markers for files the archive lacks) | 237 MB | n/a |

Funding scope: every symbol-month within one month of a month in which the symbol had `rank` or
`rank_any` <= 60 (418 symbols, 6,523 files). The rank 3-50 universe is fully covered except for
15 symbol-months the archive does not have (section 6).

## 3. Units, clocks, sign and timing

| Check | Result |
|---|---|
| Kline timestamp unit | USDT-M klines are ms in every year (including 2025-26; files carry a header row from about 2022). Spot klines switch to MICROSECONDS from 2025-01 (verified on BTCUSDT 2025-06). Unit is detected per file by magnitude. |
| Bar label | Open time, UTC. 1d bars open at 00:00 UTC (0 misaligned of all 1d rows). |
| Clock against a known event | SEC fake ETF-approval post, 21:11 UTC on 2024-01-09: BTCUSDT perp 1m bar stamped 21:11 runs 46,717 -> 47,637 (+197 bp) on 7,099 BTC versus 135 BTC in the 21:10 bar. Stamps are UTC open times. (`clock-check`) |
| Second-vendor clock | Bybit trade files against Binance 1m on four coin-days: the best lag of 1m returns is 0 min in all four (corr 0.989-0.993). |
| Funding calc_time | ms, 0-47 ms after the settlement instant (max over 418 symbols 47 ms). Rounded to the hour. 0 settlements of 8 h coins off the 00/08/16 UTC grid. |
| Funding interval column | `funding_interval_hours` is present in every file from 2020-01 on (0 missing). Verified against the settlement spacing: FTTUSDT switched to 2 h on 2022-11-10 04:00 and back to 8 h at 2022-11-14 08:00, and the column follows it. The 413 rows where column and spacing disagree are exactly such transition rows (the first row after a switch). `f8 = rate x 8 / interval_h` uses the column. |
| Interval mix (in-universe settlements) | share not 8 h: 0.0% 2020-21, 0.2% 2022, 3.8% 2023, 36% 2024, 55% 2025, 64% 2026. Of 418 symbols, 164 were 4 h-only and 61 used 1 h at some point. |
| Funding sign and timing | Rebuilt F from the 1h premium index with F = P + clamp(I - P, +-5 bp) (P weighted 1..8 over the interval), BTCUSDT 2024-01..03, 273 settlements: corr 0.962 and 94.9% within 1 bp when P is taken over the 8 h ENDING at the settlement, versus 0.79/0.80 when shifted +-8 h. So the rate printed at s is fixed by the premium of the interval that ends at s, and a positive premium gives a positive rate. Convention (Binance docs, confirmed by this sign): positive rate = longs pay shorts, paid only by positions open at the settlement instant (00/08/16 UTC for 8 h coins, every 4 h or 1 h for the others). ORDI was on 4 h funding throughout that window, so only BTC was checked. |
| 1 bp floor | Floor in f8 units is exactly 0.0001 for 8 h, 4 h and 1 h coins (rates 0.0001, 0.00005, 0.0000125). The modal f8 is 0.0001 for 416 of 418 symbols. Exceptions: BNBUSDT and MUUUSDT have mode 0 (interest component apparently 0); their dead zone sits at 0, not 1 bp. |

## 4. Point-in-time universe

Method (`compute_ranks`): at the first instant D of each month, `turnover_med30` = median daily
quote volume over [D-30 d, D). A symbol is rankable if it printed a 1d bar with volume > 0 on
D-1 (tradable at D) and has >= 20 bars in the window. `rank` adds the card's >= 90 days of history
(first archive bar <= D-90 d); `rank_any` does not. `in_universe_3_50` = `rank` in 3..50. Nothing
after D enters a month's row. Delisted symbols stay in for every month they traded.

Excluded from ranking (reported in `universe_excluded.csv`): 53 dated delivery contracts, 5 index
contracts (ALL, BLUEBIRD, BTCDOM, DEFI, FOOTBALL; DEFI from 2020-08 and BTCDOM from 2021-06, so
these do touch the explore era), 3 stablecoin bases (FRAX, USDC, USTC; USTC is the de-pegged Terra
dollar, excluded as a stablecoin base by the card's rule), 180 TradFi/commodity perps (gold, silver,
platinum, palladium, PAXG from 2025-03, XAUT, oil and gas, US/HK/KR equities, ETFs and leveraged
ETFs, USDBRL; the earliest is PAXG at 2025-03, so the explore era is unaffected), 41 BUSD- and 40 USDC-quoted perps, and 22 other non-USDT names (mostly
`<S>USDTSETTLED`: the archive's name for a contract that was settled and later relisted under the
same ticker). The TradFi list is curated by name; ambiguous single-letter tickers were kept as
crypto. One mistake was caught and fixed: SPXUSDT is the SPX6900 meme coin (from 2024-12, in ranks
3-50 in 2025-07 and 2025-08), not the S&P 500, and is now in the universe.

Universe size (rank 3-50): 23 coins in 2020-09 (only 25 symbols had 90 days of archive history),
29/34/41 in 2020-10/11/12, 48 every month from 2021-01. Distinct coins ever in ranks 3-50: 285;
50 of them were later delisted or migrated.

**Delisted and collapsed names are in the archive.** LUNAUSDT (archive 2021-01..2022-05; traded
2021-01-28..2022-05-12; in ranks 3-50 for 12 months), SRMUSDT (traded to 2022-11-15; 8 months in
universe), FTTUSDT (traded 2022-04-15..2022-11-14), BTCSTUSDT (traded only 2021-03-04..03-12),
1000LUNCUSDT and LUNA2USDT (from 2022-09). The card's survivorship worry does not apply to Binance.

**DEFECT: zombie rows.** The archive keeps publishing monthly files for delisted contracts with
zero volume and a frozen OHLC, for years: 146 symbols end in >= 3 frozen days (BTCSTUSDT 1,936
frozen days to 2026-06; FTTUSDT 1,416; AGIX/OCEAN 827 each after the 2024-06-25 FET merger).
158 perps stopped trading before 2026-09-25 although only 29 have an archive `last_month` before
2026-09. Funding files continue too, printing a constant 0.0001 (FTTUSDT through 2025-06).
Handling: the universe requires volume > 0 on D-1; funding settlements whose trading day had a 1d
bar with zero volume are dropped (874 dropped). `first_month`/`last_month` in
`universe_symbols.csv` are ARCHIVE months, not trading dates: use `alive` or the 1d volume.

**Suspended or relisted tickers:** 11 symbols have zero-volume stretches inside their trading
span (CVCUSDT 898 days, CVXUSDT 434, SLPUSDT 433, CTKUSDT 393, LITUSDT 325, TLMUSDT 264,
MAVIAUSDT 99, ICPUSDT 82, AIAUSDT 39, PUMPUSDT 26, AERGOUSDT 19). `alive` handles them month by month.

Other full-history checks on all 711 kept 1d series that existed at the scan (SPX6900 added later): 0 duplicate stamps, 0 misaligned bars,
0 non-positive prices, 0 high/low violations. 1,540 day-on-day closes move more than 50%
(LUNAUSDT max |log return| 4.9 in May 2022; new listings and relisting days account for most).
They are counted, not removed: this card does not use perp prices for its counts.

**Cost-control screen that FAILED (disclosed because it is a trap).** To save downloads I first
fetched 1d files only where the monthly aggTrades zip size (a trade-count proxy) ranked <= 200.
The check after ranking showed a coin at turnover rank 58 with trade-count rank 318 (rank <= 120
reached size rank 520 in the verdict era, 248 in 2024). So the screen would have dropped real
top-60 coins. The published universe was rebuilt from the full, unscreened pass
(`universe-fill`), and the script's default is now no screen.

Ticker changes (each ticker is its own instrument; a holding window across a change is a
migration event, last perp trade date in brackets): MATIC -> POL (2024-09-04), RNDR -> RENDER
(2024-07-16), FTM -> S (2025-01-06), AGIX and OCEAN -> FET (2024-06-25), TOMO -> VIC
(2023-11-14), EOS -> A (2025-05-21), MKR -> SKY (2025-09-08), BNX -> FORM (2025-03-17; BNX also
had a 4.0 log-return day), BTT -> 1000BTTC (2022-01), LUNA -> LUNA2 (new chain) with old LUNA
re-listed as 1000LUNC. **The spot ticker LUNAUSDT was reused**: old LUNA until 2022-05, new LUNA
from 2022-05-28. The perp LUNAUSDT never overlaps the new-LUNA spot, so the mapping check passes.

## 5. Spot coverage and the perp-to-spot map

Map: strip the multiplier prefix (`1000`, `1000000`, `1M`) and append USDT (1000PEPEUSDT ->
PEPEUSDT x 1000). 16 kept perps carry a multiplier. Of 418 ever-top-60 perps, 333 have a Binance
spot pair. Monthly spot coverage comes from the spot archive listing (`spot_month_list`).
Mapping check: on the first and last month in which both the perp traded and the spot existed,
the median |log(perp close / (spot close x multiplier))| on daily closes is 9-10 bp (max 131 bp,
OPENUSDT in its listing month). No pair flagged above 200 bp once zombie perp days were excluded.
(Before that fix, RAY, STRAX, SXP and others were falsely flagged by frozen perp prices.)

Bybit (`bybit_listing.csv`, first daily trade file as the listing proxy): 92% of 848 kept perps
have a Bybit perp archive under the same name. The 8% gap includes multiplier contracts Bybit
names differently (SHIB1000USDT vs 1000SHIBUSDT). Only 43% have a Bybit spot archive, and the
Bybit spot archive starts 2022-11 for every pair, so **Bybit spot listing dates before 2022-11
are unknowable here**. The card's "Bybit spot for >= 90 days" filter can only be verified from
2023-02.

## 6. Funding data defects

- 15 rank-3-50 symbol-months have no funding file in the archive (HTTP 404): ICPUSDT 2021-09..2022-06
  (the archive lacks ICP funding 2021-05..2022-07), TLMUSDT 2021-11..2022-03 and BNXUSDT 2023-01.
  That is 0.6% of 2,507 explore-era universe symbol-months. Not filled; F_bar is missing there.
- 874 zombie settlements dropped (section 4); 635 settlements fall in months without 1d coverage
  and were kept.
- 0 duplicate settlements, 0 missing interval values.
- 351 spacing gaps larger than the interval, most of them the edges of the rank-limited fetch
  window (a symbol leaving and re-entering the top 60).
- Extremes are real and capped by the exchange: max f8 +6.0% (BNXUSDT), min -16% per 8 h
  equivalent (-2% per 1 h settlements on ARIA, BARD, STO, RIVER, M).

## 7. Cross-vendor: Binance vs Bybit

What Bybit's public archive offers: `premium_index/` and `spot_index/` hold only 11 INVERSE USD
contracts (BTCUSD, ETHUSD, ...), daily files 2019-10-01 .. 2020-03 — nothing for USDT perps and
nothing in the explore era. `trading/` has tick trades per perp (USDT perps from 2020-03-25,
including delivery contracts). `spot/` has spot trades from 2022-11. **There is no Bybit funding
history and no USDT premium index in the archive**, so Bybit funding cannot be compared directly.
The closest check is the perp-minus-spot basis from trades, set against Binance's own basis and
premium index (`bybit-compare`, 1m last-trade prices):

| coin-day | perp |Bybit-Binance| p50 / p95 bp | spot p50 bp | basis Binance / Bybit, mean bp | basis corr 1h | Binance premium index mean bp |
|---|---|---|---|---|---|---|
| BTCUSDT 2023-11-08 | 4.1 / 5.8 (Bybit higher) | 0.4 | 3.5 / 7.6 | 0.64 | 3.5 |
| ORDIUSDT 2023-11-08 | 8.0 / 36.2 | 13.1 | 3.3 / 2.7 | 0.76 | 4.3 |
| STXUSDT 2024-03-08 (tail state) | 3.5 / 8.7 | 2.9 | 15.2 / 17.0 | 0.65 | 13.0 |
| TIAUSDT 2024-03-08 (tail state) | 8.6 / 13.9 | 3.3 | 10.9 / 17.7 | 0.14 | 9.6 |

Reading: in the tail state, funding is the premium minus about 5 bp, so funding moves one for one
with the premium. Venue premia differ by 2-7 bp per day in level and correlate 0.14-0.76 hour by
hour. **Binance funding is a noisy proxy for the funding Bybit pays.** The difference is the same
size as the excess the card harvests (7 bp entry). In these two tail coin-days Bybit's basis was
higher, which favours the carry, but four coin-days cannot justify an adjustment. Liquidity:
Bybit ORDI spot traded $1.9 M on 2023-11-08 against $256 M on its perp, so the spot hedge is the
thin leg.

## 8. bookDepth (USDT-M perps only)

Coverage (listing only): daily files from 2023-01-01 (GALA, BTC) or from listing (STX 2023-02-21,
1000PEPE 2023-05-05, TIA 2023-10-31, ORDI 2023-11-07) to 2026-10-07, with 1-4 missing days each.
Format: `timestamp, percentage, depth, notional`, 2 snapshots a minute (2,880 a day), bands
+-1, 2, 3, 4, 5%. **There is no 0.5% band and no best bid/ask.** The finest band is 1%, so spread
is not measurable from this dataset (the monthly `bookTicker` archive would give it; not fetched).
There is no spot depth in the archive.

Sampled day 2024-03-08 (tail state), cumulative notional within 1%, median (p10), USD:
ORDI bid 2.36 M (1.91 M) / ask 2.10 M (1.76 M); STX 1.01 M (0.68 M) / 0.86 M (0.52 M);
TIA 1.31 M (1.03 M) / 1.19 M (0.93 M); 1000PEPE 1.97 M (1.33 M) / 1.97 M (1.46 M);
GALA 1.26 M (0.94 M) / 1.10 M (0.84 M); BTC 110 M / 105 M.
Sketch (uniform depth within the 1% band, half-spread excluded): average perp slippage
approx. 50 bp x Q / D1%. For Q = $20k at the thinnest p10 (STX ask, $0.52 M) that is about 2 bp
per side; for $100k it is about 10 bp. The perp leg at the user's size is near the card's 1 bp
assumption. The spot leg cannot be stressed from Binance's archive.

## 9. Gate 1 counts (outcome-blind: funding states only)

Definitions: 8 h decision grid 00/08/16 UTC from 2020-09-01. F_bar(t) = mean f8 over settlements
in (t-24 h, t]. Entry when F_bar >= threshold AND the coin is in ranks 3-50 that month. The episode
lasts until F_bar <= exit (2 or 3 bp) or data ends; consecutive bars merge. Coin-day = (coin, UTC
date) with at least one in-universe grid point at or above the threshold. Spot share = episodes
whose coin had a Binance spot archive file in the entry month. Bybit-ok = Bybit perp listed at
entry AND Bybit spot listed >= 90 days before; this is unknowable before 2023-02 and counted as
not-ok there.

(a) Universe and dead zone, in-universe coin-settlements (ranks 3-50):

| year | settlements | coins | at floor (f8 = 1 bp) | below floor | above floor | f8 >= 5 bp | not 8 h | universe size / month |
|---|---|---|---|---|---|---|---|---|
| 2020 (Sep-Dec) | 11,640 | 41 | 63.4% | 13.5% | 23.0% | 9.5% | 0.0% | 31.8 |
| 2021 | 52,015 | 90 | 46.5% | 12.4% | 41.1% | 24.1% | 0.0% | 48 |
| 2022 | 51,850 | 98 | 39.4% | 60.5% | 0.1% | 0.0% | 0.2% | 48 |
| 2023 | 53,436 | 113 | 52.1% | 37.5% | 10.4% | 1.4% | 3.8% | 48 |
| 2024 | 64,169 | 110 | 50.9% | 27.7% | 21.4% | 6.0% | 35.9% | 48 |
| 2025 | 74,427 | 114 | 44.5% | 53.9% | 1.6% | 0.4% | 55.0% | 48 |
| 2026 (Jan-Sep) | 59,825 | 111 | 34.4% | 58.2% | 7.4% | 3.6% | 64.3% | 48 |

The censoring the card describes is real but weaker than assumed: only 34-63% of settlements sit
exactly on the floor. In 2022 and 2025-26 the larger mass is BELOW the floor (negative or
sub-1 bp funding).

(b) Episodes by year, exit 2 bp (exit 3 bp in brackets where it differs), with coin-days:

| entry | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | explore total | verdict total |
|---|---|---|---|---|---|---|---|---|---|
| 5 bp episodes | 167 (189) | 732 (862) | 1 | 70 (80) | 212 (264) | 26 (27) | 93 (109) | 1,182 (1,396) | 119 (136) |
| 5 bp coin-days | 490 | 5,009 | 1 | 214 | 1,249 | 46 | 416 | 6,963 | 462 |
| 7 bp episodes | 112 (121) | 533 (594) | 0 | 21 (23) | 102 (124) | 10 | 72 (82) | **768 (862)** | **82 (92)** |
| 7 bp coin-days | 302 | 3,795 | 0 | 42 | 534 | 18 | 281 | 4,673 | 299 |
| 10 bp episodes | 51 (53) | 358 (392) | 0 | 1 | 40 (45) | 3 | 44 (49) | 450 (491) | 47 (52) |
| 10 bp coin-days | 117 | 2,632 | 0 | 1 | 141 | 7 | 162 | 2,891 | 169 |
| 15 bp episodes | 16 | 223 (242) | 0 | 0 | 5 | 2 | 27 (28) | 244 (263) | 29 (30) |
| 15 bp coin-days | 25 | 1,595 | 0 | 0 | 10 | 5 | 74 | 1,630 | 79 |

Distinct months containing at least one episode (explore / verdict): 5 bp 30 / 18; 7 bp 25 / 16;
10 bp 20 / 11; 15 bp 13 / 11 (of 52 explore and 21 verdict months).

Concentration (7 bp, exit 2): 2021 alone holds 533 of 768 explore episodes (69%), and the top five
months (2021-01, 2021-03, 2020-11, 2021-05, 2021-08) hold 54%. Tail states are market-wide, not
idiosyncratic: in 2024-03 more than 40 universe coins entered within a few days of each other
(1000PEPE, FET, GALA, TIA, WLD, ORDI, SUI, ARB, OP, ...). With K = 5, most coins in such a month
cannot be held at once. The independent unit is the month, and the explore era has 25 of them at
7 bp.

(c) Hedge coverage of the episodes (7 bp, exit 2):

| year | Binance spot | Bybit perp + spot >= 90 d |
|---|---|---|
| 2020-21 | 100% | unknowable (Bybit spot archive starts 2022-11) |
| 2023 | 100% | 57% |
| 2024 | 87% | 79% |
| 2025 | 30% (3 of 10) | 50% |
| 2026 | 7% (5 of 72) | 6% |

**In the verdict era the tail-funding coins are mostly perp-only listings with no spot market on
either venue** (PIPPIN, RIVER, LAB, SIREN, ESPORTS, H, RAVE, ...). Verdict-era 7 bp episodes with a
Binance spot hedge: 8 of 82. With a Bybit hedge: 9.

## 10. Half-life of excess funding (EXPLORE ERA ONLY, chair-authorised single statistic)

Estimator: for each explore-era episode (entry thresholds 5, 7, 10 bp; de-clustered with exit
2 bp; entry while in ranks 3-50), take the path x_k = F_bar(t0 + 8 h k) - 1 bp for k = 0..63
(21 days). The path is followed regardless of exit, and every grid point at or after 2025-01-01
is masked. Decay curve R(k) = sum_e x_{e,k} / sum_e x_{e,0} over episodes observed at k.
Half-life = first k with R(k) <= 0.5 (linear interpolation), in days. Uncertainty: 2,000
bootstrap resamples of entry MONTHS with replacement. "inf" = R never reaches 0.5 inside 21 days
(right-censored). Secondary, as an estimator check only: a log-linear fit of R(k).

| entry | episodes (months) | median x0 | R at k = 3 / 9 / 21 / 42 / 63 | half-life | 95% interval | 90% interval | P(boot < 3 d) | P(boot > 21 d) | log-linear fit |
|---|---|---|---|---|---|---|---|---|---|
| 5 bp | 1,182 (30) | 4.6 bp | 1.02 / 0.93 / 0.81 / 0.70 / 0.69 | > 21 d | 3.7 d - > 21 d | 5.5 d - > 21 d | 0.5% | 56% | 44 d (unstable) |
| 7 bp | 768 (25) | 6.7 bp | 0.94 / 0.84 / 0.67 / 0.63 / 0.56 | > 21 d (boot median 14.3 d) | 3.1 d - > 21 d | 3.4 d - > 21 d | 1.9% | 39% | 35 d (unstable) |
| 10 bp | 450 (20) | 10.0 bp | 0.88 / 0.80 / 0.57 / 0.53 / 0.46 | 7.6 d | 2.9 d - > 21 d | 3.3 d - > 21 d | 3.2% | 7% | 24 d (95% 4.2-161 d) |

R(1) and R(2) are 1.08-1.18: a 24 h trailing mean keeps rising for a bar or two after it first
crosses the threshold. The curve is not exponential, which is why the log-linear fit is unstable.
Its interval for 5 and 7 bp spans negative values. Read the crossing estimator.

Against falsifier 1 (half-life under about 3 days, or fewer than about 60 independent episodes):
the point estimates are far above 3 days, and 2-3% of month-resamples fall under 3 days at 7 and
10 bp. On this statistic the card survives Gate 1. Two caveats belong next to it. (1) The sample
is 69% 2021, so the statistic largely describes the 2021 bull market. A 2023-24-only estimate is
the obvious next question; I did not compute it because the authorisation covered one statistic.
(2) Paths of re-entries overlap their predecessors. The month bootstrap covers within-month
dependence, not dependence across adjacent months, so the intervals are if anything too narrow.

## 11. What threatens the card

1. **Verdict-era testability.** 82 episodes at 7 bp in 21 months (10 in all of 2025). Only 8
   have a Binance spot market and 9 a seasoned Bybit spot. By hedgeable episodes the
   verdict era is nearly empty. Falsifier 2 then cannot be evaluated with any power. The
   hedgeable tail has moved to perp-only listings.
2. **Regime concentration.** Explore-era episodes are 69% 2021, and 2022 has none. The half-life
   and any carry result will mostly be a 2021 statement (CLAUDE.md: the era is the variable).
3. **Venue transfer.** Bybit has no funding archive. Trade-level basis differs from Binance by 2-7
   bp per day in tail states, with weak hourly correlation, so Binance's funding is a noisy proxy
   for what Bybit pays.
4. **Spot leg liquidity is unmeasured.** bookDepth is perp-only and starts at 1%. Bybit spot on a
   tail coin can trade under 1% of its perp volume.
5. **Market-wide tail states.** Dozens of coins qualify in the same week. The K = 5 cap and
   capital, not the signal, decide which episodes are traded, so selection rules will matter.

## 12. Cut, and why

- Funding for ranks 61-120: the scope was cut to symbols within one month of rank <= 60 (418
  symbols), for depth on ranks 3-50 within the time box. Command to extend:
  `funding --top 120 --only-rank 120` (about +5k files).
- Full spot 1d klines: replaced by listing-based monthly coverage plus a 1-2-file mapping check
  per pair. The spot hedge price series is NOT held. Command: `spot --top 60 --interval 1d`.
- Premium-index 1h for the top 60: not fetched (only BTC and ORDI 2024-01..03, for the formula
  check). Command: `premium --top 60 --interval 1h`.
- bookTicker (spread): not fetched.
- Wall time was about 2.5 h against a 45-minute box. The 1d universe needed 21k files at about
  9 files/s on 4 connections, and the failed screen cost a second pass.

## 13. Rebuild (container is ephemeral; `backtest/data_cache/local/` is gitignored)

Run from the repo root, one at a time (each uses at most 4 connections and resumes from `raw/`):

```
pip install pytz          # needed by backtest.bracket_experiment.load_funding (a consumer loader)
python3 backtest/fetch_edge_data_funding.py universe                         # ~40 min: listings + every 1d file, ranks
python3 backtest/fetch_edge_data_funding.py funding --top 60 --only-rank 60  # ~12 min: 418 symbols, 6,523 files
python3 backtest/fetch_edge_data_funding.py spot --coverage-only --top 60    # ~1 min
python3 backtest/fetch_edge_data_funding.py bybit --top 60                   # ~1 min, public.bybit.com
python3 backtest/fetch_edge_data_funding.py counts > backtest/data_cache/local/edge/counts.log   # ~3 min, offline
# checks quoted above
python3 backtest/fetch_edge_data_funding.py clock-check
python3 backtest/fetch_edge_data_funding.py formula-check --symbols BTCUSDT,ORDIUSDT --start 2024-01 --end 2024-03
python3 backtest/fetch_edge_data_funding.py bybit-compare --symbols BTCUSDT,ORDIUSDT --day 2023-11-08   # ~190 MB of Bybit trades
python3 backtest/fetch_edge_data_funding.py bybit-compare --symbols STXUSDT,TIAUSDT --day 2024-03-08
python3 backtest/fetch_edge_data_funding.py depth --symbols ORDIUSDT,STXUSDT,TIAUSDT,1000PEPEUSDT,GALAUSDT,BTCUSDT --day 2024-03-08
```

What was actually run: `universe --screen-k 200` (the earlier default), then `universe-fill`,
which completes every month without the screen and re-ranks. After SPX6900 was re-admitted,
`universe-fill` ran again (it lists newly admitted symbols), followed by the `funding`, `spot` and
`counts` commands above. The sequence is equivalent to `universe` with the current default
(`--screen-k 0`) and current classification. `bybit` was run on all 848 kept USDT perps; `--top 60`
covers every symbol the counts use. Data end: the 2026-09 monthly archive. Rebuilding later
changes nothing before 2026-10, except that a newly delisted coin's frozen rows grow.
