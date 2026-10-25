---
description: Run the edge-finding team (you are the chair). Takes a family name or "next" from the backlog.
argument-hint: <family | next>
---

You are the **Chair** of the edge-finding team for this repo. Family to work on: `$ARGUMENTS`
(if it says `next`, take the first unexplored family in `docs/EDGE_LAB.md` section 6).

Subagents cannot launch other subagents, so you orchestrate them from here. The five are
`mechanism-scout`, `data-engineer`, `quant-builder`, `edge-auditor`, `edge-statistician`.
Read `CLAUDE.md`, `docs/HANDOFF.md` sections 3, 4 and 11, and `docs/EDGE_LAB.md` before you
start. The rule that makes this work: **no agent grades its own work.** Scouts never see
results, builders never see the verdict era, the auditor never wrote the engine, the
statistician never wrote the hypothesis.

Create a task list with TaskCreate for the gates below and keep it current.

## Gates, in order. Do not skip one.

**Gate 0, ideas.** Run `mechanism-scout` on the family (it may be run in parallel with
different sub-families; scouts only read). Keep only cards that pass the five-point screen in
`docs/failure_path.md` and predict a gross excess of at least ~40 bp per trade. Drop the rest
and say why. If all cards fail, stop and report; zero hypotheses is a valid outcome. After
three consecutive families produce nothing, stop the batch and tell the user.

**Gate 1a, can the test resolve the claim? (before any download).** `edge-statistician` runs
the power check on the card's own numbers, using DATE-CLUSTERED independent events (one crash day
yields many coin entries, so coin-entries are not independent samples), not coin-entries, and
using only the USABLE history (check when each required archive actually starts). If the minimum
detectable edge exceeds the predicted edge, shelve the card. This costs minutes; the v0.35 batch
spent hours of downloads on cards this check would have shelved.

**Gate 1b, data and pre-registration.** For each card that passed 1a: `data-engineer` produces
the outcome-blind data report (cap the download scope up front and say what is cut);
`edge-statistician` drafts `research/prereg/<id>.md`. If the counts then show the verdict era
cannot resolve the claim, shelve it rather than open it. Otherwise **you** review the
pre-registration, commit it, push it, then
`ledger.register(path, family=..., n_cells=..., primaries=..., require_pushed=True)`.
Nothing past this line runs until it succeeds.

**Gate 2, engine.** `quant-builder` writes the engine and the self-tests, outcome-blind
(`--selftest`, `--funnel`, one crash-only smoke run). It does not read results.

**Gate 3, audit.** `edge-auditor` runs stage A. If REJECTED, the builder fixes it and the
auditor starts again from item 1. On APPROVED, you call
`ledger.mark_audited(id, note)`.

**Gate 4, the verdict era, once.** Run `--report` (its first action is
`ledger.open_holdout`, which refuses a second look). Then `edge-statistician` judges the
result against the pre-registered bars and `ledger.total_trials()`. On a pass, `edge-auditor`
runs stage B. Call `ledger.record_verdict`.

**Gate 5, record and report.** Write the DEVLOG entry (newest first, verdict in the heading,
numbers, what failed and why), add the row to HANDOFF section 4, add a CLAUDE.md lesson only
if a new way of going wrong appeared, commit and push. Then tell the user in plain words: the
verdict, the reason, the numbers, the comparison to their real alternative (the 80/20 VGS/VAS
hurdle, or the hedged alpha for a market-neutral sleeve). Offer the next test and do not start
it unasked.

## Rules for you

- Every screen you run outside a pre-registration goes into `ledger.log_exploration(...)`.
  The trial count is the one number nobody may lose.
- No more than 20 exploratory cells in a session without the user's say-so.
- A pass is a claim, not a result, until stage B has failed to break it.
- Report failures as plainly as passes. The user's best outcome here is a correct answer, and
  a correct "no" is worth as much as a "yes".
- Develop on the branch the repo names in HANDOFF; open no pull requests unless asked; never
  put a model name or identifier in a commit, code comment or committed doc.
