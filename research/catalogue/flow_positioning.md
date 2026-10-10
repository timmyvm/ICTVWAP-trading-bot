# Catalogue family: order flow, microstructure, positioning, leverage and sentiment

Family code `FLOW`. Compiled 2026-10-10. Outcome-blind: no repo result, ledger, verdict, DEVLOG,
HANDOFF or data cache was consulted. Every number under "Published claim" is the source's own figure
for its own market and era, not ours. "Cost-floor note" and "Event rate" use only the rule, contract
arithmetic and the source's published numbers; event rates are labelled estimates.

Fidelity policy in this file. **A**: primary source read and it states the full rule (signal,
direction, holding). **B**: primary read, but it gives an exact signal with no trade rule (a
predictive regression, a classifier or an event study), or a trade parameter is unspecified, or the
rule comes from a practitioner or third-party write-up. **C**: no published mechanical rule found
(folklore), or only an abstract was read so the parameters could not be verified. "Read: full" means
the relevant sections of the full text were read, sometimes through a summarising fetch or text
extraction. "Read: abstract" or "summary page" means only that was read. "Recalled, not re-fetched"
marks anything taken from memory.

Proposed P9 sub-labels for the chair (CATALOGUE.md §2 lets a scout name a new primitive):
**P9a signed order flow**: the net sign of aggressor (taker) volume or book pressure predicts the
next return. It is not P1, because flow and return differ, and not P7, which is unsigned.
**P9b external capital flow**: new money entering or leaving through a primary channel
(stablecoin minting, exchange deposits, ETF creations). **P9c attention**: search or social activity.

Gaps: the shared web-search budget ran out before targeted searches for a primary CVD source, the
full ETF-flow paper, crypto liquidation-event studies and later replications of S-FLOW-05. Those
cards say so below.

Cost reference (CATALOGUE.md §7): a perp round trip is 13 bp, so a two-leg long-short cycle is 26 bp.

---

### S-FLOW-01 Daily order-imbalance continuation (signed taker flow)
- **Fidelity.** A.
- **Sources.** Chordia and Subrahmanyam, "Order Imbalance and Individual Stock Returns", working paper Oct 2002 (published J. Financial Economics 2004; journal citation recalled, not re-fetched), https://www.cis.upenn.edu/~mkearns/finread/stock-misbalance.pdf (read: full working-paper PDF). Context only: Silantyev, "Order flow analysis of cryptocurrency markets", Digital Finance 1(1), 2019, https://ideas.repec.org/a/spr/digfin/v1y2019i1d10.1007_s42521-019-00007-w.html (read: abstract).
- **Rule.** Each day per stock, OIBNUM = (buyer-initiated − seller-initiated trades) / total trades, with trades signed by Lee-Ready (above the quote midpoint = buy); OIBVOL is the dollar-volume version. If yesterday's imbalance > 0, go long today; if < 0, go short; enter and exit within the day (the source buys at the ask and sells at the bid; returns are open-to-close from midquotes). Universe: NYSE stocks, daily. The crypto mapping is ours, not the source's: OIB = (2·taker-buy volume − volume) / volume from klines.
- **Primitive vs wrapper.** Primary P9a. Secondary P1 (imbalance moves with the same-day return). Wrapper: the same-day exit and the cross-the-spread fill assumption.
- **Claimed mechanism.** Large traders split orders to limit impact, so imbalances autocorrelate (first-lag autocorrelation about 33%). Risk-averse market makers with inventory limits absorb only part of the flow, so price pressure continues. The other side is market makers paid to carry inventory.
- **Published claim.** NYSE 1988-1998, more than 1,100 stocks: first-lag OIBNUM coefficient 0.214 (t = 26.43), about 77% of stock coefficients positive. The strategy averages about 0.09%/day, from about 0.23% (smallest firms) to 0.03% (largest). Once the same-day imbalance is included, the lagged coefficients turn negative. The authors say commissions could eliminate the profit for individuals.
- **Decay and crowding.** Not assessed in the source. Silantyev (BitMEX XBTUSD): trade-flow imbalance explains *contemporaneous* price changes better than order-flow imbalance does. That is a contemporaneous result, not a predictive one.
- **Cost-floor note.** One round trip a day. The source's large-firm 3 bp/day and full-sample 9 bp/day are below 13 bp; only its small-firm 23 bp clears it.
- **Event rate (estimate).** Daily per asset. Market-wide imbalance days are date-clustered, so about 250-365 dates a year but far fewer independent ones.
- **Applies to / testable here.** Source: US equities. Y: taker-buy volume is in Binance archive klines, which are public and free.
- **Regime hypothesis.** Should hold when large players work orders over days (institutional trends, thin liquidity providers) and in small, illiquid coins. Should fail when flow is mostly market-maker or HFT rebalancing, and in choppy mean-reverting tape.
- **Overlaps.** 02 (the same idea at tick scale), 03 (opposite-sign folklore on the same data). Trade-size variant: Feng, Wang and Zhang, "Informed trading in the Bitcoin market", Finance Research Letters 26, 2018, https://ideas.repec.org/a/eee/finlet/v26y2018icp63-70.html (read: abstract). Buy-initiated order sizes are unusually large about two days before large positive BTC events, and sell-initiated about one day before large negative ones.

