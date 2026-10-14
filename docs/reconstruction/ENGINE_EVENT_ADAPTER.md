# EndFrame event adapter: decoded target lookup

The event branch in [EndFrame](ENGINE_EVENT_SUBMISSION.md) reaches a protected adapter after loading the handle from the engine's inline holder. Bounded emulation now resolves this adapter's local behavior to a single encoded target lookup. A subsequent passive capture resolves the live target to `kernel32.dll!SetEvent`; see the live result below. The restart-side and consumer-side adapters were later resolved the same way to `ResetEvent` and `WaitForSingleObject`; see [live handshake resolution](#live-handshake-resolution).

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

## Live target resolution

[Two passive observations](live_engine_event_target_validation.json) in one initialized Highball Wine session decoded the target to the exact `SetEvent` export in `kernel32.dll`. The target lay in an executable PE section. Both observations rechecked the encoded slot and module headers. The second also compared all 75 instruction spans from the emulated path against live process bytes; every span matched.

This joins the recovered adapter formula to an identified runtime API. The invalid target in the earlier analysis image remains a separate observation: that image's slot value was not usable as the running process's target. The capture did not determine when or how the runtime slot was initialized.

The test only read memory and exports. It did not call `SetEvent`, observe EndFrame executing this branch, check a return status, attach LLDB, or modify scheduler state. Reset/wait targets, event creation/destruction, request visibility and outstanding-work coverage remain unresolved. Identifying the signal API is not a safe stepping proof.

The research bottle was deliberately closed after the observations, and the bounded launcher restored its configuration. Raw module addresses, memory reads and screenshots remain private.

## Reset and wait adapters

The restart routine and the event consumer each pass the same inline holder to a separate one-handle helper. Bounded emulation reduced both to the EndFrame pattern: load the handle into RCX, read one encoded image slot, add a fixed constant and tail-transfer to the result.

```text
reset_candidate(holder):
    tail_transfer(decode(reset_slot), first_argument=load_u64(holder))

wait_candidate(holder):
    tail_transfer(decode(wait_slot), first_argument=load_u64(holder),
                  second_argument=0xffffffff)
```

[Forty synthetic states per helper](engine_event_reset_wait_validation.json) reached a supplied destination with the handle in RCX, the original caller stack and return address, the other tested integer registers preserved and exactly one image data read. The wait helper forces the low 32 bits of RDX to `0xffffffff`; the reset helper leaves RDX unchanged. As with EndFrame, both slots in the inspected image decode to noncanonical addresses and are kept as evidence rather than replaced.

## Live handshake resolution

[One passive observation](live_engine_event_handshake_validation.json) in a fresh initialized Highball Wine session resolved all three adapters to exact `kernel32.dll` exports:

| Adapter | Caller | Export | Live spans matched |
| --- | --- | --- | --- |
| Reset | start/restart routine | `ResetEvent` | 47 |
| Signal | alternate EndFrame branch | `SetEvent` | 75 |
| Wait | event consumer, `0xffffffff` timeout | `WaitForSingleObject` | 48 |

The EndFrame result repeats the earlier capture in a new process. Each target was in an executable section; every slot and the module header were reread and unchanged at the end.

Combined with the recovered `(null, 1, 0, null)` construction arguments, the handshake is now a manual-reset, initially unsignaled event: restart resets it, an EndFrame that observes alternate mode signals it instead of resubmitting the root, and the outer routine waits on it with an infinite timeout before clearing the start flag. The creation call's own adapter target remains unresolved, so `CreateEvent` itself is inferred from argument shape, not observed.

This is API identity only. The test did not invoke any target, observe a return status or a wait completing, attach a debugger or modify state. Event creation failure, handle close/lifetime, request-byte visibility and whether the signaling EndFrame covers all outstanding work remain open gates. A known signal/wait pair is not by itself a safe stepping boundary.

## Creation, close candidate and live owner state

The holder constructor wrapper and two adjacent one-handle helpers use the same protected encoded-slot transfer. [Synthetic validation](engine_event_lifecycle_validation.json) covered 64 creation states and 40 states for each adjacent helper. Creation is an ordinary call rather than a tail transfer. It passes `(0, !second_bool, first_bool, 0)` to the target, so the engine constructor's two false arguments produce `(null, TRUE, FALSE, null)`. The wrapper stores whatever value is returned, including null, in the holder without a check, and returns the holder address.

[A second fresh passive session](live_engine_event_lifecycle_validation.json) resolved these targets and reproduced the three handshake targets:

| Helper | Export |
| --- | --- |
| Holder constructor wrapper | `kernel32.dll!CreateEventA` |
| Close candidate (31 direct callers) | `kernel32.dll!CloseHandle` |
| Adjacent generic helper | `ntdll.dll!RtlLeaveCriticalSection` (not an event operation) |

The engine event is therefore an unnamed, manual-reset, initially unsignaled `CreateEventA` event. Construction has no failure branch: a null handle would be stored and later passed to `ResetEvent`, `SetEvent` and `WaitForSingleObject`. The close candidate is confirmed as `CloseHandle`, but no call with the engine's holder as receiver has been found, so the engine event's close remains unbound (see [owner destruction](ENGINE_OWNER_DESTRUCTION.md)).

The same session sampled the engine owner 24 times over about five seconds during gameplay. The owner pointer was stable and non-null. The holder contained one stable non-null handle. The start flag was 1, alternate mode 0 and the setup gate 1 in every sample. This is the state expected while the outer routine sits in its infinite wait: start set by the restart routine and not yet cleared by the consumer. The consumer thread's blocked state itself was not observed.
