# ICT 2022 Mentorship — distilled mechanizable rules

Source: Michael J. Huddleston (ICT), 2022 Mentorship Ep. 2 "Elements of a
Trade Setup" and Ep. 3 "Internal Range Liquidity & Market Structure Shift"
(user-supplied transcripts; raw text intentionally not committed). This file
contains only rules that can be written as code, mapped against the bot.
Discretionary nuances are logged at the bottom but not mechanized — per
RESEARCH.md, that's where mechanization degrades.

## The 2022 model, as taught (bearish version; mirror for longs)

1. **Weekly bias**: before the week opens, judge which way the weekly candle
   is likely to EXPAND (not close). That is the week's directional filter.
2. **Daily chart = the liquidity map.** Old daily highs/lows are the draws on
   liquidity; "the majority of your analysis should be linked to this
   timeframe."
3. **Intraday sequence**: consolidation → break DOWN first through sell stops
   (inducement, "sucker play") → run UP through buy-side liquidity —
   *relative equal highs preferred* ("engineered liquidity") → then a
   **market structure shift** down on the 1–3m → price retraces into the
   **fair value gap** left by the displacement → short inside the FVG.
4. **Stops**: above the swept high or the FVG-forming candle's high.
5. **Targets**: "low-hanging fruit — the closest target, don't get fancy."
   Sequence of sell-stop pools and opposing imbalances; frame the intraday
   displacement range with its 50 % level (premium/premium exit → discount).
6. **Killzones**: trade 8:30–11:00 NY (extendable to noon); avoid 12:00–13:00;
   afternoon 13:30–16:00 is a separate regime. Session key levels whose
   highs/lows serve as sweep candidates: Asia 19:00–21:00, London 02:00–05:00,
   NY 07:00–10:00 (all NY time), plus the pre-9:30 intraday high/low.
7. **MSS validity (Ep. 3 core rule)**: a swing break is significant ONLY when
   the move preceding it traded INTO a liquidity pool. Sweep first, then
   shift — a break without a sweep is noise. The sweep itself needs only a
   wick through the level (no close beyond); the SHIFT needs a candle CLOSE
   beyond the short-term swing.
8. **Order block (his definition)**: the last consecutive series of
   opposite-close candles before displacement; its OPEN price extended in
   time is the entry level — valid ONLY with sweep + MSS + FVG present.

## Map against the bot (v0.5)

| Rule | Status in bot | Candidate |
|---|---|---|
| Sweep required before entry | ✅ RB detector requires it | — |
| Nearest-liquidity TP | ✅ matches ("closest target" — also confirmed empirically: retargeting farther failed, v0.4.1) | — |
| Premium/discount framing | ✅ via 1H fib EQ (ICT anchors to the intraday displacement range — minor difference) | — |
| D1 as directional anchor | ✅ new in v0.5 | validate |
| M15 MSS before entries | 🔶 v0.5 has plain swing-break MSS; ICT requires **sweep-coupled** MSS | **R1** |
| Old DAILY highs/lows in the DOL/TP map | ❌ DOL map uses 1h/4h swings, session opens, sus candles — not daily extremes | **R2** |
| Killzone windows | 🔶 ours: NY 9:30–12:00, London 3:00–6:00; ICT: NY 8:30–11:00, London 2:00–5:00 | **R3** |
| FVG-based entry (displacement imbalance) | ❌ we enter at RB open | **R4** |
| Relative-equal-highs preference for sweep targets | ❌ all swing levels treated equally | R5 |
| Weekly expansion bias above D1 | ❌ | R6 |
| Order-block entry refinement | ❌ | R7 |

## Test queue (one change at a time, pre-registered criteria, DEVLOG entry each)

1. **R1 — sweep-coupled MSS**: the M15 MSS gate only passes if the structure
   break followed a sweep of a tracked pool (session H/L, old daily H/L,
   relative equal highs). Directly tightens v0.5's weakest new part.
2. **R2 — daily extremes into the DOL map**: cheap (df_1d already flows) and
   per Ep. 2 the daily levels are THE draws; should improve TP realism.
3. **R3 — killzone alignment**: shift session windows to 8:30–11:00 / 2–5.
4. **R4 — FVG entry mode**: enter on retrace into the displacement FVG
   instead of the RB open (bigger change; only after R1–R3 verdicts).

## Logged but NOT mechanized (discretionary)

- Two stacked FVGs: sacrifice the better (lower) one, enter the upper after
  the lower is tapped.
- "Nix the trade" if price visits the premium array before the discount one.
- Speed/magnitude "feel" for how price draws to a level ("that's experience —
  I can't transfer it").
- Partial-taking choreography across successive pools.
