# The default action processor preserves the input vector

The two-axis action initializer's fallback processor is now concrete. Its vector-processing method marks a byte on first use, copies all four input lanes unchanged into its output storage and returns that storage. **It applies no deadzone, diagonal normalization, smoothing, clamp, gain or coordinate conversion.** This describes the fallback type, not every processor the configuration can select.

This was offline instruction inspection. No game code was executed, and the currently selected player action/processor was not observed. See [the action callback report](ACTION_RESET_CALLBACK.md) for the surrounding input combination and publication path.

## Selection and construction

The two-axis action initializer retains its definition handle, resolves the definition owner and dispatches its type-specific configuration binding. When the required two-axis configuration exists, it obtains that configuration's subordinate processor-definition handle.

The inspected selection logic is:

```text
initialize_two_axis_action(action, source_context, definition):
    retain_and_bind_action_definition(action, definition)
    bind_type_specific_configuration(action)
    if action.two_axis_configuration exists:
        processor_definition = action.two_axis_configuration.processor_definition
        processor = null
        if resolve(processor_definition) exists:
            processor = resolved_definition.create_processor(processor_definition)
        if processor == null:
            processor = construct_default_processor(processor_definition)
        action.processor = processor
        processor.initialize_source_context(source_context)
```

The resolved definition's creation method is virtual. Its nonnull return can select a different processor type. The new closure is the explicit fallback taken when the definition is unresolved or its creation method returns null; no claim is made that the fallback always runs.

The default factory constructs the shared processor base, installs a concrete derived table, initializes its first-use flag to zero and retains the supplied processor-definition handle. The inspected configuration-retention helper does not replace that table. The default table's source-context initializer is a no-op. Its processing method is therefore resolved through construction, rather than chosen merely because a nearby function copies vectors.

## Complete default processing kernel

```text
process_default(processor, vector4):
    if processor.first_use_byte == 0:
        processor.first_use_byte = 1
    processor.output_storage = copy_all_four_lanes(vector4)
    return address_of(processor.output_storage)
```

A preexisting nonzero byte is retained as-is. The method contains no arithmetic on the vector and reads no clock, device buffer or previous vector. Repeated calls replace the output directly. The byte is a local first-use marker, not a sample count or commit generation.

The native method copies 128 bits, including the fourth lane. It would copy nonfinite bit patterns too. [The Python adapter](../../engine/action_processor.py) deliberately accepts only finite numerical float32 lanes, rounds caller-provided numbers into that representation and returns copied state/output instead of a native pointer. These validation and ownership choices are ours. Signed zero and finite float32 lane values are preserved after conversion.

API:

```python
from engine.action_processor import initial_state, process_default

state = initial_state()
result = process_default([1.0, 1.0, 0.0, 0.0], state)
# result["output"] remains [1.0, 1.0, 0.0, 0.0]
# result["state"]["flag"] is 1; the supplied state is unchanged.
```

Calling this adapter asserts that the default processor was selected. It does not choose a factory or silently substitute for an unresolved configured processor.

## How this changes the input interpretation

The two-axis callback builds a vector from opposing boolean directions before optional processing. The surrounding callback bypasses processing when a resolved processor configuration has its inspected control byte equal to zero; otherwise it calls the processor. Bypassing the call does not set the default processor's first-use byte.

If this default processor is selected and invoked, or if the surrounding callback bypasses processing, the combined vector remains unchanged at this stage. An opposing pair cancels. Two positive perpendicular directions produce `[1, 1, 0, 0]`, whose magnitude is approximately square root of two. This processor does not turn it into unit input.

After processing, the enclosing action callback separately computes magnitude and a normalized-or-small direction cache. The motion/snow getter reads the processed sample, not that direction cache. Thus normalization of the adjacent cache does not prove that the consumed sample has unit length. Later input shaping may still transform it.

The result narrows an important branch without establishing universal keyboard/controller behavior: the actual action definition, selected processor and later consumer policy must still be joined for the player.

## Verification and remaining target

The constructor-backed default table was read from the same analyzed image identified in the [scheduler input audit](SCHEDULER_INPUT_AUDIT.md). Inspection followed the complete 199-byte two-axis initializer, the 117-byte default factory, the 161-byte shared base constructor, the definition-retention helper and the complete 27-byte processing leaf. The leaf contains seven instructions ending at its return. This is static evidence, not a native equivalence test.

Five synthetic tests in [test_engine_action_processor.py](../../tests/test_engine_action_processor.py) cover diagonal and fourth-lane preservation, signed zero and small inputs, repeated replacement without smoothing, nonzero-flag retention, input/state independence and the adapter's finite-float32 domain policy. They validate the portable adapter; they do not execute original instructions.

The next unresolved target is the configured processor-definition creation method. Resolving its concrete definition type and returned processor table will determine whether a nondefault branch adds shaping. Source-query producer ownership and timing remain independent questions. Neither the default first-use byte nor the action magnitude should be used as a publication generation.
