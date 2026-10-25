# Catalogue family: chart patterns, price-level frameworks and discretionary methods

Scout compilation, 2026-10-10. Outcome-blind: no repo results, ledgers or caches were opened. Cards follow docs/CATALOGUE.md section 3. "Read" = I read the full text or page; "abstract only" = I read only an abstract or bibliographic record; "recalled, not re-fetched" = from memory, not verified this session. The shared web-search budget ran out partway through. Academic tests of point-and-figure, Gann, Wyckoff, ICT and "finfluencer" content were therefore **not searched for**, and their absence below does not mean none exist.

---

### S-PAT-01 Candlestick reversal patterns (three-day stars, soldiers/crows, inside/outside)
- **Fidelity.** A (Caginalp & Laurent give exact definitions; the Marshall-Young-Rose (MYR) single-line thresholds come from practitioner books).
- **Sources.** Caginalp & Laurent, "The predictive power of price patterns", *Applied Mathematical Finance* 5:181-205, 1998. https://ideas.repec.org/a/taf/apmtfi/v5y1998i3-4p181-205.html. Full PDF read (copy at c.mql5.com). Marshall, Young & Rose, "Candlestick technical trading strategies: can they create value for investors?", *J. Banking & Finance* 30(8):2303-2323, 2006. https://ideas.repec.org/a/eee/jbfina/v30y2006i8p2303-2323.html. Bibliographic record only. Their manuscript "Market Timing with Candlestick Technical Analysis" (undated) was read in full; CXO Advisory's summary was also read. Nison, *Japanese Candlestick Charting Techniques*, 1991: recalled, not re-fetched.
- **Rule (C&L).** Trend: 3-day moving average of closes, with Mavg(t-6) > ... > Mavg(t) and at most one violation (downtrend; mirrored for uptrend). Bullish after a downtrend: Three White Soldiers, Three Inside Up, Three Outside Up, Morning Star. Bearish after an uptrend: the mirrors. Long-body size conditions are deliberately dropped. Buy at the close of the pattern's third day, then sell 1/3 at each of the next three closes (about a 2-day average hold). Shorts are symmetric. Daily OHLC, any universe.
- **Rule (MYR).** 28 signals: 14 single lines and 14 reversals (hammer, engulfing, harami, piercing, tweezer and others). Prior trend from a 10-day EMA. The hammer's lower shadow must be at least 2x the body (Nison). Enter at the close of the day after the signal and hold 10 days.
- **Primitive vs wrapper.** Primary P8 (pattern); secondary P1 (reversal of a 6-day trend). The trend prerequisite, the 1/3-a-day exit and the 10-day hold are wrapper.
- **Claimed mechanism.** Practitioners say the pattern shows that sentiment has shifted. C&L offer under-reaction or over-reaction psychology. Neither names who is on the other side.
- **Published claim.** C&L, S&P 500 stocks, Jan 1992 to Jun 1996: bullish success 71.22% vs a 45.05% baseline (n=4,688); bearish 67.33% vs 52.78% (n=8,391). Mean buy-side return 0.9% per ~2-day trade (0.56-0.76% after their cost estimate). Correcting for cross-stock correlation cuts Z from about 36 to about 6.6. MYR, DJIA stocks 1992-2002, bootstrap with random-walk, AR(1), GARCH-M and EGARCH nulls: no signal significant; "not generally profitable when applied to large U.S. stocks".
- **Decay and crowding.** The two samples overlap (1992-96) yet disagree. The cause is the benchmark (unconditional mean vs bootstrap) and the definitions, not decay. Fock, Klein & Zwergel (2005) on intraday futures, reporting no value: recalled, not re-fetched.
- **Cost-floor note.** A 2-day hold of daily bars. C&L's 0.9% is about 7x the 13 bp round trip if it holds. An intraday version shrinks the move toward the cost.
- **Event rate (estimate).** About 5-20 per coin-year on 1d; 20-60 date-independent dates a year market-wide.
- **Applies to / testable here.** US equities and closed-end funds. Y (1d klines).
- **Regime hypothesis.** Pays only where short-horizon reversal (negative P1) exists, e.g. after capitulation or high-volatility selloffs. Fails in persistent trends.
- **Overlaps.** S-PAT-02, S-PAT-10 (spring bar), S-PAT-14 (displacement candle).

