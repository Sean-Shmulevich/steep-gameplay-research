# EndFrame event adapter: decoded target lookup

The event branch in [EndFrame](ENGINE_EVENT_SUBMISSION.md) reaches a protected adapter after loading the handle from the engine's inline holder. Bounded emulation now resolves this adapter's local behavior to a single encoded target lookup. The target API remains unidentified.

## Recovered transfer

```text
end_frame_event_operation(holder):
    handle = load_u64(holder)
    encoded_target = load_u64(build_specific_target_slot)
    target = wrap_u64(encoded_target + 0x7ef2492e)
    tail_transfer(target, first_argument=handle)
```

The transformed calls and stack operations reconstruct a tail transfer: the target sees the original caller stack and return address, with the handle in RCX. The tested other integer registers are restored. This is a target-selection and calling-convention result, not a recovered signal implementation.

The private inspected image's slot value decodes to a noncanonical address. An unmodified emulation reaches that address after 75 instructions and fails on instruction fetch. This is retained as evidence. The static image does not supply a callable API target, and its invalid value must not be replaced with a guessed `SetEvent` address.

Possible explanations include runtime initialization or transformation of the slot, or an analysis image that does not contain the required runtime state. The experiment does not choose among those explanations. A different calling path or earlier initialization could matter.

## Synthetic validation

[Forty isolated comparisons](engine_event_adapter_validation.json) supplied an encoded slot value that decodes to a mapped synthetic destination. Each case varied the handle and initial integer registers. All reached that destination with:

- the supplied handle in RCX;
- the original caller stack pointer and return address;
- the tested other integer registers preserved;
- exactly one data read from the image, at the encoded slot.

Only the emulator's copy of the data slot was changed. No game process was launched, attached to or modified. No Windows event API was executed. The experiment fixed initial flags and did not validate vector-register preservation, every possible incoming flag combination, target failure behavior or synchronization.

## Concrete live resolution plan

1. Acquire the current process identity and module base, and verify the analyzed build.
2. Read the encoded slot in the current process, compute the wrapped sum, then reread the slot. Reject changes rather than associating an export with a stale target.
3. Check that the decoded target is a valid executable address in a loaded module. Record the module identity and relative offset privately.
4. Resolve exports or inspect a bounded forwarding thunk. A nearby symbol or matching argument shape is insufficient to name the target.
5. Repeat for the restart/reset and consuming/wait adapters. Resolving only the EndFrame operation would not establish the whole stop/restart handshake.

This check can use passive reads. It does not require calling the decoded target, changing alternate mode, or holding workers in a debugger. Even a confirmed event API would leave event lifetime, creation failure, plain-byte request visibility and outstanding-work coverage as separate scheduler release gates.
