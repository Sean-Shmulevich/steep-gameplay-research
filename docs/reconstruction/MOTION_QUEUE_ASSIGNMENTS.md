# Motion and pre-physics queue assignments

A fresh static pass connects the motion-ingestion candidate to concrete job
construction and distinguishes range configuration from concurrent execution
limits. The earlier [input audit](SCHEDULER_INPUT_AUDIT.md) already established
callback ownership and the dependency sequence. This follow-up adds queue inputs;
it does not prove active player membership or device-sample freshness.

## Construction and named setup

The action owner constructor initializes both the `Physic::PreBeforeSimulation`
motion batch and `Physic::BeforeSimulation` batch through the common job base.
Both receive category one and byte-limit argument 255. The zero register feeding
the category expression is explicitly initialized before construction and has no
intervening register write on the inspected constructor instruction path.
The base clears required and excluded masks, giving initial values of zero.

```text
construct_motion_or_before_batch(shared_default):
    category = 1
    required_mask = 0
    excluded_mask = 0
    execution_limit = uint8(min_signed(255, int32(shared_default)))
```

These are construction-time settings. This pass does not rule out later category,
mask or execution-limit overrides. With unchanged zero required masks, the
recovered enqueue rule selects shared storage. That conditional consequence is
not an observation of live queue placement.

Setup identifies the same embedded members by their names and installs the same
receiver callback target in both. The existing input audit describes the motion
callback and the dependency edges into the world step. The adjacent debug label
for the second batch is `BeforePhysicUpdate`.

## The setup value 32 is range configuration

The `BeforeSimulation` setup invokes virtual slot eight with 32. Resolving that
slot through the concrete constructor-installed table reaches this complete
setter:

```text
set_range_parameters(job, requested):
    size = max_signed(int32(requested), 1)
    job.chunk_size = size
    if size < INT_MAX:
        job.tail_threshold = int32_wrap(size * 2)
    else:
        job.tail_threshold = 0
```

Thus this call writes 32 and 64. It does not write the execution-limit field.
A follow-up checked the concrete virtual worker and joined the fields to the
[range-claim model](SCHEDULER_BATCH_EPOCH.md): the first is chunk size and the
second is the tail threshold. Calling 32 a worker count, concurrency cap or input
frequency would exceed this evidence.

The signed doubling wraps to low 32 bits. `INT_MAX` takes a separate branch that
writes zero to the second field. Negative and zero requests clamp to one. These
are local setter rules, not evidence that extreme operational requests occur.

The setup's separate zero-valued mode-helper call also does not change category.
See [AI queue assignments](AI_QUEUE_ASSIGNMENTS.md) for the decoded mode helper.

## Verification and next joins

The pass followed the name reference to setup, matched the embedded receiver to
its constructor, checked argument register writes and resolved the virtual setter
through the final installed table. The analyzed image SHA-256 is
`32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`.
No process was launched, attached to or changed.

Both range fields are now joined to their read sites and existing claim arithmetic.
Next check later execution-limit/mask writers for these particular members.
Selected-player membership and input generation remain separate live proof gates.


`range_configuration(32)` in `engine.queue_producers` now supplies the recovered
32/64 settings to the independent mixed scheduler. A 100-receiver test claims
32 entries, then four, then 64 individual entries. Claim exhaustion still leaves
one outstanding worker execution until explicit dispatch completion. The test
uses synthetic receivers and does not claim native inter-thread execution order.
