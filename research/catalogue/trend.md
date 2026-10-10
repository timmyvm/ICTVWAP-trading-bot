# Catalogue family: trend following and time-series momentum (S-TREND)

Phase-0 scout cards, compiled 2026-10-10. Outcome-blind: nothing here is a result from this repo.
Template and primitive tags: docs/CATALOGUE.md sections 2-3.

Source-access notes:
- SSRN pages could not be fetched (the fetch errored or waited on a permission nobody answered). StockCharts
  (robots) and Investopedia (blocked) could not be read either, so the indicator cards rely on Wikipedia, TradingView
  help or the author's own page.
- The shared web-search budget ran out partway through. Anything not re-read is marked "recalled, not re-fetched".
- Cost-floor arithmetic assumes a coin with 60 %/yr volatility on a 365-day year. That is an assumption, not data.
  Sigma is then about 3.1 % per day, 8.3 % per week, 14 % per 20 days, 17 % per month and 60 % per year, against
  a 13 bp round trip.
- Event rates are rough estimates of date-independent signal changes per year, not counts.

---

### S-TREND-01 · Time-series momentum 12-1, volatility-scaled (Moskowitz, Ooi, Pedersen 2012)
- **Fidelity:** A.
- **Sources:** "Time series momentum", J. Financial Economics 104 (2012) 228-250. Full text read at
  https://fairmodel.econ.yale.edu/ec439/jpde.pdf. The SSRN page https://papers.ssrn.com/abstract=2089463 was not
  fetchable.
- **Rule:**
  - At each month end, for each instrument: position = sign(past 12-month excess return) × 40 % / sigma_{t-1}.
  - sigma is the EWMA variance of daily returns, annualised ×261, with a 60-day centre of mass, lagged one day.
  - Hold 1 month (k=12, h=1); grids of k and h up to 48 months are also reported. Equal-weight across instruments.
  - Universe: 58 liquid futures and forwards (24 commodities, 12 FX, 9 equity indices, 13 government bonds).
- **Primitive vs wrapper:** Primary P1: the 12-month signed return predicts the next month. Secondary P2: the 40 %
  ex-ante volatility scaling relies on volatility persistence. Wrapper: monthly rebalance, equal-weight
  diversification. No stop, no target.
- **Claimed mechanism:** Under-reaction, then delayed over-reaction (spot shocks partly reverse after about a year).
  CFTC data show speculators ride the trend while hedgers take the other side, paying a hedging-pressure or
  liquidity premium. No link to sentiment, the TED spread or the VIX.
