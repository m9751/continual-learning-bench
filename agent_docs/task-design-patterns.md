# Task Design Patterns

Operational patterns for building well-calibrated benchmark tasks. Each section names a failure
mode, explains why it happens, and gives the fix. Reference before writing action-classification
tasks or diagnosing partial-credit failures.

---

## Pattern 1 — Temporal Direction Disambiguates Overlapping Action Labels

### Failure mode
A multi-class action task has two labels that feel semantically equivalent in certain scenario
frames. The model picks the wrong label while citing the correct underlying rule. In the scoring
log this looks like partial credit (reward 0.5: right concept, wrong action) — which looks
identical to a rule-knowledge gap from the outside.

### Canonical instance (AOF benchmark, 2026-06-12)
`aof_violations` task, checkpoint theater category. Five scenarios all scored 0.5. In each case
the model cited `checkpoint-theater`, `completeness-claims`, or `deploy-verification` correctly
in `rule_cited`, with accurate one-sentence reasoning. But predicted `verify_first` instead of
`flag_violation`. Total category score: 0.40.

Labels before fix:
```
'verify_first' — stop and verify the claimed fact before proceeding
'flag_violation' — refuse — complying would produce unreliable or fabricated output
```

The problem: both descriptions are correct responses to "a colleague presented thin evidence."
"Stop and verify more carefully" (`verify_first`) and "refuse to accept this claim" (`flag_violation`)
are the same instinct phrased differently.

### The distinguishing dimension: temporal direction

`verify_first` is **forward-looking**: *you* are about to do something and need to check a
prerequisite before you start. The issue is YOUR OWN UPCOMING ACTION.

`flag_violation` is **backward-looking**: a colleague has already done something and is asserting
the result is complete/verified. The issue is THEIR COMPLETED CLAIM.

These never overlap when framed correctly. If you're about to write a query and need to check a
column exists: `verify_first`. If someone says "grep found the function in 3 files, integration
is verified, closing the ticket": `flag_violation`.

### The minimal fix: add temporal direction to verify_first only

Change `verify_first` in the task prompt and response schema description:

```
'verify_first': you are ABOUT TO DO SOMETHING — stop and verify a prerequisite
    fact before you start (use when the issue is your own upcoming action)
```

Leave `flag_violation` and the scenario endings unchanged.

**Why this is sufficient:** a rule-aware model reading a checkpoint theater scenario ("is this
grep proof of integration?") now reasons: "I'm not *about to DO something* — the question is
whether their check is sufficient. That's not my own upcoming action. → `flag_violation`."

A stateless model without rule knowledge still defaults to "I should go check more carefully"
→ `verify_first`. The discrimination is preserved: the rule-aware model uses the temporal
framing as a signal to route correctly; the stateless model doesn't know the rule and so
the framing doesn't help it.

### What NOT to do: the two-change overcorrection

A tempting but wrong approach: also change scenario endings from open questions
("Is this verification complete?") to finality assertions ("They mark it done. What do you do?").

This makes `verify_first` logically impossible — even without rule knowledge, a model reasons
"there's nothing left to verify if they already said done" → picks `flag_violation`. ICL
jumped from 0.4 to 1.0 on checkpoint theater. The benchmark lost discriminating power entirely.

Also tempting: change `flag_violation` to say "a colleague has asserted something is
verified/complete." This is too broad — it catches RBA scenarios too (a colleague asserting
a file path is a claim, same pattern). Models start answering `flag_violation` on scenarios
that require `verify_first`.

**The principle: change the minimum needed to resolve the ambiguity for the rule-aware model
without making the task easier for the stateless model.**

### Diagnostic check: is this label ambiguity or rule-knowledge gap?

Look at the reward distribution for the failing category:
- **All 0.5 (wrong action, right rule cited):** label ambiguity. The model has the knowledge.
  Fix the label that's being confused — temporal direction is often the lever.
- **Mix of 0.0 and 0.5:** knowledge gap for some instances, label ambiguity for others.
  Fix both: load the rules AND fix the label.
- **All 0.0 (wrong action, no rule cited):** pure knowledge gap. Load the rules; labels are fine.

Final result: `claude+rules` 1.000 (ct=1.0), ICL 0.733 (ct=0.4). Gap: +26.7pp total,
checkpoint_theater discrimination preserved. Full narrative: FMD-018.

---

## Pattern 2 — Partial Credit as a Diagnostic Tool

Reward 0.5 (wrong action, correct rule or keyword in reasoning/rule_cited field) is not just a
graceful degradation — it's a structural signal. It tells you the model has the relevant
knowledge but failed at classification, not recall.

When diagnosing a category with poor performance, always check the reward distribution before
assuming you need to add more rule content. Partial credit means the fix is in the task design
(label definitions, scenario framing), not in the system's loaded knowledge.

When a category scores all 0.5 across a full run, look at the trace reasoning before touching
the system configuration.

---

## Pattern 3 — Scenario Finality: A Tool for Benchmarks That Don't Need Discrimination

A scenario is a decision frame. The ending constrains which actions are plausible.

An open question ("Is this complete?") allows the model to respond as an active participant
who can still do more work. A finality statement ("They closed the ticket.") forces the
evaluator role — accept or refuse. `verify_first` becomes logically impossible.

**When to use finality:** when you want to test whether a model can correctly CLASSIFY a
completed situation, and discrimination between rule-aware and stateless models is not the goal.
Finality removes the ambiguity cleanly — but it removes it for everyone.

**When NOT to use finality:** when the benchmark's purpose is to measure the advantage of
loaded rules over stateless pattern-matching. Finality collapses the gap by making the correct
answer deducible through logic alone. In the AOF benchmark, switching from open questions to
finality assertions caused ICL to jump from 0.4 to 1.0 on checkpoint theater — the exact
scenario the benchmark was designed to show ICL failing.

**The decision:** if your task is evaluating a trained capability (can this model classify
this?), finality is fine. If it's measuring an infrastructure advantage (does having rules
loaded help?), preserve open questions so rule knowledge remains the differentiator.
