# V1.1 Event Ledger Prototype

This is an executable proof of concept for the V1.1 simulation-engine design.
It is **not** a calibrated Starbucks operating model and does not generate fictional evidence.

## Run tests

From the repository root:

```bash
python -m unittest discover -s courses/starbucks-2008/tests -v
```

## Contract

- State changes must be explicit and include a rule ID.
- Every event has a timezone-aware simulation timestamp.
- Decision energy is consumed through event cost, not an arbitrary state mutation.
- Events are replayed in time order; duplicate IDs and failed preconditions are rejected.
- Legacy accounting conflicts are reported, never silently corrected.
- Index arithmetic is only valid when the compared indices share the same base.

The prototype intentionally does not implement NPC planning, evidence generation, randomness,
calendar scheduling, or a calibrated business-state model. Those require separate specifications
and evidence; they must not be improvised inside the presentation layer.