### S-PAT-02 Kernel-identified chart patterns: head-and-shoulders, double tops, triangles, rectangles
- **Fidelity.** A.
- **Sources.** Lo, Mamaysky & Wang (LMW), "Foundations of Technical Analysis", *J. Finance* 55(4), 2000; NBER w7613. https://www.nber.org/papers/w7613. Full working paper read. Savin, Weller & Zvingelis, "The Predictive Power of 'Head-and-Shoulders' Price Patterns in the U.S. Stock Market", *J. Fin. Econometrics* 5(2):243-265, 2007. https://ideas.repec.org/a/oup/jfinec/v5yi2p243-265.html. Full 2006 revision read. Osler & Chang, "Head and Shoulders: Not Just a Flaky Pattern", FRBNY Staff Report 4, 1995. https://econpapers.repec.org/RePEc:fip:fednsr:4. Abstract only (the FRASER PDF is an image scan).
- **Rule (LMW).** Rolling 38-day windows (l=35, d=3). Nadaraya-Watson Gaussian kernel with bandwidth 0.3 x the cross-validated h*. Extrema of the smoothed curve are mapped to price extrema E1..E5. Head-and-shoulders (HS): E1 max, E3 > E1 and E3 > E5; E1/E5 within 1.5% of their mean, and likewise E2/E4. Rectangles use 0.75%. Double tops: within 1.5% and at least 22 trading days apart. Ten patterns in all. The pattern is detected 3 days after completion and the 1-day normalized return is read from there.
- **Rule (SWZ trading).** 63-day window, bandwidth 1-2.5 x CV, 1.5% or 4% tolerance. Requires a neckline break before E6. Short from 3 days after E6 and hold 20, 40 or 60 days.
- **Primitive vs wrapper.** Primary P8; secondary P1. Tolerances, the neckline break and the hold are wrapper.
- **Claimed mechanism.** LMW claim information only, not profit. SWZ trace the gain to negative market beta and to shorting momentum losers. Osler and Chang's abstract offers none.
- **Published claim.** LMW, CRSP 1962-1996: conditional return distributions differ from unconditional ones for 7 of 10 patterns on NYSE/AMEX and 10 of 10 on Nasdaq (decile test); Kolmogorov-Smirnov significant for 5 of 10 and 10 of 10. SWZ, S&P 500 and Russell 2000 1990-99: not profitable stand-alone. Fama-French-adjusted excess return is 5-7% a year, partly absorbed by a momentum factor.
- **Decay and crowding.** None measured beyond SWZ's 1990s sample.
- **Cost-floor note.** LMW test the shape of the distribution, not the mean, so there is no size to compare with the cost. SWZ's 0.4-0.55% a month over a 20-60 day hold is several times 13 bp.
- **Event rate (estimate).** SWZ found 6,406 HS in the Russell 2000 over 10 years, about 0.3 per stock-year. Crypto: 20-50 date-independent a year.
- **Applies to / testable here.** US stocks and FX. Y (1d klines).
- **Regime hypothesis.** Works where cross-sectional losers keep losing (P3 momentum), not as a stand-alone timing rule.
- **Overlaps.** S-PAT-01, S-PAT-07, S-PAT-08.

