# Live earnings reading rubric (v0.29-live)

The scheduled reader follows this file exactly. Changing it changes the experiment, so any edit needs
its own DEVLOG entry.

## The question

For each packet in `queue/<T>.json`, answer this:

**From tomorrow's open (the first session after decision date T), will the stock be higher or lower
at the close 20 trading sessions later?**

The release came out on T−1, and the first reaction (close T−2 → close T) has already happened.
That reaction is in the packet and is already in the price. You are not predicting the reaction. You
are predicting the next 20 sessions after it.

## Inputs: the packet only

Each packet holds EPS vs the pre-release consensus (Nasdaq), `s1` (surprise ÷ the traded price before
the release), the two-day reaction vs SPY, and the first ~2,500 words of the company's earnings press
release (SEC 8-K, exhibit 99.1).

Use nothing else: no web searches, no later prices, no news written after T. This keeps every call
reproducible and free of hindsight.

## Output

Write a JSON list with one object per packet:

```json
[{"ticker": "NKE", "direction": "DOWN", "confidence": 0.62, "reason": "≤ 30 words citing the decisive facts"}]
```

`confidence` runs from 0.50 to 1.00. It is the probability that `direction` is right.

## Confidence scale

| confidence | meaning | trade |
|---|---|---|
| **0.50** | **Default.** No view, or the facts conflict. | none |
| 0.55-0.60 | A lean: one decent reason. | none |
| 0.65 | Moderate: two reasons pointing the same way. | none |
| **0.70** | A clear case from several independent facts. You expect to be wrong 3 times in 10. | **1% of portfolio** |
| 0.80 | Strong, with nothing material on the other side. | 1% |
| **0.90+** | Exceptional. You expect to be wrong 1 time in 10. A few per season at most. | **2% of portfolio** |

Start every packet at 0.50. Move away only for reasons you can state, and keep the reason in the
`reason` field.

## What has evidence behind it (weigh these)

1. **Guidance beats the quarter.** A raised or cut full-year outlook carries more information than
   the quarter's beat or miss.
2. **Quality of the surprise.** Separate operating beats from one-offs: tax benefits, investment gains,
   tariff refunds, accounting changes. A beat made of one-offs is weak.
3. **Drift.** Historically, large surprises keep drifting in their direction for weeks. The effect
   has weakened in large caps, and the v0.28 backtest measures how much is left. Without other
   support, a big surprise on its own is a lean (0.55-0.60), not a trade.
4. **News and reaction disagree.** A strong release that fell, or a weak one that rose, means the
   market saw something the headline did not show. Lower your confidence toward 0.50 instead of
   arguing with the tape.
5. **Base rate.** Stocks rose in 54.5% of 20-session windows in the v0.28 data, so a bare
   "UP at 0.55" restates the base rate. It is not a view.
6. **What the numbers alone can justify.** On 44,208 events (2018-2026), a calibrated model using
   only the EPS surprise and the reaction never went above 0.61. If your case rests on those two
   numbers, the honest ceiling is about 0.60. Reaching 0.70 needs specific information in the
   release that the model cannot see: a guidance change, one-offs, segment detail, or a change in
   capital allocation. Name it in the reason.

## Rules

- No press release in the packet (`missing_press_release: true`): decide from EPS and the reaction
  only, with a maximum confidence of 0.60.
- Do not let the size of the reaction set your confidence on its own.
- Never round up to reach a trading threshold. Calibration is scored: if 0.70 calls win well under
  60% over 100+ trades, the reading is overconfident and the experiment says so.
- Each packet is judged on its own. Do not balance longs against shorts, and do not aim for a
  number of trades.
