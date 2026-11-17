# V1.2 Rule-Registered Event Engine

This is an auditable classroom engine, not a calibrated Starbucks operating model.
Events submit inputs to pre-registered rule functions; event authors cannot write
arbitrary before/after state values.

## Run tests

From the repository root:

```bash
python -m unittest discover -s courses/starbucks-2008/tests -v
```

## Contract

- A rule registry maps each rule_id to an executable function and immutable, pre-registered parameters.
- Events contain rule invocations and inputs, not author-supplied state deltas.
- Unregistered rules, invalid inputs, unknown state fields, duplicate event IDs and unresolved dependencies fail.
- Every event has a timezone-aware simulation timestamp.
- Parallel tasks may overlap in calendar time; state commits are deterministically ordered by sim_time, sequence and event_id.
- Index arithmetic requires matching base period and base value.
- Evidence grading is a design guardrail, not a causal-effect estimator.
- NPC trigger evaluation records both fired and non-fired conditions with reasons.
- V1.0 MOVE 001–005 are loaded as the first legacy fixture; MOVE 003's accounting conflict and MOVE 004's missing sub-action prices remain visible.

## Deliberate limits

The illustrative strategy rule exists to test branch sensitivity under fixed parameters.
Its parameters are classroom assumptions, not empirical estimates. A passing T7 test
demonstrates deterministic path divergence, not which strategy would have won in reality.

The engine does not yet implement full NPC planning, a validated historical information
release gate, a complete task scheduler, or a calibrated business-state model.
