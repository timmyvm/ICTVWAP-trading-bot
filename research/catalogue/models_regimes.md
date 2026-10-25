# Catalogue family: statistical, regime and machine-learning models (S-MOD)

Phase-0 cards for docs/CATALOGUE.md, compiled 2026-10-10. Outcome-blind: nothing here comes from this repo's
data or results. Every number is the source's own, for its market and era. "Read: full" = full text read (via
text extraction); "read: abstract" = abstract or listing page only; "recalled, not re-fetched" = memory, not
verified this session. The shared web-search budget ran out before the primary texts of GHM23, NWD97 and the
LdP18 book could be fetched; those gaps are flagged per card, not filled.

**Cost convention.** 13 bp round trip per unit traded. A $1-long/$1-short book that turns over fully costs
2 x 13 = 26 bp per rebalance. Perp funding is left out.

**ML reporting rule (chair's brief).** Every ML card states target, features, training window, validation
scheme, whether it was walk-forward and/or purged, whether costs were included, and the effective number of
independent samples. A source that does not say is graded down. "Effective samples" counts dates (or regime
episodes), not rows: one market-wide day across many assets is one sample.

**Proposed P9 sub-tags (chair decides).** `P9-news`: unscheduled firm news read from text, with slow
underreaction afterwards (S-MOD-12, -13). `P9-valuation`: a long-short book's price relative to its
fundamentals, used as a slow timing signal (S-MOD-15). S-MOD-16 is a wrapper, not a primitive.

## Sources (keys used in the cards)

| key | citation | URL | read |
|---|---|---|---|
| SYM24 | Shu, Yu & Mulvey, "Downside Risk Reduction Using Regime-Switching Signals: A Statistical Jump Model Approach", arXiv 2402.05272 (2024), DOI 10.1057/s41260-024-00376-x | https://arxiv.org/abs/2402.05272 | full |
| KPT12 | Kritzman, Page & Turkington, "Regime Shifts: Implications for Dynamic Strategies", FAJ 68(3) 2012, 22-39 | https://rpc.cfainstitute.org/research/financial-analysts-journal/2012/regime-shifts-implications-for-dynamic-strategies-corrected | abstract |
| QS | QuantStart, "Kalman Filter-Based Pairs Trading Strategy In QSTrader" (reproduces Chan 2013) | https://www.quantstart.com/articles/kalman-filter-based-pairs-trading-strategy-in-qstrader | full |
| CH13 | Chan, *Algorithmic Trading: Winning Strategies and Their Rationale*, Wiley 2013 | (book) | recalled, not re-fetched |
| EHM05 | Elliott, van der Hoek & Malcolm, "Pairs trading", Quantitative Finance 5(3) 2005, 271-276 | https://ideas.repec.org/a/taf/quantf/v5y2005i3p271-276.html | abstract |
| DF10 | Do & Faff, "Does Simple Pairs Trading Still Work?", FAJ 2010 | (not fetched) | recalled, not re-fetched |
| B16 | Benhamou, "Trend without hiccups: a Kalman filter approach", 2016, arXiv 1808.03297 (SSRN 2747102) | https://arxiv.org/abs/1808.03297 | full |
| MM17 | Moreira & Muir, "Volatility-Managed Portfolios", NBER WP 22208 (JF 2017, venue recalled) | https://www.nber.org/papers/w22208 | full |
| COWY20 | Cederburg, O'Doherty, Wang & Yan, "On the performance of volatility-managed portfolios", JFE 138(1) 2020, 95-117 | https://www.lehigh.edu/~xuy219/research/COWY.pdf | full |
| FKO01 | Fleming, Kirby & Ostdiek, "The Economic Value of Volatility Timing", JF 2001 | (not fetched) | recalled, not re-fetched |
| CLS22 | Chang, Lizardi & Shah, "Optimizing Returns Using the Hurst Exponent and Q Learning on Momentum and Mean Reversion Strategies", arXiv 2205.11122 (2022, student report) | https://arxiv.org/abs/2205.11122 | full |
| QR04 | Qian & Rasheed, "Hurst exponent and financial market predictability" (Univ. of Georgia, c. 2004; venue not in copy) | https://c.mql5.com/forextsd/forum/170/hurst_exponent_and_financial_market_predictability.pdf | full (third-party mirror) |
| L91 | Lo, "Long-Term Memory in Stock Market Prices", Econometrica 1991 | (not fetched) | recalled, not re-fetched |
| WRZ21 | Wood, Roberts & Zohren, "Slow Momentum with Fast Reversion: A Trading Strategy Using Deep Learning and Changepoint Detection", arXiv 2105.13727 (2021) | https://arxiv.org/abs/2105.13727 | full |
| GHM23 | Goulding, Harvey & Mazzoleni, "Momentum Turning Points", JFE (2023, year recalled) | (paper not fetched) | not read |
| AA23 | Basilico, Alpha Architect summary of GHM23 (secondary; reposted on IBKR Campus 2023-10-27) | https://alphaarchitect.com/?p=87070 | full |
| KDH17 | Krauss, Do & Huck, "Deep neural networks, gradient-boosted trees, random forests: Statistical arbitrage on the S&P 500", EJOR 259(2) 2017, 689-702 (FAU WP 03/2016) | https://www.iwf.rw.fau.de/files/2016/03/03-2016.pdf | full (WP) |
| JKW22 | Jaquart, Koepke & Weinhardt, "Machine learning for cryptocurrency market prediction and trading", J. Finance and Data Science 8 (2022), 331-352 | https://doaj.org/article/cfc09801314441198e3e1c92a3914e54 | abstract |
| JDW21 | Jaquart, Dann & Weinhardt, "Short-term bitcoin market prediction via machine learning", J. Finance and Data Science 7 (2021), 45-66 | https://publikationen.bibliothek.kit.edu/1000150665 | full |
| GKX20 | Gu, Kelly & Xiu, "Empirical Asset Pricing via Machine Learning", NBER WP 25398 (RFS 2020, venue recalled) | https://www.nber.org/papers/w25398 | full (WP) |
| ZZR20 | Zhang, Zohren & Roberts, "Deep Reinforcement Learning for Trading", arXiv 1911.10107 (J. Financial Data Science 2020, venue recalled) | https://arxiv.org/abs/1911.10107 | full |
| LT23 | Lopez-Lira & Tang, "... Return Predictability and Large Language Models", arXiv 2304.07619 v6 (2023, rev. 2025); title shortened because its first clause names a commercial chat product | https://arxiv.org/abs/2304.07619 | full (v6 HTML) |
| BMZ11 | Bollen, Mao & Zeng, "Twitter mood predicts the stock market", arXiv 1010.3003 (J. Computational Science 2011, venue recalled) | https://arxiv.org/abs/1010.3003 | full |
| LP17 | Lachanski & Pav, "Shy of the Character Limit: 'Twitter Mood Predicts the Stock Market' Revisited", Econ Journal Watch 14(3) 2017, 302-345 | https://econjwatch.org/articles/shy-of-the-character-limit-twitter-mood-predicts-the-stock-market-revisited | abstract |
| AK99 | Allen & Karjalainen, "Using genetic algorithms to find technical trading rules", JFE 51 (1999), 245-271 | https://www.cs.montana.edu/courses/spring2007/536/materials/Lopez/genetic.pdf (SSRN https://papers.ssrn.com/abstract=6996) | full (course mirror) |
| NWD97 | Neely, Weller & Dittmar, "Is Technical Analysis in the Foreign Exchange Market Profitable? A Genetic Programming Approach", JFQA 1997 | (search budget exhausted) | recalled, not re-fetched |
| NWU09 | Neely, Weller & Ulrich, "The Adaptive Markets Hypothesis: Evidence from the Foreign Exchange Market", JFQA 2009 | (search budget exhausted) | recalled, not re-fetched |
| HKS20 | Haddad, Kozak & Santosh, "Factor Timing", NBER WP 26708 (RFS 2020, venue recalled) | https://www.nber.org/papers/w26708 | full (WP) |
| ACII17 | Asness, Chandra, Ilmanen & Israel, "Contrarian Factor Timing is Deceptively Difficult", JPM 2017 | (not fetched) | recalled, not re-fetched |
| LdP18 | Lopez de Prado, *Advances in Financial Machine Learning*, Wiley 2018 (ch. 3 labelling, ch. 4 weights, ch. 7 CV) | (book) | recalled, not re-fetched |
| LdP17 | Lopez de Prado, "The 7 Reasons Most Machine Learning Funds Fail", SSRN 3031282 (2017) | https://quantpedia.com/why-machine-learning-funds-fail/ (excerpts) | excerpts via secondary |
| WIKI | Wikipedia, "Meta-Labeling" (secondary; cites Joubert, "Meta-Labeling: Theory and Framework", JFDS 4(3) 2022, 31-44) | https://en.wikipedia.org/wiki/Meta-Labeling | full |

---

### S-MOD-01 Regime filter: 2-state HMM and statistical jump model (0/1 index timing)
- **Fidelity:** A. **Sources:** SYM24 (full), KPT12 (abstract: Markov-switching forecasts of turbulence,
  inflation and growth regimes beat static allocation in backtests; no rules read).
- **Rule:** Daily total-return index (S&P 500, DAX, Nikkei 225, each alone), 1970-2023, test 1990-2023. 100%
  index in the bull state, 100% 3-month bill otherwise; state at close t applies from t+2; 10 bp one-way.
  *Jump model:* 2 states on standardised excess-return features (EWM downside deviation hl 10d, EWM Sortino
  hl 20d and 60d); loss = squared-L2 clustering + lambda per switch; centroids refit every 6 months on 3,000
  days; online state = last state of a DP pass over 3,000 days; bull = higher cumulative excess return.
  Lambda re-chosen monthly by best Sharpe on the prior 8 years. *HMM benchmark:* 2-state Gaussian on daily
  log returns, 3,000-day window refit daily, 10 k-means++ restarts, last Viterbi state, k-day rolling-mean
  smoother (k by the same CV; Bulla et al. default 6). Unsupervised, walk-forward, costs in; purging n/a (no
  forward label). Effective samples: regime episodes, not days.
- **Primitive vs wrapper:** P2 primary (high-volatility state); P1 secondary (the Sortino features are
  signed trailing returns). Wrapper: binary sizing, jump penalty or smoother, delay, state labelling.
- **Claimed mechanism:** Bear regimes have higher variance and lower, often negative, returns, and regimes
  persist, so detecting that a shift has happened (not predicting it) cuts drawdowns. No counterparty named.
- **Published claim:** 1990-2023 after costs, Sharpe buy-and-hold / HMM / JM: S&P 0.48 / 0.54 / 0.68; DAX
  0.30 / 0.35 / 0.44; Nikkei 0.12 / 0.19 / 0.31. S&P max DD -55.2% / -28.9% / -26.6%. JM turnover ~44 / 170 /
  72 %/yr vs HMM 141 / 246 / 290 %/yr.
- **Decay and crowding:** No post-publication data. Source's delay test: HMM degrades fast at 5-10 day delay
  on DAX and Nikkei; JM DAX Sharpe 0.29 at 10 days (below buy-and-hold 0.30). The edge sits in the first days.
- **Cost-floor note:** At 6.5 bp a side, 44-290 %/yr turnover costs about 3-19 bp a year: not binding. The
  binding costs are the signal delay and, on perps, funding paid while long.
- **Event rate (estimate):** A few regime switches a year per index. Across coins the calls are one market
  call, so date-independent events are roughly BTC's count.
- **Applies to / testable here:** Equity indices in the source. Y: BTC/ETH/coin-index daily klines vs cash.
- **Regime hypothesis:** Works when vol regimes last months and high-vol states carry negative drift
  (deleveraging). Fails on V-shaped crashes shorter than the detection lag, and in high-vol bull runs, where
  it sits in cash through the gains.
- **Overlaps:** S-MOD-04 (same P2, continuous sizing), S-MOD-07 (state machine from momentum signs),
  S-MOD-14 (GP rules converge on the same low-vol in/out filter).

### S-MOD-02 Kalman-filter pairs trading (dynamic hedge ratio)
- **Fidelity:** B. **Sources:** QS (full; the page reproduces CH13, book not read), EHM05 (abstract), DF10
  (recalled).
- **Rule:** Observation y_t = theta0_t * x_t + theta1_t + v_t on daily adjusted closes (QS: y = IEI, x = TLT,
  2009-08-03 to 2016-08-01). theta follows a random walk with system noise delta = 1e-4 (W = delta/(1-delta)
  * I) and measurement noise 1e-3. Forecast error e_t = y_t - yhat_t, variance Q_t. Long the spread when
  e_t < -sqrt(Q_t), short when e_t > +sqrt(Q_t); close the long when e_t rises back above -sqrt(Q_t), the
  short when it falls below +sqrt(Q_t). N = 2,000 units of one leg, hedge floor(theta0 * N), not rebalanced
  while open. No costs. QS flags its own gaps: leg direction differs between prose and code, and the signal
  and the fill use the same close. EHM05: spread as a mean-reverting Gaussian Markov chain observed in noise,
  calibrated by filter; trade when the observation departs from the filtered prediction; thresholds not given.
- **Primitive vs wrapper:** P1 primary (reversal of a spread); P3 secondary (relative value of two related
  assets). Wrapper: +/-1 sqrt(Q) bands, exit on band re-entry, delta and noise settings.
- **Claimed mechanism:** Only "the spread returns to equilibrium" (EHM05). Nobody is named on the other side.
  Note: delta sets how fast the hedge ratio adapts, so a fast filter absorbs divergence into theta and
  erases part of the very signal it trades.
- **Published claim:** QS, TLT/IEI 2009-2016, gross of costs: CAGR 8.73%, Sharpe 0.75, max DD 15.79%, DD
  duration 777 days. EHM05: no empirical result in the abstract.
- **Decay and crowding:** None in the sources read. DF10 (recalled): profits of simple distance-method pairs
  trading in US equities declined over time.
- **Cost-floor note:** Two legs: 26 bp per pair round trip. The exit captures only the overshoot beyond one
  forecast sd, so that overshoot must exceed 26 bp of notional; tight pairs (small sqrt(Q)) fail by arithmetic.
- **Event rate (estimate):** 10-50 entries per pair a year; across coin pairs, entries cluster on market
  shock days, so date-independent events are far fewer.
- **Applies to / testable here:** ETFs and equities in the sources. Y: perp pairs from klines, funding on both.
- **Regime hypothesis:** Works when both legs share a stable driver and idiosyncratic shocks are transient.
  Fails when one leg trends on its own news (listing, unlock, narrative): theta drifts and the spread trends.
- **Overlaps:** S-MOD-03 (same filter, opposite P1 sign); z-score and band mean-reversion cards elsewhere.

### S-MOD-03 Kalman-filter trend following
- **Fidelity:** C (not mechanizable). **Sources:** B16 (full).
- **Rule:** Four state-space models on the E-mini S&P continuous future, daily, 2015-02-28 to 2016-02-28:
  (1) position and speed, acceleration as noise; (2) local linear trend; (3) short- and long-term factors;
  (4) model 3 plus an oscillator on the position inside the 14-period high-low range. 4/5/10/15 free
  parameters fitted by "a general optimization" on the same year that is reported. Signal: "compare the KF
  prediction with the current price" to go long or short; exact entry/exit not stated (pseudo-code section
  empty). One contract, $4 round-trip commission. No out-of-sample test.
