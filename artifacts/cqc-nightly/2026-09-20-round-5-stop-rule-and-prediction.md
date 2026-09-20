# Round 5: stop rule and pre-registered prediction

Written from the six-hats pass of 2026-09-20, before round 5's result exists. Purpose: an
evidence-bound failure mode has now moved layers five times without failing, and without a
pre-registered stop rule this loop can run forever.

## The observed pattern (White)

| Verdict | Tool revision | Where the surviving fail-open lived |
|---|---|---|
| review 1 | `1ac082d` ratings | classifier / policy layer |
| review 2-4 | `5dc1759`, `db513ed`, `3456195` | per-shape guards, 8 shapes |
| review 5 | `72b391c` | no verdict (reviewer killed) |
| Option A review | `de7ede14` | **inside the element evaluators** |

Each round the *verdict layer* got stronger and the surviving defect moved one layer down.
Nobody has yet shown the regress is finite.

## Pre-registered prediction (Black)

Round 5 will close the three reproduced HIGHs — boolean-as-measurement, count
inconsistency, freshness-without-age — and will then FAIL on a **new layer**: a measurement
object that is well-formed and correctly shaped but whose *value* was not derived from the
data it claims to measure. Most likely a probe of the form "measurement present, provenance
field populated, value not reproducible from the query".

If that happens, the finding is not a bug report — it is the signature of an unbounded
proof obligation over a whole program, and it should be read as such.

## Stop rule (Blue)

- Round 5 is the last structural round on the report tool.
- **If round 5's review finds the three reproduced shapes closed**, the tool may proceed to
  the merge gate on the strength of that review.
- **If round 5's review finds a defect in a NEW layer rather than a repeat of the three
  reproduced shapes**, the loop stops. The remedy then is Option B or C from the decision
  packet (`2026-09-20-decision-packet-cqc-report-tool-after-option-a.md`) — never an
  unbounded round 6.
- **If round 5's review repeats one of the three reproduced shapes**, that is a builder
  failure and a corrected round is warranted on that ground alone.

## Falsification condition for this artifact

This stop rule is wrong if the tool reaches a review with no surviving defect in any layer
— in which case the regress was finite all along and rounds 1-5 were the cost of getting
there honestly.

## The instrument that makes the rule decidable

A reviewer-authored **executable mutant oracle** (`evidence_mutant_oracle.py`, five
families including the provenance layer predicted above) is being authored on the reviewed
parent `de7ede14`. It proves its own power by escaping on `de7ede14` and must block on the
fixed revision. An argument between a builder and a reviewer about whether a shape is
closed becomes a test that either blocks the mutant or does not.

Independent of every verdict above: no threshold was weakened, no fabricated data was found
in any review, and the secrets scans are clean on every artifact. The one defect in this
whole stream with a *safety* character — a committed green attestation without the evidence
it claims — is closed and independently verified (`6ac1888`).