- **Published claim (source's numbers, futures 1985-2009):** All 58 contracts are positive and 52 are significant at
  5 %. Diversified Sharpe is "greater than one". Alpha vs MSCI World, SMB, HML and UMD is 1.58 %/month (t=7.99).
  Sharpe for 1966-1985 is 1.1. With a 12-month lookback, the t-stat falls from 6.61 (1-month hold) to 0.66
  (36-month hold): the effect partly reverses.
- **Decay and crowding:**
  - Kim, Tse, Wald (J. Fin. Markets 30, 2016; abstract only,
    https://ideas.repec.org/a/eee/finmar/v30y2016icp103-124.html): the alpha is "largely driven by
    volatility-scaling". Unscaled TSMOM performs about like buy-and-hold.
  - Huang, Li, Wang, Zhou (JFE 135, 2020; abstract only, https://ideas.repec.org/a/eee/jfinec/v135y2020i3p774-794.html):
    the evidence is "weak". Pooled t-stats fail bootstrap critical values, and a historical-mean strategy does
    about as well.
- **Cost-floor note:** At most one position change a month against about 17 % monthly sigma, so 13 bp is about
  0.008 sigma. Volatility rescaling adds small trades. Not cost-bound.
- **Event rate (estimate):** 2-4 independent sign regimes a year for a crypto basket. Coins share one dominant factor,
  so flips cluster.
- **Applies to / testable here:** The source covers futures and FX. Y as a crypto adaptation (daily klines). Partial
  for the original universe (Yahoo daily proxies only).
- **Regime hypothesis:** Should work in persistent macro moves and large up or down markets (the paper's "smile").
  Should fail in V-shaped reversals faster than the lookback, and in range-bound years.
- **Overlaps:** S-TREND-02 (multi-horizon), S-TREND-03 and S-TREND-04 (price vs long average, the same kernel),
  S-TREND-15.

### S-TREND-02 · Multi-horizon trend, CTA replication (Hurst, Ooi, Pedersen, "A Century of Evidence")
- **Fidelity:** A.
- **Sources:**
  - J. Portfolio Management, Fall 2017. Full text read at https://fairmodel.econ.yale.edu/ec439/hurst.pdf; the
    exhibit tables could not be extracted.
  - The 2014 AQR white-paper version (1880-2013), read in full for Exhibit 1 via a third-party mirror:
    https://oxfordstrat.com/coasdfASD32/uploads/2016/03/A-Century-of-Evidence-on-Trend-Following-Investing.pdf
- **Rule:** Three always-in sub-strategies, each the sign of a market's past 1-, 3- or 12-month excess return. Each
  position is sized to equal volatility (rolling 3-year equal-weight estimate from monthly returns). The three are
  combined equally and the portfolio is scaled to a 10 % ex-ante volatility target, rebalanced monthly. Universe: 67
  markets (29 commodities, 11 equity indices, 15 bonds, 12 FX; the appendix lists 10 currencies, an inconsistency).
- **Primitive vs wrapper:** Primary P1. Secondary P2: volatility parity and the portfolio volatility target.
  Wrapper: the 3-horizon blend, monthly rebalance and the 2/20 fee layer. No stop.
- **Claimed mechanism:** Anchoring and herding. Non-profit-seeking participants (central banks smoothing FX and
  rates, corporate hedgers) slow the rate at which information gets into prices.
- **Published claim (source's numbers):**
  - 1880-2013 (2014 version): 14.9 %/yr gross of fees, 11.2 % net of 2/20; volatility 9.7 %; net Sharpe 0.77;
    correlation 0.00 with the S&P 500.
  - 1880-2016 (2017 version): positive in every decade; average per-market Sharpe about 0.4; positive in 8 of the 10
    largest 60/40 drawdowns.
- **Decay and crowding:**
  - The 2000-2013 decade had a net Sharpe of 0.62, against 0.96 in the 1980s and 0.98 in the 1990s. The 2017 text
    ties the weaker 2008-2014 period to high cross-market correlation.
  - Lempérière et al., "Two centuries of trend following" (2014; full text read, https://arxiv.org/pdf/1404.3274):
    long trends show no significant decay but were "virtually flat since 2011". The 3-day trend decayed after 1990.
- **Cost-floor note:** The 1-month leg flips most often; at about 17 % monthly sigma, 13 bp is under 0.01 sigma. The
  source models costs at 2012 levels, ×2 for 1993-2002 and ×6 for 1880-1992.
- **Event rate (estimate):** 3-6 independent signal changes a year for a crypto basket.
- **Applies to / testable here:** The source covers multi-asset futures. Partial for the original (Yahoo proxies; no
  pre-1990 futures). Y as a crypto adaptation.
- **Regime hypothesis:** Should work when cross-asset correlation is low and in prolonged macro bull or bear
  regimes. Should fail in fast crashes such as 1987, which the paper itself flags.
- **Overlaps:**
  - S-TREND-01: a single horizon.
  - Lempérière's alternative kernel: sign of (price minus an EMA of monthly closes, n = 5 months) divided by an EMA of
    absolute monthly changes, with 1/sigma sizing. t-stat about 5 since 1960 and about 10 since 1800.

### S-TREND-03 · Faber 10-month SMA timing (tactical asset allocation)
- **Fidelity:** B.
- **Sources:**
  - Faber, "A Quantitative Approach to Tactical Asset Allocation", J. Wealth Management, Spring 2007 (SSRN 962461;
    2013 update). The primary was not readable.
  - Rules and numbers come from the CXO Advisory summary of the 2013 update (full page read):
    https://www.cxoadvisory.com/?p=1115
- **Rule:**
  - At each month end, for each asset: hold it if its monthly close is above its 10-month SMA, else hold 90-day
    T-bills.
  - Five assets, equal-weighted and rebalanced monthly: S&P 500, 10-year Treasuries, MSCI EAFE, GSCI, NAREIT.
  - Long or cash only. Fills are at the signal-date close, which CXO notes needs "some anticipation".
- **Primitive vs wrapper:** Primary P1 (a 10-month price-vs-average kernel). Wrapper: the monthly check, the cash leg
  (no shorting) and the 5-asset equal weight.
- **Claimed mechanism:** Avoiding long bear markets; a risk and drawdown argument. No counterparty is named.
- **Published claim (source's numbers, gross of frictions, via CXO):**
  - S&P 500, 1901-2012: 10.2 %/yr vs 9.3 % buy-and-hold; volatility 12.0 % vs 17.9 %; Sharpe 0.55 vs 0.32; max
    drawdown -50.3 % vs -83.5 %.
  - Five assets, 1973-2012: Sharpe 0.73 vs 0.44; max drawdown -9.5 % vs -46.0 %.
- **Decay and crowding:**
  - CXO: the five-asset edge "may depend on rare conditions" such as 2008, and choosing 10 months carries
    data-snooping bias.
  - Zakamulin (J. Asset Mgmt 15, 2014) tested SMA rules out-of-sample and net of costs over 1926-2012. Only 2 of 8
    cases reliably beat buy-and-hold, and stock timing lagged over 1975-1999. Sources: the CXO summary (read in full),
    https://www.cxoadvisory.com/technical-trading/net-performance-of-sma-and-intrinsic-momentum-timing-strategies,
    and the abstract at https://ideas.repec.org/a/pal/assmgt/v15y2014i4d10.1057_jam.2014.25.html
- **Cost-floor note:** About 1-3 switches per asset per year (estimate) against about 17 % monthly sigma. Not
  cost-bound.
- **Event rate (estimate):** 1-3 a year per market factor.
- **Applies to / testable here:** The source covers US and global indices. Partial for the original (Yahoo monthly).
  Y as a crypto adaptation, but with few events.
- **Regime hypothesis:** Should help in slow bear markets lasting several months (2000-02, 2008). Should cost money in
  sharp V-shaped dips and in sideways markets near the average.
- **Overlaps:** S-TREND-04 (the BLL 1-200 rule on daily data), S-TREND-01, S-TREND-05.

### S-TREND-04 · Price vs long moving average: variable- and fixed-length MA (Brock, Lakonishok, LeBaron 1992)
- **Fidelity:** B. The primary (J. Finance 47(5), 1731-1764) was not read.
- **Sources:**
  - AAII summary (full page read): https://www.aaii.com/journal/article/two-technical-analysis-rulespass-academic-muster
  - Sullivan, Timmermann, White, LSE FMG DP303 (full text read): https://www.fmg.ac.uk/sites/default/files/2020-11/dp303.pdf.
    Its 1999 J. Finance publication is recalled, not re-fetched.
- **Rule:**
  - VMA, on daily DJIA closes: long while the short MA is above the long MA by more than band b; short while it is
    below by more than b; no new signal inside the band.
  - Fast MA in {1, 2, 5} days, slow MA in {50, 150, 200} days, b in {0, 1 %}. The five tested pairs, (1,50),
    (1,150), (5,150), (1,200) and (2,200), are recalled, not re-fetched.
  - The (1,200) pair is the "price vs 200-day SMA" rule.
  - FMA variant: hold 10 days after a crossover, ignoring other signals during the hold.
- **Primitive vs wrapper:** Primary P1. Secondary P2: returns after sell signals were more volatile than after buy
  signals. Wrapper: the 1 % band (a whipsaw filter) and the FMA's fixed 10-day hold.
- **Claimed mechanism:** None beyond rejecting random-walk, AR(1) and GARCH-type nulls. No counterparty identified.
- **Published claim (source's numbers, DJIA 1897-1986, via AAII):** VMA buy days +0.042 %/day and sell days
  -0.025 %/day, against +0.017 % unconditional. FMA 10-day: buy +0.53 %, sell -0.40 %. These are conditional mean
  returns, not a trading P&L.
- **Decay and crowding:** Sullivan, Timmermann and White: on DJIA 1987-1996, the best BLL rule "is not even
  statistically significant at standard critical levels". On S&P 500 futures 1984-1996, no rule beat the benchmark.
  Zakamulin 2014 (S-TREND-03) finds the performance "highly overstated" out-of-sample and net of costs.
- **Cost-floor note:** The (1,200) rule with a 1 % band flips perhaps 3-8 times a year (estimate). At 13 bp that is
  about 0.4-1 %/yr of drag, against 60 % annual sigma.
- **Event rate (estimate):** 3-8 a year per market factor; more with the fast pairs or no band.
- **Applies to / testable here:**
  - The source covers the US equity index. Y as a crypto adaptation.
  - Corbet et al., Finance Research Letters 31 (2019) 32-37, tested high-frequency BTC and found "significant support"
    for MA rules, with VMA the best (abstract only, https://ideas.repec.org/a/eee/finlet/v31y2019icp32-37.html).
- **Regime hypothesis:** Should work in drifting markets where volatility clusters on the downside. Should fail in
  low-volatility chop around the average.
- **Overlaps:** S-TREND-03, S-TREND-05, S-TREND-06. The trading-range-breakout half of BLL is under S-TREND-07.

### S-TREND-05 · Golden cross / death cross (50/200-day SMA)
- **Fidelity:** C. Folklore with no primary source found, but fully mechanizable.
- **Sources:** Wikipedia, "Moving average crossover" (full page read):
  https://en.wikipedia.org/wiki/Moving_average_crossover
- **Rule:** On daily closes, a golden cross is the 50-day SMA crossing above the 200-day SMA; a death cross is the
  reverse. Long from a golden cross to the next death cross. What to hold after a death cross (flat or short) is not
  specified. No stop or target.
- **Primitive vs wrapper:** Primary P1. The only wrapper is the choice of the two windows.
- **Claimed mechanism:** None offered.
- **Published claim:** No performance number. The source states "Death cross is not a reliable indicator of future
  market declines", citing a 2018 MarketWatch column by Hulbert (not fetched).
- **Decay and crowding:** No decay study found. The cross is heavily publicised and usually visible days ahead as
  the averages converge.
- **Cost-floor note:** About 1-2 crosses a year (estimate); cost is negligible next to about 14 % 20-day sigma. The
  risk is lag, not cost.
- **Event rate (estimate):** 1-2 a year per market factor.
- **Applies to / testable here:** The source covers stocks and indices. Y on crypto daily klines.
- **Regime hypothesis:** Pays only in trends that last well beyond about 100 days. Gives back most of the move in
  2-6 month mean-reverting swings.
- **Overlaps:** S-TREND-04 (the same dual-MA kernel), S-TREND-06.

### S-TREND-06 · MACD 12/26/9 (signal-line and zero-line crossovers, i.e. the EMA 12/26 cross)
- **Fidelity:** B.
- **Sources:**
  - Wikipedia, "MACD" (full page read; Gerald Appel, late 1970s): https://en.wikipedia.org/wiki/MACD
  - Chio, "A comparative study of the MACD-base trading strategies", 2022 (abstract only): https://arxiv.org/abs/2206.12282
- **Rule:**
  - MACD = EMA12(close) - EMA26(close). Signal = EMA9(MACD).
  - Signal-line variant: long on MACD crossing above the signal line; sell or short on crossing below.
  - Zero-line variant: long while MACD > 0, which is the same as EMA12 > EMA26.
  - The source uses daily bars. No stop or target.
- **Primitive vs wrapper:** Primary P1. The signal-line cross is a second difference (trend acceleration) of the same
  past-return filter. Wrapper: the choice of cross. Divergence reading is not mechanizable.
- **Claimed mechanism:** None offered; the source describes it only as a momentum and trend display.
- **Published claim (Chio 2022, US stocks 2015-2021):** MACD(12,26,9) alone had a win rate below 50 % and weak but
  positive returns. No buy-and-hold comparison is reported in the abstract.
- **Decay and crowding:** None measured. It is a default on every charting platform.
- **Cost-floor note:** The signal-line version flips about 10-20 times a year on daily data (estimate), a 1.3-2.6 %/yr
  drag at 13 bp. The zero-line version flips 4-8 times a year. On intraday bars the flip count scales with bars per
  day and the cost floor binds.
- **Event rate (estimate):** 10-20 signal-line or 4-8 zero-line flips a year per market factor (daily).
- **Applies to / testable here:** The source covers equities. Y on crypto at any kline timeframe.
- **Regime hypothesis:** The zero-line version should behave like a medium-horizon trend rule. The signal-line
  version should do worst in choppy, high-noise regimes.
- **Overlaps:** S-TREND-04 and S-TREND-05 (the zero-line version is a dual-MA cross), S-TREND-13.

### S-TREND-07 · Turtle trading rules (Donchian 20/55-day channel breakout)
- **Fidelity:** A.
- **Sources:** "The Original Turtle Trading Rules", https://www.tradingblox.com/originalturtles/originalturtlerules.pdf,
  read in full after OCR of the scanned PDF. The landing page says it was published by one of the original Turtles.
  The attribution to Curtis Faith (about 2003) is recalled, not re-fetched.
- **Rule:**
  - N = (19 × prior N + true range) / 20, seeded with a 20-day SMA of true range. Unit = 1 % of account / (N × $ per
    point).
  - System 1: enter on an intraday one-tick break of the prior 20-day high (long) or low (short). Skip it if the last
    20-day breakout, taken or not, would have won (it lost if price went 2N against it before a profitable 10-day
    exit); when skipped, take the 55-day breakout instead. Exit on the opposite 10-day breakout.
  - System 2: 55-day breakout, every signal taken; exit on the opposite 20-day breakout.
  - Add 1 unit every ½N from the last fill, up to 4. Stop 2N from entry, with earlier stops raised ½N per add.
    Limits: 4 units per market, 6 closely correlated, 10 loosely correlated, 12 per direction. Cut the notional
    account 20 % per 10 % loss. Universe: liquid US futures excluding grains and meats.
- **Primitive vs wrapper:** Primary P1 (a range-break kernel at 20 and 55 days). Secondary P2 (N sizing and N stops).
  Wrapper: the skip-after-winner filter, pyramiding, the 2N stop, the channel exits and the unit limits.
- **Claimed mechanism:** None beyond "most of the profits in a given year might come from only two or three large
  winning trades". The document is about discipline.
- **Published claim:**
  - The rules document reports no performance.
  - BLL's 10-day trading-range breakout (DJIA 1897-1986, via AAII): +0.63 % after buys, -0.24 % after sells.
  - Wikipedia's Donchian page cites a blog backtest calling the channel "ineffective", with a 35 % win rate:
    https://en.wikipedia.org/wiki/Donchian_channel
- **Decay and crowding:** No decay study found. Once the rules were published, breakout levels became widely watched.
- **Cost-floor note:** The 2N stop is about 2 daily ATR, roughly 8 % of price for a coin with a 4 % ATR (assumed).
  13 bp is then about 0.02 R. Not cost-bound on daily bars.
- **Event rate (estimate):** S1 about 5-10 and S2 about 2-4 breakouts per market per year. Crypto breakouts cluster
  across coins.
- **Applies to / testable here:** The source covers US futures. Y on crypto daily OHLC. N for the original universe
  (no contract-level futures history with $-per-point specs).
- **Regime hypothesis:** Should pay in rare, large, extended trends. Should bleed in range-bound regimes with false
  breaks.
- **Overlaps:** S-TREND-16 (the same kernel as a crypto ensemble), S-TREND-10, S-TREND-11, and BLL's TRB arm
  (S-TREND-04).

### S-TREND-08 · ADX / DMI (Wilder 1978) and Elder's ADX timing rule
- **Fidelity:** B. Wilder's book was not read.
- **Sources:** Wikipedia, "Average directional movement index" (full page read):
  https://en.wikipedia.org/wiki/Average_directional_movement_index. It cites Wilder, *New Concepts in Technical
  Trading Systems* (1978), and Elder, *Trading for a Living* (1993).
- **Rule:**
  - +DM = up-move if up-move > down-move and up-move > 0, else 0; -DM is the mirror.
  - Wilder-smooth +DM, -DM and true range over 14 periods. ±DI = 100 × smoothed ±DM / ATR.
  - ADX = smoothed 100 × |+DI - -DI| / (+DI + -DI).
  - Published rule (Elder, via the source): buy when ADX turns up while below both DI lines and +DI > -DI; sell when
    ADX turns back down. Long side only as written.
  - Wilder's own DI-crossover rule with its "extreme point" entry is recalled, not re-fetched.
- **Primitive vs wrapper:** Primary P1 (the sign of +DI vs -DI). Secondary P2: ADX is a trend-strength state built
  from range, not sign. Wrapper: the ADX turn condition.
- **Claimed mechanism:** None. The source says ADX measures "only trend strength".
- **Published claim:** None; no backtest is cited. Readings below 20 indicate a weak trend and above 40 a strong one.
- **Decay and crowding:** None found.
- **Cost-floor note:** ADX turns often, perhaps 10-20 exits a year on daily data (estimate), a 1.3-2.6 %/yr drag at
  13 bp.
- **Event rate (estimate):** 5-15 entries a year per market factor (daily).
- **Applies to / testable here:** Generic. Y on crypto at any timeframe.
- **Regime hypothesis:** Should help when it separates trending from ranging periods. Should fail when ADX lags a
  regime change (the source calls it lagging).
- **Overlaps:** S-TREND-09 (the same book), S-TREND-06.

### S-TREND-09 · Parabolic SAR (Wilder 1978), stop-and-reverse
- **Fidelity:** B.
- **Sources:** Wikipedia, "Parabolic SAR" (full page read; cites Wilder 1978): https://en.wikipedia.org/wiki/Parabolic_SAR
- **Rule:**
  - Always in the market. SAR_{n+1} = SAR_n + AF × (EP - SAR_n); the formula is recalled, not re-fetched, because the
    page shows it only as an image.
  - EP is the extreme of the current trend. AF starts at 0.02, rises 0.02 with each new EP, and is capped at 0.20.
  - SAR may not sit inside the current or previous bar's range; it is capped at that bound.
  - When price penetrates SAR, reverse: SAR resets to the prior EP and AF to 0.02.
  - The source prefers a 0.01 start for stocks.
- **Primitive vs wrapper:** Primary P1. The rule is mostly wrapper: an accelerating trailing stop that doubles as the
  entry through stop-and-reverse.
- **Claimed mechanism:** None. The source says it works "only in trending markets".
- **Published claim:** Wikipedia cites a 2023 blog backtest (Barry D. Moore, not fetched) on DJIA-30 stocks: a 19 %
  win rate on OHLC bars and 63 % on Heikin-Ashi bars. These are win rates, not returns.
- **Decay and crowding:** None found.
- **Cost-floor note:** As AF rises toward 0.20 the stop tightens fast. Perhaps 10-25 reversals a year on daily data
  (estimate), i.e. 1.3-3.3 %/yr. On intraday bars the stop distance can reach the cost floor.
- **Event rate (estimate):** 10-25 flips a year per market factor (daily).
- **Applies to / testable here:** Generic. Y on crypto.
- **Regime hypothesis:** Should work in smooth, persistent trends with expanding range. Whipsaws in sideways markets,
  as the source says.
- **Overlaps:** S-TREND-10 (a flipping trailing band), S-TREND-14 (the cited Heikin-Ashi pairing).

### S-TREND-10 · Supertrend (ATR band, flip on close)
- **Fidelity:** C. Mechanizable, but the parameters are not specified in the source.
- **Sources:** TradingView Help, "Supertrend" (full page read; credits Olivier Seban):
  https://www.tradingview.com/support/solutions/43000634738-supertrend/
- **Rule:**
  - Midpoint = (H+L)/2. Basic bands = midpoint ± m × ATR(n).
  - Ratchet: the final upper band takes the new basic value only if that is lower, or if the prior close was above
    the prior upper band. The lower band is the mirror.
  - The trend flips up on a close above the upper band and down on a close below the lower band. Long in an up-trend,
    short in a down-trend; the line is the stop.
  - n and m are not specified in the source. The common platform default of 10 and 3 is recalled, not re-fetched.
- **Primitive vs wrapper:** Primary P1. Secondary P2: the ATR band scales with the volatility state. Wrapper: the
  ratchet (trailing stop) and the always-in flipping.
- **Claimed mechanism:** None offered.
- **Published claim:** None found.
- **Decay and crowding:** None found. It is very common in retail crypto scripts.
- **Cost-floor note:** At m=3 on daily bars, the stop is about 3 × 4 % (assumed ATR) = 12 % away, far above 13 bp.
  On 1m or 5m bars an ATR is tens of bp, so 3 ATR sits at the cost floor.
- **Event rate (estimate):** 4-8 flips a year per market factor at m=3 (daily).
- **Applies to / testable here:** Generic. Y on crypto at any timeframe.
- **Regime hypothesis:** Should work in trends with stable volatility. Should fail when volatility expands within a
  range: the band widens and entries come late.
- **Overlaps:** S-TREND-11 (the same idea with a symmetric band and no ratchet), S-TREND-09, S-TREND-07.

### S-TREND-11 · Keltner "ten-day moving average rule" (original 1960 channel breakout)
- **Fidelity:** B.
- **Sources:** Wikipedia, "Keltner channel" (full page read), https://en.wikipedia.org/wiki/Keltner_channel. It cites
  Keltner, *How to Make Money in Commodities* (1960). The page itself says "the origin of this idea is uncertain".
- **Rule:**
  - Centre = 10-day SMA of the typical price (H+L+C)/3. Bands = centre ± the 10-day SMA of the daily high-low range.
  - Buy on a close above the upper band; sell or short on a close below the lower band.
  - The exit is not specified. Stop-and-reverse at the opposite band is the natural reading, but it is an assumption
    and is labelled as one.
  - Later EMA and ATR-multiple variants (Raschke and others) have unspecified parameters.
- **Primitive vs wrapper:** Primary P1 (a short-horizon breakout). Secondary P2: the band width comes from the recent
  range. Wrapper: the exit convention.
- **Claimed mechanism:** None offered.
- **Published claim:** None in the source.
- **Decay and crowding:** None found.
- **Cost-floor note:** The band sits one average daily range from the centre, about 4-5 % on a coin, against 13 bp.
  Not cost-bound daily. Perhaps 6-12 reversals a year (estimate).
- **Event rate (estimate):** 6-12 a year per market factor (daily).
- **Applies to / testable here:** The source covers commodity futures. Y on crypto.
- **Regime hypothesis:** Should work in short, strong trends. Should fail in mean-reverting ranges of 1-2 weeks.
- **Overlaps:** S-TREND-10, S-TREND-07.

### S-TREND-12 · Ichimoku Kinko Hyo: TK cross filtered by the cloud
- **Fidelity:** B. Hosoda's full method is not mechanizable; this card mechanizes one published signal.
- **Sources:** Wikipedia, "Ichimoku Kinko Hyo" (full page read), https://en.wikipedia.org/wiki/Ichimoku_Kink%C5%8D_Hy%C5%8D.
  Goichi Hosoda developed it in the late 1930s and released it publicly in the late 1960s.
- **Rule:**
  - Tenkan = midpoint of the 9-bar high and low. Kijun = midpoint of the 26-bar high and low.
  - Span A = (Tenkan + Kijun)/2 and Span B = midpoint of the 52-bar high and low, both plotted 26 bars ahead. The
    cloud at bar t is therefore the Spans computed at t-26.
  - Long when Tenkan crosses above Kijun while the close is above both Spans; short is the mirror.
  - The exit is not specified (the opposite TK cross, or a close back inside the cloud).
  - The Chikou cross, the kumo twist and the 8/21/42 settings are other published signals, not part of this card.
- **Primitive vs wrapper:** Primary P1. Secondary P8: the cloud acts as a support or resistance location. Wrapper:
  the cloud filter and Chikou confirmation.
- **Claimed mechanism:** None offered.
- **Published claim:** The source cites no empirical study; its support is books and broker guides.
- **Decay and crowding:** None found.
- **Cost-floor note:** About 6-10 TK crosses a year on daily data, fewer after the cloud filter (estimate). Cost is
  small at daily resolution.
- **Event rate (estimate):** 3-8 filtered entries a year per market factor.
- **Applies to / testable here:** Generic (designed on Japanese equities). Y on crypto.
- **Regime hypothesis:** The cloud filter should help in established trends. Should fail at turning points, where all
  the midpoint lines lag.
- **Overlaps:** S-TREND-07 (the midpoint of an n-bar high-low range is a Donchian statistic), S-TREND-05.

### S-TREND-13 · Low-lag and adaptive MA turning points (Hull MA; Kaufman KAMA)
- **Fidelity:** C. The HMA period is only an example default, and the KAMA rules are recalled.
- **Sources:**
  - Hull, "Hull Moving Average" (author's page, full page read): https://alanhull.com/hull-moving-average
  - Kaufman, *Smarter Trading* (1995), for KAMA: recalled, not re-fetched; no source page was readable.
- **Rule:**
  - HMA(n) = WMA_{√n}(2 × WMA_{n/2}(P) - WMA_n(P)).
    - The author says to "employ the turning points as entry/exit signals", and that the HMA "shouldn't be used to
      generate crossover signals".
    - Mechanized here as: long while HMA_t > HMA_{t-1}, flip when the slope changes sign.
    - n is not recommended; the author's MetaStock example default is 20.
  - KAMA (recalled):
    - ER = |P_t - P_{t-10}| / Σ|ΔP| over 10 bars.
    - SC = [ER × (2/3 - 2/31) + 2/31]².
    - KAMA_t = KAMA_{t-1} + SC × (P_t - KAMA_{t-1}).
    - The trade filter is not specified here.
- **Primitive vs wrapper:** Primary P1. KAMA's efficiency ratio is a trendiness state, a conditioner like a variance
  ratio. Wrapper: the turning-point flip.
- **Claimed mechanism:** None. The author claims only that the HMA "almost eliminates lag".
- **Published claim:** None.
- **Decay and crowding:** None found.
- **Cost-floor note:** An HMA(20) slope turns often on daily data, perhaps 15-30 times a year (estimate): a 2-4 %/yr
  drag. Likely at the cost floor on intraday bars.
- **Event rate (estimate):** 15-30 a year per market factor (daily).
- **Applies to / testable here:** Generic. Y on crypto.
- **Regime hypothesis:** Cutting lag passes more noise, so this should do worse than slow MAs in noisy regimes. KAMA,
  by design, should stay flat in choppy ones.
- **Overlaps:** S-TREND-06, S-TREND-14, S-TREND-05.

### S-TREND-14 · Heikin-Ashi colour trend
- **Fidelity:** C. The reading rules are not mechanizable as published; this card uses a colour-flip mechanization.
- **Sources:**
  - Wikipedia "Heikin-Ashi" redirects to "Candlestick chart" (full page read): https://en.wikipedia.org/wiki/Heikin-Ashi.
    It gives the formulas.
  - Valcu, "Using the Heikin-Ashi technique", *Technical Analysis of Stocks & Commodities*, Feb 2004: recalled, not
    re-fetched.
- **Rule:**
  - HA close = (O+H+L+C)/4. HA open = (prior HA open + prior HA close)/2. HA high = max(H, HA open, HA close).
    HA low = min(L, HA open, HA close).
  - Mechanization: long while HA close > HA open, short or flat while below, flip on a colour change.
  - The folklore "no lower shadow" strong-candle filter is recalled, not re-fetched; its threshold is not specified.
- **Primitive vs wrapper:** Primary P1 (two-bar smoothed price with recursive open smoothing). The colour flip is the
  whole wrapper.
- **Claimed mechanism:** None.
- **Published claim:** Indirect only: Wikipedia's Parabolic SAR page cites a 63 % win rate for PSAR on HA bars (a blog
  backtest, not fetched).
- **Decay and crowding:** None found.
- **Cost-floor note:** The colour flips often on daily bars, perhaps 25-50 times a year (estimate): 3-6.5 %/yr at
  13 bp. Cost-bound on intraday bars.
- **Event rate (estimate):** 25-50 a year per market factor (daily).
- **Applies to / testable here:** Generic. Y on crypto.
- **Regime hypothesis:** Can only work where 1-3 bar serial correlation is positive. Should fail wherever short
  returns mean-revert.
- **Overlaps:** S-TREND-13, S-TREND-09.

### S-TREND-15 · Bitcoin weekly time-series momentum (Liu and Tsyvinski)
- **Fidelity:** A, as a predictability result. The source reports quintile sorts, not a trading rule.
- **Sources:** "Risks and Returns of Cryptocurrency", NBER WP 24877 (2018); Rev. Financial Studies 34(6), 2021.
  - Full working paper read: https://www.nber.org/system/files/working_papers/w24877/w24877.pdf
  - Abstract page: https://www.nber.org/papers/w24877
- **Rule:**
  - Form: BTC's return over week t, sorted into quintiles. The no-lookahead version takes its cutoffs from the first
    two years.
  - Long for the next k weeks (k=1-4) after a top-quintile week, short after a bottom-quintile week, otherwise flat.
    This is the "Difference" portfolio written as a single-asset rule.
  - Data: CoinDesk BTC daily, 2011-01 to 2018-05.
- **Primitive vs wrapper:** Primary P1 at a 1-week horizon. Wrapper: the quintile threshold and the hold length.
- **Claimed mechanism:** Not committed. Investor attention (Google, Twitter) is tested as a separate predictor.
  Under-reaction is the reader's interpretation, not the authors'.
- **Published claim (source's numbers, BTC):**
  - Weekly regressions: coefficients 0.19-0.22 (t 3.7-4.5) on the next 1-3 weeks; bootstrap t 2.2-2.7.
  - After a top-quintile week, the mean next-week return is 11.22 % (t=3.95), against 2.60 % after a bottom-quintile
    week.
  - XRP and ETH daily coefficients are mostly insignificant under the bootstrap.
- **Decay and crowding:**
  - Within the paper, the 1-week difference falls from 8.62 (full sample) to 4.35 (post-2013) and 4.53 (no
    lookahead).
  - Hudson and Urquhart, Annals of OR 297 (2021), tested about 15,000 rules and found "no predictability for Bitcoin
    in the out-of-sample period" (abstract only):
    https://ideas.repec.org/a/spr/annopr/v297y2021i1d10.1007_s10479-019-03357-1.html
- **Cost-floor note:** About 8 % weekly sigma (assumed) against 13 bp, i.e. about 0.016 sigma. Not cost-bound.
- **Event rate (estimate):** About 21 signal weeks a year, overlapping, so roughly 10-20 independent events. The
  source covers one asset.
- **Applies to / testable here:** The source covers BTC spot (plus XRP and ETH daily). Y on BTC and coin perps, but
  the perp archive covers a later era than 2011-2018, and era dependence is the central question.
- **Regime hypothesis:** Should hold in attention-driven, retail-dominated years. Should fade as institutional and
  arbitrage capital arrives, consistent with the shrinkage after 2013 inside the paper.
- **Overlaps:**
  - S-TREND-01 (the monthly cross-asset analogue), S-TREND-16.
  - Detzel, Liu, Strauss, Zhou, Zhu, Financial Management 50(1), 2021: price-to-MA ratios forecast daily BTC returns
    in and out of sample (abstract only, https://ideas.repec.org/a/bla/finmgt/v50y2021i1p107-137.html).

### S-TREND-16 · Crypto Donchian-ensemble trend with volatility targeting (Zarattini, Pagani, Barbon 2025)
- **Fidelity:** A.
- **Sources:** "Catching Crypto Trends; A Tactical Approach for Bitcoin and Altcoins" (2025). Full paper read:
  https://concretumgroup.com/wp-content/uploads/2026/02/Catching-Crypto-Trends.pdf (summary page
  https://concretumgroup.com/catching-crypto-trends-a-tactical-approach-for-bitcoin-and-altcoins/; SSRN 5209907 not
  fetched).
- **Rule:**
  - For each n in {5, 10, 20, 30, 60, 90, 150, 250, 360} days, on daily closes: go long when the close hits the n-day
    max close. The stop is max(prior stop, mid of the n-day max and min close), starting at the mid; exit on the
    first close below it. Long-only (long-short in the appendix).
  - Combo = equal-weight average of the 9 signals. Weight = min(25 % / sigma_90d, 200 % × signal). Skip
    volatility-driven trades unless the weight drifts by more than 20 %.
  - Universe, re-selected monthly: the top 20 coins by 30-day median daily volume, with at least 365 days listed and
    at least $2M median volume; no stablecoins or wrapped tokens. CoinMarketCap data, 2015-2025. Costs: 10 bp base
    case (25 and 50 bp tested).
- **Primitive vs wrapper:** Primary P1 (a multi-horizon breakout kernel). Secondary P2 (the 25 % volatility target).
  Wrapper: the mid-channel ratchet stop, the 20 % rebalance band and the liquidity screen.
- **Claimed mechanism:** Trend following carried over from traditional futures. No crypto-specific counterparty is
  argued.
- **Published claim (source's numbers):**
  - BTC Combo, 2015-2025, gross: Sharpe 1.58, CAGR 30 %, max drawdown 19 %, beta 0.17.
  - Top-20 portfolio, net of 10 bp: Sharpe 1.57, CAGR 18 %, max drawdown 11 %, alpha 10.8 %/yr vs BTC.
  - On BTC, the 5-30 day models were strongest; the 150- and 250-day alphas were not significant.
- **Decay and crowding:** Not studied. Cost sensitivity: the 5-day model's CAGR falls to 18 % at 50 bp.
- **Cost-floor note:** The 5-day mid-channel stop can sit within about 1-2 daily sigma (3-6 %). Fine at 13 bp on daily
  bars, but the short legs carry most of the turnover.
- **Event rate (estimate):** 5-15 independent market-wide entry clusters a year; coin entries cluster on BTC-led dates.
- **Applies to / testable here:** The source covers crypto spot (aggregated prices). Y on perp daily klines; perps add
  funding, which the paper ignores.
- **Regime hypothesis:** Should work in crypto bull legs, and should sit out long drawdowns because it is long-only.
  Should fail in sideways 2-6 month ranges with false breaks.
- **Overlaps:** S-TREND-07 (the same kernel), S-TREND-02 (multi-horizon blend), S-TREND-15.

---

## Family notes

The sixteen cards hold essentially one primitive, P1 serial dependence, at horizons from 1-3 bars (Heikin-Ashi,
PSAR, HMA) to 12 months (01, 03). Levine and Pedersen (FAJ 2016, abstract only) argue that general trend filters
are equivalent. On that view, cards 01-06 and 13 are one weighted sum of past returns with different kernels, and
07, 10, 11, 12 and 16 swap in a breakout kernel plus a trailing-stop wrapper. The only second primitive is P2,
volatility scaling (01, 02, 07, 16), which Kim, Tse and Wald credit with most of TSMOM's alpha. Not mechanizable as
published: the full Ichimoku method, the Heikin-Ashi reading rules and MACD divergence. Wilder's DMI entry rule was
not verified.