### S-FLOW-02 Top-of-book queue imbalance and order-flow imbalance (OFI)
- **Fidelity.** B (the predictor is exact; there is no trade rule).
- **Sources.** Gould and Bonart, "Queue Imbalance as a One-Tick-Ahead Price Predictor in a Limit Order Book", 2015, arXiv:1512.03492, https://arxiv.org/pdf/1512.03492 (read: full). Cont, Kukanov and Stoikov, "The Price Impact of Order Book Events", J. Financial Econometrics 12(1), 2014, arXiv:1011.6402, https://ar5iv.labs.arxiv.org/html/1011.6402 (read: full text to about 70%).
- **Rule.** Queue imbalance I = (n_bid − n_ask) / (n_bid + n_ask), where n is the size of the best bid and best ask queues, sampled between mid-price changes. Predict the direction of the next mid-price change with a logistic fit ŷ = 1/(1 + exp(−(x0 + x1·I))), trained per stock on an 80/20 split. OFI (Cont et al.) sums the signed best-quote size changes e_n per interval: 1{Pb_n ≥ Pb_n−1}·qb_n − 1{Pb_n ≤ Pb_n−1}·qb_n−1 − 1{Pa_n ≤ Pa_n−1}·qa_n + 1{Pa_n ≥ Pa_n−1}·qa_n−1. Then ΔP_k = β·OFI_k over 10-second intervals, which is contemporaneous. Entry threshold, holding time and exit: not specified. Data: L1 quotes and sizes.
- **Primitive vs wrapper.** Primary P9a (book pressure). Secondary P7 (depth). No published wrapper; any threshold is ours.
- **Claimed mechanism.** The shorter queue is mechanically more likely to deplete first. Resting liquidity on the thin side is run over. It persists because using it needs queue position and colocation.
- **Published claim.** Nasdaq, 10 stocks, 2014 (LOBSTER), out of sample: ROC AUC 0.75-0.81 for large-tick stocks and 0.58-0.64 for small-tick stocks. Cont et al., 50 US stocks, April 2010: average R² 65% for contemporaneous ΔP on OFI, with a slope inversely proportional to depth. Lagged prediction is not tested.
- **Decay and crowding.** None reported. By the source's own split, the predictive power sits in large-tick names, and most crypto perps are small-tick relative to price.
- **Cost-floor note.** The horizon is one mid-price move. For example, a 0.1 tick on a 60,000 price is about 0.02 bp, against 13 bp. A taker cannot capture this; only a maker or queue-position use is conceivable, which is secondary under CATALOGUE.md §7.
- **Event rate (estimate).** Thousands per day per asset, none date-independent in any useful sense.
- **Applies to / testable here.** Source: US equity order books. N: needs L1/L2 snapshots or tick quotes, which are not in our listed data. Some Binance book archives may be public (recalled, not verified).
- **Regime hypothesis.** Holds for large-tick, long-queue books. Fails in small-tick, fast books and under spoofing or rapid cancellation.
- **Overlaps.** 01 (the daily aggregate), 04 (flow imbalance used for volatility instead).

### S-FLOW-03 Cumulative volume delta (CVD) and taker-ratio divergence
- **Fidelity.** C. Folklore; not mechanizable as commonly stated (no parameters).
- **Sources.** No primary source found in this pass; the search budget ran out before a dedicated search. Exchange definitions of the taker buy/sell ratio: recalled, not re-fetched. Context: Silantyev 2019 (see 01; read: abstract), which is contemporaneous only.
- **Rule.** Common retail form, parameters not specified. CVD = running sum of (taker-buy volume − taker-sell volume) from an anchor (session, day or swing). Bearish divergence: price makes a higher swing high while CVD makes a lower high, so short. Bullish divergence is the mirror. Anchor, swing definition, lookback, exit and stop: not specified.
- **Primitive vs wrapper.** Primary P9a. Secondary P8 (swing-high location). Wrapper: the swing definition and divergence confirmation.
- **Claimed mechanism.** Folklore: price rising on weakening aggressive buying means passive sellers are absorbing it, so a reversal follows. The implied other side is informed passive limit sellers. No published test was found.
- **Published claim.** None.
- **Decay and crowding.** Not applicable; a staple of retail order-flow tools.
- **Cost-floor note.** Usually traded on 5m-1h. The size of the post-divergence move is not specified, so the cost comparison cannot be made from the rule.
- **Event rate (estimate).** Depends on the swing definition. Perhaps tens a year per asset at 1h.
- **Applies to / testable here.** Crypto perps and futures. Y: taker volume in klines is public and free, once a swing rule is fixed (our choice).
- **Regime hypothesis.** If it works: range-bound markets with deep passive liquidity. Fails in trends driven by passive accumulation (TWAP, ETF-style buying), where CVD and price diverge for weeks.
- **Overlaps.** Opposite sign to 01 on the same data, so both can be measured at once. 08 uses the same divergence wrapper on open interest.

