# Bounded debugger observation for the matched animation component

The player-to-Kino [membership observation](ANIMATION_MEMBERSHIP_OBSERVATION.md) now provides a target identity. Polling showed changing scheduler requests but did not observe worker execution. The next execution experiment can target the component's actual animation-interface call, after its readiness gates, rather than infer execution from copied pointers.

## A tested observation window

A private LLDB observer was tested against an isolated synthetic Wine leaf using required hardware execution breakpoints. It verifies instruction signatures before installing any breakpoint, switches LLDB to asynchronous process control, polls state with an independent wall-clock deadline, records exact stop reasons and removes its own breakpoints before detaching. It does not patch code or allocate executable memory in the target.

Three fixture cases passed:

| Case | Observations | Cleanup |
| --- | --- | --- |
| Entry and return | Six events forming three ordered entry/return pairs; thread and stack pointer matched within each pair; token register preserved | Both breakpoints deleted, code unchanged, clean detach and normal fixture exit |
| Unreached breakpoint | Zero events; window ended at its one-second deadline, measured 1.0021 seconds | Breakpoint deleted, clean detach and normal fixture exit |
| Wrong instruction signature | Rejected before breakpoint installation; zero events | Clean detach and normal fixture exit |

The [receipt](bounded_debugger_validation.json) records the checks and hashes of private results and observer/runner sources. Debugger attach/setup plus cleanup took approximately 9–10 seconds per case. The one-second capture deadline starts after setup; it is not the total attach timeout. The fixture controller separately bounds debugger lifetime and cleans up only its owned fixture process/prefix. Successful fixture cases do not prove every timeout or target-failure cleanup path.

The new loop can terminate without a callback arriving, addressing a weakness of the earlier event-driven deadline. It records and bounds trace-stop continuations, but the tested cases did not exercise those trace stops. It stops on unexpected reasons rather than treating every trap as harmless. No original game was launched or attached to in this pass.

## The exact animation call boundary

In the inspected image, `KinoComponent` update chooses a float32 interval and builds a stack packet before its interface call:

```text
component = preserved RDI
packet = current RSP + 0x20
packet.context = address of local context
packet.interval = selected interval
packet.status_12 = 0
packet.status_13 = 0
packet.status_14 = 1

if auxiliary exists and auxiliary.field_240 is nonnull:
    interface = component.interface_b0
    interface.update(packet)             # before/after observation pair
    interface.other_method_200()
    inspect packet.status_14
```

An earlier interface readiness call must also have succeeded to reach this block. Reaching the paired sites would therefore prove more than merely entering the component method. Absence of hits would be inconclusive: readiness gates, different timing, target lifetime or an unobserved interval could explain it.

The static pair is the virtual call at `140de1cfd` and the immediately following instruction at `140de1d00`. Before the call, RDI is the component, RCX the interface and RDX the packet. After the call, RDI and the caller's RSP remain preserved by the inspected calling convention, while volatile RCX/RDX cannot be reused as identity evidence. The packet can be read through `RSP + 0x20` at both sites. Its interval occupies bytes 8–11, followed by three status bytes at offsets 12, 13 and 14. Only those defined bytes should be decoded; surrounding stack data is not a serialized structure.

Six original instruction spans were rechecked against the image hash, covering packet address, interval/status stores, call and return site. The two sites bracket the interface update call, not the entire Kino method, all animation work, or a physics substep. Status-byte meanings remain unresolved and should be recorded as raw values.

## Conditions for the next original-game test

1. Acquire the player/world/component again in the current process. Revalidate the component table, owner, world and interface link at debugger setup. Never reuse the earlier session's address.
2. Verify both instruction signatures before installing hardware breakpoints, and filter events by the freshly matched RDI component. Retain counts of filtered/unexpected stops so absence is not mistaken for non-execution.
3. Pair before/after events by thread, component and caller stack address, with a per-thread invocation sequence. Repeated invocations reuse stack addresses; a missing entry or return must remain unmatched. Do not pair across lost events or unexpected stops.
4. Record the interval's original float32 bits and the three packet bytes at both sites. Preserve the thread and caller evidence separately from scheduler-request observations; a nearby request counter is not an invocation identifier.
5. Bound attach/setup independently from the event window and leave enough time before the game watchdog expires. Record removal and detach outcomes, including failure. Leave game settings restoration to the existing bounded session controller.

The current fixture observer validates the bounded stop loop and cleanup on these tested paths. Player filtering, packet reads and original-game before/after pairing still need implementation and validation before a live attempt. The existing generic register recorder must not be described as already capturing that packet.

Debugger stops perturb execution and timing. Even a successful pair would establish that the call ran and expose the supplied interval; elapsed host time between the stops would not measure the uninstrumented callback cost. This observer is not a scheduler pause/step implementation and does not establish a safe point for modifying job state.
