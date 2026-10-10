# Catalogue family: carry, basis and risk premia (being paid for holding something)

Family code `CARRY`. Compiled 2026-10-10. Outcome-blind: no repo result, ledger, verdict or data
cache was consulted. Every number under "Published claim" is the source's own figure for its own
market and era, not ours. Arithmetic in "Cost-floor note" and "Event rate" uses only the rule and
the source's published numbers.

Fidelity policy in this file. **A**: primary source read, and it states every rule parameter.
**B**: primary read only in part (abstract, summary or the authors' column), a rule parameter is left
unspecified, or the rules come from an issuer or third-party description. **C**: no published
mechanical rule found (folklore, or a regression only). "Read: full" means the full text of the
relevant sections was read. "Read: abstract" or "summary" means only that was read.

Cost reference (CATALOGUE.md §7): a perp round trip is 13 bp and spot is 0.10% a side, so one
cash-and-carry cycle (open and close, spot and perp legs) costs **33 bp**.

---

### S-CARRY-01 Perp funding cash-and-carry (long spot, short perpetual, always on)
- **Fidelity.** A.
- **Sources.** Christin, Routledge, Soska and Zetlin-Jones, "The Crypto Carry Trade", working paper, 1 Aug 2022, https://www.andrew.cmu.edu/user/azj/files/CarryTrade.v1.0.pdf (read: full text through an extraction tool; tables spot-checked). Borri, Liu, Tsyvinski and Wu, "Cryptocurrency as an Investable Asset Class: Coming of Age", arXiv:2510.14435, Oct 2025, https://arxiv.org/abs/2510.14435 (read: stylized fact 6, Section 3.6, in full; checked against the arXiv PDF by the chair: the 6.45 / 4.06 / negative-in-2025 sentences are there, data are Binance Bitcoin perpetuals Aug 2020-May 2025, and the paper itself labels the strategy 'crypto carry' / 'Tether carry trades').
- **Rule.** Hold +1 unit of spot and −1 unit of the same coin's perpetual on Binance (18 coins, each with a USDT-settled and a coin-settled perp; the coin-settled leg uses hedge ratio F/(1−r)). Collect or pay funding every 8 h and hold continuously: no entry filter, no exit. Return per 8 h = funding net of the risk-free rate (set to 0) + the change in basis. Data: spot and perp prices at funding times, and the funding rate.
- **Primitive vs wrapper.** Primary P4. Secondary P6: funding is the price of the demand for leverage. There is no wrapper; hedge ratio and settlement coin are implementation choices.
- **Claimed mechanism.** Longs pay for access to leverage. Binance funding is "0.01% per eight-hour period plus an adjustment", so the design builds in a positive baseline. Exchange margin, non-recourse liquidation and basis risk at exit limit arbitrage.
- **Tail risk paid for.** A margin call or auto-deleverage on the short perp in a squeeze; one venue failing while it holds both legs; the basis blowing out at exit; regimes of negative funding.
- **Published claim.** Christin et al., Binance, 2020-08-11 to 2022-06-20, BTC: USDT carry 21.84%/yr, sd 1.90%, Sharpe 11.47; coin carry 16.74%/yr, Sharpe 6.41; median funding 0.010% per 8 h (about 11%/yr). Across coins the USDT Sharpe runs from 11.47 (BTC) down to 1.15 (FIL). Borri et al.: BTC carry Sharpe 6.45 over 2020-2025.
- **Decay and crowding.** Christin et al.: after Binance cut maximum leverage from 125x to 50x (2021-07-23), BTC USDT carry fell from 33.03% to 10.22%/yr and ETH from 44.60% to 9.75%. Borri et al.: Sharpe fell to 4.06 from 2024 and turned negative in 2025; they link this to funding-harvesting products such as Ethena's synthetic dollar (about $14bn by Sep 2025).
- **Cost-floor note.** One cycle costs 33 bp. At the 0.01%/8 h baseline (3 bp/day) break-even is about 11 days held; at Christin's BTC mean (0.0194%/8 h) it is about 6 days. Re-hedging drift is not costed.
- **Event rate (estimate).** Funding accrues 1,095 times a year, but this is one strongly autocorrelated state: about 3-8 independent funding regimes a year.
- **Applies to / testable here.** Crypto perps. Partial: funding and perp klines are Y; the spot leg needs spot klines.
- **Regime hypothesis.** Pays most in leveraged bull phases (rising open interest, retail demand for longs) while arbitrage capital is scarce. Compresses when arbitrage capital arrives (lower leverage caps, ETF access, delta-neutral stablecoins). Turns negative in deleveraging bear phases.
- **Overlaps.** 02 (same trade with a threshold wrapper), 03 (dated-futures version), 04 and 05 (relative and cross-sectional versions), 06 (the same state read as a directional signal).

### S-CARRY-02 Perp no-arbitrage band ("random-maturity arbitrage")
- **Fidelity.** A.
- **Sources.** He, Manela, Ross and von Wachter, "Fundamentals of Perpetual Futures", arXiv:2212.06888 v5, Jun 2024, https://arxiv.org/abs/2212.06888 (read: full PDF).
- **Rule.** Hourly signal ρ ≈ κ(f − s) − (r − r′), with f and s the log perp and log spot prices, κ = 1095, r′ = 0, and r the Aave borrow rate when F > S (the Aave supply rate when F < S). Bands ρl = κ·ln(1−C) and ρu = κ·ln(1+C), where C is the round-trip percentage cost of both legs. If ρ > ρu, go long λ spot and short 1 perp; if ρ < ρl, go long the perp and short spot. Close when ρ first returns to 0. Universe: Binance BTC, ETH, BNB, DOGE and ADA, Jan-2020 to 2024-03-11, maker fees.
- **Primitive vs wrapper.** Primary P4. Secondary P1 (the spread mean-reverts) and P6. Wrapper: the cost-scaled entry band, the exit at zero, and a long-spot-only variant.
- **Claimed mechanism.** Funding is proportional to the gap, so any finite gap is eventually paid away. Gaps persist because of margin needs during the trade, thin liquidity and positive-feedback trading: past-return momentum explains the gap with R² above 50%. The source names Alameda on FTX as a counterparty example.
- **Tail risk paid for.** The gap widening before it closes (forced liquidation on margin), and venue insolvency: in Nov 2022, funding on FTX flipped opposite to funding at solvent exchanges.
- **Published claim.** Table 6, high-fee tier (spot 6.75 bp, futures 1.44 bp a side): BTC Sharpe 1.80, 6.38%/yr, maxDD −4.43%, active 20% of hours. Same tier for the other coins: ETH 2.55, BNB 4.84, DOGE 3.58, ADA 2.68. No-fee tier: BTC Sharpe 3.53. Mean absolute deviation 60-90%/yr.
- **Decay and crowding.** Deviations shrink by about 11% a year. The band opened less often in 2022, but trades were still profitable when it did.
- **Cost-floor note.** With our costs C = 33 bp, so ρu ≈ 1095 × ln(1.0033) ≈ 361% annualised: the perp must sit at least 33 bp above spot to open, about twice the source's high-fee band of 179%.
- **Event rate (estimate).** From the source's active share and average open-to-close time at the high-fee tier: BTC ≈ 0.20 × 8,760 / 135 h ≈ 13 openings a year, ETH ≈ 24. Openings co-move across coins, so about 10-20 date-independent episodes a year.
- **Applies to / testable here.** Crypto perps. Partial: needs spot klines and a borrow rate; perp and funding data are Y.
- **Regime hypothesis.** The band is hit in fast trending markets (momentum chasing) and under venue stress. A quiet, mature market rarely opens it at retail cost.
- **Overlaps.** 01 (always-on version), 03.

### S-CARRY-03 Dated-futures cash-and-carry (crypto basis)
- **Fidelity.** B. The authors' column and abstracts were read. The BIS PDF could not be retrieved, so the roll rules were not read.
- **Sources.** Schmeling, Schrimpf and Todorov, "Crypto Carry", BIS WP 1087 (2023), https://www.bis.org/publ/work1087.htm (read: landing-page summary); the same paper as CEPR DP20719 (Oct 2025), https://cepr.org/publications/dp20719 (read: abstract), and in Management Science, https://pubsonline.informs.org/doi/10.1287/mnsc.2024.05069 (read: abstract). VoxEU column "Crypto carry: market segmentation and price distortions in digital asset markets", https://cepr.org/voxeu/columns/crypto-carry-market-segmentation-and-price-distortions-digital-asset-markets (read: full).
- **Rule.** Carry = annualised (F − S)/S on 1-month and 3-month BTC and ETH futures (OKEx, with CME as the comparison venue). Trade: long spot, short the dated future, hold to expiry, then roll. Not specified in what was read: roll timing, contract choice, any carry threshold.
- **Primitive vs wrapper.** Primary P4, secondary P6. Wrapper: maturity choice and roll schedule.
- **Claimed mechanism.** Holding spot carries an "inconvenience yield", created by trend-chasing small traders ("nonreportables" in CFTC data) who demand leverage. Arbitrage capital is scarce: regulation keeps institutions out of spot, CME has no cross-margining, and positions are marked to market before they converge.
- **Tail risk paid for.** Margin spikes and forced liquidation of the short leg in rallies. At 10x leverage, the short leg would have been liquidated in "over half the months" of the sample.
- **Published claim.** OKEx, Mar-2019 to Jul-2024: carry averages about 7-8%/yr and sometimes exceeds 40% (the BIS summary says "up to 60% p.a." and an average "above 10%"). A 10% rise in standardised carry predicts a 22% rise in sell liquidations relative to open interest over the next month, and high carry predicts crashes. No strategy Sharpe ratio appears in what was read.
- **Decay and crowding.** The Jan-2024 spot ETF launch cut carry by about 3 pp on all exchanges (36% of the mean) and by a further 5 pp on CME. CME micro futures raised CME carry by about 11% (difference-in-differences).
- **Cost-floor note.** One cycle costs 33 bp. A 3-month contract at 7.5%/yr carry earns about 190 bp a quarter, so costs take about one sixth when rolled quarterly.
- **Event rate (estimate).** Four quarterly rolls a year; about 2-6 independent carry regimes a year.
- **Applies to / testable here.** Crypto dated futures (CME, OKEx, Binance quarterlies). Partial: needs delivery-futures and spot klines, which are not in the USDT-perp archive as described.
- **Regime hypothesis.** Carry is high in boom phases with leverage demand and compresses as institutions gain access. The trade loses only if it is forced out before convergence.
- **Overlaps.** 01 and 02 (perp versions), 06 (carry as a crash predictor), 11 (curve-slope analogue).

### S-CARRY-04 Relative funding: USDT-margined vs coin-margined perps, and across exchanges
- **Fidelity.** C. No published trading rule was found; the sources only document the inputs.
- **Sources.** Christin et al. 2022 (as in 01; read: full): Binance funding series for USDT-margined and coin-margined perps. He et al. 2024 (as in 02; read: full): FTX funding moved opposite to solvent exchanges in Nov 2022. Exchange and industry guides describe the trade but were not used as evidence.
- **Rule (folklore).** Short the perp with the higher funding and go long the same coin's perp with the lower funding (other margin type or other exchange), equal notional. Collect the funding difference; exit when the spread closes. Not specified: threshold, holding horizon, venue set.
- **Primitive vs wrapper.** Primary P4, secondary P6. Wrapper: the entry threshold on the spread and the exit on convergence.
- **Claimed mechanism.** Different clienteles pay different prices for leverage. Christin et al. tie the higher USDT-margined funding partly to margin mechanics: coin-margined longs face a higher probability of liquidation. Venue spreads persist because capital has to be split across venues.
- **Tail risk paid for.** A venue defaulting or freezing withdrawals (on FTX in 2022, the "cheap" side was the failing venue), and the convexity of the inverse contract on a coin-margined leg.
- **Published claim.** No strategy result. Inputs (Christin et al., BTC, 2020-08 to 2022-06): mean funding 0.0194% per 8 h on USDT-margined vs 0.0146% on coin-margined; medians 0.010% vs 0.000%.
- **Decay and crowding.** Not documented.
- **Cost-floor note.** Two perp legs cost 26 bp per cycle. At the mean gap (about 0.005% per 8 h, or 1.5 bp/day), break-even is about 18 days held.
- **Event rate (estimate).** 5-20 venue-divergence episodes a year.
- **Applies to / testable here.** Y for Binance vs Bybit USDT perps (both funding series are in the archive). Partial for the coin-margined leg.
- **Regime hypothesis.** Spreads widen under venue stress and in booms when one clientele crowds a venue. The widest spreads are the most likely to be default-risk premia, not free carry.
- **Overlaps.** 01, 05.

### S-CARRY-05 Cross-sectional perp funding carry (long low-funding, short high-funding perps)
- **Fidelity.** C. No primary source applies this to perps; the construction is borrowed from KMPV.
- **Sources.** Koijen, Moskowitz, Pedersen and Vrugt (KMPV), "Carry", NBER WP 19325 (Aug 2013; JFE 2018), https://www.nber.org/papers/w19325 (read: full), the source of the rank weights. Presto Research (J. H. Jung), "Can Funding Rate Predict Price Change?", 2 Aug 2024, https://www.prestolabs.io/research/can-funding-rate-predict-price-change (read: full).
- **Rule.** Carry of a short perp = expected funding received, annualised. Rank all perps and apply KMPV eq. 23, w = z·(rank(C) − (N+1)/2), with longs summing to 1 and shorts to −1: the portfolio is long the lowest-funding perps and short the highest-funding ones. Not specified for perps: rebalance frequency, universe, funding window. Presto's variant uses funding *changes*: `scale(indneutralize(decay_linear(funding,24) − decay_linear(funding,6)))` on the top 50 Binance USDT-M perps, 5-minute data, costs excluded.
- **Primitive vs wrapper.** Primary P4. Secondary P3 and P6. Wrapper: rebalance frequency and beta neutralisation.
- **Claimed mechanism.** High funding marks crowded leveraged longs. The short leg is paid to hold them and also bets that their price premium reverts. No source states who loses on perps.
- **Tail risk paid for.** A short squeeze in the high-funding (crowded) leg, and delistings.
- **Published claim.** None for the level-sorted rule. Presto, on funding *changes*: R² 12.5% with the same-week BTC price change, R² ≈ 0 for the next period. The cross-sectional alpha statistics are in an image and could not be extracted; the author calls its turnover "extremely high".
- **Decay and crowding.** Not applicable.
- **Cost-floor note.** Full turnover on both legs costs 26 bp per rebalance: about 3.1%/yr monthly, 13.5%/yr weekly. Monthly rebalancing therefore needs a long-minus-short funding spread of at least ~0.3 bp per 8 h.
- **Event rate (estimate).** 12-52 rebalances a year; about 12 independent.
- **Applies to / testable here.** Y (funding and klines for ~700 perps).
- **Regime hypothesis.** Works when funding dispersion is wide (alt seasons, listing waves) and squeezes are rare. Fails in short-squeeze rallies of crowded names.
- **Overlaps.** 01 (single-asset version), 07 (cross-sectional crypto carry), and the same KMPV construction in other markets: 08, 11, 12.

### S-CARRY-06 Funding-rate contrarian (fade extreme funding)
- **Fidelity.** C. Only regressions and summaries were found; no published rule has parameters.
- **Sources.** Fulgur Ventures (M. Lescrauwaet), "Bitcoin funding rates and price predictability", 29 Mar 2021, https://medium.com/@fulgur.ventures/bitcoin-funding-rates-and-price-predictability-27ce95535af1 (read: full). Presto Research 2024 (as in 05; read: full). Schmeling et al. (as in 03; read: summary and column).
- **Rule (as described).** Fulgur: a BTC perp position sized −k × standardised funding at t, held for 8 h; the article describes this "mean-reversion scaling strategy" in prose and does not backtest it. Folklore variant: short above a funding percentile, long at negative extremes. Not specified: k, the standardisation window, thresholds.
- **Primitive vs wrapper.** Primary P6. Secondary P4 and P1. Wrapper: thresholds, holding period, any stop.
- **Claimed mechanism.** Extreme positive funding marks crowded leveraged longs whose liquidation causes the crash; Schmeling et al. find that high carry predicts crashes and liquidations. Against the contrarian reading, He et al. find that past-return momentum explains more than 50% of the perp-spot gap, so funding is partly lagged momentum.
- **Tail risk.** Trend continuation: in strong rallies funding stays extreme and the contrarian is short the trend.
- **Published claim.** Fulgur, BitMEX XBTUSD from 14 May 2016: regressing 8-h returns on funding gives β = −0.087 (p = 0.008), R² = 0.003. Presto: next-period R² ≈ 0 for BTC. Schmeling et al.: a 10% rise in standardised carry precedes a 22% rise in sell liquidations over the next month.
- **Decay and crowding.** Not documented.
- **Cost-floor note.** Each 8-h trade must clear 13 bp, and flipping every period costs up to 39 bp/day. At R² 0.003, the published 8-h effect has to be held over far longer horizons to matter.
- **Event rate (estimate).** About 10-30 market-wide extremes a year. Coin-level extremes cluster on the same dates.
- **Applies to / testable here.** Y (funding and klines, with open interest available as confirmation).
- **Regime hypothesis.** Works at the end of leveraged booms (open interest peaks, funding spikes, then a liquidation cascade). Fails in persistent trends where funding stays high for weeks.
- **Overlaps.** 01-03 (the same state read as carry rather than as a signal), 05.

### S-CARRY-07 Staking-yield carry (cross-section of proof-of-stake tokens)
- **Fidelity.** B. The primary source was read in full for the strategy section, but the cut-off x% is not specified.
- **Sources.** Cong, He and Tang, "Staking, Token Pricing, and Crypto Carry", ABFER 2023 version, https://www.abfer.org/media/abfer-events-2023/annual-conference/papers-investment/AC23P3055-Staking-Token-Pricing-and-Crypto-Carry.pdf (read: full §6, with the June 2022 version's abstract).
- **Rule.** Universe: 60 stakable tokens (35 proof-of-stake base layers, 25 DeFi) from stakingrewards.com, Jul-2018 to Feb-2022, weekly data. Each week, rank tokens by their staking reward rate in the previous period. Long the top x% equal-weighted and stake them; short the bottom x% equal-weighted and pay their reward rate. Rebalance weekly and exclude projects launched within the past week. x is not specified (the authors say it "does not affect" the result). Variants: no staking, monthly rebalance, long-only top 50%.
- **Primitive vs wrapper.** Primary P4, secondary P3. Wrapper: x% and rebalance frequency.
- **Claimed mechanism.** The reward pays stakers for lock-up, slashing and lost transaction convenience. Uncovered interest parity fails: carry predicts excess returns "almost one-for-one" in the cross-section. A high reward attracts staking, which persists and dilutes the future reward.
- **Tail risk paid for.** Lock-up (no exit in a crash), slashing, inflationary dilution, token collapse (Terra is in the universe), and the borrow the short leg needs on small tokens.
- **Published claim.** Table 7, weekly trade with staking: annual mean 0.658 and sd 0.411 (units as printed), skew 1.41, max drawdown 29.97%, Sharpe 1.60. Without the staking yield: Sharpe 1.28. Monthly rebalance: 0.79. Equal-weighted all tokens: Sharpe 0.20, max drawdown 92.9%. The text describes negative skewness, but the table prints +1.41.
- **Decay and crowding.** Sharpe falls from 1.60 (weekly) to 0.79 (monthly), which the source blames on reward dilution. There is no out-of-sample period.
- **Cost-floor note.** Full weekly turnover on spot costs 40 bp/week (about 21%/yr) in the worst case, against average rewards of 8% value-weighted and 15% equal-weighted per year (about 15-29 bp/week). Borrow costs are excluded.
- **Event rate (estimate).** 52 rebalances a year; about 12-26 independent.
- **Applies to / testable here.** Crypto spot. N: needs reward-rate history (perps can proxy the price leg).
- **Regime hypothesis.** Works in calm or rising markets with stable reward schedules. Fails in crashes (lock-ups, slashing, collapses).
- **Overlaps.** 05 (cross-sectional crypto carry), 01 (yield for holding spot), 08.

### S-CARRY-08 FX carry, high-minus-low portfolios (HML_FX)
- **Fidelity.** A.
- **Sources.** Lustig, Roussanov and Verdelhan, "Common Risk Factors in Currency Markets", RFS 24(11), 2011, https://www.johnhcochrane.com/s/Lustig_Roussanov_Verdelhan_common_risk_currency.pdf (read: full, published version). Brunnermeier, Nagel and Pedersen, "Carry Trades and Currency Crashes", NBER WP 14473, 2008, https://www.nber.org/papers/w14473 (read: abstract).
- **Rule.** At the end of each month, sort all currencies (9 in 1983, 26 in 2009, at most 34) into six portfolios by the 1-month forward discount f − s. Equal weights within each portfolio; hold one month through forwards. Long portfolio 6 (highest rates), short portfolio 1 (lowest rates). Net returns use bid and ask quotes, with the investor short portfolio 1 and long the rest. Data: Barclays and Reuters, Nov-1983 to Dec-2009.
- **Primitive vs wrapper.** Primary P4, secondary P3. Wrapper: number of portfolios and the developed-only subsample.
- **Claimed mechanism.** High-rate currencies load on a global "slope" factor tied to global equity volatility, so the trade "loads up on global risk". Brunnermeier et al.: crash risk comes from sudden unwinds when funding liquidity and risk appetite fall.
- **Tail risk paid for.** Negatively skewed crashes in which high-rate currencies fall together.
- **Published claim.** 1983-2009: net high-minus-low spread 454 bp/yr, Sharpe 0.50 after bid-ask (developed currencies only: 0.32). Currencies switch portfolios roughly every 3 months. Second-half sample: sorting on current rates gives Sharpe 0.70, against 0.23 for sorting on first-half average rates.
- **Decay and crowding.** Lustig et al. 2014 (card 10) report high-minus-low returns net of costs of about 3%/yr (developed) and 4.4%/yr (all) through 2010. Burnside et al.'s carry index fell 10.7% between Jul-2008 and Feb-2009.
- **Cost-floor note.** The published figure is already net of forward bid-ask. 454 bp/yr is about 38 bp/month, roughly 3× a 13 bp round trip at full monthly turnover.
- **Event rate (estimate).** 12 rebalances a year with persistent holdings; about 4-12 independent.
- **Applies to / testable here.** FX forwards. N: needs forward points or short rates for 20-30 currencies.
- **Regime hypothesis.** Works when volatility is low, risk appetite is high and funding is ample. Crashes when global equity volatility spikes.
- **Overlaps.** 09 and 10 (same premium, different wrappers); 05, 11, 12 and 13 (the same sort construction).

### S-CARRY-09 FX carry: equal-weighted bet per currency, unhedged and hedged with ATM options
- **Fidelity.** A.
- **Sources.** Burnside, Eichenbaum, Kleshchelski and Rebelo, "Do Peso Problems Explain the Returns to the Carry Trade?", NBER WP 14054 (revised Sep 2010; RFS 2011), https://www.nber.org/papers/w14054 (read: full).
- **Rule.** Each month, for each currency against the home currency (USD or GBP), sell it forward if it is at a forward premium and buy it forward if it is at a discount. With costs, trade only if the bid/ask forward-vs-spot condition holds, otherwise hold no position. Stake 1/n_t per currency and hold one month, non-overlapping. Hedged version: buy a 1-month near-ATM CME option on each leg (a call when short the currency, a put when long). Data: Jan-1976 to Jul-2009 for spot and forwards; Feb-1987 to Apr-2009 for options.
- **Primitive vs wrapper.** Primary P4. Wrapper: the option hedge, which buys back the crash tail, and the cost filter.
- **Claimed mechanism.** A "peso problem": the premium pays for a rare state in which the stochastic discount factor is very high, not for very large carry losses. The hedge removes most of the left tail yet keeps about half the payoff.
- **Tail risk paid for.** That rare high-discount-factor state.
- **Published claim.** Equal-weighted carry Sharpe: GBP base 0.748 before costs and 0.507 after bid-ask; USD base 0.865 / 0.694. CME sample, 1987-2009: unhedged 2.96%/yr (Sharpe 0.476), hedged 1.58%/yr (Sharpe 0.449). The hedged return falls to 1.21% after paying half the average option bid-ask, which is 5.2% of the option price.
- **Decay and crowding.** Ending the sample in Jul-2008 instead of Apr-2009 gives Sharpe 0.586 unhedged and 0.530 hedged, against 0.476 and 0.449. The carry index fell 10.7% from Jul-2008 to Feb-2009, while US stocks fell 51.6% from their Oct-2007 peak. In contrast, Lustig et al. 2014 find a similar per-currency strategy "barely breaks even" net of costs over 1983-2010.
- **Cost-floor note.** ATM insurance costs 2.96 − 1.58 = 1.38%/yr, about half the premium (computed from the source's figures).
- **Event rate (estimate).** About 12 date-independent events a year.
- **Applies to / testable here.** FX. N: needs forwards and FX options.
- **Regime hypothesis.** As card 08. The hedged version should survive crash regimes at about half the carry.
- **Overlaps.** 08, 10. The option leg buys the premium that cards 14-16 sell.

### S-CARRY-10 Dollar carry (time series: short USD vs a basket when the average foreign rate exceeds the US rate)
- **Fidelity.** A.
- **Sources.** Lustig, Roussanov and Verdelhan, "Countercyclical Currency Risk Premia", NBER WP 16427 (Sep 2010, revised Feb 2013; JFE 2014), https://www.nber.org/papers/w16427 (read: full).
- **Rule.** Each month, compute the average forward discount (AFD) of developed-country currencies against USD. If AFD > 0, go long an equal-weighted basket of all foreign currencies against USD; otherwise short it. Returns are net of forward bid-ask. Sample: Nov-1983 to Jun-2010, with a developed basket and an all-currency basket.
- **Primitive vs wrapper.** Primary P4. Secondary P9, a macro-cycle state: the sign tracks the US business cycle. No wrapper.
- **Claimed mechanism.** The US price of risk is counter-cyclical. The trade is short the dollar during and after US recessions, when US rates are low, and is paid for the risk of the dollar appreciating in bad times.
- **Tail risk paid for.** A dollar spike in a global crisis while short USD.
- **Published claim.** Net returns: 5.60%/yr for the developed basket (Sharpe 0.66) and 4.28%/yr for all currencies (Sharpe 0.56). Skew −0.27, against −0.98 for high-minus-low carry. A 100 bp rise in AFD adds 245 bp to the expected excess return, and R² reaches 25% at one year together with US industrial production.
- **Decay and crowding.** Not checked in this pass.
- **Cost-floor note.** The position flips at business-cycle frequency, so turnover is near zero. The average return is about 47 bp/month.
- **Event rate (estimate).** About one independent state per US cycle, at most one a year, so the evidence rests on few events.
- **Applies to / testable here.** FX. N: needs short rates.
- **Regime hypothesis.** Pays during and after US recessions. Fails if the dollar rallies in a US-led crisis while the trade is short USD.
- **Overlaps.** 08, 09; the KMPV timing variant (cards 12-13).

### S-CARRY-11 Commodity basis (backwardation) sort
- **Fidelity.** A.
- **Sources.** Gorton, Hayashi and Rouwenhorst, "The Fundamentals of Commodity Futures Returns", NBER WP 13249 (2007; Review of Finance 2013), https://www.nber.org/papers/w13249 (read: full). Gorton and Rouwenhorst, "Facts and Fantasies about Commodity Futures", NBER WP 10595 (2006), https://www.nber.org/papers/w10595 (read: abstract and index method). KMPV 2013 (read: full).
- **Rule.** Basis = (F1/F2 − 1) × 365 / (D2 − D1), from the nearest (F1) and next-nearest (F2) contracts, with D the days to the last trading date. At each month end, split the commodities (31-33, 1969-2006; gold, silver and electricity excluded) into halves by basis, equal weights. Hold the nearest contract that does not expire within the next month, rebalance monthly, and go long the high-basis half (backwardated) and short the low-basis half (contango). KMPV variant: carry = (F1 − F2)/(F2·(T2 − T1)), rank-weighted, 24 commodities, 1980-2012.
- **Primitive vs wrapper.** Primary P4. Secondary P3 and P1: high-basis names have high prior 12-month returns (t = 12.93). Wrapper: halves versus rank weights.
- **Claimed mechanism.** Theory of storage: low inventories mean a high convenience yield, backwardation and a premium for stock-out risk. The source rejects hedging pressure as the main driver. Gorton and Rouwenhorst: "rolling itself is not a source of return".
- **Tail risk paid for.** Supply shocks reversing (backwardation collapses as inventories rebuild), and higher volatility in high-basis names.
- **Published claim.** Gorton et al., 1969-2006: high basis beat the equal-weighted index by 5.42%/yr (t 3.98) and low basis lagged it by 4.82%. High-minus-low 10.23%/yr (t 3.73), positive in 58% of months. Equal-weighted long-only index: 5.48%/yr. KMPV: commodity carry 11.22%/yr, Sharpe 0.60, skew −0.40.
- **Decay and crowding.** Not checked; the samples end in 2006 and 2012.
- **Cost-floor note.** About 85 bp/month from high-minus-low.
- **Event rate (estimate).** 12 rebalances a year; inventories are persistent, so about 4-12 independent.
- **Applies to / testable here.** Commodity futures. N: needs futures curves. The crypto analogue is card 03.
- **Regime hypothesis.** Works when inventories are tight in some commodities and loose in others. Fails in synchronised gluts or demand crashes.
- **Overlaps.** 12, 13, 03, 08.

### S-CARRY-12 Global equity index carry (futures-implied dividend yield)
- **Fidelity.** A.
- **Sources.** KMPV, "Carry", NBER WP 19325 (Aug 2013; JFE 2018), https://www.nber.org/papers/w19325 (read: full).
- **Rule.** Universe: futures on 13 indices (S&P 500, TSE 60, FTSE 100, CAC, DAX, IBEX, FTSE MIB, AEX, OMX, SMI, Nikkei, Hang Seng, ASX 200). Each month compute C = (S − F)/F on a synthetic 1-month future interpolated from the two nearest contracts; C is approximately the expected dividend yield minus the local risk-free rate. Weights w = z·(rank(C) − (N+1)/2); trade the most active contract and hold one month. Variants: carry1-12, the 12-month average carry, which removes dividend seasonality; and a timing version that is long if C > 0 and short if C < 0.
- **Primitive vs wrapper.** Primary P4, secondary P3. Wrapper: rank weights and the smoothing variant.
- **Claimed mechanism.** Carry is a forward-looking dividend yield. It is correlated with value but not explained by value, momentum or time-series momentum.
- **Tail risk paid for.** Global recessions. The worst drawdowns of the global carry factor were Aug-1972 to Sep-1975, Mar-1980 to Jun-1982 and Aug-2008 to Feb-2009.
- **Published claim.** Through Sep-2012: equity carry 9.14%/yr, sd 10.42, skew 0.22, Sharpe 0.88, against 0.32 for passive equal weights. The carry factor across all nine asset classes has a Sharpe ratio of 1.10.
- **Decay and crowding.** Not checked in this pass.
- **Cost-floor note.** About 76 bp/month on average.
- **Event rate (estimate).** 12 rebalances a year. "Current carry" picks countries in dividend season, so about 4-12 independent.
- **Applies to / testable here.** N: needs equity index futures and spot.
- **Regime hypothesis.** Works in expansions. Carry in every asset class fails together in global recessions.
- **Overlaps.** 11, 13, 08, 07.

### S-CARRY-13 Global bond carry (level, and the 10y−2y slope)
- **Fidelity.** A.
- **Sources.** KMPV, as in 12 (read: full).
- **Rule.** Level: for 10 government bond markets, the carry of a synthetic 1-month future on a 10-year zero is C = [1/(1+y_9y11m)^(9+11/12)] / [(1+rf)/(1+y_10y)^10] − 1, approximately (y10 − rf) − Dmod·(y10 − y9y11m), that is, term spread plus roll-down. Rank-weight as in card 12 and hold one month. Slope: in each country, long 10y and short 2y, with carry C10 − C2. US Treasury variant: CRSP maturity buckets from 1 to 120 months, 1971-2012.
- **Primitive vs wrapper.** Primary P4, secondary P3. Wrapper: level versus slope.
- **Claimed mechanism.** Term premium plus roll-down. Carry has a 0.90 correlation with the 10y−3m spread, and portfolios built on either are 0.91 correlated.
- **Tail risk paid for.** Curve shocks in high-carry markets, which cluster with recessions as in card 12.
- **Published claim.** Level carry 3.85%/yr, Sharpe 0.52; passive equal weights score 0.74, so carry does not beat passive here. Slope carry 3.77%/yr, Sharpe 0.66 (passive 0.71). US Treasuries: 0.46%/yr, Sharpe 0.68.
- **Decay and crowding.** Not checked in this pass.
- **Cost-floor note.** About 32 bp/month. A 13 bp round trip at full monthly turnover would take about 40% of it.
- **Event rate (estimate).** 12 rebalances a year; yields are very persistent, so about 2-6 independent.
- **Applies to / testable here.** N.
- **Regime hypothesis.** Works when rates are stable or falling. Fails in global rate shocks.
- **Overlaps.** 12, 11, 08, 10.

### S-CARRY-14 Index option writing: cash-secured put-write (PUT) and covered call (BXM)
- **Fidelity.** B. The rules come from issuer and third-party descriptions; neither index rulebook nor Whaley (2002) was read.
- **Sources.** Nasdaq information circular for the WisdomTree CBOE S&P 500 PutWrite Strategy Fund, 24 Feb 2016, https://m.nasdaqtrader.com/content/newsalerts/2016/infocircular/PUTWcircular.pdf (read: full). Callan Associates, "An Historical Evaluation of the CBOE S&P 500 BuyWrite Index Strategy", Oct 2006 (CBOE-financed), https://cdn.cboe.com/resources/education/research_publications/Callan_CBOE.pdf (read: full). S. Solaka, Cboe Insights, 6 Oct 2023, https://www.cboe.com/insights/posts/generating-income-and-managing-risk-cash-secured-put-writing-in-a-low-equity-return-environment (read: full). Israelov, "Covered Calls Uncovered", FAJ 2015, https://www.aqr.com/Insights/Research/Journal-Article/Covered-Calls-Uncovered (read: summary page).
- **Rule.** PUT: on the third Friday of each month, sell 1-month ATM SPX puts (European, struck "at or very near" the index) and hold to expiry, collateralised by T-bills sized to the maximum settlement loss (3-month bills in Mar/Jun/Sep/Dec, 1-month bills otherwise). BXM: hold the S&P 500 and sell a 1-month ATM call on the third Friday; hold to expiry, then roll. Not read: the strike tie-break and the roll-pricing window.
- **Primitive vs wrapper.** Primary P4, secondary P2. Wrapper: ATM strike, 1-month tenor, collateral. Israelov splits a covered call into passive equity, short volatility, and an uncompensated active-equity component that behaves like reversal; hedging that component keeps the premium with less risk.
- **Claimed mechanism.** Option buyers seeking insurance pay implied volatility above what is later realised.
- **Tail risk paid for.** Crashes, which hit the short put and the short gamma. BXM also gives up upside in strong rallies.
- **Published claim.** BXM, Jun-1988 to Aug-2006: 11.77%/yr vs 11.67% for the S&P 500; sd 9.29% vs 13.89%; Sharpe 0.77 vs 0.51; max drawdown −32.5% vs −47.4%; average monthly call premium 1.64%. PUT, Jul-1986 to Aug-2023: 9.40%/yr vs 9.91%; sd 10.26% vs 15.38%; max drawdown −32.66% vs −50.96%.
- **Decay and crowding.** BXM lagged in most rising markets. Over 1986-2023, PUT no longer beats the S&P 500 on return but keeps the lower risk. VIX minus 30-day realised volatility has averaged 3.33 points since 2013.
- **Cost-floor note.** The monthly premium is about 164 bp gross. Option spreads are quoted as a percentage of the option price (5.2% for the FX options in card 09), so the true cost depends on the venue.
- **Event rate (estimate).** 12 a year.
- **Applies to / testable here.** N: needs options data. The crypto analogue is card 16.
- **Regime hypothesis.** Pays in calm markets after a shock, while implied volatility is still high. Loses in crashes and lags in strong bull runs.
- **Overlaps.** 15, 16, and 09 (the hedge there buys what this card sells).

### S-CARRY-15 Short variance (variance swap or zero-beta straddle): the variance risk premium
- **Fidelity.** B. The paper gives an exact replication but measures a premium; the trading wrapper is implied rather than published.
- **Sources.** Carr and Wu, "Variance Risk Premia", working paper, May 2004 (RFS 2009), https://engineering.nyu.edu/sites/default/files/2019-01/CarrReviewofFinStudiesMarch2009-a.pdf (read: full; the hosted file is the 2004 draft). Coval and Shumway, "Expected Option Returns", JF 56(3), 2001, DOI 10.1111/0022-1082.00352 (read: abstract).
- **Rule.** Synthesise the 30-day variance swap rate SW from a strip of options, interpolating between the two nearest maturities without extrapolating. Short the swap: receive SW − RV at 30 days, where RV is the annualised realised variance of daily returns (equivalently, sell the option strip and delta-hedge with futures). Universe: SPX, OEX, DJX, NDX, QQQ and 35 stocks, 1996 to Feb-2003. Coval and Shumway use zero-beta ATM straddles; their sizing and hedging were not read.
- **Primitive vs wrapper.** Primary P4, secondary P2. Wrapper: the tenor only.
- **Claimed mechanism.** Buyers of variance pay to hedge upward variance moves. CAPM beta and the Fama-French factors explain only a small part of the premium, so either the market is inefficient or this is a separate, heavily priced variance factor.
- **Tail risk paid for.** Variance spikes; the loss on a short variance position is convex.
- **Published claim.** SPX: mean 100·(RV − SW) = −2.279, mean ln(RV/SW) = −0.594 (t −9.48). OEX −0.509 and DJX −0.525 in logs; Nasdaq-100 is weaker; 21 of 35 stocks are significantly negative in logs. Coval and Shumway: zero-beta ATM straddles lose about 3% a week.
- **Decay and crowding.** Not checked in this pass. Recalled, not re-fetched: the collapse of short-VIX products in Feb-2018, an instance of this tail.
- **Cost-floor note.** A premium of about 0.59 log points per 30 days dwarfs 13 bp, but the option strip costs several percent of option value in spreads.
- **Event rate (estimate).** 12 non-overlapping a year.
- **Applies to / testable here.** N for index options. Card 16 is the partial crypto analogue.
- **Regime hypothesis.** Works when implied volatility sits above later realised volatility, typically in post-shock calm. Fails at volatility regime breaks.
- **Overlaps.** 14, 16. KMPV's index-option carry: puts Sharpe 1.80, calls 0.37 (their Table II).

### S-CARRY-16 Bitcoin covered call (harvesting the crypto volatility risk premium)
- **Fidelity.** A. The rules are exact, but the source is an industry research note, not peer-reviewed.
- **Sources.** D. Lawant (Anchorage Digital), "Synthetic Yield on Bitcoin: Implementation, Discipline, and Performance Boundaries of Systematic Covered Call Writing", 28 May 2026, https://www.anchorage.com/research/synthetic-yield-on-bitcoin-implementation-discipline-and-performance-boundaries-of-systematic-covered-call-writing (read: full). Almeida, Grith, Miftachov and Wang, "Risk Premia in the Bitcoin Market", arXiv:2410.15195, https://arxiv.org/abs/2410.15195 (read: full). Alexander and Imeraj, "The Bitcoin VIX and its Variance Risk Premium", J. Alternative Investments, https://sro.sussex.ac.uk/id/eprint/91094/ (read: abstract).
- **Rule.** Baseline: hold BTC and sell a ~20-delta, 30-day call; hold to expiry and repeat, priced off the Deribit IV surface with Black-76, r = 0 and 1 vol point of slippage. Filtered version: enter only when the 10/30/50-day SMAs are not stacked in a bull trend and 30-day IV at the target delta is above its 90-day average; exit at 75% premium decay, at a delta stop (example given: 0.45), or 2 days before expiry. Hourly data, Oct-2021 to Apr-2026.
- **Primitive vs wrapper.** Primary P4, secondary P2. Wrapper: the trend filter (P1), the IV filter, the take-profit and the delta stop.
- **Claimed mechanism.** BTC's upside call IV exceeds later realised upside volatility by roughly two to three times what SPY and QQQ show. Almeida et al.: the 1-month BTC variance premium (σ²Q − σ²P) averages 14% on Deribit 2017-2022; it is larger in low-volatility regimes and comes mostly from large positive returns.
- **Tail risk paid for.** Violent bull runs that overrun the short calls: the premium pays for right-tail risk, not crash risk.
- **Published claim.** Unfiltered, full period: −0.5% net (−0.1%/yr), profit factor 1.00, 70 trades. Last year (Apr-2025 to Apr-2026): +5.5% overlay while BTC fell 19.4%. Filtered, full period: +23.7% (5.2%/yr), blended Sharpe 0.30 against 0.20 for spot. Rolling 3-year windows: median 4-6%/yr.
- **Decay and crowding.** The premium has had negative excursions, most prominently in Jan-2026.
- **Cost-floor note.** The overlay's 4-6%/yr is about 33-50 bp/month, after the source's 1-vol-point slippage.
- **Event rate (estimate).** 12-15 a year (70 trades in about 4.6 years).
- **Applies to / testable here.** Crypto options. Partial: the trend and realised-volatility inputs are Y from klines; implied volatility is N (needs Deribit IV history).
- **Regime hypothesis.** Pays in range-bound or falling BTC markets. Loses in strong bull trends.
- **Overlaps.** 14, 15, and 06 (both read crowded demand for upside).

---

## Family notes

The 16 cards hold about **three distinct primitives**. (1) Leverage-demand carry: cards 01-06 are
one state, perp or futures premium over spot, in six wrappers: always on, cost band, dated basis,
relative venue or margin type, cross-sectional, and contrarian (06 reads the state as P6). Card 07
(staking yield) is a separate yield. (2) Interest and convenience-yield carry with recession crash
risk: cards 08-13 apply the KMPV construction to different markets, and 08, 09 and 10 are one FX
premium in three wrappers. (3) Volatility risk premium: cards 14-16 sell it, and card 09's hedge
buys it. Not mechanizable as published: 04, 05 and 06.