### S-FLOW-04 VPIN flow toxicity as a volatility forecast
- **Fidelity.** B (the signal is exact and explicitly non-directional; there is no trade rule).
- **Sources.** Easley, López de Prado and O'Hara, "Flow Toxicity and Liquidity in a High Frequency World", Review of Financial Studies 25(5), 2012, https://www.stern.nyu.edu/sites/default/files/assets/documents/con_035928.pdf (read: full, by text extraction). Critique: Andersen and Bondarenko, "VPIN and the Flash Crash", J. Financial Markets 2014, https://www.kellogg.northwestern.edu/faculty/research/detail/2014/vpin-and-the-flash-crash/ (read: summary page).
- **Rule.** Volume bucket V = average daily volume / 50; window n = 50 buckets. Each 1-minute bar's volume is split into buy and sell by the normal CDF of its standardised price change (bulk classification). VPIN = Σ|V_S − V_B| / (n·V), recomputed every bucket. "High toxicity" = CDF(VPIN) > 0.9. The forecast target is the absolute return over the next bucket. The source says "VPIN is not a directional indicator". A trading use is not specified (risk alert).
- **Primitive vs wrapper.** Primary P2 (predicts size). Secondary P9a and P7. Wrapper: the 0.9 CDF threshold.
- **Claimed mechanism.** Informed, one-sided flow adversely selects market makers, who widen or withdraw. The liquidity crash produces large moves. The other side is the adversely selected liquidity providers.
- **Published claim.** E-mini S&P 500, 2008-2011: corr(ln VPIN(τ−1), |return(τ)|) = 0.400 on 44,537 observations at 50 buckets/day and a 250-bucket window. The upper quartile of prior VPIN holds over 84% of absolute returns above 0.75%. CDF(VPIN) crossed 0.9 at least two hours before the 6 May 2010 flash crash. The authors disclose a patent and a financial interest.
- **Decay and crowding.** Andersen and Bondarenko: VPIN is "a poor predictor of short run volatility". Its content comes mainly from a mechanical link to trading intensity, and it peaked after the flash crash, not before.
- **Cost-floor note.** It forecasts size, not sign, so there is no directional trade. Its only use under our costs is as a P2 filter on another signal.
- **Event rate (estimate).** CDF > 0.9 is 10% of buckets by construction. Perhaps 10-30 independent high-toxicity episodes a year per market.
- **Applies to / testable here.** Source: index and oil futures. Y: 1m klines, and taker volume can replace bulk classification (our variant). Public and free.
- **Regime hypothesis.** Should add information when liquidity providers are inventory-constrained. Should add nothing once volume and recent volatility are controlled for, as the critique predicts.
- **Overlaps.** 05 (volume state), 01 and 02 (signed flow).

### S-FLOW-05 High-volume return premium
- **Fidelity.** A.
- **Sources.** Gervais, Kaniel and Mingelgrin, "The High-Volume Return Premium", J. Finance 56(3), 877-919, 2001; working paper https://rodneywhitecenter.wharton.upenn.edu/wp-content/uploads/2014/04/9901.pdf (read: full).
- **Rule.** Split history into non-overlapping 50-trading-day intervals. Days 1-49 are the reference period and day 50 is the formation day. Use dollar volume (shares × last price). A stock is high-volume if its day-50 volume ranks in the top 10% of the 50 days (rank ≥ 46) and low-volume if in the bottom 10% (rank ≤ 5). Within each size group, go $1 long equal-weighted high-volume and $1 short low-volume, and hold 20 trading days without rebalancing (1 and 10 days also reported). Weekly variant: the last week against the nine before it, high = rank 10, low = rank 1. Filters: price ≥ $5 in the reference period, no mergers or SEOs.
- **Primitive vs wrapper.** Primary P7. Secondary P3 (a cross-sectional sort). Wrapper: size groups, the price filter, non-overlapping intervals.
- **Claimed mechanism.** Visibility (Merton 1987): a volume shock draws attention, which brings in new holders and raises the price. Short-sale constraints (Diamond-Verrecchia) keep pessimists out. The source: "probably related to stock visibility and trading constraints". No specific losing counterparty is named.
- **Published claim.** NYSE 1963-1996, zero-investment, 20 days: small 0.94%, medium 1.07%, large 0.50%; weekly sample: small 1.36%, large 0.90%; t-statistics generally about 3 or higher.
- **Decay and crowding.** Later replications were not fetched (budget). Not assessed.
- **Cost-floor note.** A two-leg 20-day cycle costs 26 bp against the source's 50-107 bp per 20 days on equities. Perp funding on both legs is extra.
- **Event rate (estimate).** One formation date per 50-day interval gives about 5 independent dates a year. Rolling formation adds dates but they overlap.
- **Applies to / testable here.** Source: US equities. Y: daily klines for about 700 perps are public and free.
- **Regime hypothesis.** The mechanism needs scarce attention and costly shorting. Perps short freely, so the effect should be weaker there and stronger in spot-only small coins. Crypto volume spikes often coincide with liquidations or news, which confounds visibility with forced flow.
- **Overlaps.** 04 (volume-derived state). It is the opposite claim to "volume-spike reversal" folklore.

