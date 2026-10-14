# Recovered scalar comparisons in executable graphs

`engine.animation_decisions` implements the six float32 comparisons documented
in [grab-direction findings](../systems/animations/decisions/CLIENT_GUIDE.txt).
The recovered equality test is `abs(F(F(left)-F(right))) <= F(1e-5)`; inequality
is its logical negation. Relational tests use float32 operands without epsilon.
Unknown operators return false. NaN makes only NotEquals true; equal infinities
also produce an unordered subtraction for equality. Finite values overflowing
float32 convert to signed infinity in this implementation.

The API also decodes the verified 184-byte comparison-record variant: exact
comparison/input-port signatures, constant integer operator, named scalar runtime
parameter, and constant float threshold. It rejects other binding variants.
It resolves a predicate, not an outgoing graph edge or clip identity. Five
selected original encoded examples match their prior decoded predicates in the
[validation receipt](animation_decisions_validation.json). Payloads stay private.

## Graph expression schema

```python
condition = {
    "compare": "Equals",
    "left": {"input": "GrabPadIntensity"},
    "right": 0.0,
}
# A select node may use condition, with explicit if_true / if_false node IDs.
```

The operator can also be enum 0 through 5. Existing numeric and named-input scalar
forms remain valid. Comparison operands may themselves be expressions; the
adapter bounds nesting at 64. Structural validation checks scalar expressions
in all nodes, including inactive branches. Missing named inputs fail when used.
Graph JSON rejects nonfinite values, although the standalone comparison kernel
preserves native unordered semantics for explicit numerical tests.

`predicate_expression(decode_comparison(payload, typed_inputs))` connects the
supported authored predicate form to this expression schema. Graph node names,
connections, selection destinations, evaluation order and active-child clock
ownership remain independent design choices. In particular, the 321 known grab
comparison instances do not supply 321 verified gameplay transitions. Five
unique predicates and their multiplicities remain documented in the source
findings, not promoted into invented clip-selection rules.

The simulation currently supplies its own controls and body-derived generic graph
inputs. It does not automatically map those into captured GrabPadAngle or
GrabPadIntensity. Callers of graph.evaluate_pose must supply those named values
from explicit evidence or a labeled experiment. The retained-cache and one-update
angular override semantics remain separate from raw physical angular velocity.

## Validation and next evidence boundary

Synthetic tests cover float32 rounding, tolerance edges, inclusive versus strict
relations, NaN/infinity, unknown operators, authored-record signatures and binding
variants. A graph test crosses the authored zero-intensity threshold, checks
retained inactive clocks and rejects malformed expressions in an inactive node.
Saved authored examples are checked for exact decoded metadata and evaluated on
their supplied samples; that check does not compare with native execution.

The next missing evidence is the actual outgoing connection from a comparison
output into state/clip selection, together with parameter capture timing. Neither
clip name matching nor neighboring serialized records proves that connection.
The runtime now has a place to execute those predicates when connections are
established; no specific landing, spin, grab or ski/snowboard transition is claimed.
