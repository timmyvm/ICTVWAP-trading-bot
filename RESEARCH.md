# ICT + VWAP: what the evidence actually says

Synthesis of a deep-research pass (5 search angles, primary-source fetches with
claim extraction) reconciled with this repo's own backtests. Stopped before the
full adversarial-verification stage to save budget, so treat this as
well-sourced but single-pass — links are primary sources, read them.

## 1. Is ICT/SMC real? The mechanism yes, the rulebook unproven

The strongest evidence comes from Carol Osler's FX microstructure work, using
actual dealer order books (not chart patterns):

* **Stops and take-profits genuinely cluster at salient levels.** Take-profit
  orders cluster AT round numbers (~10 % of all orders end in 00); stop-losses
  cluster just BEYOND round numbers and prior highs/lows. "Liquidity pools at
  old highs/lows" is documented microstructure, not folklore.
  — Osler, *Currency Orders and Exchange-Rate Dynamics*, **Journal of Finance
  (2003)** ([free NY Fed version](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr125.html))
* **Triggered stop clusters cause self-reinforcing price cascades** — sweeps
  accelerate trends. Critically, the response to stops is **larger and lasts
  longer** than the mean-reverting response to take-profits: at swept levels,
  *continuation dominates reversal*. Naively fading every sweep is
  counter-evidence — which is exactly how our bot lost $825 buying the March
  crash. — Osler, *Stop-Loss Orders and Price Cascades in Currency Markets*,
  [NY Fed Staff Report 150](https://www.newyorkfed.org/medialibrary/media/research/staff_reports/sr150.pdf)
* **Pre-identified support/resistance levels do predict intraday bounces — by
  ~4–6 percentage points over random levels** (≈60.8 % vs 56.2 %), decaying
  over ~5 days, and varying a lot by who drew the levels. A real but *thin*
  edge, nothing like the near-certainty course marketing implies — and thin
  edges die to taker fees. — Osler, *Support for Resistance*, [FRBNY Economic
  Policy Review 2000](https://www.newyorkfed.org/medialibrary/media/research/epr/00v06n2/0007osle.pdf)
* The only formal study of a named SMC construct found: an SSRN preprint on
  **32,202 Fair Value Gap events** — slowly-forming FVGs produce ~3.2× stronger
  reactions (p<0.001). It measures reaction strength, **not net-of-fees
  profitability**, and is not peer-reviewed.
  — [Kondapally, *Quantifying Fair Value Gaps*, SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6032676)

**Nothing found validates the assembled ICT rulebook** (OTE 0.62–0.79, order
blocks, rejection blocks, NWOG, session filters) as a profitable mechanical
system. The evidence supports two narrow claims — levels attract reactions;
broken levels accelerate — and our backtest agrees: the *short* side (trading
with the cascade) was net positive; every counter-trend long lost.

## 2. VWAP mean reversion on 5m crypto: the math says no at retail fees

* Intraday reversal in BTC **exists but is state-dependent** — it flips to
  momentum around large jumps, news, and liquidity shifts. An unconditioned
  ±2σ fade trades both states and nets ≈ zero gross — matching our gross
  −$650 / 60d. — Wen, Bouri, Xu, Zhao, [*Intraday Return Predictability in
  Crypto*, SSRN 4080253](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4080253)
* Once realistic costs are imposed, high-turnover BTC strategies "**collapse
  into persistent decline**" at ~10 bps round trip (walk-forward evidence) —
  our fee bill was 85 % of the VWAP loss at 7.5–11 bps. —
  [arXiv 2606.00060](https://arxiv.org/abs/2606.00060); see also Beluská &
  Vojtko, [*Revisiting Trend-following and Mean-Reversion in Bitcoin*,
  SSRN 4955617](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4955617)
  (69 rules tested with/without costs; prior crypto TA work "largely ignored"
  them).
* **Switching to maker entries is not free money**: passive limit orders
  suffer fill-probability and adverse-selection costs — they miss the winners
  and fill preferentially on the reversals. — [*The Market Maker's Dilemma*,
  arXiv 2502.18625](https://arxiv.org/html/2502.18625)
* Fee floor per [Bybit's schedule](https://www.bybit.com/en/announcement-info/fee-rate/):
  0.055 %/0.02 % non-VIP, falling toward ~0.03 %/0 % at VIP tiers. Viability
  rule of thumb from the cost literature: **expected move per trade ≥ 3–5×
  all-in round-trip cost**. Ours was ~1×. That ratio — not signal quality —
  is why Strategy B bleeds.

## 3. Why "backed by thousands" strategies fail honest backtests

* **A handful of configuration trials near-guarantees a great in-sample
  backtest, and overfit strategies have *negative* expected out-of-sample
  returns.** Social-media proof never reports how many variants were tried.
  — Bailey, Borwein, López de Prado, Zhu, [*Pseudo-Mathematics and Financial
  Charlatanism*, Notices of the AMS 2014](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2308659)
* **Small samples make raw metrics uninformative** — ~20 trades/180 days is
  exactly the regime where a Sharpe ratio needs deflation for trials and fat
  tails. — [*The Deflated Sharpe Ratio*](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551)
* **The overfit probability is measurable**: split history into blocks,
  recombine train/test partitions, count how often the in-sample winner loses
  out-of-sample (PBO/CSCV). — [Bailey et al., *The Probability of Backtest
  Overfitting*](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf)
* ICT-specific failure modes: heavy **discretion** (Osler showed level-drawing
  skill varies by practitioner — a mechanized version doesn't inherit a
  discretionary trader's levels), **survivorship** (losers stop posting), and
  **unfalsifiability** (a failed setup is retroactively "not a valid setup").
* **Honest self-critique that applies to US:** relaxing the tier floors until
  trades appeared is itself a configuration search. The +$378-gross ICT result
  is in-sample evidence only until it survives walk-forward / PBO testing.

## 4. What to do, in order of evidence strength

1. **Trade with the cascade, not against it.** Block counter-trend entries
   while 4H/1D structure disagrees (Osler's asymmetry + our March longs).
   Shorts-only in our 180d window was net positive at current fees.
2. **Enforce a minimum target distance ≥ 3× round-trip cost** (~0.15–0.3 % of
   price at current fees). Skip nearest-DOL targets closer than that; 3-minute
   median holds cannot out-earn the fee line.
3. **Fix the cost side**: VIP/maker fee tiers or a cheaper venue multiply the
   set of viable trades more reliably than any signal tweak — but model
   maker fills with adverse selection, not as free fee savings.
4. **Shelve 5m VWAP ±2σ** unless redesigned around the ratio rule (wider
   bands / higher timeframe / jump-and-news conditioning per Wen et al.).
5. **Harden the iteration loop**: walk-forward splits, cost-sensitivity
   sweeps, a 50+ trade minimum before believing any number, and track every
   configuration tried so significance can be judged against the trial count
   (DSR/PBO). `run_backtest.py --days 180` is the start, not the finish.

*Caveats: source claims were extracted but the 3-vote adversarial verification
stage was cut for budget; two fetched sources were auto-flagged unreliable and
discarded. Osler's data is 1990s dealer FX — mechanism transfer to 2026 crypto
perps is plausible (same stop-clustering logic, 24/7 liquidations) but not
itself proven.*
