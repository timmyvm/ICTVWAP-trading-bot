# Catalogue family: mean reversion, oscillators and statistical arbitrage (S-MR)

Phase-0 cards for docs/CATALOGUE.md, compiled 2026-10-10. Outcome-blind: nothing here comes from this repo's
data or results. Every number is the source's own, for its market and era, and none is computed here. "Read:
full" = full text read; "read: abstract" = abstract, listing or summary page only; "recalled, not re-fetched" =
memory, not verified this session. The shared web-search budget ran out before Wilder's and Connors' books,
Lane's 1984 article and Chan's book could be re-checked; those items are flagged per card, not filled in.

**Cost convention.** 13 bp round trip per unit traded. A two-leg pair (or $1 long / $1 short book) that
turns over fully costs 2 x 13 = 26 bp per round trip. Perp funding is left out.

## Sources (keys used in the cards)

| key | citation | URL | read |
|---|---|---|---|
| CA08 | Connors & Alvarez, "Short Term Trading Strategies That Work", TradingMarkets 2008 | (book; not fetched) | recalled, not re-fetched |
| SC-R2 | StockCharts ChartSchool, "RSI(2)" (describes Connors' rules) | https://chartschool.stockcharts.com/table-of-contents/trading-strategies-and-models/trading-strategies/rsi-2 | full |
| CXO-R2 | CXO Advisory, "Out-of-sample tests of bullish regime 2-day RSI signals" | https://www.cxoadvisory.com/technical-trading/out-of-sample-tests-of-bullish-regime-2-day-rsi-signals | full |
| SQ-D7 | StrategyQuant blog, "Larry Connors' Double 7 Strategy" (secondary) | https://strategyquant.com/blog/larry-connors-double-7-strategy-tested-on-spy-and-8-other-markets/ | full |
| W-RSI | Wikipedia, "Relative strength index" (cites Wilder 1978 book and Commodities, June 1978) | https://en.wikipedia.org/wiki/Relative_strength_index | full |
| W-STO | Wikipedia, "Stochastic oscillator" (cites Lane, TASC May/June 1984, pp. 87-90) | https://en.wikipedia.org/wiki/Stochastic_oscillator | full |
| SC-WR | StockCharts ChartSchool, "Williams %R" | https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/williams-r | full |
| BB-R | Bollinger, "Bollinger Band Rules" (primary, author's site) | https://www.bollingerbands.com/bollinger-band-rules | full |
| W-BB | Wikipedia, "Bollinger Bands" (cites Lento et al. 2007; Balsara, Chen & Zheng 2007) | https://en.wikipedia.org/wiki/Bollinger_Bands | full |
| LGW07 | Lento, Gradojevic & Wright, "Investment information content in Bollinger Bands?", Applied Financial Economics Letters 3(4) 2007, 263-267 | https://ideas.repec.org/a/taf/raflxx/v3y2007i4p263-267.html | abstract |
| C13 | Chan, "Algorithmic Trading: Winning Strategies and Their Rationale", Wiley 2013, ch. 2 | (publisher page fetch failed) | recalled, not re-fetched |
| MKM19 | Moon, Kim & Moon, "Empirical investigation of state-of-the-art mean reversion strategies for equity markets", arXiv 1909.04327 (2019) | https://www.arxiv.org/abs/1909.04327 | abstract |
| SC-CCI | StockCharts ChartSchool, "Commodity Channel Index (CCI)" | https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/commodity-channel-index-cci | full |
| W-CCI | Wikipedia, "Commodity channel index" (cites Schlossberg 2006 for Lambert's rules) | https://en.wikipedia.org/wiki/Commodity_channel_index | full |
| P13 | Pagonidis, "The IBS Effect: Mean Reversion in Equity ETFs", NAAIM white paper (data to 2013-05-12; listed under 2014) | https://naaim.org/wp-content/uploads/2014/04/00V_Alexander_Pagonidis_The-IBS-Effect-Mean-Reversion-in-Equity-ETFs-1.pdf | full |
| PJ23 | Pandey & Joshi, "Using Internal Bar Strength as a Key Indicator for Trading Country ETFs", arXiv 2306.12434 (2023) | https://arxiv.org/html/2306.12434v1 | full |
| W-VWAP | Wikipedia, "Volume-weighted average price" | https://en.wikipedia.org/wiki/Volume-weighted_average_price | full |
| N12 | Nagel, "Evaporating Liquidity", NBER WP 17653 (2011); RFS 2012 (journal version recalled) | https://www.nber.org/papers/w17653.pdf | full |
| L90 | Lehmann, "Fads, Martingales, and Market Efficiency", NBER WP 2533; QJE 105(1) 1990 | https://www.nber.org/papers/w2533 | abstract |
| BBD19 | Baltussen, van Bekkum & Da, "Indexing and Stock Market Serial Dependence Around the World", JFE (accepted 2018, DOI 10.1016/j.jfineco.2018.07.016) | https://personal.eur.nl/vanbekkum/2018%20JFE%20BaltussenVanBekkumDa.pdf | full |
| GGR | Gatev, Goetzmann & Rouwenhorst, "Pairs Trading: Performance of a Relative Value Arbitrage Rule", NBER WP 7032 (1999); RFS 19(3) 2006, 797-827 | https://www.nber.org/system/files/working_papers/w7032/w7032.pdf | full (WP) |
| DF10 | Do & Faff, "Does Simple Pairs Trading Still Work?", FAJ 66(4) 2010, 83-95 | https://ideas.repec.org/a/taf/ufajxx/v66y2010i4p83-95.html | abstract |
| RLF16 | Rad, Low & Faff, "The profitability of pairs trading strategies: distance, cointegration and copula methods", Quantitative Finance 16(10) 2016, 1541-1558 | https://ideas.repec.org/a/taf/quantf/v16y2016i10p1541-1558.html ; summary https://www.cxoadvisory.com/?p=27232 | abstract; secondary full |
| F20 | Fil, "Gold Standard Pairs Trading Rules: Are They Valid?", arXiv 2010.01157 (2020) | https://arxiv.org/pdf/2010.01157 | full |
| QP-PT | Quantpedia, "Pairs trading with stocks" (literature list incl. Clegg on cointegration persistence) | https://quantpedia.com/strategies/pairs-trading-with-stocks | full (secondary) |
| AL10 | Avellaneda & Lee, "Statistical Arbitrage in the U.S. Equities Market", drafts 2008-07 and 2009-06; Quantitative Finance 2010 (journal recalled) | https://math.nyu.edu/~avellane/AvellanedaLeeStatArb071008.pdf ; https://www.math.nyu.edu/faculty/avellane/AvellanedaLeeStatArb20090616.pdf | full |
| W-GAP | Wikipedia, "Gap (chart pattern)" | https://en.wikipedia.org/wiki/Gap_(chart_pattern) | full |
| LC19 | Lobão & Costa, "Short-term overreaction in equity ETFs following extreme one-day returns", Revista Contabilidade & Finanças 30(81) 2019, 352-367 | https://revistas.usp.br/rcf/article/view/161315 | abstract |
| Z21 | Zaremba, Bilgin, Long, Mercik & Szczygielski, "Up or down? Short-term reversal, momentum, and liquidity effects in cryptocurrency markets", IRFA 78 (2021) 101908 | https://earsiv.medeniyet.edu.tr/items/23a96c9f-3952-4bdf-aec5-abafb3aaab70/full | abstract |
| KPZ20 | Kozlowski, Puleo & Zhou, "Cryptocurrency return reversals", Applied Economics Letters (2020) | https://fairfield.elsevierpure.com/en/publications/cryptocurrency-return-reversals/ | abstract |
| KW26 | Kitron & Wengrowicz, "Short-horizon mean reversion in cryptocurrency markets: a matched cross-market measurement", arXiv 2608.21888 (2026) | https://ideas.repec.org/p/arx/papers/2608.21888.html | abstract |
| BD18 | Bianchi & Dickerson, "Trading Volume in Cryptocurrency Markets" (Aug 2018 draft), via CXO summary | https://www.cxoadvisory.com/?p=31597 | secondary full |
| FK20 | Fil & Kristoufek, "Pairs Trading in Cryptocurrency Markets", IEEE Access 8 (2020) 172644-172651 (author names recalled; registry page lists none) | https://starfos.tacr.cz/vysledky-vyzkumu/RIV%2F00216208%3A11230%2F20%3A10416379 ; https://ieeexplore.ieee.org/document/9200323 (did not render) | abstract |
| CU19 | Charles University bachelor thesis, "Pairs Trading in Cryptocurrency Markets" (2019; Binance 2018 data) | https://dspace.cuni.cz/handle/20.500.11956/109634 | abstract |

## Cards

### S-MR-01 Connors RSI(2) pullback inside a 200-day trend
- **Fidelity:** B. Rules from SC-R2 (secondary, full); attribution to CA08 recalled, not re-fetched.
- **Sources:** SC-R2 (full), CXO-R2 (full), CA08 (recalled).
- **Rule:** Daily bars. RSI(2) on close (Wilder smoothing). Long when close > SMA(200) and RSI(2) closes
  below 5 (SC-R2: Connors found 5 beat 10). Short when close < SMA(200) and RSI(2) closes above 95. Enter
  just before the close of the signal day (Connors' preference) or at the next open. Exit long on a close above
  SMA(5); exit short on a close below SMA(5). No stop (SC-R2: Connors found stops hurt on stocks and indices).
  Optional SC-R2 variant: wait for RSI(2) to cross back through 50. Universe: stocks, indices, index ETFs.
- **Primitive vs wrapper:** P1 primary (1-3 day reversal), gated by a 200-day P1 trend state. Wrapper: SMA(200)
  gate, SMA(5) exit (a target), no stop, close execution.
- **Claimed mechanism:** None offered beyond "buy pullbacks in uptrends". Nearest published counterparty story
  is liquidity provision to short-term sellers (S-MR-09); the source does not make it.
- **Published claim:** SC-R2 gives no figures. CXO-R2 tests TradingMarkets' "Improved R2" rule set (a
  variant, in-sample through 2006, headline "84% correct") out of sample 2007-01 to 2009-03: XLK 24 trades, 70%
  winners, +0.25% per trade gross; SPY 12 trades, 83% winners, +0.69% gross. CXO calls the evidence mixed.
- **Decay and crowding:** No formal post-publication study read. Book figures not re-fetched.
- **Cost-floor note:** One round trip (13 bp) per trade held a few days. On CXO-R2's XLK number, 13 bp would
  take about half of the 25 bp gross (arithmetic on the source's figure).
- **Event rate (estimate):** 5-15 entries a year per index; signals across assets fall on the same
  market-wide down days, so date-independent events are of the same order.
- **Applies to / testable here:** US equities/indices in the sources. Y here (daily or intraday perp klines);
  partial for SPY via Yahoo daily.
- **Regime hypothesis:** Works where drift is positive and short-horizon autocorrelation negative (index-like,
  stressed-liquidity days). Fails in crashes where down days cluster, and in assets with daily momentum
  (Z21: the largest coins).
- **Overlaps:** S-MR-07 (same idea, price channel), S-MR-06, S-MR-02, S-MR-10.

### S-MR-02 Classic bounded oscillators: RSI(14) 30/70, Stochastic, Williams %R
- **Fidelity:** C for the trade rule (folklore). Formulas are primary-sourced via W-RSI/W-STO; Lane ties the
  stochastic to cycles, Elliott waves and Fibonacci timing, which is not mechanizable as he intended.
- **Sources:** W-RSI (full), W-STO (full), SC-WR (full). Wilder 1978 and Lane 1984 recalled via citations only.
- **Rule (as described):** RSI(14), Wilder SMMA (alpha = 1/14, seeded with an SMA); overbought 70, oversold 30.
  Folklore entry: long when RSI crosses back above 30, short when it crosses back below 70; exit not specified.
  Wilder's own signal is the failure swing (e.g. RSI 76, back to 72, 77, then below 72). Stochastic: %K =
  100(C - LL_N)/(HH_N - LL_N), N = 5, 9 or 14; %D = SMA(3) of %K; signal = %K crossing %D in an extreme area
  (extreme level not specified). Williams %R(14) = -100(HH - C)/(HH - LL); oversold -80 to -100, overbought 0 to
  -20; SC-WR suggests waiting for a cross of -50 as confirmation.
- **Primitive vs wrapper:** P1 (reversal of an N-bar move). Wrapper: level thresholds, crossovers, divergence,
  confirmation crosses. %R is the stochastic %K mirrored; all three measure location in a recent range.
- **Claimed mechanism:** None beyond "overbought/oversold". Cardwell (W-RSI) reads the same RSI as a trend
  gauge (uptrends live in 40-80): the same statistic is traded with opposite signs.
- **Published claim:** Marek & Šedivá 2017 (via W-RSI; Apple, Exxon, IBM, Microsoft): RSI "can still produce
  good results" but is usually beaten by buy-and-hold over longer periods. No figures.
- **Decay and crowding:** None found.
- **Cost-floor note:** Horizon of ~N bars. The rule clears 13 bp only on timeframes where the expected
  reversion over N bars exceeds 13 bp; at 1m-5m bars that is a strict test.
- **Event rate (estimate):** A few to ~10 oversold crossings a year per asset on daily bars; many more
  intraday, but clustered in time.
- **Applies to / testable here:** All markets. Y.
- **Regime hypothesis:** Works in ranges (variance ratio < 1); fails in trends, where RSI shifts range
  (Cardwell) and oscillators stay pinned.
- **Overlaps:** S-MR-01 (2-bar RSI), S-MR-03 (%b is a stochastic on bands), S-MR-06 (IBS = 1-bar %K), S-MR-05.

### S-MR-03 Bollinger Band contrarian and %b
- **Fidelity:** B. Parameters are primary (BB-R); the contrarian trade rule comes from testers (LGW07 abstract,
  W-BB), not from Bollinger, who rejects it as stated.
- **Sources:** BB-R (full), W-BB (full), LGW07 (abstract).
- **Rule:** Middle band = SMA(20) of close; bands = middle +/- 2 sigma (population sigma, 20 periods). %b =
  (C - lower)/(upper - lower). Contrarian form: long when %b < 0 (close below the lower band), short when %b > 1;
  exit at the middle band (W-BB describes this practice). LGW07 varied MA length and band width (values not
  in the abstract). Bollinger's scaling (BB-R rule 11): 1.9 sigma at 10 periods, 2.1 sigma at 50.
- **Primitive vs wrapper:** P1 primary (z-score of price vs its 20-bar mean); P2 secondary (bandwidth is a
  vol state; the "squeeze" belongs to the breakout family). Wrapper: band threshold, middle-band target.
- **Claimed mechanism:** None. BB-R: "Tags of the bands are just that, tags not signals"; price can "walk" a
  band in trends (rule 7).
- **Published claim:** LGW07 (DJIA, Forex and others, ~a decade from 1995 per W-BB): BB rules do not beat
  buy-and-hold after costs; the contrarian version improves profitability. Balsara, Chen & Zheng 2007 (China,
  via W-BB): contrarian buy trades significant after 0.50% costs. W-BB: only ~88% (85-90%) of closes stay
  inside the bands, not ~95%.
- **Decay and crowding:** None found.
- **Cost-floor note:** The target is the middle band, so gross per completed trade is ~2 x sigma_20 of closes;
  the rule is sub-cost on any timeframe where that is under 13 bp plus the loss on trades that never revert.
- **Event rate (estimate):** 10-20 band closes a year per asset on daily bars.
- **Applies to / testable here:** All markets. Y.
- **Regime hypothesis:** Works when the 20-bar variance ratio is below 1; fails in trends (band walking).
- **Overlaps:** S-MR-04 (same z-score, continuous sizing), S-MR-05 (MAD z-score), S-MR-02, S-MR-08.

### S-MR-04 Price z-score vs moving average, linear scaling
- **Fidelity:** B (primary book recalled, not re-fetched; would be A if the chair verifies C13).
- **Sources:** C13 (recalled), MKM19 (abstract).
- **Rule (recalled):** First test the series for stationarity (ADF, Hurst, variance ratio). Estimate the
  half-life from OLS dy_t = lambda * y_{t-1} + mu; half-life = -ln(2)/lambda. Lookback L = round(half-life).
  z_t = (y_t - MA_L(y))/MSTD_L(y). Hold -z_t units, rebalanced every bar; no thresholds, no stop. Applied in the
  book to single price series and to spreads. Exact example series and results not re-fetched.
- **Primitive vs wrapper:** P1 (reversal of the deviation from a local mean). Wrapper: the stationarity gate,
  the half-life lookback, continuous sizing (the book calls the linear version impractical: unbounded size;
  recalled).
- **Claimed mechanism:** Statistical only; no counterparty named (recalled).
- **Published claim:** C13 figures not re-fetched, so none quoted. MKM19 (S&P 500 constituents 2000-2017):
  multi-asset moving-average reversion (OLMAR, PAMR, TCO) "may fail even in favorable market conditions",
  especially with costs; benchmark datasets flatter them.
- **Decay and crowding:** MKM19 is the only evidence read, and it is negative.
- **Cost-floor note:** Cost is paid on every change in z, not once per round trip: per-bar cost is about
  13 bp x |dz_t| / 2 per unit of position. Fast-moving z (short L) can consume the edge without any losing trade.
- **Event rate (estimate):** Continuous; independent excursions ~ (bars per year) / half-life.
- **Applies to / testable here:** All markets. Y.
- **Regime hypothesis:** Works only while the series is stationary over L; the gate is the strategy. Fails
  when a unit root or trend appears, because exposure grows against the trend.
- **Overlaps:** S-MR-03 (thresholded form), S-MR-12/-13 (z-score of a spread or residual), S-MR-08.

### S-MR-05 Commodity Channel Index (CCI)
- **Fidelity:** B. Lambert's 1980 Commodities article not read; two secondary sources describe it.
- **Sources:** SC-CCI (full), W-CCI (full).
- **Rule:** TP = (H + L + C)/3; CCI = (TP - SMA_20(TP)) / (0.015 x MD_20), MD = mean absolute deviation of TP.
  0.015 is set so ~70-80% of values fall within +/-100. Lambert's ORIGINAL rule (W-CCI, citing Schlossberg
  2006) is a breakout: buy when CCI rises above +100, close when it falls back below +100; sell below -100,
  close when back above -100. Later contrarian use (SC-CCI): +/-100 in ranges; +/-200 as a true extreme, entering
  only when CCI moves back inside +/-200. Default period 20 (SC-CCI).
- **Primitive vs wrapper:** P1, sign set by the wrapper: the original reads a +/-100 excursion as continuation,
  the later use as reversal. Wrapper: thresholds and exit lines.
- **Claimed mechanism:** None; SC-CCI says Lambert built it "to identify cyclical turns in commodities".
- **Published claim:** No figures found.
- **Decay and crowding:** None found.
- **Cost-floor note:** ~20-bar horizon; same arithmetic as S-MR-03 with MAD in place of sigma.
- **Event rate (estimate):** 5-15 +/-200 excursions a year per asset on daily bars.
- **Applies to / testable here:** All markets. Y.
- **Regime hypothesis:** The breakout reading should hold in trending states, the contrarian one in ranging
  states. The card is mainly a sign test of P1 at the 20-bar horizon.
- **Overlaps:** S-MR-03 (z-score with sigma), S-MR-02.

### S-MR-06 Internal bar strength (IBS)
- **Fidelity:** A. **Sources:** P13 (full), PJ23 (full).
- **Rule (P13):** IBS = (C - L)/(H - L) of the daily bar. Long at the close when IBS <= 0.2, short at the close
  when IBS >= 0.8; measured close to next close (exit not stated beyond that). Filter variant: Cutler RSI(3) < 10
  long, hold while RSI(3) <= 40, entering or holding only if IBS <= 0.5. Universe: 33 ETFs (mostly iShares
  country funds, SPY, QQQ, IWM), start dates 1993-2009, data to 2013-05-12. PJ23 "MinMax": each day, long the
  lowest-IBS and short the highest-IBS of 15 country ETFs, close to next close (2009-2019).
- **Primitive vs wrapper:** P1 primary (one-day reversal of the close's location in the day's range); P2
  secondary (stronger after high-range, high-vol days); P5 secondary (tied to the session close). Wrapper:
  thresholds, RSI(3) combination.
- **Claimed mechanism:** P13: possibly intraday overreaction to news or market moves, corrected next day; the
  source "difficult, if not impossible, to establish". The effect is largely absent in local-market ETFs
  (France, Austria, Germany, Spain, Switzerland, Taiwan, UK); P13 suggests stat-arb around US-listed foreign ETFs.
- **Published claim:** P13: next-day mean +0.350% for IBS 0-0.2 vs -0.126% for 0.8-1; simple strategy "over
  30%" a year before costs over 19 years (Table 5 average 29.38%). Strongest Mondays, weakest Fridays; stronger
  in bear markets and, for US ETFs, only on high-volume days. PJ23: MinMax Sharpe 2.91; open-to-open entry
  gives Sharpe near zero or negative.
- **Decay and crowding:** None measured after 2019. PJ23's open-to-open result says the edge lives in the
  closing print itself.
- **Cost-floor note:** P13's 35 bp gross next-day mean is ~2.7x a 13 bp round trip, but only if filled at the
  close that defines the signal (arithmetic on the source's figures).
- **Event rate (estimate):** Tens of signal days a year per ETF, clustered across ETFs on the same dates.
- **Applies to / testable here:** ETFs in the sources. Partial: Yahoo daily ETFs. Perps trade 24/7, so a UTC
  daily close is not a session close; a perp test is mechanical only, not a test of the mechanism.
- **Regime hypothesis:** Works where the close is followed by a closed or thin period (ETFs, especially
  foreign-market ETFs listed in the US) and in high-vol regimes; fails in continuous markets and off-close fills.
- **Overlaps:** S-MR-02 (IBS = 1-bar stochastic %K, per P13), S-MR-01, S-MR-14.

### S-MR-07 N-day low (Connors "Double 7s") and consecutive-down-day buys
- **Fidelity:** B (SQ-D7 secondary, full). Attribution to CA08 recalled; SQ-D7 names no book.
- **Sources:** SQ-D7 (full), CA08 (recalled, not re-fetched).
- **Rule:** Daily bars. Require close > SMA(200). Buy at the close when the close is at or below the lowest
  close of the last 7 bars (including today). Sell at the close when the close is at or above the highest close
  of the last 7 bars. No stop, no target, no time exit. Consecutive-down-day variants (buy after N lower closes)
  are recalled from CA08; N not re-fetched, so not specified.
- **Primitive vs wrapper:** P1 (reversal of a multi-day decline) inside a long-horizon P1 trend. Wrapper:
  SMA(200) gate, 7-day-high exit, no stop.
- **Claimed mechanism:** None offered.
- **Published claim:** None from the book was re-fetched. SQ-D7's own backtest assumes zero costs and is not
  quoted as evidence.
- **Decay and crowding:** None read.
- **Cost-floor note:** One round trip per trade, variable hold; gross per trade must clear 13 bp.
- **Event rate (estimate):** 5-15 entries a year per index.
- **Applies to / testable here:** US equities/indices in the sources. Y.
- **Regime hypothesis:** As S-MR-01: positive drift plus negative short-horizon autocorrelation; fails in
  crash sequences and momentum assets.
- **Overlaps:** S-MR-01 (same idea with RSI), S-MR-03.

### S-MR-08 Intraday VWAP reversion
- **Fidelity:** C. Not mechanizable as published: no source with a threshold or exit was found. W-VWAP
  documents VWAP as an execution benchmark and, citing StockCharts, as a TREND reference (long above VWAP,
  entries on crosses), not as a reversion level.
- **Sources:** W-VWAP (full). No primary source for the reversion rule.
- **Rule (folklore form):** Session-anchored VWAP from intraday bars with volume. Fade price when it is k
  session-sigma bands from VWAP; target VWAP. k, stop, anchor time and session gate: not specified.
- **Primitive vs wrapper:** P7 primary (VWAP distance), P1 secondary. Wrapper: band level, VWAP target, anchor.
- **Claimed mechanism:** None in the source. W-VWAP's execution-algorithm material (orders paced to volume)
  is not claimed by anyone to cause reversion.
- **Published claim:** None found.
- **Decay and crowding:** Not applicable.
- **Cost-floor note:** The target is VWAP itself, so the gross is capped by the distance at entry, which must
  exceed 13 bp plus losses on non-reverting days. A cumulative average lags more as the session ages, so any
  threshold must be in session-sigma units, not fixed bp.
- **Event rate (estimate):** At most one or two per session per asset; ~1 date-independent event per day.
- **Applies to / testable here:** Equity index futures and stocks by usage. Y on perp 1m klines (UTC anchor is
  arbitrary for a 24/7 market); partial on cached NQ.
- **Regime hypothesis:** Works on range days with no scheduled news; fails on trend days, where price stays
  on one side of VWAP all session.
- **Overlaps:** S-MR-03/-04 (same z-score with a volume-weighted, session-anchored mean).

### S-MR-09 Daily cross-sectional reversal as liquidity provision (Nagel)
- **Fidelity:** A. **Sources:** N12 (full), L90 (abstract). Lo & MacKinlay 1990 recalled, not re-fetched.
- **Rule (N12 eq. 9):** Each day, weight stock i by -(R_i,t-1 - R_m,t-1), R_m = equal-weighted market; scale
  to $1 long / $1 short; hold one day. Reported return averages five sub-strategies formed on lags t-1 to
  t-5. Lo-MacKinlay variant: w = -(1/N)(R_i - R_m). Universe: NYSE/AMEX/Nasdaq common stocks, price >= $1,
  1998-2010. Industry variant on 48 Fama-French industry portfolios.
- **Primitive vs wrapper:** P3 primary (relative return, negative sign); P1 secondary; P2 secondary (VIX sets
  the size of the premium). Wrapper: linear weights, five-lag averaging.
- **Claimed mechanism:** Market makers absorb public order imbalances and dislike inventory, so price impact
  is partly transitory; lagged returns proxy their inventory. Informed impact is permanent and does not reverse.
  When VIX rises, liquidity supply is withdrawn and the required return on providing it rises.
- **Published claim:** N12 (US 1998-2010): +0.30% a day on transaction prices (0.29% hedged), ~0.18% on quote
  midpoints; industry version ~0.02%. Lagged VIX coefficient 0.22 (daily adj. R2 0.07; up to 0.56 monthly).
  L90 (abstract): weekly reversals survive bid-ask and thin-trading corrections and "plausible" costs.
- **Decay and crowding:** N12 Fig. 1: ~1% a day in 1998 and 2000-01, below 0.2% by 2007, then up almost
  ten-fold by Q4 2008. The gap between transaction-price and midpoint returns shows bid-ask bounce is a large
  share of the raw number.
- **Cost-floor note:** Full daily turnover costs one 13 bp round trip per $ of position per day, the same
  order as the source's 18-30 bp gross (arithmetic, ignoring partial turnover).
- **Event rate (estimate):** One rebalance a day, all assets on the same date: ~252 (equities) or 365 (crypto)
  date-independent events a year.
- **Applies to / testable here:** US equities in the source. Y (perps, 1h-1d).
- **Regime hypothesis:** Pays when market vol is high and liquidity providers retreat; near zero in calm years.
  In perps, expect it mostly in low-volume names.
- **Overlaps:** S-XS-02 (weekly/monthly version, cross_sectional.md), S-MR-13, S-MR-15, S-MR-10.

### S-MR-10 Index-level daily reversal after indexing (MAC(5))
- **Fidelity:** A. **Sources:** BBD19 (full).
- **Rule:** MAC(5)_t = r_t(4r_t-1 + 3r_t-2 + 2r_t-3 + r_t-4)/(5 sigma^2), computed daily per index. The
  strategy trades against it: position in the index proportional to -(4r_t-1 + 3r_t-2 + 2r_t-3 + r_t-4), held
  for one day (the paper gives no holding period beyond the daily return). 20 indexes in 15 countries plus their
  futures and ETFs, start to 2016.
- **Primitive vs wrapper:** P1 primary (index serial dependence); P7 secondary (index-arbitrage flow).
  Wrapper: lag weights 4-3-2-1.
- **Claimed mechanism:** Index arbitrage: liquidity providers hedging index-product positions in the
  underlying spread non-fundamental price pressure into both markets, which reverses when it fades (citing
  Ben-David, Franzoni & Moussawi 2018). The initial shock's traders are not identified.
- **Published claim:** BBD19: after 1999-03-02, Sharpe 0.63 across indexes, 0.67 for the S&P 500, similar on
  futures and ETFs. Panel daily AR(1) 0.094 before 1999, -0.026 after; MAC(5) negative after 1999 for all 20
  indexes (13 significant). After costs "perhaps is not exploitable to many investors" (not quantified).
- **Decay and crowding:** The reverse of decay: index serial dependence flipped from momentum to reversal as
  indexing grew.
- **Cost-floor note:** With rho near -0.03 (source), a 1-sigma day predicts ~0.03 sigma next day. The trade
  clears 13 bp only on multi-sigma signals or high-sigma assets (arithmetic).
- **Event rate (estimate):** One decision a day per market: ~252 (equities) or 365 (crypto) a year.
- **Applies to / testable here:** Equity indexes in the source. Partial (Yahoo daily, cached NQ). Y as a crypto
  analog on BTC/ETH perps, where perp-spot basis arbitrage would play the index-arbitrage role (hypothesis).
- **Regime hypothesis:** Works when tracking-product arbitrage is a large share of trading; fails where
  indexing is small and in crash runs where daily momentum dominates.
- **Overlaps:** S-MR-01/-07 (single-index reversal with wrappers), S-MR-09, S-MR-06.

### S-MR-11 Distance pairs (Gatev, Goetzmann & Rouwenhorst)
- **Fidelity:** A. **Sources:** GGR (full WP), DF10 (abstract), QP-PT (secondary).
- **Rule:** Formation 12 months: build each stock's cumulative total-return index (dividends reinvested);
  pair each stock with the partner minimizing the sum of squared deviations; trade the top 5 or 20 pairs.
  Trading 6 months: open when the normalized prices diverge by more than 2 formation-period sigma (long the
  laggard, short the leader, equal dollars); close at the next crossing or at period end. One-day-wait variant
  opens and closes the day after the signal. CRSP stocks with no missing trade days; staggered monthly starts.
- **Primitive vs wrapper:** P1 on a spread (relative price reversal); P3 secondary. Wrapper: 2-sigma trigger,
  crossing exit, 6-month forced exit, no stop.
- **Claimed mechanism:** Law of one price for close substitutes; practitioner view of overreaction by
  individual investors (GGR, citing Tartaglia). DF10: a risky arbitrage limited by fundamental, noise-trader and
  synchronization risk.
- **Published claim:** GGR (US 1963-1997): six-month excess return of the top 20 is 6.01% same-day, 3.96% with
  the one-day wait; 8.02% a year (wait, geometric); implied ~83 bp per pair round trip. DF10 (US 1962-2009):
  top-20 monthly excess 0.86% (1962-88), 0.37% (1989-2002), 0.24% (2003-09); strong in 2000-02 and 2007-09.
- **Decay and crowding:** GGR's own Fig. 2 falls to near zero by the late 1990s. DF10: rising arbitrage risk
  explains up to 70% of the decline. F20 (1990-2020): base distance 0.11% a month vs market 0.47%.
- **Cost-floor note:** Two legs, so 26 bp per pair round trip. A converged trade earns ~2 sigma of the spread,
  which must exceed 26 bp plus the losses on non-converging pairs.
- **Event rate (estimate):** Top 20 x ~2.4 round trips per 6 months (GGR) is ~100 trades a year, but they
  open together in market-wide dislocations: tens of date-independent events.
- **Applies to / testable here:** US equities in the source. Y (perps, daily or hourly).
- **Regime hypothesis:** Works in bear and high-dispersion markets; fails on structural breaks (for coins:
  unlocks, hacks, delistings).
- **Overlaps:** S-MR-12 (same selection plus a test), S-MR-13, S-MR-16, S-MR-04.

### S-MR-12 Cointegration pairs (Engle-Granger)
- **Fidelity:** A. **Sources:** F20 (full), RLF16 (abstract and CXO summary), QP-PT (secondary).
- **Rule (F20 baseline, from GGR):** Formation 12 months, trading 6. Sort all pairs by distance (SSD of
  normalized log prices); test the closest for Engle-Granger cointegration (confidence 0.01/0.05/0.1 in the
  grid) until N pairs are found (grid 5/10/20/40). Spread = Engle-Granger residual, normalized by formation-period
  values. Open when |spread| > 2 (grid 0.5-3); close at the zero crossing or period end; one-period execution
  lag; no stop. F20 costs: one-way 35/30/26 bp by decade plus a 0.6% a year short fee. RLF16: top-20 cointegrated
  pairs by SSD, with position sizes from cointegration statistics.
- **Primitive vs wrapper:** P1 on a spread; P3 secondary. Wrapper: cointegration gate, 2-sigma trigger,
  zero-cross exit.
- **Claimed mechanism:** As S-MR-11. Cointegration makes a stronger statistical claim, not a new counterparty.
- **Published claim:** RLF16 (US 1962-2014): cointegration 85 bp a month before costs, 33 bp after (distance
  91/38, copula 43/5); all better in volatile periods, cointegration strongest in turbulent markets. F20 (US
  1990-2020): base cointegration 0.18% a month vs market 0.47%; adaptive executable version -0.11%; 2007-09
  +0.41% a month vs market -1.95%.
- **Decay and crowding:** RLF16: rolling Sharpe falling since ~1990 (CXO summary), fewer opportunities from 2009.
  Clegg (via QP-PT): cointegration does not persist from year to year.
- **Cost-floor note:** As S-MR-11: 26 bp per pair round trip.
- **Event rate (estimate):** As S-MR-11.
- **Applies to / testable here:** US equities in the sources. Y.
- **Regime hypothesis:** As S-MR-11. If formation-period cointegration does not persist, the gate adds
  nothing over distance.
- **Overlaps:** S-MR-11, S-MR-13, S-MR-16, S-MR-04.

### S-MR-13 Factor-residual OU stat-arb (Avellaneda & Lee)
- **Fidelity:** A. **Sources:** AL10 (both drafts, full).
- **Rule:** US stocks with market cap above $1bn. Daily: regress each stock's returns over 60 days on either its
  sector ETF or 15 PCA eigenportfolios (correlation matrix over 252 days; variants explain 45-75% of variance).
  Fit the cumulative residual X(t) as an OU process (AR(1) on 60 days); trade only if kappa > 252/30 (reversion
  within about half the window). s = (X - m)/sigma_eq, sigma_eq = sigma/sqrt(2 kappa). Open long s < -1.25, open
  short s > +1.25, close long s > -0.50, close short s < +0.75. All-or-nothing size, 2+2 leverage, factor-hedged.
  Thresholds chosen on 2000-2004 data. Costs: 5 bp a side. Variant: returns in "trading time" (volume-adjusted).
- **Primitive vs wrapper:** P3 primary (residual relative reversal); P1 secondary; P7 secondary (trading-time
  variant). Wrapper: kappa filter, s thresholds, hedge construction.
- **Claimed mechanism:** Overreaction (citing Lo & MacKinlay 1990). The August 2007 drawdown is read as a
  crowded unwind (Khandani & Lo 2007), presented as plausible, not tested. No counterparty identified.
- **Published claim:** AL10: PCA Sharpe 1.44 over 1997-2007, 0.9 over 2003-2007; ETF Sharpe 1.1 over
  1997-2007 (synthetic ETFs before 2002), 0.6 for 2003-2007 with actual ETFs, 1.51 with the volume adjustment
  (2003-2007). August 2007 drawdown ~5% (PCA) and ~10% (ETF).
- **Decay and crowding:** AL10 itself: "much stronger performances prior to 2003"; the ETF version degrades
  after 2002 too.
- **Cost-floor note:** Each trade captures ~0.5-0.75 sigma_eq of residual, and the factor hedge is a second leg.
  The source's 10 bp round trip is below our 13 bp per leg.
- **Event rate (estimate):** Entries every day across hundreds of names; ~252-365 date-independent events a
  year, correlated in deleveraging episodes.
- **Applies to / testable here:** US equities in the source. Y for the PCA variant on ~700 perps; N for sector
  ETFs (no crypto equivalent; use PCA).
- **Regime hypothesis:** Works when residual dispersion is high and liquidity is scarce; fails in crowded
  unwinds (Aug 2007) and when the factor model misses a common shock (e.g. sector narrative rotation in coins).
- **Overlaps:** S-MR-09 (market-only version), S-MR-11/-12 (two-asset version), S-MR-04 (s = z-score).

### S-MR-14 Overnight gap fade ("gaps get filled")
- **Fidelity:** C. Not mechanizable as published: gap types (common, breakaway, runaway, exhaustion) are
  assigned by judgement. LC19 supports overnight reversal, at abstract level only.
- **Sources:** W-GAP (full), LC19 (abstract).
- **Rule (folklore):** At the session open, if open differs from the prior close, short up-gaps and buy
  down-gaps; target the prior close (the fill). Minimum gap size, stop and time-out: not specified. W-GAP:
  speculators fade only when fill probability is high, and trade with the gap otherwise.
- **Primitive vs wrapper:** P1 primary (reversal of the overnight return during the session); P5 secondary
  (the open). Wrapper: gap threshold, fill target, gap-type classification.
- **Claimed mechanism:** LC19: after-hours extreme ETF returns are overreactions, with tax-motivated and noise
  trading contributing. W-GAP offers none.
- **Published claim:** LC19 (US equity ETFs, period not in the abstract): after-hours extreme returns reverse in
  the following period on average, while extreme moves in normal hours behave differently. No magnitudes in
  the abstract. W-GAP: common gaps "usually" fill; runaway gaps not for a long time. No figures.
- **Decay and crowding:** None found.
- **Cost-floor note:** The target is the gap itself, so gaps under 13 bp are sub-cost by construction.
- **Event rate (estimate):** One open per trading day per market, ~252 a year; only a fraction pass any size
  threshold.
- **Applies to / testable here:** Exchange-traded equities, ETFs and futures. Partial (cached NQ/FX/gold, Yahoo
  daily). Perps trade 24/7 with no session gap; the CME weekend gap needs CME data (N).
- **Regime hypothesis:** Works when the gap comes from thin after-hours trading without news; fails when it
  reflects scheduled news (earnings, macro), where the gap is the information.
- **Overlaps:** S-MR-06 (close location predicts next day), S-MR-10.

### S-MR-15 Crypto short-horizon reversal (daily cross-section, intraday time series)
- **Fidelity:** B (abstracts and summaries only). **Sources:** Z21, KPZ20, KW26 (abstracts); BD18 (secondary).
- **Rule:** Z21: each day, sort coins on the previous day's return; long the low-return portfolio, short the
  high-return portfolio (breakpoints and weights not in the abstract). KPZ20: same idea at daily, weekly and
  monthly rebalancing, 200 coins 2015-2019. KW26: per pair, bet against the sign of the previous 15-minute candle
  (183 Binance pairs, out-of-sample protocol). BD18: every 12 h, long low-past-return/low-volume coins, short
  high-past-return/low-volume coins (26 coins, 2017-01 to 2018-05).
- **Primitive vs wrapper:** P3 primary (daily cross-section) and P1 (15-minute time series); P7 secondary
  (liquidity and taker flow set the sign and size). Wrapper: sort breakpoints, volume conditioning.
- **Claimed mechanism:** Illiquidity and compensation for liquidity provision (Z21, KPZ20). KW26: reversal
  concentrates after moves driven by aggressive taker flow and grows with flow intensity; depth consumed
  does not matter.
- **Published claim:** Z21 (3,600+ coins): low last-day returns outperform high; the largest, most tradeable
  coins show daily MOMENTUM instead. KPZ20: significant at all three frequencies, robust to size, turnover and
  illiquidity, in both halves and in high and low implied vol. KW26: 90% of 183 Binance pairs show significant
  15-min reversal (vs 2.7% of 187 US stocks/ETFs), every coin-year since 2021; gross edge peaks ~1.3 bp per
  trade vs a 5 bp round trip. BD18: gross Sharpe up to 2.96 in BTC terms.
- **Decay and crowding:** KW26: persistent but sub-cost at 15 min. BD18 (per CXO): gains concentrated in the
  first months of a short sample; gross only.
- **Cost-floor note:** KW26's 1.3 bp gross is one tenth of a 13 bp round trip. The daily version is largest in
  illiquid coins, where real spreads exceed the 13 bp model.
- **Event rate (estimate):** Daily: 365 date-independent rebalances a year. 15-min: ~35,000 bars a year,
  heavily clustered across coins.
- **Applies to / testable here:** Crypto (spot and Binance pairs) in the sources. Y (perps 1m-1d, taker flow).
- **Regime hypothesis:** Works in the low-volume tail and after taker-driven bursts; fails for large caps
  (daily momentum) and at multi-week horizons, where crypto momentum dominates (S-XS-13).
- **Overlaps:** S-XS-13 and S-XS-02 (cross_sectional.md), S-MR-09, S-MR-16.

### S-MR-16 Crypto pairs (distance and cointegration)
- **Fidelity:** B (abstract only; thresholds and periods not in the abstract). **Sources:** FK20, CU19
  (abstracts).
- **Rule:** The distance and cointegration methods of S-MR-11/-12 (rules taken from the equity literature),
  applied to 26 liquid Binance coins at 5-minute, 1-hour and daily frequency. Formation and trading periods,
  entry and exit thresholds: not specified in the abstract.
- **Primitive vs wrapper:** P1 on a spread; P3 secondary. Wrapper: as S-MR-11/-12, plus bar frequency.
- **Claimed mechanism:** FK20 offers market inefficiency: simple mean reversion in intraday prices that is
  absent from daily data. No counterparty named.
- **Published claim:** FK20: underperforms classical benchmarks; sensitive to parameters, costs and
  execution windows. Daily distance -0.07% a month; 5-minute 11.61% a month. CU19 (Binance 2018): mostly
  unprofitable after costs; distance ~3% a month at baseline; cointegration a small loss in every case.
- **Decay and crowding:** Not studied; samples are 2018-2019 only.
- **Cost-floor note:** 26 bp per pair round trip. At 5 minutes, 2 sigma of the spread must exceed 26 bp, which
  is the binding constraint at that frequency.
- **Event rate (estimate):** Many trades a day at 5 minutes, clustered; date-independent count unclear.
- **Applies to / testable here:** Crypto spot (Binance) in the sources. Y (perps 1m-1d).
- **Regime hypothesis:** Works intraday when a flow shock hits one coin of a co-moving pair; fails on
  token-specific news.
- **Overlaps:** S-MR-11, S-MR-12, S-MR-15 (KW26 is the single-asset form of the intraday effect).

## Family notes

Underneath, the family contains one primitive: P1 reversal of a deviation from a local mean. It is measured
on three objects: one price (S-MR-01 to -08, -10, -14), a two-asset spread (-11, -12, -16) and a residual
against the market or factors (-09, -13, -15). RSI(2), Double 7s, %b, the z-score, CCI, IBS, stochastic and %R
are one location-in-range or z-score statistic in different wrappers: IBS is a 1-bar stochastic, %R a
mirrored %K, CCI a MAD z-score, the s-score a residual z-score. The conditioning states are P2
(VIX, range) and P7 (taker flow, volume). Not mechanizable: oscillator divergence and failure swings, gap
typology, VWAP fades. The sign is unsettled: Lambert's CCI was trend-following, and large coins show daily
momentum.
