# Catalogue family: calendar, seasonality, time-of-day and scheduled events

Family code `CAL`. Compiled 2026-10-10. Outcome-blind: no repo result, ledger, verdict or data cache
was consulted. Every number under "Published claim" is the source's own figure for its own market and
era, not ours. "Cost-floor note" and "Event rate" use only the rule and the source's published numbers.

Fidelity policy in this file. **A**: a primary source states the rule exactly. **B**: the rule comes
from a secondary description, or the primary source was not read. **C**: no published mechanical rule
was found (folklore). "Read: full" means the full text was read; "abstract" or "bibliographic page"
means only that. "Recalled, not re-fetched" marks content from memory that was not checked against a
fetched page during compilation. The scout's web-search budget ran out partway through. Sources after
that point were reached only through known URLs, so a "no source found" here is weaker than usual.

Cost reference (CATALOGUE.md §7): one perp round trip costs 13 bp; a hedged or long-short trade has
two legs, so 26 bp.

---

### S-CAL-01 Turn-of-the-month (TOM)
- **Fidelity.** A.
- **Sources.** McConnell and Xu, "Equity Returns at the Turn of the Month", Financial Analysts Journal 64(2), 2008, https://rpc.cfainstitute.org/research/financial-analysts-journal/2008/equity-returns-at-the-turn-of-the-month (read: abstract); working-paper version, https://docs.lib.purdue.edu/ciberwp/43 (read: abstract, which defines the window); CXO Advisory summary of the 2006 draft, https://www.cxoadvisory.com/calendar-effects/the-turn-of-the-month-effect/ (read: full, secondary). Origin: Lakonishok and Smidt, "Are Seasonal Anomalies Real? A Ninety-Year Perspective", RFS 1(4), 1988, https://academicnewsletter.sufe.edu.cn/info/355994 (read: abstract). SPY implementation: https://quantpedia.com/strategies/turn-of-the-month-in-equity-indexes (read: full).
- **Rule.** Hold the broad equity index for four daily close-to-close returns: the last trading day of month m and trading days 1-3 of month m+1. Enter at the close of the second-to-last trading day of m, exit at the close of trading day 3 of m+1, and hold cash on the other ~16 days. Data: daily closes and the exchange calendar. Quantpedia's wording "buy one trading day before the end of the month" is ambiguous about which close; the paper's four-return window is the reference.
- **Primitive vs wrapper.** Primary P5; secondary P7 (the claimed flow). No wrapper beyond the cash leg.
- **Claimed mechanism.** The usual story is month-start cash: payroll, pension and 401(k) contributions, and reinvested coupons (Ogden 1990, as cited by Quantpedia). McConnell and Xu test month-end buying pressure (volume, net equity-fund flows) and reject it, calling the effect "a puzzle in search of an answer". The source names no confirmed counterparty.
- **Published claim.** McConnell and Xu (US, 1926-2005, focus 1987-2005): all of the positive excess market return fell in the four-day window. In 1987-2005, value-weighted returns were 0.14%/day at TOM vs −0.01% on other days; equal-weighted, 0.24% vs 0.04% (CXO's summary of the draft). Found in 31 of 35 countries; volatility at TOM no higher than on other days.
- **Decay and crowding.** Plastun, Sibande, Gupta and Wohar, "Rise and Fall of Calendar Anomalies over a Century", Univ. Pretoria WP 2019-02, https://www.up.ac.za/media/shared/61/WP/wp_2019_02.zp166894.pdf (read: full). On the DJIA, TOM scores 5/5 in each decade from the 1920s to the 1970s, then 3 (1980s), 2 (1990s), 1 (2000s) and absent in 2010-2018. Quantpedia cites Carcano and Tornero, who find TOM the only persistent calendar effect in S&P 500 futures (not read).
- **Cost-floor note.** 0.14%/day × 4 days ≈ 56 bp gross per event (VW, 1987-2005), about 4x one 13 bp round trip; one round trip a month.
- **Event rate (estimate).** 12 a year, each market-wide (one sample per month).
- **Applies to / testable here.** The US and 30 other equity markets. Equities: partial (Yahoo daily). Crypto analog: Y (UTC month boundaries in the archive).
- **Regime hypothesis.** Holds where scheduled month-start contributions buy the asset. In crypto it should appear only where such flows exist (spot BTC ETFs since 2024, recurring-buy retail plans) and be absent in altcoin perps. It fails where flows are continuous or front-run.
- **Overlaps.** S-CAL-14 (the same month-boundary window with a rebalancing-flow mechanism), S-CAL-04 (the December/January turn is one TOM), S-CAL-03.

### S-CAL-02 Weekend / Monday effect
- **Fidelity.** A (a single calendar dummy).
- **Sources.** French, "Stock Returns and the Weekend Effect", JFE 8(1):55-69, 1980, https://ideas.repec.org/a/eee/jfinec/v8y1980i1p55-69.html (read: bibliographic page only; content recalled, not re-fetched). Schwert, "Anomalies and Market Efficiency", NBER WP 9277, 2002, https://www.nber.org/papers/w9277.pdf (read: full). Crypto: Baur, Cahill, Godfrey and Liu, "Bitcoin Time-of-Day, Day-of-Week and Month-of-Year Effects in Returns and Trading Volume", UWA WP 2017, https://research-repository.uwa.edu.au/en/publications/bitcoin-time-of-day-day-of-week-and-month-of-year-effects-in-retu/ (read: abstract); Caporale and Plastun, "The day of the week effect in the cryptocurrency market", Finance Research Letters, 2019 (recalled, not re-fetched).
- **Rule.** Short the broad index (or stand aside) over the "weekend" return, i.e. from Friday's close to the close of the first trading day after a weekend; long or flat on other days. Daily closes; S&P composite/DJIA in Schwert. No crypto source states a trading rule.
- **Primitive vs wrapper.** Primary P5. No wrapper.
- **Claimed mechanism.** French (recalled) rejects the calendar-time hypothesis (Monday should carry three days of return) and finds no explanation. Later stories (bad news released after Friday's close; individual investors selling on Mondays) were seen only as paper titles in search results, not read. Treat it as "no confirmed counterparty".
- **Published claim.** Schwert Table 3 (daily S&P composite/DJ). 1953-1977, which replicates French: α0 = +0.07%/day, weekend coefficient −0.23% (t −8.86), so the weekend mean is −0.16%. Over 1885-2002 the coefficient is −0.17% (t −10.13).
- **Decay and crowding.** Schwert: 1978-2002 coefficient −0.05% (t −1.37), weekend mean "essentially zero"; "the weekend effect seems to have disappeared ... since it was first documented in 1980". Plastun et al. 2019 find day-of-week effects absent on the DJIA in 2000-2018. Baur et al. find Bitcoin effects time-varying with "no consistent or persistent patterns".
- **Cost-floor note.** Pre-1978, about 16 bp per event (≈1.2x of 13 bp); after 1978, about zero, so below cost.
- **Event rate (estimate).** 52 a year, market-wide.
- **Applies to / testable here.** Equities: partial (Yahoo daily). Crypto: Y for the analog (weekend UTC days vs weekdays). Perps never close, so the closure mechanism itself is absent.
- **Regime hypothesis.** If the mechanism is closure plus the timing of news releases, crypto should show it only through equity-linked venues that close (CME futures, and spot ETFs since 2024), and only in that era. In equities it should be absent after 1978.
- **Overlaps.** S-CAL-06 (the weekend is the longest overnight), S-CAL-03 (closure effects).

### S-CAL-03 Pre-holiday effect
- **Fidelity.** A.
- **Sources.** Ariel, "High Stock Returns before Holidays: Existence and Evidence on Possible Causes", JF 45(5):1611-1626, 1990, https://ideas.repec.org/a/bla/jfinan/v45y1990i5p1611-26.html (read: abstract). Lakonishok and Smidt 1988 (read: abstract; card 01). Plastun et al. 2019 (read: full; card 01).
- **Rule.** Hold the broad index for the one close-to-close return of the last trading day before an exchange holiday closure (NYSE full-day closures, about eight a year); hold cash otherwise. Data: daily closes and the NYSE holiday calendar.
- **Primitive vs wrapper.** Primary P5. No wrapper.
- **Claimed mechanism.** The abstract tests causes but confirms none. Hourly data show the high returns spread through the day, so the effect is not an artifact of the close. Popular explanations (short covering before the closure, holiday mood) are not supported in the text read. The source names no counterparty.
- **Published claim.** Ariel (US, 1963-1982): mean pre-holiday returns are 9-14x the mean of other days, and more than one third of the market's total return over 1963-82 was earned on the ~8 pre-holiday days a year. The paper also examines 1983-86.
- **Decay and crowding.** Plastun et al. 2019 (DJIA): the holiday effect scores 5/5 in the 1920s and in each decade from the 1950s to the 1970s, 1 in the 1980s and 0 from 1990 onward.
- **Cost-floor note.** Taking an ordinary day as ~5 bp (Schwert's 1885-2002 non-weekend mean, a different source) gives 9-14x ≈ 45-70 bp per event vs 13 bp. This mixes two sources and is rough.
- **Event rate (estimate).** About 8-9 a year, market-wide.
- **Applies to / testable here.** US equities: partial (Yahoo daily). Crypto: Y as an analog (BTC trades through US holidays), but the closure mechanism is absent.
- **Regime hypothesis.** Holds where a closure interrupts trading for the marginal holder. It should be absent in 24/7 markets unless closures of equity-linked venues (ETFs, CME) carry over.
- **Overlaps.** S-CAL-02 (closure effects), S-CAL-04 (Christmas and New Year's Eve are pre-holidays), S-CAL-01.

### S-CAL-04 Turn-of-the-year / January small-cap effect (with the "Santa Claus rally" folklore variant)
- **Fidelity.** A for the academic window (Schwert's test, read). C for the Santa Claus variant (folklore).
- **Sources.** Rozeff and Kinney, "Capital Market Seasonality: The Case of Stock Returns", JFE 3(4), 1976 (recalled, not re-fetched). Keim, "Size-related Anomalies and Stock Return Seasonality: Further Empirical Evidence", JFE 12(1):13-32, 1983, https://ideas.repec.org/a/eee/jfinec/v12y1983i1p13-32.html (read: bibliographic page only). Schwert 2002, NBER w9277 (read: full). Santa Claus rally: Hirsch, Stock Trader's Almanac (recalled, not re-fetched).
- **Rule.** Long the CRSP NYSE smallest size decile and short the largest decile, equal capital, from the close of the last trading day of December to the close of 15 January (the first 15 calendar days); flat otherwise. Daily data with size deciles. Santa Claus variant (folklore, recalled): hold the index over the last five trading days of December and the first two trading days of January.
- **Primitive vs wrapper.** Primary P5; secondary P3 (the size cross-section). The size sort is a selection filter.
- **Claimed mechanism.** Tax-loss selling (Roll 1983, as cited by Schwert): taxable individuals sell losers, often small caps, before 31 December and buying resumes in January. Year-end window dressing by institutions is also cited. Small-cap trading costs and short-sale limits limit arbitrage.
- **Published claim.** Schwert Table 2 (NYSE decile 1 minus decile 10, daily January dummy): 0.815%/day in 1962-1979 (t 7.14), 0.433% in 1980-1989 (t 4.55), 0.565% in 1990-2001 (t 5.37). Keim 1983: roughly half of the annual size premium falls in January (recalled, not re-fetched).
- **Decay and crowding.** Schwert: smaller than Keim found but "still reliably positive" to 2001. Booth and Keim (2000, cited by Schwert) find it not reliably non-zero in the investable DFA 9-10 portfolio in 1982-1995. Plastun et al. (DJIA, large caps): turn-of-year scores 0 from the 1990s onward.
- **Cost-floor note.** 0.565%/day × ~10 trading days ≈ 5.6% gross per event vs 26 bp for two legs. Real small-cap costs are far above 13 bp, and that is the limit to arbitrage.
- **Event rate (estimate).** 1 a year.
- **Applies to / testable here.** Equity cross-section: N (needs CRSP size deciles). Index (Santa Claus): partial (Yahoo). Crypto analog (small vs large coins over 1-15 January): Y.
- **Regime hypothesis.** Requires taxable holders forced to realise losses by 31 December. In crypto, the US wash-sale rule did not apply to crypto as of the scout's knowledge (recalled; check current law). Sellers could then rebuy at once, which predicts a December dip with NO January rebound.
- **Overlaps.** S-CAL-01, S-CAL-03, S-CAL-05 (month-of-year).

### S-CAL-05 Halloween indicator / "Sell in May and go away"
- **Fidelity.** A (the rule is exact and widely stated). The primary paper was not read; numbers come from a secondary page.
- **Sources.** Bouman and Jacobsen, "The Halloween Indicator, 'Sell in May and Go Away': Another Puzzle", AER 92(5):1618-1635, 2002, https://www.aeaweb.org/articles?id=10.1257/000282802762024683 (read: bibliographic page only). Quantpedia, "Market Seasonality Effect in World Equity Indexes", https://quantpedia.com/strategies/market-seasonality-effect-in-world-equity-indexes (read: full, secondary). That page summarises Jacobsen and Zhang, "The Halloween Indicator: Everywhere and All the Time", and Dichtl and Drobetz, SSRN 2439280 (neither read).
- **Rule.** Hold the national equity index from the close of the last trading day of October to the close of the last trading day of April; hold T-bills or cash from May through October. Monthly data suffice.
- **Primitive vs wrapper.** Primary P5. No wrapper.
- **Claimed mechanism.** The source calls it "another puzzle". Proposed explanations: lower summer participation (vacations), seasonal affective disorder (Kamstra, Kramer and Levi 2003, cited), an optimism cycle (Doeswijk, cited). No counterparty is identified; this is a seasonal risk-appetite story.
- **Published claim.** Bouman and Jacobsen (via Quantpedia): present in 36 of 37 markets, particularly strong in Europe. Jacobsen and Zhang (via Quantpedia): 108 markets over 319 years; winter returns exceed summer by 4.52%/yr (t 9.69), and by 6.25% over the past 50 years. Quantpedia's source table: winter minus summer 7.5% (1970-86) and 7.7% (1987-2003).
- **Decay and crowding.** Mixed. Dichtl and Drobetz: "strongly weakened or even diminished in recent years". Quantpedia's own out-of-sample backtest was "significantly negative", and it rates confidence "Weak". Zakamulin finds it robust internationally (via Quantpedia).
- **Cost-floor note.** Two switches a year cost 26 bp/yr vs a published 4.5-7.7%/yr spread. Cost is irrelevant here; statistical power is the constraint.
- **Event rate (estimate).** 1 a year per market, and markets are highly correlated.
- **Applies to / testable here.** Equities: partial (Yahoo monthly). Crypto: Y for data, but the archive holds only ~6-7 seasons, too few to resolve.
- **Regime hypothesis.** The SAD story predicts the pattern inverts in southern-hemisphere markets (the hemisphere-rotation variant). The vacation story predicts it weakens where participation is not seasonal (global 24/7 crypto).
- **Overlaps.** S-CAL-04 (month-of-year), S-CAL-16 (long-period calendar timing).

### S-CAL-06 Overnight vs intraday returns ("tug of war")
- **Fidelity.** A.
- **Sources.** Lou, Polk and Skouras, "A Tug of War: Overnight Versus Intraday Expected Returns", JFE 2019, https://personal.lse.ac.uk/polk/research/TugOfWar.pdf (read: full). Market-level papers: Cliff, Cooper and Gulen, "Return Differences between Trading and Non-trading Hours: Like Night and Day", SSRN 1004081, 2008; Kelly and Clark, "Returns in Trading versus Non-trading Hours: The Difference Is Day and Night", Journal of Asset Management, 2011 (both recalled, not re-fetched; the SSRN fetch failed).
- **Rule.** Lou, Polk and Skouras, monthly: drop stocks priced under $5 and those in the bottom NYSE size quintile. Intraday return = open-to-close, with the open defined as the VWAP of 09:30-10:00 (TAQ). Overnight return = close-to-close divided by intraday, minus 1. Sort into deciles on the past one-month cumulative overnight return and hold value-weighted decile 10 minus decile 1 only over the overnight periods (close to next open) of the next month. The mirror strategy sorts on past intraday returns and holds intraday only. Market-level variant (recalled): long the index from close to open, flat from open to close.
- **Primitive vs wrapper.** Primary P5 (a clock split of the return). Secondary P3 (cross-sectional sort) and P1 (persistence within each period). Wrapper: the VWAP-open definition and the microcap screen.
- **Claimed mechanism.** Different clienteles trade at different times. Small trades cluster at the open and large trades near the close. Institutions push characteristics such as value, size and IVOL intraday, while momentum demand shows up overnight. Each clientele partly reverses the other's price pressure. It persists because exploiting it means trading every open and close and financing overnight positions.
- **Published claim.** LPS (US, 1993-2013). Overnight-sorted 10-1: overnight 3-factor alpha 3.47%/month (t 16.83), intraday −3.02%/month. Momentum earns 0.98%/month (CAPM) overnight and ~0 intraday; size, value and IVOL earn intraday. CRSP VW market: 0.55%/month overnight vs 0.38% intraday. The pattern holds in nine non-US markets.
- **Decay and crowding.** None reported; in-sample the pattern persists at lags up to 60 months. No post-publication test was read.
- **Cost-floor note.** Overnight-only holding needs a round trip every day: 252 × 26 bp ≈ 66%/yr for a long-short, against ~42%/yr gross (3.47% × 12). So the decile spread does not clear our floor as a trade; at best it is a state to condition on.
- **Event rate (estimate).** About 252 nights a year, market-wide and date-clustered.
- **Applies to / testable here.** Equity cross-section: N (needs TAQ/CRSP). Crypto analog: Y. Split each coin's 24 h return into US cash-session hours (13:30-20:00 UTC in summer, 14:30-21:00 in winter) and the rest, then sort coins on past session returns.
- **Regime hypothesis.** Needs distinct clienteles active at distinct clock times. In crypto, the candidates are US-hours (institutional, ETF) flow and Asia-hours retail flow. It should weaken where the same algorithmic participants trade around the clock.
- **Overlaps.** S-CAL-07 and S-CAL-08 (session clienteles), S-CAL-02 (the weekend is a long overnight).

### S-CAL-07 FX time-of-day: currencies weaken during their own trading hours
- **Fidelity.** A.
- **Sources.** Breedon and Ranaldo, "Intraday Patterns in FX Returns and Order Flow", SNB Working Paper 2011-04 (later published in JMCB), https://www.snb.ch/en/publications/research/working-papers/2011/working_paper_2011_04 (read: full PDF).
- **Rule.** EUR/USD: short EUR over the European session (07:00-15:00 European local time, +5 h vs New York) and long EUR over the US session (08:00-16:00 New York time); flat otherwise. Session returns run open-to-close at the session boundaries. General form: "short the base currency in its own trading hours and long in the trading hours of the counter currency." Data: EBS bid/ask, 1997-2007, six pairs (EUR/USD, USD/JPY, GBP/USD, EUR/JPY, USD/CHF, AUD/USD). Entry times inside a session are not specified, and bank holidays are not excluded.
- **Primitive vs wrapper.** Primary P5; secondary P7 (order flow). Wrapper: the session boundaries.
- **Claimed mechanism.** Participants are net buyers of foreign currency during their own hours: international funds trade in local hours, and invoicing currency adds to it. EBS order flow shows local-currency selling in local hours. Liquidity providers are paid to absorb this home-hours demand.
- **Published claim.** Breedon and Ranaldo (EBS EUR/USD, 1997-2007, annualised log returns): EUR session −8.4% (GARCH −9.5%) and USD session +10.0% (+11.1%), all significant at 1%. After EBS bid/ask, the morning short earns 6%/yr (Sharpe 1.3) and the afternoon long 7%/yr (Sharpe 0.9).
- **Decay and crowding.** None reported; the read source does not cover the period after 2007.
- **Cost-floor note.** 8.4%/yr over ~252 sessions ≈ 3.3 bp per session, far below 13 bp. The source's profit relies on interbank EBS spreads, not taker costs like ours.
- **Event rate (estimate).** About 250 sessions a year per pair; one market-wide sample per day.
- **Applies to / testable here.** FX: partial (cached FX intraday; the vendor's timezone must be verified first). Crypto analog: Y (USDT-quoted coins in Asian vs US hours; see 08).
- **Regime hypothesis.** Holds while home-bias flows are executed in local hours. It weakens with 24 h algorithmic execution and with flows concentrating at fixing windows such as the London 4 pm fix.
- **Overlaps.** S-CAL-06, S-CAL-08, S-CAL-14 (month-end fix flows).

### S-CAL-08 Bitcoin hour-of-day (long 21:00-23:00 UTC)
- **Fidelity.** A for the rule as published. Two pages by the same publisher state the timing one hour apart (see Rule).
- **Sources.** Padyšák and Vojtko, "Seasonality, Trend-following, and Mean Reversion in Bitcoin", SSRN 4081000 (not read; SSRN blocked). Quantpedia, "Are There Seasonal Intraday or Overnight Anomalies in Bitcoin?", 18 Feb 2022, https://quantpedia.com/are-there-seasonal-intraday-or-overnight-anomalies-in-bitcoin/ (read: full). Quantpedia, "The Seasonality of Bitcoin", 13 Sep 2023, https://quantpedia.com/the-seasonality-of-bitcoin/ (read: full). Strategy page: https://quantpedia.com/strategies/intraday-seasonality-in-bitcoin (read: full). Counter-evidence: Baur et al. 2017 (card 02; read: abstract).
- **Rule.** Every day, buy BTC at 21:00 UTC and sell at 23:00 UTC; long only, flat otherwise; hourly BTC/USD from the Gemini crypto exchange. The strategy page instead says "open a long position at 22:00 (UTC+0) and hold it for two hours". The blog names the 22:00 and 23:00 hourly returns as the best, which fits bars labelled by their close, so 21:00-23:00 is the consistent reading. Variants: trade only when 30-day volatility is above its one-year median (checked at 00:00 UTC), or only in an uptrend by the 10/20/50/200-day MA.
- **Primitive vs wrapper.** Primary P5. Wrapper: the volatility filter and the MA trend filter.
- **Claimed mechanism.** Source: "the best time to trade (and hold) BTC is when every other major exchange is closed" (at 22:00-23:00 UTC the NYSE, Tokyo, Hong Kong and London are all shut). No counterparty is named. The worst hours are 03:00-04:00 UTC.
- **Published claim.** BTC/USD on the Gemini exchange, 2015-10-09 to 2022-02-03: 33%/yr annualised, volatility 20.93%. Max drawdown −22.45% on the blog, −34.04% with Sharpe 1.58 on the strategy page. Extended to 2023-06-30: 40.64%/yr, max drawdown −22.7%, Calmar 1.79; volatility-filtered 37.26%, max drawdown −18.87%. No costs; in-sample (the rule was picked from the same hourly table).
- **Decay and crowding.** The 2023 article says the strategy "had a rough period in 2022 and 2023". Baur et al. (seven exchanges) find time-varying effects with "no consistent or persistent patterns".
- **Cost-floor note.** 33-40.6%/yr over 365 trades ≈ 9-11 bp gross per trade vs a 13 bp round trip. As a standalone trade it is below our floor; at most it can time a position that is held anyway.
- **Event rate (estimate).** 365 a year, all market-wide (one sample per day).
- **Applies to / testable here.** Y (1m-1h klines for BTC and ~700 perps; 24 hourly buckets per coin).
- **Regime hypothesis.** If US-close flow drives it, the window should track US DST (it would move one UTC hour) and strengthen after the 2024 spot ETFs. A fixed UTC hour that ignores DST argues against that story. The source notes it suffers in bear markets because it is long-only.
- **Overlaps.** S-CAL-06 (the crypto overnight analog), S-CAL-07, S-CAL-09 (the 00:00 UTC funding stamp follows the window by an hour).

### S-CAL-09 Funding-settlement-time effect on perps (folklore)
- **Fidelity.** C. No primary source was found, and the search budget ran out before a dedicated search, so this absence is weak evidence. Not mechanizable as published.
- **Sources.** Binance FAQ, "Introduction to Binance Futures Funding Rates", https://www.binance.com/en/support/faq/introduction-to-binance-futures-funding-rates-360033525031 (read: full; schedule facts only). He, Manela, Ross and von Wachter, "Fundamentals of Perpetual Futures", arXiv 2212.06888 (read: abstract; nothing on settlement timing).
- **Rule.** Not specified by any source read. Folklore form (recalled, unsourced): when funding is strongly positive, longs close or hedge just before the settlement stamp to avoid paying and reopen after it, so price dips into the stamp and recovers; the mirror case applies when funding is negative. Window length and funding threshold: not specified.
- **Primitive vs wrapper.** Primary P5 (clock); secondary P4 (carry) and P6 (positioning). Wrapper: the threshold and the window.
- **Claimed mechanism.** Funding is paid only by positions open at the stamp. Binance's default stamps are 00:00, 08:00 and 16:00 UTC, with up to ~15 s deviation in charge time, and intervals can switch to hourly when funding hits its cap or floor. A payer can avoid funding by being flat for seconds around the stamp, which implies predictable exits before the stamp and re-entries after it. Counterparty: market makers who absorb the round trip. The limit: the payment avoided is usually much smaller than a taker round trip.
- **Published claim.** None found.
- **Decay and crowding.** Unknown.
- **Cost-floor note.** Baseline Binance funding is 0.01% per 8 h (recalled; the FAQ read did not state it). Avoiding it saves 1 bp against 13 bp to exit and re-enter, so the flow can only exist when |funding| per interval exceeds roughly 13 bp.
- **Event rate (estimate).** 1,095 stamps a year, market-wide and clustered. Stamps in tail-funding states are far rarer.
- **Applies to / testable here.** Y (1m klines plus funding history for ~700 perps). Each symbol's interval changes must be read from its funding timestamps.
- **Regime hypothesis.** Should appear only when |funding| is large relative to the round-trip cost, and only on 8 h-interval symbols. It should vanish on symbols moved to 1 h or 4 h intervals, where each stamp pays less.
- **Overlaps.** Carry-family cards (P4); S-CAL-08; S-CAL-14 (scheduled mechanical flow).

### S-CAL-10 FOMC calendar: pre-FOMC drift (rule A) and FOMC-cycle even weeks (rule B)
- **Fidelity.** A for both rules.
- **Sources.** Lucca and Moench, "The Pre-FOMC Announcement Drift", JF 70(1):329-371, 2015; FRBNY Staff Report 512, 2011, https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr512.pdf (read: full). Cieslak, Morse and Vissing-Jorgensen, "Stock Returns over the FOMC Cycle", JF 2019, NBER conference draft https://conference.nber.org/conf_papers/f74573/f74573.pdf (read: full, though the Table 3 strategy figures were missing from the fetched text), SSRN 2687614 (read: abstract). Kurov, Wolfe and Gilbert, "The Disappearing Pre-FOMC Announcement Drift", Finance Research Letters 40, 2021, https://www.skidmore.edu/economics/documents/KurovWolfeGilbert-TheDisappearingPre-FOMC-Announce-Drift-200914.pdf (read: full).
- **Rule.** A: buy the S&P 500 (index or E-mini) 24 h before a scheduled FOMC statement and sell 15 minutes before it. In 1994-2011 that meant 14:00 ET on the day before to 14:00 ET on announcement day, with statements at ~14:15 ET. Cash otherwise; unscheduled meetings excluded. B: day 0 is the scheduled announcement day (the second day of a two-day meeting), and days are weekdays. Hold stocks only in even FOMC weeks: week 0 = days −1 to +3, week 2 = +9 to +13, week 4 = +19 to +23, week 6 = +29 to +33. Be out in odd weeks.
- **Primitive vs wrapper.** Primary P5. No wrapper; both rules are pure holding windows.
- **Claimed mechanism.** Lucca and Moench call it a puzzle. Candidates are inattentive or slow-moving investors exiting before the news (Duffie) and an uncertainty premium; the VIX innovation explains 18 bp. Cieslak et al. propose a risk premium for Fed news, possibly leaked informally around the Board's bi-weekly discount-rate meetings. Kurov et al. link the drift to uncertainty (VIX). Counterparty: investors who de-risk ahead of Fed news.
- **Published claim.** A (SPX, Sep 1994 to Mar 2011, 131 meetings): +49 bp in the window (t > 4.5), about 80% of the equity premium, Sharpe 1.14. Similar in the DAX, FTSE, CAC, IBEX and SMI (29-52 bp); none in the Nikkei or Treasuries. B (1994-2013): 5-day mean returns of +0.57% (week 0) and +0.30/+0.42/+0.61% (weeks 2/4/6); odd weeks from ~0 to −0.17%. "The equity premium ... was earned entirely in weeks 0, 2, 4 and 6." Staying out in odd weeks gives Sharpe ~0.8 vs ~0.4 and ~+3 pp/yr.
- **Decay and crowding.** Kurov et al. (E-mini): Apr 2011 to Dec 2019 mean +4.7 bp over 70 meetings. Meetings with press conferences: +44.5 bp in 2011-2015, +9.2 bp in 2016-2019. The drift "essentially disappeared after 2015", alongside a lower VIX. No post-publication test of rule B was read.
- **Cost-floor note.** A: 49 bp per event ≈ 3.8x of 13 bp (1994-2011), and post-2015 ~9 bp, below the floor. B: about 3-4 round trips per cycle × 8 cycles ≈ 24-32 a year, i.e. 3.1-4.2%/yr of cost against a published gain of ~3 pp/yr.
- **Event rate (estimate).** A: 8 scheduled meetings a year. B: 8 cycles a year; the weeks within a cycle are not independent.
- **Applies to / testable here.** Crypto: Y (FOMC dates are public; the calendar must be verified). Equities: partial (cached NQ intraday).
- **Regime hypothesis.** Present when policy uncertainty is high (high VIX, uncertain rate path) and absent in calm, well-guided regimes such as 2016-2019. In crypto it should appear only in eras when BTC trades as a macro risk asset.
- **Overlaps.** S-CAL-11 (announcement premium), S-CAL-03 (holding into a scheduled event).

### S-CAL-11 Macro-announcement days (CPI/PPI, employment, FOMC) and pre-release drift
- **Fidelity.** A for the announcement-day rule. The pre-release drift is a finding, not a tradable rule.
- **Sources.** Savor and Wilson, "How Much Do Investors Care About Macroeconomic Risk? Evidence from Scheduled Economic Announcements", JFQA 48(2):343-375, 2013, draft https://faculty.wharton.upenn.edu/wp-content/uploads/2012/04/Draft20111128p_edited.pdf (read: full draft). Kurov, Sancetta, Strasser and Wolfe, "Price Drift before U.S. Macroeconomic News: Private Information about Public Announcements?", JFQA, draft 2017, https://www.skidmore.edu/economics/documents/KSSW2017-PriceDriftBeforeUSMacroeconomicNews.pdf (read: full draft).
- **Rule.** A (Savor and Wilson): hold the CRSP VW market (daily return) on days with a scheduled CPI release (before 1971) or PPI release (after), an employment report, or a scheduled FOMC announcement; cash on other days. B (Kurov et al.): prices drift in the direction of the coming surprise during [t−30 min, t−5 s] in E-mini and 10-year note futures. B cannot be traded without knowing the surprise's sign, so it is listed as information only.
- **Primitive vs wrapper.** Primary P5. No wrapper.
- **Claimed mechanism.** A: a premium for bearing macro "state variable" risk on the days it is resolved; volatility rises only modestly. B: leakage and superior forecasting from proprietary data. In A nobody is fooled: holders are paid to carry the risk.
- **Published claim.** A (CRSP VW, 1958-2009): 11.4 bp on announcement days vs 1.1 bp on other days; the Sharpe ratio is "ten times higher". B (2008-2014, second-by-second): 9 of 20 market-moving releases show drift, and on average drift is ~40% of the total price adjustment (49% in stocks, 36% in bonds). Drift was negligible in 2003-2007.
- **Decay and crowding.** Lucca and Moench (card 10) find no pre-announcement equity drift before non-FOMC macro releases. No test of rule A after 2009 was read.
- **Cost-floor note.** About 10 bp excess per announcement day vs a 13 bp round trip: below the floor as an in-and-out trade. It is useful only as "do not be flat on these days" for a position held anyway.
- **Event rate (estimate).** About 12 CPI + 12 PPI + 12 employment + 8 FOMC ≈ 35-44 a year (some coincide).
- **Applies to / testable here.** Crypto: Y, given a release calendar checked against public schedules. Equities: partial.
- **Regime hypothesis.** The premium should scale with macro uncertainty and with how macro-sensitive the asset is: in crypto, only in macro-correlated eras. CPI days should matter more in inflation-scare regimes than in the low-inflation 2010s.
- **Overlaps.** S-CAL-10, S-CAL-12 (scheduled firm-level information).

### S-CAL-12 Post-earnings-announcement drift (PEAD)
- **Fidelity.** B (the rule comes from a secondary description; the original paper was recalled).
- **Sources.** Bernard and Thomas, "Post-Earnings-Announcement Drift: Delayed Price Response or Risk Premium?", Journal of Accounting Research 27 (Supplement), 1989 (recalled, not re-fetched; the JSTOR fetch was blocked). Brandt, Kishore, Santa-Clara and Venkatachalam, "Earnings Announcements are Full of Surprises" (not read), as described at https://quantpedia.com/strategies/post-earnings-announcement-effect (read: full, secondary). Martineau, "Rest in Peace Post-Earnings Announcement Drift", Critical Finance Review, 2022 (recalled, not re-fetched).
- **Rule.** Universe: NYSE/AMEX/NASDAQ, excluding financials, utilities and stocks priced under $5. SUE = (actual EPS − seasonal-random-walk-with-drift forecast) / standard deviation of past surprises. EAR = abnormal return over the 3 days centred on the announcement. Sort into quintiles on SUE and on EAR using the previous quarter's breakpoints. Equal-weight long the top-SUE ∩ top-EAR stocks and short the bottom ∩ bottom. Enter on day +2 after the announcement and hold 60 trading days. The classic Bernard and Thomas form (recalled) uses SUE deciles, long top and short bottom, held about 60 days.
- **Primitive vs wrapper.** Primary P1 (continuation after a scheduled information event); secondary P5 (the event clock). Wrapper: the quintile sort, the 60-day horizon and the price screen.
- **Claimed mechanism.** Investors under-react to earnings news and anchor on naive forecasts. Bernard and Thomas (recalled) found part of the drift lands around the following announcements. Limits to arbitrage: small caps, idiosyncratic risk, cost.
- **Published claim.** Brandt et al. via Quantpedia (US, 1987-2004): the 60-day long-short is 2.97% − (−0.58%) = 3.55% per quarter, which Quantpedia annualises to ~15%/yr. EAR alone earns 7.55%/yr and EAR+SUE ~12.5%/yr; max drawdown −11.2%.
- **Decay and crowding.** Martineau (recalled): the drift has disappeared among large caps in recent decades. Quantpedia cites Kim and Kim (insignificant after a 4-factor adjustment) and notes returns are concentrated in small caps.
- **Cost-floor note.** 3.55% per 60-day hold vs 26 bp for two legs: well above our floor. Equity small-cap costs are higher than 13 bp.
- **Event rate (estimate).** ~4 events per stock a year, clustered into 4 earnings seasons. Market-wide, that is roughly 4 independent seasons a year.
- **Applies to / testable here.** N in the crypto archive (needs equity earnings dates, EPS and prices). Crypto has no earnings; token unlocks and listings belong to another family.
- **Regime hypothesis.** Works where attention is scarce: small caps, many simultaneous announcements, thin arbitrage capital. Fails for large caps once machine-read news is common.
- **Overlaps.** S-CAL-11; P1 momentum-family cards.

### S-CAL-13 Index inclusion and deletion (S&P 500)
- **Fidelity.** A for the event-study window. The tradable entry is not specified (see Rule).
- **Sources.** Greenwood and Sammon, "The Disappearing Index Effect", NBER WP 30748, 2022 (JF 2025), https://www.nber.org/system/files/working_papers/w30748/w30748.pdf (read: full). Origins: Shleifer, "Do Demand Curves for Stocks Slope Down?", JF 41(3), 1986; Harris and Gurel, JF 1986 (both recalled, not re-fetched).
- **Rule.** Event: an S&P 500 addition (deletion) announcement. The effective date follows after 4.8 days on average for additions and 5.8 for deletions. Source measure: market-adjusted return (stock minus S&P 500) from the day before the announcement to the day after the effective date. Tradable version (not specified by the source): buy additions (short deletions) at the first price after the announcement, exit at the effective-date close, and hedge with the index.
- **Primitive vs wrapper.** Primary P5 (scheduled effective-date flow); secondary P7 (an inelastic demand shock). Wrapper: the index hedge and the exit date.
- **Claimed mechanism.** Index funds must buy at the effective-date close whatever the price, and demand curves slope down (Shleifer). Arbitrageurs front-run and supply liquidity. Limited arbitrage capital and idiosyncratic risk let it persist.
- **Published claim.** Greenwood and Sammon (S&P 500, 1980-2020; 684 additions, 263 deletions). Additions, total effect: 3.42% (1980s), 7.59% (1990s), 5.21% (2000s), 0.80% (2010-2020, not significant). Deletions: −4.64%, −16.6%, −12.3%, −0.60% (not significant). Part of it reversed after the effective date in the 1990s and 2000s; little did in the 2010s.
- **Decay and crowding.** The paper's own finding: the effect disappeared in 2010-2020 even as the indexed share grew. Main driver: migrations from the S&P MidCap. Also more anticipation (the pre-announcement run-up reached 11.6% in the 2010s) and more liquidity provision (effective-date volume rose from ~15% to ~30%).
- **Cost-floor note.** 2010s: 0.80% per event vs 26 bp for two legs, about 3x but not significant. 1990s: 7.6%, far above.
- **Event rate (estimate).** About 17 additions a year after the source's filters (684 over 41 years). They are mostly date-independent.
- **Applies to / testable here.** N (needs the S&P change list and stock prices). Crypto analogs (exchange listings, crypto index or ETF basket changes) are a different event family and are not in the archive as events.
- **Regime hypothesis.** Large when index demand is inelastic relative to arbitrage capital and additions surprise the market (1990s). It vanishes when additions are predictable and migrations dominate.
- **Overlaps.** S-CAL-14 (mechanical rebalancing flow), S-CAL-15 (mechanical flow around expiry).

### S-CAL-14 Month-end and quarter-end rebalancing and liquidity flows
- **Fidelity.** A (the signal is constructed exactly in the full text; one appendix formula was not in the fetched text).
- **Sources.** Harvey, Mazzoleni and Melone, "The Unintended Consequences of Rebalancing", NBER WP 33554, 2025 (revised 2026), https://www.nber.org/system/files/working_papers/w33554/w33554.pdf (read: full except Appendix B). Etula, Rinne, Suominen and Vaittinen, "Dash for Cash: Monthly Market Impact of Institutional Liquidity Needs", RFS 33(1):75-111, 2020, https://ideas.repec.org/a/oup/rfinst/v33y2020i1p75-111..html (read: abstract summary; its exact day windows were not seen).
- **Rule.** Harvey et al.: simulate a 60/40 portfolio of the S&P 500 and the 10-year Treasury, rebalanced on the last business day of each month, with daily weights w_{t+1} = w_t(1+R_SP) / [w_t(1+R_SP) + (1−w_t)(1+R_10Y)]. Calendar signal = the drift in equity weight since the last rebalance. Threshold signal = the average, over bands δ from 0% to 2.5% in 0.1% steps, of the deviation beyond δ. Position: long S&P 500 futures and short 10-year futures, or the reverse. Weight = the average of (i) the sign-flipped, risk-scaled threshold signal and (ii) sign(−Calendar) during the last 5 business days of the month, sign(Calendar) on the first business day of the next month, and 0 otherwise. The position is set at close t and earns day t+1.
- **Primitive vs wrapper.** Primary P5; secondary P1 (contrarian to the month's stock-vs-bond move) and P7. Wrapper: the risk scaling and the threshold averaging.
- **Claimed mechanism.** Pensions and balanced funds mechanically sell the asset that outperformed at month or quarter end, or when a band is breached. That predictable flow pushes equities down and bonds up, it reverses within ~2 weeks, and front-runners profit. Etula et al.: month-end payment needs make institutions sell before month end, briefly raising the cost of capital.
- **Published claim.** Harvey et al. (daily, 1997-09-10 to 2023-03-17): a one-sd fall in the threshold signal predicts +20 bp next-day cross-asset return; equities move −17 bp (abstract). The strategy earns 10.20%/yr excess with volatility 9.17% and Sharpe 1.11 (0.90 excluding 2008-09 and March 2020), "close to 1" net of costs. CAPM alpha 9.61%/yr (t ≈ 5.4).
- **Decay and crowding.** The paper is too recent for post-publication evidence. Profits are higher in high-friction periods.
- **Cost-floor note.** About 6 active days a month; ~17-20 bp per signal-day vs 26 bp for two legs at our taker rate, so roughly at our floor (index and bond futures cost less in practice).
- **Event rate (estimate).** 12 month-ends a year plus threshold breaches, all market-wide.
- **Applies to / testable here.** Partial (needs daily S&P 500 and 10-year Treasury futures; Yahoo daily proxies). Crypto: no direct rebalancer, but Y for testing whether the stock-bond month-end signal spills over into BTC.
- **Regime hypothesis.** Largest when the month's stock-bond return gap is large and dealer balance sheets are tight (quarter-ends, crises); weak in calm, low-drift months.
- **Overlaps.** S-CAL-01 (the first-day reversal sits in the TOM window), S-CAL-13, S-CAL-07 (London 4 pm fix flows at month end; Melvin and Prins 2015, recalled, not re-fetched).

### S-CAL-15 Option-expiration week and strike pinning
- **Fidelity.** B (the rule comes from a secondary description; the pinning paper was recalled). The "max pain" variant is C.
- **Sources.** Stivers and Sun, "Returns and Option Activity over the Option-Expiration Week for S&P 100 Stocks", SSRN 1571786 (not read), as described at https://quantpedia.com/strategies/option-expiration-week-effect (read: full, secondary). Ni, Pearson and Poteshman, "Stock Price Clustering on Option Expiration Dates", JFE 78(1):49-87, 2005, https://ideas.repec.org/a/eee/jfinec/v78y2005i1p49-87.html (read: bibliographic page only; content recalled, not re-fetched). "Max pain": retail and crypto folklore, no source.
- **Rule.** Hold S&P 100 stocks (equal weight; the main variant uses the 28 stocks with the highest option open interest relative to shares) during the option-expiration week, the week ending on the Friday before the third Saturday; cash otherwise. Exact entry and exit days inside the week are not specified. Pinning (Ni et al., recalled) is a finding, not a rule: closes cluster at strikes on expiration days. Max pain (folklore): price drifts toward the strike that minimises option holders' payout; no parameters are specified.
- **Primitive vs wrapper.** Primary P5; secondary P7 (hedging flow) and P8 (the strike as a level, for pinning). Wrapper: the open-interest screen.
- **Claimed mechanism.** Option market makers hold short-stock delta hedges against customers' calls. As near-term open interest decays into expiry, they buy back those hedges, creating buying pressure. Implied volatility (perceived risk) also falls through the week. Pinning (recalled): hedgers who are net long gamma trade against moves away from strikes.
- **Published claim.** Quantpedia's derivation from Stivers and Sun Table 3 (1988-2010): 0.528% mean stock return per expiration week, ~9.3%/yr including ~4% cash, volatility 8.7%, Sharpe 0.61, max drawdown −15.14%. High-O/S 28-stock spread: 67.9 bp (1996 to mid-2002) and 70.7 bp (mid-2002 to 2008).
- **Decay and crowding.** None reported through 2008. Weekly and daily expiries since then (recalled) spread open interest away from the monthly cycle.
- **Cost-floor note.** 0.528% per event vs 13 bp ≈ 4x; 12 events a year.
- **Event rate (estimate).** 12 a year (monthly expiries), market-wide.
- **Applies to / testable here.** Partial. The expiry calendar is deterministic; for crypto, Deribit monthly options expire on the last Friday at 08:00 UTC (recalled). Options open interest is not in the archive, so the OI screen and max pain are N.
- **Regime hypothesis.** Holds when dealers are net short calls and the monthly expiry dominates open interest. It weakens when weekly and 0DTE options spread open interest out, or when customers are net short options.
- **Overlaps.** S-CAL-13 and S-CAL-14 (mechanical flow); P8 level cards (max pain).

### S-CAL-16 Bitcoin halving cycle (folklore)
- **Fidelity.** C. No primary source for a trading rule was found; not mechanizable as published.
- **Sources.** None for the rule. The block subsidy halves every 210,000 blocks; past halvings were Nov 2012, Jul 2016, May 2020 and Apr 2024 (recalled, not re-fetched). The stock-to-flow model (PlanB, 2019 blog; recalled, not re-fetched) is the most cited quantitative framing, but it is a valuation model, not a timing rule.
- **Rule.** Not specified. The folklore form (recalled, with no canonical parameters): accumulate in the year before a halving, hold to a cycle top some 12-18 months after it, then go to cash for the bear year. No source fixes dates, thresholds or a universe.
- **Primitive vs wrapper.** Primary P5 (a 4-year clock); P9 (a supply-schedule narrative). Every parameter is wrapper.
- **Claimed mechanism.** New supply (miners' selling) halves while demand stays put, so the price must rise, and the narrative draws in reflexive buyers. Against it: the schedule has been public since 2009, so a rational market would price it in. Any effect has to come from narrative-driven flow.
- **Published claim.** None from a primary source.
- **Decay and crowding.** Unknown. The folklore itself speaks of "diminishing returns" with each cycle (recalled).
- **Cost-floor note.** Negligible (1-2 trades per 4 years).
- **Event rate (estimate).** 0.25 a year: 4 halvings in BTC's history and 1-2 inside the perp archive.
- **Applies to / testable here.** The data exist (Y), but with ~1.5 cycles in the archive the test has no statistical power.
- **Regime hypothesis.** Plausible only while miner issuance is a material share of daily flow and retail narrative sets the marginal price. It should weaken as issuance shrinks relative to other flows (such as spot ETFs since 2024).
- **Overlaps.** S-CAL-05 (long-period calendar timing); P1 trend-family cards.

---

### Family notes
Every card carries P5, but there are really three mechanisms. (1) Scheduled mechanical flow: 01, 04, 09, 13, 14, 15. (2) Clientele by clock: 02, 06, 07, 08. (3) A premium for scheduled risk resolution: 10, 11, and possibly 03. Card 12 is P1 on an event clock. Several are the same idea in different wrappers: 01 and 14 (month-boundary flows), 10 and 11 (Fed and macro news), and 06, 07 and 08 (who trades when). Not mechanizable: 09, 16, Santa Claus and max pain. Market intraday momentum (Gao, Han, Li and Zhou, JFE 2018; recalled) was left uncarded as a P1-family item. Most effects decayed after publication; standalone crypto versions (08, 06-analog) price out under 13 bp.