### S-FLOW-06 Round-number stop cascades and take-profit reversals
- **Fidelity.** B (event definitions are exact; there is no entry or exit rule; summary page only).
- **Sources.** Osler, "Stop-Loss Orders and Price Cascades in Currency Markets", FRBNY Staff Report 150, 2002, https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr150.html (read: summary page, not the full PDF). Journal version (J. International Money and Finance 2005) and Osler, "Currency Orders and Exchange Rate Dynamics", J. Finance 2003: recalled, not re-fetched.
- **Rule.** A round number is a rate ending in 00 (the source's definition). Cross event: price crosses a round number, so expect continuation in the crossing direction over the next 15 min to 2 h. Touch event: price reaches a round number without crossing, so expect a reversal within 30 min. Both are compared against arbitrary levels. Entry, stop and exit: not specified.
- **Primitive vs wrapper.** Primary P8. Secondary P7 (resting-order liquidity at the level) and P1 (continuation after a cross). Every trade detail is wrapper.
- **Claimed mechanism.** Stop-loss buys cluster just above round numbers and stop-loss sells just below. A cross fires them as market orders, which can cascade. Take-profit orders sit exactly at round numbers and absorb flow. The other side is stop placers, who pay through forced market orders. It persists because people choose round numbers. It is a rare P8 card with a stated mechanism.
- **Published claim.** RBS order book, Aug 1999 to Apr 2000 (9,655 orders, $55bn): stop-losses are 43% of orders by volume; 9.9% of take-profit value sits at 00 levels against 3.8% of stop value. Reuters 1-minute quotes 1996-1998, New York hours, USD/DEM: 15-minute move after a round-number cross 0.061% against 0.054% for arbitrary levels (higher in 51 of 58 ten-day intervals). Reversal rate 59.3% against 54.8%. The trend effect lasts at least 2 h and the reversal under 30 min; effects last hours, not days.
- **Decay and crowding.** The evidence is from the pre-algorithmic FX era; later evidence was not fetched. Crypto hint: Griffin and Shams (see 14; read: abstract) report Tether-linked BTC buying clustered below round price levels.
- **Cost-floor note.** The source's increment over arbitrary levels is 0.061 − 0.054 = 0.007%, or 0.7 bp, and the absolute 15-minute move is 6.1 bp. Both are below 13 bp.
- **Event rate (estimate).** Many round-number crosses per day per asset; each is tiny.
- **Applies to / testable here.** Source: FX. Y: 1m klines are public and free. "Ends in 00" must be rescaled per coin price level, and that rule is not specified (our choice).
- **Regime hypothesis.** Holds when discretionary stop placement dominates and depth near levels is thin. Fails when stops are randomised or the level is crowded enough to be front-run.
- **Overlaps.** 08 (leveraged cascade analog), P8 level and zone cards in other families.

### S-FLOW-07 Open-interest growth predicts returns (momentum sign)
- **Fidelity.** B (predictive regression with an exact predictor; no threshold or position rule).
- **Sources.** Hong and Yogo, "What Does Futures Market Interest Tell Us about the Macroeconomy and Asset Prices?", NBER WP 16712, 2011, revised 2012 (J. Financial Economics 2012), https://www.nber.org/papers/w16712 (read: introduction and data section of the PDF, not all tables).
- **Rule.** For each commodity, take the monthly growth rate of open interest. Take the median within each of four sectors, then the equal-weighted average across sectors, then smooth with a 12-month geometric average. Predict next month's commodity-index return with a positive sign: rising OI predicts higher returns. Monthly horizon; threshold and position sizing not specified.
- **Primitive vs wrapper.** Primary P6. Secondary P1 (the 12-month smoothing correlates with momentum). Wrapper: sector aggregation and smoothing.
- **Claimed mechanism.** Gross hedging demand rises with expected economic activity. Risk-absorption capacity is limited, so prices underreact and OI leads them; the result is momentum, not mean reversion. The other side is hedgers paying for insurance in an underreacting market.
- **Published claim.** 1965-2008: a one standard deviation rise in commodity market interest raises expected commodity returns by 0.73%/month and lowers bond returns by 0.32%/month. Effects are weaker in currency, bond and stock futures (from 1983-84). Twelve-month OI growth has mean 1.47%/month and standard deviation 2.06%.
- **Decay and crowding.** Not reported in the sections read. In crypto, OI growth is mostly speculative leverage rather than hedging, so the mechanism differs and the sign may flip (see 08).
- **Cost-floor note.** Monthly rebalance: 13 bp a month against the source's 73 bp a month per standard deviation.
- **Event rate (estimate).** Twelve signals a year, but 12-month smoothing leaves about 1-2 independent observations a year.
- **Applies to / testable here.** Source: US commodity, currency, bond and stock futures. Y: perp open interest is in the Binance archive metrics, public and free, with short history for most coins. CFTC open interest is public and free.
- **Regime hypothesis.** Holds where OI is hedger-driven and risk capacity is limited. In speculator-driven markets, rising OI means a leverage build-up and should predict the opposite sign.
- **Overlaps.** 08 (OI with price), 10 (funding as the price of the same leverage), 11 (COT positions).

### S-FLOW-08 Open interest versus price quadrant, and OI flush
- **Fidelity.** B (a practitioner write-up gives state thresholds but no complete exit and no systematic test). The quadrant idea itself is futures folklore traced to Murphy, *Technical Analysis of the Futures Markets* (1986): recalled, not re-fetched.
- **Sources.** Adler Jr., "Bitcoin open interest price divergence patterns", 11 Feb 2026, https://axeladlerjr.com/bitcoin-open-interest-price-divergence-patterns/ (read: full). StoneX, "Open Interest", https://futures.stonex.com/technical-analysis-learning-center/open-interest (read: full; it gives only the volume and OI version and cites Murphy 1986 and Kaufman 1978).
- **Rule.** Regimes from 7-day changes: R1 (OI up, price up) is healthy, but turn defensive when OI grows about 1.5x faster than price over 30+ days. R2 (OI up, price down) is bearish "cascade loading". R3 (OI down, price down) is capitulation. R4 (OI flat or down, price up) is an organic rally. Actionable short-term: 7-day OI change ≥ ±15% with an opposite 7-day price move ≥ ±5%, persisting 3+ days. Actionable macro: 30-day OI ±25% with opposite price ±10%, persisting 2+ weeks. Flush: OI −15% within 48 h; capitulation: OI −30% within 7 days, which marks a long re-entry candidate. Exit not specified; the source says R3 resolves in 1-5 days and R2 in 7-21 days.
- **Primitive vs wrapper.** Primary P6. Secondary P1 (the price leg). Wrapper: confirmations from an estimated leverage ratio (ELR) and funding (> 0.01%/8 h confirms R2), and the persistence filters.
- **Claimed mechanism.** OI rising into falling prices means fresh shorts or trapped longs, which is fuel for a cascade. A flush means forced sellers are exhausted and the marginal seller is gone. The other side of the flush buy is liquidated over-levered longs, who sell without regard to price.
- **Published claim.** Episode anecdotes only; the source gives no systematic forward-return statistics. Example: BTC, 10-25 May 2021, OI −49% in 15 days and price −33%. The fetch noted an internal inconsistency in the source's R4 episode.
- **Decay and crowding.** Unmeasured. These are standard dashboard readings since about 2020.
- **Cost-floor note.** The thresholds imply moves of 5% or more over 7 days, far above 13 bp.
- **Event rate (estimate).** Per coin, a flush (OI −15% in 48 h) a few times a year. Market-wide, perhaps 3-8 independent dates a year.
- **Applies to / testable here.** Source: BTC perps. Y: OI metrics plus klines, public and free. Liquidation prints themselves are not in our listed data, so the OI drop is the proxy.
- **Regime hypothesis.** The flush buy works when forced liquidation, not information, drives the OI drop. It fails when OI falls because informed holders de-risk ahead of bad news (an exchange failure, for example), and price keeps falling.
- **Overlaps.** 07 (OI growth, opposite sign claim), 09 (crowding), 10 (funding confirmation), 06 (cascade mechanism).

### S-FLOW-09 Long/short account-ratio contrarian
- **Fidelity.** C (no tested rule; a single practitioner note).
- **Sources.** Lunde (K33 Research), "Binance traders expecting downside?", 7 Feb 2022, https://k33.com/research/archive/articles/binance-traders-expecting-downside (read: full). Binance's account, top-trader-account and top-trader-position ratio definitions: recalled, not re-fetched.
- **Rule.** Account ratio = accounts net long / accounts net short on the BTCUSDT perp (data from Coinalyze). The note observes that a ratio above 4 preceded sell-offs on five dates in 2021-22, so de-risk or short. It treats a low ratio (0.743, most accounts short) as a contrarian-bullish backdrop. Long-side threshold, holding horizon and exit: not specified.
- **Primitive vs wrapper.** Primary P6. Wrapper: the threshold.
- **Claimed mechanism.** Account counts are dominated by small accounts. When most accounts are long, size-weighted positioning can be short (large accounts on the other side). The crowded side is also fuel for liquidations. The other side is large accounts and market makers.
- **Published claim.** No return statistics. Five dated sell-offs after a ratio above 4. The note also says the Binance and Bybit crowd has been wrong many times.
- **Decay and crowding.** Unmeasured. The ratio is widely displayed.
- **Cost-floor note.** Holds of days imply moves far above 13 bp if any edge exists; the size is unknown.
- **Event rate (estimate).** By the note's own count, about 5 ratio-above-4 episodes on BTC in about 10 months.
- **Applies to / testable here.** Binance and Bybit perps. Y: the Binance archive metrics include long/short ratios, public and free.
- **Regime hypothesis.** Should work when the account ratio and the position ratio disagree (retail against whales). Should fail in retail-led trends, where the crowd is right for a long time.
- **Overlaps.** 11 (the COT version: small against large traders; Wang finds small-trader sentiment has little forecasting value), 08, 10.

### S-FLOW-10 Funding and basis extremes, read contrarian
- **Fidelity.** B. The predictor is exact (a regression); the threshold rule comes from a third-party report of an industry note, with n = 7.
- **Sources.** Schmeling, Schrimpf and Todorov, "Crypto carry", BIS Working Paper 1087, 2023, https://www.bis.org/publications/working-paper-1087-crypto-carry.pdf (read: full, through summarising fetches). Lunde and Zimmerman (K33), as reported by The Block on 11 Sep 2024, https://www.theblock.co/post/315831/perp-signal-bitcoin-bottom-bullish-year-end-k33 (read: article; the report itself was not read). Christin, Routledge, Soska and Zetlin-Jones, "The Crypto Carry Trade", 2022, https://www.andrew.cmu.edu/user/azj/files/CarryTrade.v1.0.pdf (read: abstract and introduction). He, Manela, Ross and von Wachter, "Fundamentals of Perpetual Futures", arXiv:2212.06888 (read: abstract).
- **Rule.** Rule A (Schmeling): carry = annualised log futures-spot basis, 1-month and 3-month constant maturity, measured daily. High carry predicts lower spot and lower futures premium over 1-3 months, more negative skew and more liquidations; threshold not specified. Rule B (K33): when the 30-day average perp funding rate turns negative, go long BTC; the cited horizon is 90 days.
- **Primitive vs wrapper.** Primary P6. Secondary P4. Wrapper: the averaging window and the threshold.
- **Claimed mechanism.** Carry is a convenience yield paid by small, trend-chasing, leverage-seeking longs: it rises with Reddit subscriber growth and past returns, and with non-reportable traders' net longs. Arbitrage capital is scarce and slow because of margin and liquidation risk (the futures leg would have been liquidated in 52% of months at 10x). Christin et al. find that derivative demand is driven by the long side.
- **Published claim.** Schmeling (Mar 2019 to Jan 2022, BTC and ETH, OKEx, CME and others): carry averages about 10% a year and peaks near 60%. For OKEx 1-month, a $1 rise in basis predicts about a $5 drop in spot and a $6 drop in the futures premium. A 10% rise in carry predicts 44% more "sell liquidations" (the paper's term, defined there as liquidated *short* positions) relative to OI next month. Risk-reversal coefficient −4.44 (OKEx) and −5.48 (CME); OKEx 3-month realised-return coefficient −0.14. K33: the 30-day average went negative "for just the seventh time since 2018"; average 90-day return 79%, median 55% (BTC).
- **Decay and crowding.** He et al.: perp-spot deviations shrink over time. Rule B has 7 instances and cannot be told from luck.
- **Cost-floor note.** Holds of 1-3 months make 13 bp negligible. Funding paid or received during the hold is part of the P&L.
- **Event rate (estimate).** Rule B: about 1 a year (7 since 2018, per the source). Rule A: carry is very persistent, so about 1-3 independent extremes a year.
- **Applies to / testable here.** Source: BTC and ETH dated futures and perps. Y: funding history is in the archive, public and free. Dated-futures basis is partial.
- **Regime hypothesis.** Fading high carry works at the end of leveraged retail booms and fails mid-boom; the source shows high carry also predicts *short* liquidations, meaning squeezes. Buying negative funding works after capitulation and fails in structural bears, where funding stays negative while price falls.
- **Overlaps.** 08, 09, 11; the carry family (`CARRY`) cards that read funding as a directional signal.

### S-FLOW-11 COT large-trader sentiment (follow speculators, fade hedgers)
- **Fidelity.** A.
- **Sources.** Wang, "Investor sentiment and return predictability in agricultural futures markets", J. Futures Markets 21(10), 929-952; MPRA 36425, https://mpra.ub.uni-muenchen.de/36425 (read: full, by text extraction). Wang, "The behavior and performance of major types of futures traders", J. Futures Markets 23(1), 2003, https://mpra.ub.uni-muenchen.de/36426/1/MPRA_paper_36426.pdf (read: full, through a summarising fetch). Briese's COT index, which Wang cites as practitioner precedent: recalled, not re-fetched.
- **Rule.** SI_t = (S_t − min S) / (max S − min S), with min and max over the previous 3 years of weekly COT reports. S = net position (long − short OI) of a trader type, detrended by total OI. Types: large speculators (non-commercial), large hedgers (commercial), small traders (non-reportable). Extremes: top 20% (EH) and bottom 20% (EL). Go long when speculator SI is in EH and/or hedger SI is in EL; go short on the mirror. Hold 2, 4, 6 or 8 weeks, non-overlapping.
- **Primitive vs wrapper.** Primary P6. Secondary P4 (the hedging-pressure premium). Wrapper: the 3-year min-max normalisation and the quintile cutoffs.
- **Claimed mechanism.** Hedging pressure (Keynes and Hicks): hedgers pay a premium to offload risk and speculators earn it. The author finds no evidence that speculators have superior forecasting skill. The other side is hedgers, who knowingly pay for insurance.
- **Published claim.** Six agricultural futures, 1993 to Mar 2000, agricultural portfolio, large speculators: EH − EL 2.80% over 4 weeks (t = 7.35) and 3.22% over 6 weeks. Large-hedger extremes forecast the opposite sign with similar size (4-week magnitude 2.97%; minus signs were lost in our text extraction, and the text states the hedger EH return is negative). Small-trader sentiment has little value. Wang 2003 (15 markets, Oct 1992 to Mar 2000): following large speculator position changes earns, for example, 2.38% a month in corn, attributed to hedging pressure.
- **Decay and crowding.** The sample ends in 2000; the index-fund era is not assessed here.
- **Cost-floor note.** A 4-6 week hold with several-percent spreads; 13 bp is minor.
- **Event rate (estimate).** Weekly data with 20% tails gives about 10 weeks a year in each tail per market. With autocorrelation, about 2-4 independent episodes.
- **Applies to / testable here.** Source: US agricultural and other futures. Partial: CFTC COT for CME bitcoin and ether futures is public and free, but it covers one or two underlyings. N for the perp cross-section, which has no trader-type split.
- **Regime hypothesis.** Holds where hedgers sit structurally on one side (commodities). In crypto, "commercials" are mostly dealers and basis traders, so the hedging-pressure mechanism may not apply.
- **Overlaps.** 09 (small against large), 10 (long-side demand premium), 07.

### S-FLOW-12 Search-volume and social-mood timing
- **Fidelity.** A (the Preis rule is exact). Bollen et al. is included as a believed-dead sibling.
- **Sources.** Preis, Moat and Stanley, "Quantifying Trading Behavior in Financial Markets Using Google Trends", Scientific Reports 2013, https://pmc.ncbi.nlm.nih.gov/articles/PMC3635219 (read: full). Bollen, Mao and Zeng, "Twitter mood predicts the stock market", J. Computational Science 2011, arXiv:1010.3003 (read: abstract). Lachanski and Pav, Econ Journal Watch 14(3), 2017, https://econjwatch.org/articles/shy-of-the-character-limit-twitter-mood-predicts-the-stock-market-revisited (read: summary page).
- **Rule.** Take weekly Google search volume n(t) for a term. Δn(t, Δt) = n(t) − N(t−1, Δt), where N is the mean of the previous Δt weeks. If Δn(t−1, Δt) > 0, sell the DJIA at the close of the first trading day of week t and buy back at the close of the first trading day of week t+1. If < 0, buy and sell a week later. Default Δt = 3 weeks; best term "debt" (out of 98 tested).
- **Primitive vs wrapper.** Primary P9c. Secondary P5 (a weekly clock). Wrapper: term choice and Δt.
- **Claimed mechanism.** Investors gather information (search) before selling. No counterparty is named beyond that.
- **Published claim.** 5 Jan 2004 to 22 Feb 2011: "debt" strategy 326%, against 16% buy-and-hold and 33% for the same rule run on DJIA prices. The mean across 98 terms is 0.60 standard deviations of the random strategy (t = 8.65). Costs are ignored (at most 104 trades a year). Bollen: 87.6% accuracy on daily DJIA up/down from the "Calm" mood dimension (2008).
- **Decay and crowding.** Bollen failed replication: Lachanski and Pav find significance only in the original window, none once extended back to 2007, and no out-of-sample power. The fund launched to trade it closed in early 2012. Preis: 326% is the best of 98 terms, a multiple-testing winner.
- **Cost-floor note.** A weekly round trip costs 52 × 13 bp = 6.8% a year.
- **Event rate (estimate).** About 52 date-independent weekly signals a year per asset.
- **Applies to / testable here.** Source: DJIA. Partial: Google Trends is public and free but not in our archive, and it is rescaled and sampled. Bitcoin search-volume studies (Kristoufek 2013): recalled, not re-fetched.
- **Regime hypothesis.** If real, strongest in retail-attention markets (crypto) and in stress. Fails when search simply follows price moves (reverse causality), in which case it is P1 relabelled.
- **Overlaps.** 13 (which puts 10% weight on Trends and 15% on social media), 05 (attention through volume).

### S-FLOW-13 Crypto Fear & Greed index, read contrarian
- **Fidelity.** C (the vendor publishes the construction but no contrarian thresholds or test).
- **Sources.** alternative.me, "Crypto Fear & Greed Index", https://alternative.me/crypto/fear-and-greed-index/ (read: full). Huang, Xu, Xue and Zhang, "How does the Bitcoin Sentiment Index of Fear & Greed affect Bitcoin returns?", Corporate Ownership & Control 21(2), 2024, https://virtusinterpress.org/How-does-the-Bitcoin-Sentiment-Index-of-Fear-Greed-affect-Bitcoin-returns.html (read: abstract).
- **Rule.** Index 0-100, from 0 "Extreme Fear" to 100 "Extreme Greed". The vendor's reading: extreme fear may be a buying opportunity, extreme greed signals a correction. Cutoffs, holding period and exit: not specified. Components: volatility and max drawdown against their 30/90-day averages (25%); momentum and volume against 30/90-day averages (25%); social media (15%); surveys (15%, paused); BTC dominance (10%); Google Trends (10%).
- **Primitive vs wrapper.** Primary P1 (the momentum leg). Secondary P2 (the volatility leg) and P9c. It is a composite of other primitives.
- **Claimed mechanism.** Crowd over-reaction. No counterparty is named.
- **Published claim.** No test of the contrarian rule was found. Huang et al. (monthly, 2016-2021, ARDL/ECM) report a *positive* significant relation between the index and BTC returns, which is the opposite sign to the contrarian reading; the lag structure is not stated in the abstract.
- **Decay and crowding.** Unmeasured. Widely followed.
- **Cost-floor note.** A daily index with multi-week holds; 13 bp is minor.
- **Event rate (estimate).** Perhaps 3-6 extreme-fear episodes a year.
- **Applies to / testable here.** BTC only. Partial: the index history is public and free (vendor API, recalled, not verified), and the P1/P2 components can be rebuilt from klines (Y).
- **Regime hypothesis.** Buying extreme fear should work in bull-market pullbacks and fail in bear markets, where fear persists.
- **Overlaps.** 12. P1 and P2 cards in other families: testing the components directly dominates testing the index.

### S-FLOW-14 Stablecoin issuance and exchange net flows (on-chain capital flow)
- **Fidelity.** B (an event study and predictive regressions with exact definitions; no trade rule).
- **Sources.** Ante, Fiedler and Strehle, "The Influence of Stablecoin Issuances on Cryptocurrency Markets", Blockchain Research Lab WP 11, 2020 (Finance Research Letters version recalled, not re-fetched), https://www.blockchainresearchlab.org/wp-content/uploads/2020/05/The_Influence_of_Stablecoin_Issuances_on_Cryptocurrency_Markets_BRL_Working_Paper_No_11.pdf (read: full). Chi, Chu and Hao, "Return and Volatility Forecasting Using On-Chain Flows in Cryptocurrency Markets", arXiv:2411.06327, https://arxiv.org/pdf/2411.06327 (read: full, through a summarising fetch). Griffin and Shams, "Is Bitcoin Really Un-Tethered?", SSRN 3195066 (J. Finance 2020), https://papers.ssrn.com/abstract=3195066 (read: abstract).
- **Rule.** Rule A (Ante): an event is a stablecoin issuance of at least US$1m (USDT, USDC, PAX, BUSD, HUSD, DAI, GUSD). Using hourly data, compute the CAR over [−24 h, +24 h] against the mean return over [−150 h, −30 h]. Our reading of the event study, not a source rule: long at issuance, hold 24 h. Rule B (Chi): R(t+k) = β0 + β1·NetInflow(t) (+ R(t)), where NetInflow = exchange inflows − outflows in US$m and k = 1-6 h. ETH net inflow predicts a lower ETH return; USDT net inflow predicts higher BTC and ETH returns.
- **Primitive vs wrapper.** Primary P9b. Secondary P6. Wrapper: the issuance threshold and the event window.
- **Claimed mechanism.** Issuance is demand-driven: minting follows buying demand and peg arbitrage (57% of issuances happened above peg, average premium 0.19%). Griffin and Shams instead read a supply story: Tether flows timed after downturns and followed by BTC rises. Coin deposits to exchanges signal intent to sell; stablecoin deposits signal buying power.
- **Published claim.** Ante (Apr 2019 to Mar 2020, 565 events, BTC, ETH, XRP and LTC on Bitstamp): CAAR over the 12 h before the event 0.31-0.47%, and over 0 to +24 h 0.47-0.69%; no size effect. Chi (16 Dec 2017 to 20 Jan 2023): "US$ 1 million of ETH net inflows predict -1.70% of ETH return in the next hour" (the source's number; implausibly large for $1m, so check the units before use). US$100m of USDT net inflow predicts +0.11% (ETH) and +0.065% (BTC) in the next hour.
- **Decay and crowding.** Ante covers one year and Griffin-Shams the 2017 boom. Later issuance behaviour is not assessed.
- **Cost-floor note.** Ante's 0 to +24 h CAAR of 47-69 bp clears 13 bp. Chi's USDT effect is 6.5-11 bp per $100m per hour, below the floor unless flows are much larger.
- **Event rate (estimate).** About 565 issuances a year, heavily clustered; perhaps 100-200 independent days a year.
- **Applies to / testable here.** Source: BTC, ETH and large caps. N in our archive. Issuance is public on-chain and free; labelled exchange-flow series mostly come from paid vendors (recalled, not verified).
- **Regime hypothesis.** Works while stablecoins are the marginal on-ramp (offshore venues, before ETFs). Weaker once fiat and ETF channels dominate new money.
- **Overlaps.** 15 (the same "new money" primitive with the opposite claimed sign), 01.

### S-FLOW-15 ETF creation and redemption flows, faded
- **Fidelity.** C on this pass. A primary source exists, but only its abstract and a summary page were read, so the flow definition, sort and horizon are unverified and written as not specified.
- **Sources.** Brown, Davies and Ringgenberg, "ETF Arbitrage, Non-Fundamental Demand, and Return Predictability", Review of Finance 25(4), 937-972, 2021, https://experts.arizona.edu/en/publications/etf-arbitrage-non-fundamental-demand-and-return-predictability/ (read: abstract); https://revfin.org/?p=2019 (read: summary page).
- **Rule.** Rank ETFs by primary-market flows (creations − redemptions; the exact measure, window and breakpoints are not specified on the pages read). Short high-flow ETFs and long low-flow ETFs; returns are quoted per month, so the holding is presumably monthly (not verified).
- **Primitive vs wrapper.** Primary P9b, with a contrarian sign. Secondary P3. Wrapper: the sort breakpoints.
- **Claimed mechanism.** Authorised participants create or redeem to close law-of-one-price gaps opened by non-fundamental demand. That demand pushes prices from fundamentals and later reverses, and investors who supply it underperform.
- **Published claim.** The long-short earns 1.1-2.0% a month (published abstract), or 1-4% a month (revfin summary, probably an earlier version). Sample years not stated on the pages read.
- **Decay and crowding.** Not assessed. Daily spot-BTC ETF flow rules (2024 onward) are popular folklore; no primary test was found in this pass.
- **Cost-floor note.** A two-leg monthly cycle at 26 bp against the source's 110-200 bp a month.
- **Event rate (estimate).** About 12 independent cross-sectional dates a year.
- **Applies to / testable here.** Source: US ETFs. Partial: spot BTC and ETH ETF flows are public and free (issuer shares outstanding), but they start in 2024 (recalled), cover only two underlyings, and give a time series with no cross-section.
- **Regime hypothesis.** Works when flows are non-fundamental (retail flow-chasing). Fails when creations carry information.
- **Overlaps.** 14 (crypto stablecoin inflows are claimed as bullish continuation, the opposite sign), 01.

### S-FLOW-16 Anchored VWAP and volume-profile levels
- **Fidelity.** C. Not mechanizable as published: the source calls the anchor choice subjective.
- **Sources.** Shannon, *Maximum Trading Gains With Anchored VWAP* (book; year not stated on the page), https://alphatrends.net/anchored-vwap-book/ (read: the product page; the book was not read). Market Profile and volume-profile concepts (Steidlmayer): recalled, not re-fetched.
- **Rule.** Compute VWAP from a chosen anchor event; the page lists IPOs, breakouts, pullbacks, gaps and short squeezes as applications. Price above the AVWAP means buyers are "in control", and its slope shows who dominates. Entry, exit, stop and anchor rule: not specified. The page says the anchor is "the most subjective, and most important, decision".
- **Primitive vs wrapper.** Primary P8. Secondary P7. Everything beyond the level is wrapper.
- **Claimed mechanism.** AVWAP is the average cost of everyone who traded since the event. Holders defend or exit at breakeven (the disposition effect), which creates support or resistance. No counterparty is named.
- **Published claim.** None.
- **Decay and crowding.** Not applicable.
- **Cost-floor note.** Depends entirely on a wrapper the source does not specify.
- **Event rate (estimate).** Not specified; depends on the anchor rule.
- **Applies to / testable here.** Source: equities. Y only once we mechanise an anchor (day high or low, gap open, swing point), which would be our choice. Klines are public and free.
- **Regime hypothesis.** If it works: holder bases with stable cost and a disposition effect (spot equities). Weaker in levered, short-dated perp positioning.
- **Overlaps.** 06 (levels with an order-clustering mechanism), P8 level cards in other families.

---

## Family notes

There are about five distinct primitives here. **P6** (positioning and leverage: 07, 08, 09, 10, 11)
is one idea, crowded or levered positioning, read through OI, account ratios, funding and COT
wrappers; 07 and 08 claim opposite signs for rising OI. **P9a** (signed flow: 01, 02, 03) is one
idea at three time scales, with 03 the opposite-sign folklore. **P9b** (capital flow: 14, 15)
claims opposite signs in crypto and ETFs. **P7/P2** (05, 04) are volume states. **P8** (06, 16) is
levels, and only 06 has a mechanism. 12 and 13 are attention wrappers, and 13 mostly repackages
P1 and P2. Not mechanizable: 03, 16, 09's long side, and 15 as read.