### S-PAT-03 Published support/resistance levels (intraday bounce)
- **Fidelity.** B. The test is exact, but its input (banks' daily levels) is proprietary and not reproducible.
- **Sources.** Osler, "Support for Resistance: Technical Analysis and Intraday Exchange Rates", FRBNY *Economic Policy Review* 6(2), 2000. https://www.newyorkfed.org/medialibrary/media/research/epr/00v06n2/0007osle.pdf. Full paper read. Brock, Lakonishok & LeBaron (1992), the trading-range-break rule: recalled, not re-fetched.
- **Rule.** Levels published each morning by 6 firms for DEM, JPY and GBP vs USD (Jan 1996 to Mar 1998). A hit is the bid (for support) or ask (for resistance) within 0.01% of the level; 0.00% and 0.02% were also tested. Data are Reuters 1-minute quotes, 9:00-16:00 New York. A bounce means that 15 minutes later (30 also tested) the rate is still on the near side of the level. Control: 10,000 sets of 20 random support and 20 random resistance levels per day.
- **Primitive vs wrapper.** Primary P8; secondary P7 (resting-order clustering). The tolerance and horizon are wrapper.
- **Claimed mechanism.** Clustered take-profit and limit orders at the levels, plus self-fulfilment. About 96% of levels end in 0 or 5, so part of the effect is round numbers and prior extremes (S-PAT-04).
- **Published claim.** Bounce frequency 60.8% for published levels vs 56.2% for artificial ones. Every one of 16 firm-currency pairs was above artificial, significant at 5% in all but three. Five days later published levels still beat artificial ones (9 of 16 significant). Firms' "strength" ratings carried no information.
- **Decay and crowding.** Not measured after 1998.
- **Cost-floor note.** The test scores direction over 15 minutes, not size. A tradeable bounce must travel more than 13 bp in that time, and the source shows no magnitude.
- **Event rate (estimate).** Hits on most days, so at most about 250-365 date-independent days a year per market.
- **Applies to / testable here.** FX. N for the published levels. Y for proxies: round numbers and prior local extremes.
- **Regime hypothesis.** Bounces in ranging, liquidity-provider-dominated sessions. Breaks on news and trend days.
- **Overlaps.** S-PAT-04, S-PAT-05, S-PAT-12, S-PAT-14.

### S-PAT-04 Round-number levels: take-profit reversals and stop-loss cascades
- **Fidelity.** A.
- **Sources.** Osler, "Currency Orders and Exchange Rate Dynamics: An Explanation for the Predictive Success of Technical Analysis", *J. Finance* 58(5), 2003; FRBNY Staff Report 125. https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr125.pdf. Full staff report read. Osler, "Stop-loss orders and price cascades in currency markets", *JIMF*, 2005: recalled, not re-fetched (the conference .doc was unreadable).
- **Rule (two predictions).** (a) Reversal: price reaching a round number (quote ending in 00 or 50) bounces more often than at an arbitrary number. (b) Continuation: after crossing a round number, price moves further than after crossing an arbitrary number. Horizon: 1-2 periods in the simulation, 15-30 minutes in the empirical comparison. Not specified: which digit position counts as "round" for a crypto price.
- **Primitive vs wrapper.** Primary P8; secondary P7 (order-book clustering) and P1 (continuation after a cross). Bounce vs break is the only "wrapper".
- **Claimed mechanism.** Taken from a dealing bank's conditional-order book: 9,667 orders in USD/JPY, EUR/USD and GBP/USD, Sep 1999 to Apr 2000. 9.3% of take-profit orders sit at 00 vs 4.4% of stop-losses, so take-profits make round numbers partially reflecting barriers. Stop-loss buys cluster just above round numbers and stop-loss sells just below, so crossings set off cascades. The other side is customers who place orders at convenient numbers. The parts read do not argue why this is not arbitraged.
- **Published claim.** Simulated bounce frequency was higher at round numbers in 20 of 20 cases (average gap 3.47 pp); the actual-rate gap was 4.6 pp. Moves after a failed bounce were larger at round numbers in 20 of 20 cases; the text and table disagree on magnitudes.
- **Decay and crowding.** Not measured.
- **Cost-floor note.** Simulated moves are in model points. Nothing in the source shows a move above 13 bp over the horizon.
- **Event rate (estimate).** Several round-number touches per coin-day; about 365 date-independent days a year.
- **Applies to / testable here.** FX. Y for price behaviour (1m klines). N for the order book itself.
- **Regime hypothesis.** Bounce dominates in quiet, take-profit-rich ranges. Cascade dominates in high-volatility trends where stops sit beyond the level.
- **Overlaps.** S-PAT-03, S-PAT-10 (spring), S-PAT-14 (liquidity sweep), S-PAT-15. This is the only card in the family with primary order data behind its mechanism.

### S-PAT-05 Floor-trader pivot points
- **Fidelity.** B. The formula comes from a software reference; the reaction rule is folklore, tested only in a master's thesis.
- **Sources.** Linnsoft, "Pivot Point" indicator reference. https://linnsoft.com/techind/pivot-point. Full page read; it gives no origin and no evidence. Johnsson & Frykmer, "Pivot Point Trading in the Foreign Exchange Market: A Test for Market Efficiency", Lund University MSc thesis, 2019. https://www.lunduniversity.lu.se/lup/publication/8979805. Abstract only.
- **Rule.** From the prior session's H, L, C: P = (H+L+C)/3; R1 = 2P-L; S1 = 2P-H; R2 = P+(H-L); S2 = P-(H-L); R3 = 2P+(H-2L); S3 = 2P-(2H-L). Folklore use: fade the first touch of R1/S1 toward P, or treat a break as continuation toward R2/S2. Not specified: the session boundary for 24/7 markets, the touch tolerance, the stop and the horizon.
- **Primitive vs wrapper.** Primary P8; secondary P2. R1-P = P-L, so the levels are yesterday's range re-centred, and a touch is a volatility statement. Fade vs break, stop and target are wrapper.
- **Claimed mechanism.** Self-fulfilment: widely watched levels. No other side is named.
- **Published claim.** The thesis (3 FX pairs; pairs and period not on the abstract page) finds "no support for the hypothesis that pivot points reveal useful information" in the traditional form. Trading them inversely was profitable for two pairs.
- **Decay and crowding.** No evidence.
- **Cost-floor note.** An R1-to-P fade earns at most P-L, i.e. part of yesterday's range. That clears 13 bp easily on a 100+ bp range day but not on a quiet one.
- **Event rate (estimate).** One level set per day; at most about 365 date-independent days a year, highly correlated across coins.
- **Applies to / testable here.** FX, futures and equities by tradition. Y (1m-1d klines; the UTC-day session must be fixed first).
- **Regime hypothesis.** The fade works when today's range is below yesterday's; the break works on range-expansion days.
- **Overlaps.** S-PAT-03, S-PAT-12, S-PAT-06.

### S-PAT-06 Fibonacci retracements
- **Fidelity.** B. One paper gives a mechanical rule but leaves the swing choice under-specified. The levels themselves are folklore.
- **Sources.** Gurrib, Nourani & Bhaskaran, "Energy crypto currencies and leading U.S. energy stock prices: are Fibonacci retracements profitable?", *Financial Innovation* 8:8, 2022. https://link.springer.com/article/10.1186/s40854-021-00311-8. Full page read. "Automatic identification and evaluation of Fibonacci retracements: Empirical evidence from three equity markets", *Expert Systems with Applications*, 2021, doi 10.1016/j.eswa.2021.115893. Abstract only; authors not shown on the indexing page. Forexop, "Fibonacci Retracement: A Myth or Reality?" https://forexop.com/strategy/fibonacci-fact-or-fiction/. Practitioner study, read.
- **Rule (Gurrib et al.).** Trend = sign of the OLS slope of the last 50 daily closes. Swing high and low = the highest and lowest price "within a specific trending period" (length not specified). Levels at 23.6, 38.2, 50, 61.8 and 78.6% of the swing. Uptrend: go long when price crosses above the 23.6% level; exit when it crosses below 61.8%. Downtrend: mirrored. Daily closes.
- **Primitive vs wrapper.** Primary P8; secondary P1 (pullback-in-trend continuation). The trend filter and the 61.8% exit are wrapper.
- **Claimed mechanism.** "Natural" ratios and self-fulfilment. No other side is named.
- **Published claim.** Gurrib et al., top-10 S&P 1500 Energy stocks, Nov 2017 to Jan 2020: positive on 6 of 10 (4% to 177%), with the highest Sharpe 0.139 ("relatively low"). Energy tokens traded too rarely to judge. ESWA 2021: bounces are more likely in Fibonacci zones, but price behaviour there does not differ statistically from non-Fibonacci zones. Forexop, 9 FX pairs on 1m data 2003-2016, 40,243 corrections: log-normal correction sizes with no peaks at Fibonacci ratios (no formal test).
- **Decay and crowding.** n/a.
- **Cost-floor note.** Daily swings run from a few % to tens of %, so the cost does not bind. Intraday swings of 20-50 bp would be at the floor.
- **Event rate (estimate).** One entry per qualifying swing: about 5-15 per coin-year on 1d.
- **Applies to / testable here.** Equities, crypto, FX. Y once a swing rule is fixed (the source leaves it open).
- **Regime hypothesis.** Works only when trend persistence (P1) at the swing horizon is positive. The ESWA result predicts that any retracement zone works as well as a Fibonacci one.
- **Overlaps.** S-PAT-07, S-PAT-08, S-PAT-11 (50% level), S-PAT-14 (optimal trade entry (OTE) zone).

### S-PAT-07 Harmonic patterns (Gartley, Bat, Butterfly, Crab)
- **Fidelity.** B. One student implementation gives exact ratios; the canonical sources were not re-fetched.
- **Sources.** Mo Ka Lok, "Analysis of Trading with Harmonic Patterns in US Stock, Forex, and Crypto Market", independent-study report supervised by D. Rossiter, 2021. https://cse.hkust.edu.hk/~rossiter/independent_studies_projects/trading_harmonic_patterns/trading_harmonic_patterns.pdf. Full report read. Gartley, *Profits in the Stock Market*, 1935, and Carney, *Harmonic Trading*, 2010: both recalled, not re-fetched.
- **Rule (as implemented).** ZigZag swings X-A-B-C-D, with the deviation parameter tested at 0.15-2%. Each pattern is matched on the ratios (AB/XA, BC/AB, CD/BC) within a tolerance T of 0.05-0.15. Gartley: (0.618, 0.382, 1.13), (0.618, 0.382, 1.272), (0.618, 0.886, 1.618). Butterfly: (0.786, 0.382, 1.618), (0.786, 0.886, 2.618). Bat: ({0.382, 0.5}, {0.382, 0.886}, {1.618, 2.618}). Crab: (0.382, 0.382, 2.618), (0.618, 0.886, 3.618). Enter at D. Stop 1 ATR beyond X. Target the 0.618 retracement of AD. Time stop of 1000 bars. Hourly data. Carney's templates instead fix D as a retracement of XA (recalled), so the two give different builds unless one template is chosen.
- **Primitive vs wrapper.** Primary P8; secondary P1 (reversal at D). Stop, target and time stop are wrapper.
- **Claimed mechanism.** Natural ratios. No other side is named.
- **Published claim.** SPY, EUR/USD and BTC/USD, hourly, 2017-2021, no costs. Gartley on SPY: 64 trades, 70.31% hit rate, CAGR -1.57% vs buy-and-hold 16.29%. Bat on BTC: 103 trades, 75.73% hit rate, CAGR 12.25% vs buy-and-hold 77.71%. The author concludes "traders should not use harmonic patterns as their trading strategy". A high hit rate with a low CAGR is a target-smaller-than-stop wrapper signature.
- **Decay and crowding.** n/a.
- **Cost-floor note.** With a 0.25% ZigZag deviation, the smallest AD leg is about 25 bp, so the smallest target is about 0.618 x 25 ≈ 15 bp, roughly the 13 bp round trip.
- **Event rate (estimate).** About 25-50 per pattern per asset-year on 1h, from the report's trade counts.
- **Applies to / testable here.** Equities, FX, crypto. Y.
- **Regime hypothesis.** Reversal at D needs short-horizon mean reversion (range regimes). Fails in trends.
- **Overlaps.** S-PAT-06, S-PAT-02, S-PAT-08.

### S-PAT-08 Elliott wave
- **Fidelity.** C. Not mechanizable.
- **Sources.** Frost & Prechter, *Elliott Wave Principle*, 1978, and Elliott, *The Wave Principle*, 1938: both recalled, not re-fetched. CXO Advisory's grading of Robert Prechter's forecasts. https://www.cxoadvisory.com/individual-gurus/robert-prechter/. Full page read. Zhalgasbek, "Analysis of Elliott Wave Theory on Time-Series Data from Forex", Nazarbayev University capstone, 2023. https://nur.nu.edu.kz/items/ce5e8705-2615-4ffe-81a0-3b4aaf7189bb. Abstract only.
- **Rule.** A 5-wave impulse with the trend, then a 3-wave (A-B-C) correction, nested fractally. Three hard rules (recalled): wave 2 never retraces more than 100% of wave 1; wave 3 is never the shortest of waves 1, 3 and 5; wave 4 does not enter wave 1's price territory. Typical use: enter in the trend direction once wave 2 or wave 4 is judged complete.
- **What is unspecified.** The swing scale ("degree"), how to choose among several valid counts, and when a wave is complete. Counts are revised after the fact, so no fixed rule exists.
- **Primitive vs wrapper.** Primary P8 (path template); secondary P1 (wave 3 = continuation).
- **Claimed mechanism.** Crowd mood alternates between optimism and pessimism in a fractal rhythm. No other side and no limit to arbitrage are given.
- **Published claim.** The practitioner sources give no systematic evidence. CXO graded 24 Prechter forecasts (2002-2012): 21% accurate vs a guru average of 47% (CXO warns the sample is small). The thesis found no statistically significant predictive power on daily FX.
- **Decay and crowding.** n/a.
- **Cost-floor note.** Multi-day to multi-month waves, so the cost does not bind. The problem is the definition.
- **Event rate (estimate).** Undefined until a degree is fixed.
- **Applies to / testable here.** All markets. N as published. A ZigZag plus the three-rule filter would be our own invention.
- **Regime hypothesis.** The source claims it is universal, which leaves nothing to test.
- **Overlaps.** S-PAT-06, S-PAT-07, S-PAT-09, S-PAT-11.

### S-PAT-09 Dow theory (Hamilton/Rhea)
- **Fidelity.** C. The tenets are published but the swing definitions are not, so it is not mechanizable as published.
- **Sources.** Brown, Goetzmann & Kumar (BGK), "The Dow Theory: William Peter Hamilton's Track Record Reconsidered", *J. Finance* 53(4), 1998; Yale working paper. https://ideas.repec.org/p/ysm/somwrk/ysm30.html. Abstract only, plus CXO's summary (read): https://www.cxoadvisory.com/technical-trading/classic-research-dow-theory-long-dead/. Rhea, *The Dow Theory*, 1932, and Cowles, "Can Stock Market Forecasters Forecast?", *Econometrica*, 1934: recalled, not re-fetched.
- **Rule (recalled tenets).** The primary trend turns bullish when both the Industrials and the Rails (now Transports) close above their prior secondary-reaction highs, and bearish when both break their prior reaction lows. Secondary reactions typically retrace 1/3 to 2/3 of the primary move. Be long in a primary bull trend and out or short in a bear. Daily index closes.
- **What is unspecified.** The size and duration that make a "secondary reaction", how long a non-confirmation may last, and "line" formations. BGK replicated Hamilton's calls with a neural net whose weights are not public.
- **Primitive vs wrapper.** Primary P1 (time-series trend); secondary P8 (break of the prior reaction high). Cross-index confirmation is a candidate P9 element.
- **Claimed mechanism.** Primary trends reflect the business cycle. Confirmation by the transport index shows that real goods are flowing. No other side is named.
- **Published claim.** 255 Hamilton editorials in the WSJ, 1902-1929: right on short-term direction about 60% of the time, more often in bear markets. Positive alphas and "high Sharpe ratios" (no numbers on the pages read). After 1929, "trading frictions preclude large excess returns, especially since the 1970s".
- **Decay and crowding.** CXO's summary says the excess return shrank after 1929 and especially after the 1970s.
- **Cost-floor note.** Holds of weeks to months and few switches, so 13 bp is negligible.
- **Event rate (estimate).** About 9 editorial calls a year; fewer regime switches.
- **Applies to / testable here.** US equity indices. Partial (Yahoo daily DJIA/DJTA). A crypto two-index analogue would be our own invention.
- **Regime hypothesis.** Works in long trending markets, especially bears. Whipsaws in ranges.
- **Overlaps.** S-PAT-13, S-PAT-03 (range break), the trend-following family.

### S-PAT-10 Wyckoff accumulation and the spring
- **Fidelity.** C. Not mechanizable: the source gives no numeric thresholds.
- **Sources.** Pruden & von Lichtenstein, "Wyckoff Schematics: Visual templates for market timing decisions", *Market Technician* 55, 2006. https://www.prorealcode.com/wp-content/uploads/2019/11/WyckoffSchematics-VisualTemplatesForMarketTimingDecisions.pdf. Full article read. LuxAlgo Library, "Wyckoff method". https://www.luxalgo.com/library/concept/wyckoff-method.md. Read. Wyckoff's 1930s course: recalled, not re-fetched.
- **Rule.** After a prolonged decline, a range forms between the selling climax (SC) low and the automatic rally (AR) high (Phases A-B). The spring (Phase C) breaks below range support and quickly reverses back inside. Light volume on the break is bullish; heavy volume means renewed decline. Enter long on a low-volume test of the spring, or on the last point of support (LPS) or back-up (BU) after a sign of strength (SOS). Stop below the spring low. The target is a point-and-figure count of the range ("cause and effect").
- **What is unspecified.** Range length, depth of the break, the number of bars that counts as "quickly", and any volume or spread multiple. The article "gives no numeric rules".
- **Primitive vs wrapper.** Primary P8 (failed break of a range low); secondary P7 (volume conditions) and P6 (trapped breakout shorts). The test entry, LPS and P&F target are wrapper.
- **Claimed mechanism.** A "composite operator" (large informed buyer) accumulates from weak holders and shakes out stops below support to get liquidity. Weak holders and breakout shorts are on the other side. Persistence is not argued.
- **Published claim.** None. One Nokia case study. LuxAlgo states there is little rigorous public evidence that the schematics predict anything.
- **Decay and crowding.** n/a.
- **Cost-floor note.** Daily-to-weekly holds with a target set by range height, far above 13 bp unless the range is tiny.
- **Event rate (estimate).** A full schematic appears a few times per coin-year on 1d. A bare "failed N-day-low break" fires far more often.
- **Applies to / testable here.** Equities originally. Partial: price and volume are available, but every threshold would be our own.
- **Regime hypothesis.** Works after high-volume capitulation in mean-reverting regimes. Fails when the break extends (trend-down regimes).
- **Overlaps.** S-PAT-04, S-PAT-14 (liquidity sweep), S-PAT-15 (Judas swing), S-PAT-01.

### S-PAT-11 Gann angles, Square of Nine and time cycles
- **Fidelity.** C. Not mechanizable.
- **Sources.** Wikipedia, "William Delbert Gann". https://www.wikipedia.org/wiki/W._D._Gann. Read; the article carries a maintenance banner. Gann, *Truth of the Stock Tape*, 1923, and *How to Make Profits in Commodities*, 1942: recalled, not re-fetched.
- **Rule.** Angles: lines from a major high or low at fixed price-per-time slopes (1x1, 2x1, 1x2 and so on), acting as support and resistance. Square of Nine: levels found by rotating around the square root of a pivot price. Time cycles: anniversary and "natural" dates, which Mikula (per Wikipedia) traced to astrological events.
- **What is unspecified.** The price-per-bar scale (a 1x1 angle changes with chart units), which pivot anchors the analysis, the rotation step, and which dates count. The writing is "esoteric and indirect".
- **Primitive vs wrapper.** Primary P8; secondary P5 (calendar cycles).
- **Claimed mechanism.** Geometry, astronomy and natural law. No other side is named.
- **Published claim.** None verifiable. The claimed $50M fortune "is lacking" evidence. His son reportedly said Gann could not support his family by trading, and the estate was about $100,000 (Elder, via Wikipedia).
- **Decay and crowding.** n/a.
- **Cost-floor note.** n/a until the rule is defined.
- **Event rate (estimate).** Undefined.
- **Applies to / testable here.** Commodities and stocks. N: not mechanizable, and the angles are not scale-invariant.
- **Regime hypothesis.** None stated by the source.
- **Overlaps.** S-PAT-06 (Gann's 50% level), S-PAT-08.

### S-PAT-12 Market Profile value-area "80% rule"
- **Fidelity.** B. A secondary source states the rule. The "80%" figure has no published test.
- **Sources.** NexusFi wiki, "80 Percent Rule". https://nexusfi.com/a/concepts/80-percent-rule. Read. It attributes the rule to Dalton Capital's *The Profile Reports* (1987-91). Dalton, Jones & Dalton, *Mind Over Markets*, 1990, and Steidlmayer & Koy, *Markets and Market Logic*, 1986: recalled, not re-fetched.
- **Rule.** Build the prior regular session's profile in 30-minute time-price opportunity (TPO) brackets, or by volume. The value area (VA) holds about 70% of TPOs (or volume), bounded by the value-area high (VAH) and low (VAL). If today opens outside the prior VA, then re-enters and holds inside for two consecutive 30-minute periods, trade toward the opposite VA edge, which is the target. Not specified: the stop, whether "inside" means the close or the whole bracket, the VA expansion algorithm, and the session definition for 24/7 markets.
- **Primitive vs wrapper.** Primary P7 (volume/TPO profile); secondary P8 (level reaction) and P5 (session open, 30-minute gate). The two-bracket confirmation is wrapper.
- **Claimed mechanism.** Auction theory: price rejected outside value rotates back to fair value. Initiative traders who accepted the out-of-value open are trapped. No limit to arbitrage is given.
- **Published claim.** "80% chance" (Profile Reports; no test shown). A forum test cited by the wiki (ES regular hours, about 1,000 days, 2012): 20 of 23 (87%) in one strict case, but the target was usually hit during the second bracket, before entry was possible. The other side was 6 of 12 (50%). The wiki concludes the 80% does not hold under strict criteria.
- **Decay and crowding.** n/a.
- **Cost-floor note.** The target is the VA width, about 70% of the prior profile's range, far above 13 bp on any normal day.
- **Event rate (estimate).** About 10-30 qualifying days a year per market (the forum counted 53 + 67 over ~1,000 days before filters).
- **Applies to / testable here.** Index futures. Partial: cached NQ intraday for the original session. For crypto the 1m klines suffice but the session must be invented.
- **Regime hypothesis.** Rotational (balance) days. Fails on trend and news days.
- **Overlaps.** S-PAT-05, S-PAT-03, S-PAT-15.

### S-PAT-13 Point-and-figure and Renko box/brick breakouts
- **Fidelity.** B. Construction comes from secondary sources. Point-and-figure (P&F) signals are defined; Renko signals are not.
- **Sources.** Anderson & Faff, "Point and Figure charting: A computational methodology and trading rule performance in the S&P 500 futures market", *Int. Rev. Financial Analysis* 17(1):198-217, 2008. https://ideas.repec.org/a/eee/finana/v17y2008i1p198-217.html. Bibliographic record only; no abstract, results not read. LuxAlgo Library, "Point and figure" and "Renko". https://www.luxalgo.com/library/concept/point-and-figure/ and https://www.luxalgo.com/library/concept/renko/. Both read. Dorsey, *Point and Figure Charting*, 1995, and Nison, *Beyond Candlesticks*, 1994: recalled, not re-fetched.
- **Rule (P&F).** Box size b (fixed, %, or volatility-scaled; no default given), classic 3-box reversal. An X column extends while price rises; a new O column starts only after a 3b decline from the column high. Double-top buy: an X column rises one box above the prior X column's high. Sell is mirrored. Objective: vertical count = column length x b x 3.
- **Rule (Renko).** Brick B (fixed, %, or ATR(14)). An up brick prints when the close ≥ top + B; a reversal needs 2B. Entry and exit rules: not specified. A colour change is described as a trailing exit or trend filter.
- **Primitive vs wrapper.** Primary P1 (a time-free breakout trend filter); secondary P8. Box size and reversal count are wrapper.
- **Claimed mechanism.** Filtering noise reveals supply and demand. No other side is named.
- **Published claim.** None read. The LuxAlgo pages cite no studies.
- **Decay and crowding.** Unknown.
- **Cost-floor note.** A whipsaw costs about 3b (P&F) or 2B (Renko) plus 13 bp. With b = 0.1% the cost is a third of the box loss; with b ≥ 1% it is small.
- **Event rate (estimate).** Set by b. Weekly-scale signals with a 1% box on an active coin.
- **Applies to / testable here.** Futures, equities. Y (1m-1d klines).
- **Regime hypothesis.** Trending regimes (positive P1 at the box scale). Bleeds in ranges.
- **Overlaps.** S-PAT-09, S-PAT-03 (Brock-Lakonishok-LeBaron range break), the trend family, S-PAT-10 (P&F count).

### S-PAT-14 ICT / smart-money price structure: fair value gap, order block, liquidity sweep
- **Fidelity.** B for the fair value gap (FVG) retrace rule, which a secondary source codifies. The order-block "displacement" and the higher-timeframe "draw on liquidity" are unspecified.
- **Sources.** Michael J. Huddleston, "The Inner Circle Trader" video and mentorship material: recalled, not re-fetched; no written primary rulebook was found. LuxAlgo Library, "Fair value gap" and "Order block". https://www.luxalgo.com/library/concept/fair-value-gap/ and https://www.luxalgo.com/library/concept/order-block/. Both read; neither cites evidence.
- **Rule (FVG).** Bullish FVG at bar t if low[t] > high[t-2], with a "wide-range" middle bar (threshold not specified). The zone is [high[t-2], low[t]]. Go long on the first return into the zone, commonly at its midpoint ("consequent encroachment"). Invalidate on a close below high[t-2]. Target: the "opposing liquidity" (not specified). Bearish mirrored. Any timeframe.
- **Rule (order block, sweep).** Order block: the last opposite-colour candle before a displacement that breaks structure; the zone is its range, its body or its 50% level, entered on return. Sweep: a trade through a prior swing or equal highs or lows, followed by a market-structure shift.
- **Primitive vs wrapper.** Primary P8; secondary P1 (displacement, then continuation) and P7 (the sweep is resting stop liquidity, as in S-PAT-04). The structure shift, higher-timeframe bias and midpoint entry are wrapper.
- **Claimed mechanism.** "Institutional" order flow leaves imbalances that get rebalanced, and "smart money" runs retail stops for liquidity. Retail stops and breakout traders are on the other side. The sources offer no evidence. Only S-PAT-04 documents stop clustering with order data.
- **Published claim.** None. The order-block page notes that blocks "fail routinely".
- **Decay and crowding.** These concepts were popularised in the early 2020s. No data.
- **Cost-floor note.** Entering at the midpoint with the stop at the far edge risks half the gap width. Any gap narrower than 26 bp puts the stop below the 13 bp round trip, which is common on 1m-5m bars.
- **Event rate (estimate).** Many raw FVGs per coin-day. Date-independent events are bounded by about 365 days a year.
- **Applies to / testable here.** FX, index futures, crypto. Y (klines; matched non-touch control as in S-PAT-03).
- **Regime hypothesis.** Continuation after displacement needs positive short-horizon P1 (high-volatility, news sessions). Fails in chop.
- **Overlaps.** S-PAT-04, S-PAT-10, S-PAT-06 (OTE zone), S-PAT-15, S-PAT-16.

### S-PAT-15 ICT time models: killzones, Silver Bullet, Power of Three / Judas swing
- **Fidelity.** B for the Silver Bullet (windows and steps are specified). The Power of Three (PO3) is descriptive and not mechanizable.
- **Sources.** LuxAlgo Library, "Silver bullet" and "Power of three". https://www.luxalgo.com/library/concept/silver-bullet/ and https://www.luxalgo.com/library/concept/power-of-three/. Both read. Huddleston's ICT content ("popularized ... in the early 2020s"): recalled, not re-fetched. Killzone clock times were not given on the pages read.
- **Rule (Silver Bullet).** Three 60-minute windows in New York time (daylight-saving aware): 03-04, 10-11 and 14-15. Beforehand, mark liquidity: untapped session highs and lows, equal highs and lows, open FVGs. Inside the window, wait for a sweep of one pool or a structure shift. Then enter in an FVG created by the displacement within the same hour. Stop beyond the manipulation swing; target the opposing pool. No FVG in the window means no trade.
- **Rule (PO3).** Anchor at the midnight New York open (or Monday's open). Accumulation near the open, then a "Judas" false move beyond it that takes liquidity, then displacement back through the open. Join on a retracement. No stop or target is given; the source calls it "descriptive, not mechanical".
- **Primitive vs wrapper.** Primary P5 (clock windows, session opens); secondary P8. The FVG entry and sweep requirement are wrapper.
- **Claimed mechanism.** Price is "drawn to liquidity at predictable times". No other side is named beyond retail stops. The measurable part is volatility concentrated at session opens (P2/P5). Direction is not addressed.
- **Published claim.** None: "no audited statistics exist for the model".
- **Decay and crowding.** No data.
- **Cost-floor note.** Same as S-PAT-14. 1m-5m FVG stops are often below 13 bp; targets at session extremes are larger.
- **Event rate (estimate).** At most 3 windows a day, so at most about 365 date-independent days a year.
- **Applies to / testable here.** Index futures and FX. Y as clock buckets on crypto klines (map New York daylight saving explicitly). Partial on cached NQ/FX.
- **Regime hypothesis.** Windows containing scheduled US flow (cash open, 10:00 data) on US-linked instruments. Weak on holidays and in Asia-led crypto sessions.
- **Overlaps.** S-PAT-14, S-PAT-12, S-PAT-10 (spring is a Judas swing), S-PAT-16.

### S-PAT-16 Social-media and prop-firm "reel" strategies (retail discretionary intraday)
- **Fidelity.** C. Folklore: there is no primary source for any single recipe, and the parameters vary by creator. The evidence below is about the trader population, not a rule.
- **Sources.** Barber, Lee, Liu & Odean, "The Cross-Section of Speculator Skill: Evidence from Taiwan", *J. Financial Markets* 18:1-24, 2014. https://faculty.haas.berkeley.edu/odean/papers/Day%20Traders/The%20Cross-Section%20of%20Speculator%20Skill.pdf. Full paper read. ESMA press release, 27 Mar 2018. https://www.esma.europa.eu/press-news/esma-news/esma-agrees-prohibit-binary-options-and-restrict-cfds-protect-retail-investors. Read. Chague, De-Losso & Giovannetti, "Day Trading for a Living?", 2019: recalled, not re-fetched. SSRN id 3423101 is from memory; the page could not be fetched.
- **Rule (typical composite, folklore).** 1-5 minute chart during the London or New York open. Wait for a sweep of the prior session's (often Asia's) high or low, then a 1m structure shift, then enter at the FVG. Stop beyond the sweep extreme; target a fixed R multiple. The sweep size, swing definition, R multiple and risk per trade are all not specified (they vary by creator). Prop-firm drawdown limits add a daily-loss stop.
- **Primitive vs wrapper.** Primary P8; secondary P5. Almost everything is wrapper.
- **Claimed mechanism.** "Smart money hunts retail stops". The followers of these reels are that retail side.
- **Published claim.** About the population, not the recipe. Fewer than 1% of Taiwan day traders (about 450,000 in an average year, 1992-2006) "predictably and reliably earn positive abnormal returns net of fees". ESMA: "74-89% of retail accounts typically lose money" on CFDs. Chague et al. (recalled): about 97% of Brazilian index-futures day traders who persisted beyond 300 days lost money.
- **Decay and crowding.** n/a. Creators' P&L screenshots are not a published source and were not collected.
- **Cost-floor note.** A 1-5m stop beyond a sweep extreme is often a few to tens of bp, at or below the 13 bp round trip.
- **Event rate (estimate).** 1-2 setups per session per instrument; at most about 365 date-independent days a year.
- **Applies to / testable here.** FX, index futures, crypto. Y only for a mechanised composite, which would be our own invention.
- **Regime hypothesis.** No market regime: reported success is predicted by survivorship and selective posting.
- **Overlaps.** S-PAT-14, S-PAT-15, S-PAT-04, S-PAT-10.

---

## Family notes

The 16 cards hold about three distinct primitives. First, reaction at a price location (P8): S/R, round numbers, pivots, Fibonacci, value-area edges, order blocks and FVGs are the same level-touch idea in different wrappers. Second, failed-break reversal: the spring, liquidity sweep, Judas swing and the reel recipe are one idea. Third, breakout continuation (P1): P&F, Renko, Dow theory and range breaks. Candlesticks, head-and-shoulders, harmonics and Elliott are swing-template variants of the first two. Clock windows (P5) and profile (P7) appear only as gates. Only Osler's order-book data supports a mechanism, and it suggests a candidate P10: resting stop and take-profit clustering. Elliott, Gann, Wyckoff, Dow theory (as published) and Power of Three cannot be mechanized as published.