- **Primitive vs wrapper:** P1 primary (trend continuation). The filter is a low-lag replacement for a
  moving average, i.e. wrapper; long/short flip.
- **Claimed mechanism:** Lower lag and fewer whipsaws than moving averages (author's claim; no whipsaw count).
  No counterparty argument.
- **Published claim:** In-sample, one year, ES: net profit USD 18,755-39,558 per contract by model; Sharpe
  0.72-1.22 (model 3 best at 1.22).
- **Decay and crowding:** Not applicable; a single in-sample year.
- **Cost-floor note:** Daily bars with multi-day holds make 13 bp small against daily index moves; the flip
  rate is not reported, so the ratio cannot be stated.
- **Event rate (estimate):** Tens of flips a year.
- **Applies to / testable here:** Y for data, but the rule must be completed by us, which would make it our
  strategy, not the source's.
- **Regime hypothesis:** As any trend filter: wins in persistent trends, loses in ranges; lower lag buys
  earlier entries at the price of more noise flips.
- **Overlaps:** Moving-average and time-series-momentum cards (trend family); S-MOD-02 (same filter on a
  spread).

### S-MOD-04 Volatility-managed sizing (realised variance; GARCH variant)
- **Fidelity:** A. **Sources:** MM17 (full), COWY20 (full), FKO01 (recalled: GARCH-type conditional
  covariance forecasts used for volatility timing; no parameters recalled).
- **Rule:** Monthly: managed return = (c / sigma2_t) * f_{t+1}, sigma2_t = realised variance of the factor's
  daily returns over the previous month (~22 days; exact normalisation illegible in the copy read). c makes
  managed and unmanaged unconditional vol equal and is set on the FULL sample (in-sample). Factors: Mkt, SMB,
  HML, Mom (1926-2015), RMW, CMA, ROE, IA, FX carry, BAB. Robustness: AR(1) log-variance forecast instead of
  realised variance. Not ML; MM17 has no out-of-sample split. COWY20 runs it in real time: 10-year initial
  window, expanding, leverage cap 5, risk aversion 5.
- **Primitive vs wrapper:** P2 primary (variance forecasts variance), and the profit needs expected return
  NOT to rise in proportion to variance. Wrapper: inverse-variance scaling, monthly rebalance, leverage cap.
- **Claimed mechanism:** Variance is forecastable but weakly linked to future returns, so the price of risk
  falls when vol rises; alpha is proportional to -cov(mu/sigma2, sigma2). "Slow-moving investors" is offered
  as untested speculation. No counterparty named.
- **Published claim:** MM17: market alpha 4.86%/yr, Sharpe up ~25%; momentum alpha 12.5%; market alpha 3.98%
  after 10 bp; break-even cost ~56 bp; 2.12% with weights capped at 1. COWY20 (103 equity strategies): managed
  Sharpe higher in 53, lower in 50 (8 significant, mostly momentum); real-time combination beats unmanaged
  Sharpe in 45/103 and has lower certainty-equivalent return in 72/103.
- **Decay and crowding:** MM17 weaker in 1956-1985. COWY20: in-sample alphas do not survive real time
  because the spanning-regression parameters are unstable.
- **Cost-floor note:** Cost scales with the monthly change in weight, small against monthly moves at 13 bp.
  The binding limit is leverage (MM17 99th-percentile weight 6.4) and, on perps, funding on levered notional.
- **Event rate (estimate):** 12 rebalances a year; 2-4 independent vol shocks a year.
- **Applies to / testable here:** US equity factors and FX carry in the sources. Y: monthly realised
  variance from perp daily klines (BTC or an equal-weight coin index).
- **Regime hypothesis:** Works when vol spikes come with flat or negative drift and vol decays slowly. Fails
  when high-vol periods hold the best returns (manias, squeezes) and after V-shaped crashes it de-risks into.
- **Overlaps:** S-MOD-01 (binary version), vol targeting inside S-MOD-06 and S-MOD-11; vol-scaling wrappers
  across the trend family.

### S-MOD-05 Hurst-exponent switching between trend and reversion
- **Fidelity:** C (not mechanizable from the sources). **Sources:** CLS22 (full, student report), QR04 (full,
  forecasting only), L91 (recalled).
- **Rule:** CLS22: Hurst H per stock from the first half of 2021 (estimator and window not specified); H > 0.5
  -> momentum (SMA 5/10 crossover), H < 0.5 -> mean reversion (Bollinger 20, +/-2 sd; entry/exit "at the
  trader's discretion"); trade the second half of 2021; ~1,800 Nasdaq stocks > $2bn; no costs. QR04: R/S
  regression over t = 2^4..2^10 in 1,024-day windows of DJIA log returns (1930-2004); random-walk H averages
  0.5454 (sd 0.0485); periods with H > 0.65 vs 0.54-0.55 forecast by a small NN (60/20/20 chronological split);
  no trading. No published source gives a complete switching rule with costs.
- **Primitive vs wrapper:** P1 primary (H estimates the sign of serial dependence; the switch is P1
  conditioned on past P1). Wrapper: SMA cross, Bollinger band, the 0.5 threshold.
- **Claimed mechanism:** None beyond "trending vs mean-reverting series". QR04's own baseline shows a
  1,024-point random walk scores H ~ 0.545, so a 0.5 threshold labels noise as trending.
- **Published claim:** CLS22, H2 2021: mean return momentum 0.05%, mean reversion 1.92%, Hurst-selected in
  between (not better than both). QR04: NRMSE 0.9439 (H > 0.65) vs 0.9731 (control); error, not P&L.
- **Decay and crowding:** L91 (recalled): little long-term memory in US stock returns once short-range
  dependence is controlled (modified R/S).
- **Cost-floor note:** SMA 5/10 flips often on daily bars: 13 bp per flip against small per-trade drift. Band
  reversion targets ~2 sd of 20-day vol and clears 13 bp except on very quiet coins.
- **Event rate (estimate):** 1-2 regime labels a year per asset at half-year windows; under 1 a year at
  1,024-day windows.
- **Applies to / testable here:** US stocks and DJIA in the sources. Y: any kline series.
- **Regime hypothesis:** Needs dependence regimes that outlast the estimation window. H needs hundreds of
  points to separate from 0.545 by 2 sd, so regimes must last years on daily data; likely fails in crypto.
- **Overlaps:** S-MOD-06 and S-MOD-07 (other switches between trend and reversion), S-MOD-02.

### S-MOD-06 Changepoint detection + deep momentum network ("slow momentum, fast reversion")
- **Fidelity:** A. **Sources:** WRZ21 (full).
- **Rule:** 50 continuous futures (Pinnacle CLC: commodities, equities, rates, FX), daily. *CPD:* standardise
  returns over lookback l in {10, 21, 63, 126, 252}; fit a GP with a Matern-3/2 kernel and with a changepoint
  kernel; features severity = 1 - 1/(1 + exp(-(nlml_C - nlml_M))) and location = (c - (t - l))/l. *Model:*
  LSTM (sequence 63) -> tanh position in (-1, 1). Inputs: normalised returns at 1, 21, 63, 126, 252 days; MACD
  at (8,24), (16,28) [as read; ZZR20 uses long 48, so likely 48], (32,96); severity and location. *Target:*
  none; loss = -annualised Sharpe. Positions vol-scaled to 15% with 60-day EW vol. *Validation:* expanding
  window, retrain every 5 years (train 1990-95, test 1995-2000, ... to 2020), 90/10 train/val split, 50-trial
  random search, early stopping (patience 25). Walk-forward; not purged. *Costs:* main results gross;
  sensitivity 0-5 bp only. *Effective samples:* 5 test windows over 50 correlated futures; trend episodes
  not counted by the source.
- **Primitive vs wrapper:** P1 primary (slow trend plus fast reversal); P2 secondary (the changepoint score
  mostly flags a change in covariance). Wrapper: LSTM sizing, vol targeting.
- **Claimed mechanism:** Momentum loses at turning points; the CPD input lets the model cut or flip quickly
  after a break. 2015-2020 momentum weakness attributed to "factor crowding". No counterparty named.
- **Published claim:** 1995-2020, gross: Sharpe TSMOM 0.94, LSTM 1.62, LSTM+CPD 2.16. About +70% Sharpe for
  LBW 21 over 2015-2020 (no absolute figure). Beats classical strategies only up to ~2 bp cost.
- **Decay and crowding:** Source reports TSMOM weakness 2015-2020; no post-publication data.
- **Cost-floor note:** Source break-even ~2 bp a trade; our 13 bp is about 6x past its tested range. The
  gain is the high-turnover fast-reversion part; at our cost only the slow part (plain TSMOM) could survive.
- **Event rate (estimate):** A few changepoints per asset a year; positions change daily.
- **Applies to / testable here:** Futures in the source (partial: cached NQ/FX/gold). Y on perps; daily GP
  fits per coin are compute-heavy but feasible.
- **Regime hypothesis:** Helps where long trends have sharp, frequent reversals; fails at retail costs
  because the improvement is turnover.
- **Overlaps:** S-MOD-07 (same idea, no ML), S-MOD-11 (same lab and features, RL wrapper), S-MOD-05.

### S-MOD-07 Momentum turning points (fast/slow momentum states)
- **Fidelity:** B. **Sources:** AA23 (full, secondary); GHM23 not read.
- **Rule:** Slow signal = sign of the trailing 12-month return, fast = sign of the trailing 1-month return
  (AA23 gives these as examples). States: Bull (both up), Bear (both down), Correction and Rebound (signals
  disagree; Correction = slow up / fast down, Rebound = slow down / fast up: recalled, not re-fetched).
  Intermediate-speed strategies blend slow and fast; the dynamic version picks the blend by state (weighting
  rule not given in the source read). US market main sample plus 20 international equity markets, monthly.
  Sample period, costs and any out-of-sample test: not in the source read.
- **Primitive vs wrapper:** P1 primary (two horizons); P2 secondary (Correction and Bear states carry
  higher vol). Wrapper: the state machine and the blend weight.
- **Claimed mechanism:** Slow momentum wins in the long run because expected returns are persistent; fast
  momentum wins just after turning points. No counterparty named.
- **Published claim:** AA23: intermediate-speed blends "consistently outperform" pure slow and fast across
  countries; no numbers in the source read.
- **Decay and crowding:** Unknown.
- **Cost-floor note:** Monthly index signals, a few flips a year: 13 bp is negligible.
- **Event rate (estimate):** 12 decisions a year; 2-6 state changes. Across coins the state is market-wide:
  one sample.
- **Applies to / testable here:** Equity indices in the source. Y: BTC or coin index, monthly or weekly.
- **Regime hypothesis:** Works when turning points start sustained new trends; fails in chop, where the
  fast signal flips back and the blend whipsaws.
- **Overlaps:** S-MOD-06 (ML version), S-MOD-01 (state machine), time-series momentum cards.

### S-MOD-08 Tree and neural classifiers on lagged returns, daily cross-sectional stat-arb
- **Fidelity:** A. **Sources:** KDH17 (full WP), JKW22 (abstract; crypto analogue).
- **Rule:** *Target:* 1 if a stock's next-day return beats the cross-sectional median, else 0. *Features:* 31
  lagged simple returns (1-20 days, then 40, 60, ..., 240). *Universe:* S&P 500 month-end constituents
  (survivor-free), stocks with 750 days of history. *Training:* 750 days, then trade 250 days, roll by 250:
  23 non-overlapping batches (walk-forward; not purged, labels are 1 day). *Validation:* none; fixed
  hyperparameters (DNN 31-31-10-5-2 maxout/dropout; GBT 100 trees depth 3 lr 0.1; RF 1,000 trees depth 20;
  ENS = equal average). *Trade:* daily, long top k = 10 and short bottom 10 by probability, equal weight, hold
  1 day. *Costs:* 5 bp per share per half-turn, included. *Effective samples:* ~5,750 daily cross-sections,
  12/1992-10/2015 (date-clustered), ~1,450 of them after 2010 (estimate).
- **Primitive vs wrapper:** P3 primary (cross-sectional rank of lagged returns); P1 secondary (importance
  led by the last ~5 days, i.e. short-term reversal, then 12-month returns); P2 secondary (best in turmoil).
  Wrapper: k = 10 tails, 1-day hold, ensembling.
- **Claimed mechanism:** Models learn short-term reversal and momentum; mispricings appear in turmoil when
  attention shifts to the market as a whole. Decay blamed on the spread of ML methods and cheap compute.
- **Published claim:** k = 10, ENS daily mean 0.45% before and 0.25% after costs; Sharpe after costs ENS 1.81,
  RF 1.90. Sharpe ~6.7 in 1992-2001, ~0.51 in 2001-2008, ~4.5 in 2008-2009; 2010-2015 all models negative after
  costs (-14% to -25% a year), still positive before. JKW22 (abstract): LSTM/GRU long-short on the 100 largest
  coins, out-of-sample Sharpe 3.23 / 3.12 after costs vs 1.33 market; cost level not read.
- **Decay and crowding:** Strong: negative after costs from 2010.
- **Cost-floor note:** Both legs turn over daily: 26 bp a day at our cost (source: 4 x 5 = 20 bp). The
  predicted 1-day excess must clear that every day.
- **Event rate (estimate):** 252 cross-sections a year; the date is the independent unit.
- **Applies to / testable here:** US equities in the source. Y: daily klines of ~700 perps including delisted
  ones, funding on both legs.
- **Regime hypothesis:** Works in high-dispersion, high-vol, attention-shock periods; fails in calm eras and
  wherever the 1-day reversal premium is below the round trip.
- **Overlaps:** S-MOD-10 (monthly version), S-MOD-09 (single asset, intraday), short-term reversal cards.

### S-MOD-09 Minute-horizon bitcoin direction classifiers
- **Fidelity:** A. **Sources:** JDW21 (full).
- **Rule:** *Target:* 1 if the next-m-minute BTC return >= the training-set median m-minute return, m in
  {1, 5, 15, 60}. *Features:* BTC 1-minute lagged returns (120-step sequences for LSTM/GRU; 169 aggregated
  features otherwise) and a 1-week return; minute returns of MSCI World, S&P 500, VIX, gold, oil, EUR/CNY/JPY
  vs USD; blockchain transaction count and mempool growth; tweet count and two sentiment sums. *Data:*
  2019-03-11 to 2019-12-10, weekends dropped. *Models:* LR, RF, XGBoost (depth 1), LSTM, GRU, FNN, ensemble;
  10 seeds. *Validation:* one chronological split: ~5 months train, ~1 month validation, ~3 months test; not
  walk-forward, not purged. *Trade:* long if P(class 1) > the 99% quantile of training predictions, short if
  P(class 0) > its 99% quantile, exit at horizon end. *Costs:* 30 bp round trip, included. *Effective
  samples:* one asset, ~65 test days (estimate).
- **Primitive vs wrapper:** Unknown: the paper does not attribute. Inputs are mostly P1 (lagged returns) plus
  P9 cross-asset and sentiment. Wrapper: 99% confidence threshold, fixed-horizon exit.
- **Claimed mechanism:** None tested; cites equilibrium models; momentum left for future research.
- **Published claim:** Accuracy 50.9-56.0%, rising with horizon. Before costs, up to ~116% over the 3-month
  test (LSTM, 60 min) vs ~30% buy-and-hold; after 30 bp round trip, negative for every model.
- **Decay and crowding:** Not analysed.
- **Cost-floor note:** 1-60 minute holds. Our 13 bp is under half the source's 30 bp, but a 1-15 minute BTC
  move is typically a few bp (estimate), so the rule is sub-cost unless the threshold isolates rare large moves.
- **Event rate (estimate):** ~1% of windows trigger; ~250 date-independent days a year.
- **Applies to / testable here:** Partial: BTC 1m klines Y; cross-asset minute data only where cached (FX,
  gold, NQ); blockchain and tweet features N.
- **Regime hypothesis:** Anything real would sit in high-vol hours where the threshold fires; the cost floor
  binds regardless.
- **Overlaps:** S-MOD-08 (same design, daily cross-section), S-MOD-13 (sentiment inputs).

### S-MOD-10 Machine-learning return forecasts on firm characteristics (monthly cross-section)
- **Fidelity:** B (costs not addressed in the text read). **Sources:** GKX20 (full WP).
- **Rule:** *Target:* next-month individual stock excess return (regression). *Features:* 94 firm
  characteristics interacted with 8 macro predictors, plus 74 industry dummies: 920 inputs. *Universe:* CRSP
  NYSE/AMEX/NASDAQ, 1957-03 to 2016-12, ~30,000 stocks (>6,200 a month). *Training:* 1957-1974 (18 years),
  validation 1975-1986 (12 years), test 1987-2016 (30 years); refit annually, training expanding, validation
  rolling. Walk-forward; not purged (monthly labels, adjacent). *Models:* OLS, PLS, PCR, elastic net,
  group-lasso GLM, RF, GBRT, NN1-NN5. *Trade:* long the top decile, short the bottom decile of forecasts,
  monthly, value- or equal-weighted. *Costs:* not addressed. *Effective samples:* 360 monthly cross-sections.
- **Primitive vs wrapper:** P3 primary (the paper's top predictors are price trends: momentum, industry
  momentum, short-term reversal); P7 secondary (size, dollar volume, bid-ask spread); P2 secondary (return
  and idiosyncratic volatility, beta). Wrapper: decile tails, monthly rebalance, model choice.
- **Claimed mechanism:** Framed as better measurement of risk premia; nonlinear interactions add accuracy.
  No counterparty argument.
- **Published claim:** Monthly out-of-sample R2 peaks at 0.40% (NN3); full OLS -3.46%. Neural-net long-short
  decile Sharpe 1.35 value-weighted, 2.45 equal-weighted, vs 0.61 / 0.83 for OLS. S&P 500 timing Sharpe 0.77
  vs 0.51. Top 1,000 stocks R2 0.52-0.70%.
- **Decay and crowding:** Not reported in the text read.
- **Cost-floor note:** Reversal-driven tail names turn over almost fully each month: up to 26 bp a month per
  unit of gross. Equal-weighted (small-cap) results are the most exposed.
- **Event rate (estimate):** 12 cross-sections a year.
- **Applies to / testable here:** US equities in the source. Partial: crypto versions of the dominant inputs
  (momentum, reversal, dollar volume, volatility) Y on ~700 perps; accounting characteristics N.
- **Regime hypothesis:** Strongest where the cross-section is wide and thinly arbitraged (small caps, equal
  weight); in crypto that means illiquid alts, exactly where costs are highest.
- **Overlaps:** S-MOD-08 (daily version), cross-sectional momentum and reversal cards.

### S-MOD-11 Deep reinforcement learning on futures (DQN, policy gradient, A2C)
- **Fidelity:** B (no validation set described; test-time cost rate not stated in the main table).
  **Sources:** ZZR20 (full).
- **Rule:** 50 liquid continuous futures (Pinnacle CLC: commodities, equity indices, rates, FX), daily,
  2005-2019; test 2011-2019. *State:* last 60 observations of normalised close, returns over 1, 2, 3 and 12
  months scaled by 60-day EW vol, MACD, RSI(30). *Actions:* {-1, 0, 1} (DQN, PG) or [-1, 1] (A2C), positions
  vol-scaled to a target. *Reward:* additive P&L minus bp x traded value (bp = 20 bp in training); gamma 0.3.
  Two-layer LSTM (64, 32), one model per asset class. *Target:* none (reward maximisation). *Training:*
  retrain every 5 years on all prior data (expanding), frozen for the next 5. Walk-forward; no validation
  set described; not purged. *Costs:* included in training; sensitivity up to 25 bp. *Effective samples:* two
  model generations; trend positions held for weeks, so few independent bets per contract.
- **Primitive vs wrapper:** P1 primary, inferred (inputs and benchmarks are time-series momentum; the
  authors say the agent follows large trends and holds through consolidation; not tested). Wrapper: vol
  scaling, discrete action set, discount factor.
- **Claimed mechanism:** None named. Claims it handles mean-reverting markets (FX) better than TSMOM.
- **Published claim:** 2011-2019, portfolio vol-targeted, net of costs: Sharpe DQN 1.288, A2C 1.050, PG 0.754,
  sign of 12-month return 0.441, MACD 0.091, long-only 0.058. DQN and A2C still profitable at 25 bp. Long-only
  beats DQN on equity indices (0.688 vs 0.648).
- **Decay and crowding:** None reported.
- **Cost-floor note:** Trained at 20 bp per unit traded, above our 13 bp; persistent positions keep cost
  small against multi-week moves.
- **Event rate (estimate):** 5-20 trend bets per contract a year; far fewer across correlated contracts.
- **Applies to / testable here:** Futures in the source (partial: cached NQ/FX/gold). Y on perps.
- **Regime hypothesis:** As TSMOM: strong in long persistent trends, weak in chop; loses to long-only in
  steadily rising markets.
- **Overlaps:** S-MOD-06 (same group and inputs, Sharpe loss), S-MOD-07, time-series momentum cards.

### S-MOD-12 Large-language-model headline scoring (post-news drift)
- **Fidelity:** B (how several headlines per firm-day are combined is not specified). **Sources:** LT23 (full).
- **Rule:** Newswire and outlet headlines matched to RavenPack entities and timestamps; keep relevance 100,
  full articles and press releases, event-similarity days > 90; drop "stock-gain"/"stock-loss" categories and
  near-duplicates (similarity > 0.6, same firm-day). CRSP common stocks, 2021-10 to 2024-05 (after the
  model's training cutoff). Prompt: as a financial expert, answer YES / NO / UNKNOWN on line one on whether the
  headline is good or bad for the short-term price, then one sentence; temperature 0; score +1 / -1 / 0.
  *Trade:* news before 09:00 -> that day's open to close; after 16:00 -> next open to next close; equal-weight
  long and short legs (>= 2 firms each), daily. Zero-shot (no training window). *Costs:* mainly gross; 5 / 10
  / 20 bp round-trip sensitivity. *Effective samples:* ~650 trading days; 159,137 firm-headline-days.
- **Primitive vs wrapper:** P9 primary (proposed `P9-news`: unscheduled firm news read from text, followed by
  underreaction); P7 secondary (stronger in small, illiquid stocks). Wrapper: open-to-close window, equal
  weights.
- **Claimed mechanism:** Limited information-processing capacity -> underreaction; limits to arbitrage in
  small stocks; drift stronger for bad news. The other side is slow investors. Model in the paper.
- **Published claim:** Initial reaction (not tradable): ~90% portfolio-day hit rate. Drift (tradable):
  overnight hit 58%, 0.34% a day, pre-cost Sharpe 2.97; intraday 0.50%, Sharpe 2.63. Overnight long-short ~700%
  cumulative pre-cost, >300% at 5 bp, >100% at 10 bp, unprofitable at 20 bp. Short leg 26 bp a day vs long 8.
  Smaller and older models weaker (Sharpe 1.66, 1.26); dictionary-style tools mostly negative.
- **Decay and crowding:** Sharpe 6.54 (2021Q4), 3.68 (2022), 2.33 (2023), 1.22 (2024 Jan-May); the source
  calls this suggestive evidence of decay as LLM adoption rises.
- **Cost-floor note:** One-day hold, turnover ~190% a day (source). Our 13 bp lies between the source's 10 bp
  (profitable) and 20 bp (not).
- **Event rate (estimate):** ~60,000 firm-headline-days a year; ~250 date-independent days.
- **Applies to / testable here:** US stocks. N: needs timestamped company headlines (or a crypto news feed)
  and a model scoring pass; neither is in the archive.
- **Regime hypothesis:** Works where information is absorbed slowly (small caps, bad news, low attention);
  decays as machine reading spreads, already visible in-sample.
- **Overlaps:** S-MOD-13 (aggregate mood, failed); earnings-drift cards in the event family.

### S-MOD-13 Aggregate Twitter mood predicts the index (known failure)
- **Fidelity:** A (as a forecast; no trading rule published). **Sources:** BMZ11 (full), LP17 (abstract).
- **Rule:** 9.85M tweets containing "i feel" / "i am feeling" etc., 2008-02-28 to 2008-12-19. Daily mood:
  OpinionFinder positive/negative ratio and six GPOMS dimensions (incl. Calm; 964-term lexicon), z-scored in a
  k-day window described as "around" each date (if centred, it uses future days). *Target:* daily change in
  the DJIA close. Granger tests at lags 1-7. Forecaster: 5-layer self-organising fuzzy NN, inputs DJIA t-1..t-3
  plus Calm t-1..t-3 (delta 0.04, sigma 0.01). *Training:* 2008-02-28 to 2008-11-28; *test:* 2008-12-01 to
  12-19 = 15 weekdays; single split, no walk-forward. *Costs:* none (no trading). *Effective samples:* 15.
- **Primitive vs wrapper:** P9 primary (proposed `P9-news`, aggregate mood variant); P1 secondary (DJIA lags).
- **Claimed mechanism:** Public mood shifts drive investment decisions with a lag. No counterparty argument.
- **Published claim:** Direction accuracy 86.7% in the table (87.6% in the abstract) over 15 test days; MAPE
  1.83% vs 1.94% for the DJIA-only model. Calm significant at lags 2-5 (lag 3 p = 0.022).
- **Decay and crowding:** LP17: the p-value pattern does not replicate; the effect is significant in the
  original subsample but not when extended back into 2007 (consistent with data snooping); no out-of-sample
  forecasting power. The fund set up to trade it closed in early 2012.
- **Cost-floor note:** Not the issue: 13 bp against daily index moves; the signal is.
- **Event rate (estimate):** 252 days a year.
- **Applies to / testable here:** US index. N: no tweet archive or social-sentiment feed.
- **Regime hypothesis:** If anything, attention-driven crisis markets; the evidence says sample artefact.
- **Overlaps:** S-MOD-12 (firm-level news text; much stronger design).

### S-MOD-14 Genetic-programming rule discovery (index in/out rules)
- **Fidelity:** A. **Sources:** AK99 (full), NWD97 and NWU09 (recalled, not re-fetched).
- **Rule:** S&P 500 daily, 1928-1995; prices normalised by the 250-day MA. Rule trees from MA, rolling max/min,
  arithmetic, absolute difference, lag, if-then-else, and/or/not, comparisons, constants U(0, 2); Boolean root:
  True = in the index, False = in T-bills; no shorts. Population 500, <= 100 nodes, <= 10 levels; <= 50
  generations, stop after 25 without selection-period gain. Fitness = excess return over buy-and-hold in the
  training period, net of costs (0.25% one-way base; 0.1% and 0.5% tested). 5-year training, 2-year selection
  period (a rule is kept only if best on it), then out-of-sample to 1995; 10 start years (1929, 1934, ...,
  1974) x 10 trials. Walk-forward with a validation (selection) period; not purged. *Effective samples:* 10
  out-of-sample periods; 1-18 trades a year.
- **Primitive vs wrapper:** P1 primary (the source: rules "exploit positive low-order serial correlation"; a
  1-day signal delay cuts the in-minus-out return gap from ~7 to ~2 bp a day); P2 secondary (rules are in
  the market when vol is low). Wrapper: the tree's syntax, in/out switching.
- **Claimed mechanism:** Rules find low-vol, positive-return periods; reactions to volatility changes are
  offered as a hypothesis. No counterparty named.
- **Published claim:** Out-of-sample excess over buy-and-hold after costs: -2.1%/yr at 0.25% (negative in 9 of
  10 periods; 3.8 trades a year; in the market 57% of days); -1.0%/yr at 0.1% (6 of 10 negative; ~18 trades);
  -2.4%/yr at 0.5%. Rule composite vol 8.7% vs index 14.7%.
- **Decay and crowding:** Already negative. NWD97 (recalled) found GP rules profitable in FX; NWU09
  (recalled) reports those FX rule profits declined in later samples.
- **Cost-floor note:** At 6.5 bp a side (below the source's lowest 0.1%) cost shrinks, but the delay result
  says the information sits in the same close the rule trades on.
- **Event rate (estimate):** 1-18 trades a year per rule (source); a few regime calls a year.
- **Applies to / testable here:** US index (and FX) in the sources. Y on klines; every evolved rule counts as
  a trial.
- **Regime hypothesis:** Works only where index returns have positive low-order autocorrelation (thin or
  early markets); fails where they are close to iid.
- **Overlaps:** S-MOD-01 (in/out filter keyed on low vol), S-MOD-05, moving-average cards.

### S-MOD-15 Factor timing with factor valuation (book-to-market of principal components)
- **Fidelity:** B (costs not modelled). **Sources:** HKS20 (full WP), ACII17 (recalled).
- **Rule:** 50 anomaly long-short portfolios (decile 10 minus 1, value-weighted, NYSE breakpoints), monthly
  1974-01 to 2017-12; market-adjusted and rescaled with first-half betas and variances. PCA of anomaly
  returns on the first half; keep the market plus PC1-PC5. Predictor for each PC: its own log book-to-market
  (eigenvector-weighted anomaly book-to-market); market: aggregate book-to-market. Monthly OLS, one month
  ahead. *Validation:* split sample (fit on the first half, evaluate the second), no refit. *Portfolio:*
  w_t = Sigma^-1 E_t[Z_{t+1}] with a homoskedastic Sigma from residuals. *Costs:* not modelled. *Effective
  samples:* ~264 out-of-sample months of a very persistent predictor; independent valuation cycles far
  fewer (not stated).
- **Primitive vs wrapper:** P9 primary (proposed `P9-valuation`); P4 secondary (a yield-like valuation
  ratio as predictor). Wrapper: PCA, mean-variance weights.
- **Claimed mechanism:** Rational time-varying risk premia; absence of near-arbitrage forces predictability
  into the largest PCs. SDF variance higher in recessions but not tied to financial stress. Nobody loses: it
  is a risk-premium story.
- **Published claim:** Out-of-sample R2: market 1.0% (not significant), PC1 4.8%, PC4 3.5%. Sharpe in-sample /
  out-of-sample: static factor investing 1.27 / 0.76, factor timing 1.19 / 0.87; information ratio vs static
  0.42 out-of-sample.
- **Decay and crowding:** Not reported. ACII17 (recalled) argues value-spread timing of factors adds little
  beyond the extra value exposure it brings.
- **Cost-floor note:** Not modelled by the source. Timing turnover is low (slow predictor), but the 50
  underlying anomaly books carry their own turnover, uncounted.
- **Event rate (estimate):** 12 decisions a year; about 1 independent timing call a year.
- **Applies to / testable here:** US equities. N: needs book-to-market for each anomaly; coins have no book
  value. A crypto "valuation" of a long-short book (e.g. its funding or basis) would be a new idea.
- **Regime hypothesis:** Works when factor valuation spreads are wide and mean-revert within a few years;
  fails when spreads keep widening for years, and persistence leaves very few independent tests.
- **Overlaps:** Carry cards (yield as predictor), S-MOD-04 (timing on variance instead of valuation).

### S-MOD-16 Meta-labelling with triple-barrier labels (Lopez de Prado)
- **Fidelity:** B (method only; no real-market claim found). **Sources:** LdP18 (recalled), LdP17 (excerpts
  via secondary: confirms purging and alternative bars), WIKI (full, secondary).
- **Rule (recalled unless marked):** Sample events (the book's example uses a symmetric CUSUM filter). A
  primary model M1 sets the side (-1 / 0 / +1; WIKI). Triple-barrier label per event: upper and lower barriers
  at multiples of a rolling EWMA volatility, plus a vertical barrier at a maximum holding time; meta-label = 1
  if M1's side earned a positive return at the first barrier touched, else 0. A secondary binary classifier
  M2 predicts the meta-label from features (WIKI); bet size maps M2's probability to position size (WIKI).
  Training with sample weights by label uniqueness; validation by purged k-fold CV with an embargo (LdP17
  confirms purging training labels that overlap test labels in time). Barrier multiples, horizon, M1, M2 and
  features are user choices; no published defaults.
- **Primitive vs wrapper:** None of its own: a wrapper (filter plus sizing) that inherits M1's primitive. The
  triple barrier is exactly a stop, target and time stop.
- **Claimed mechanism:** Raise precision without losing recall by suppressing M1's false positives, and turn
  trading off in states where M1 fails. A statistical method; no market counterparty.
- **Published claim:** WIKI cites higher Sharpe and lower max drawdown on synthetic data and simulated
  environments (Joubert 2022; Meyer et al. 2023); no figures; no real-market claim read.
- **Decay and crowding:** Not applicable.
- **Cost-floor note:** Barriers narrower than a few times 13 bp make labelled "wins" that lose net; labels must
  be computed net of costs.
- **Event rate (estimate):** Inherits M1's; M2 can only lower it.
- **Applies to / testable here:** Y over any M1 on our klines. Its purged CV with embargo is the validation
  standard the other ML cards in this file should be judged against.
- **Regime hypothesis:** Helps only if M1's failure states are predictable from observable features (often
  the P2 vol state). If M1 has no edge, M2 cannot create one.
- **Overlaps:** S-MOD-01 and S-MOD-04 (regime filters as the simplest meta-model), S-MOD-08 (ensembles).

---

## Family notes

Sixteen cards hold about four primitives. P1 serial dependence at one or two horizons: 02, 03, 05, 06, 07,
11, 14. P2 volatility state, paying because returns do not rise with variance: 01, 04. P3 cross-sectional
lagged-return rank: 08, 10. P9: text news (12, 13) and factor valuation (15). The models mostly re-discover
reversal, momentum and vol state. 06, 07 and 11 are one trend idea in three wrappers; 01 and 04 are one
vol-state idea, binary and continuous; 08 and 10 are one cross-sectional idea, daily and monthly. The
primitive behind 09 is unknown. 03 and 05 are not mechanizable; 16 is a wrapper. Most ML gains are gross,
or break even below 13 bp.
