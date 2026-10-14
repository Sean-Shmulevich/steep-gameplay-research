# Decoding and pairing animation update observations

The [trace analyzer](../../engine/animation_call_trace.py) decodes the 15 defined bytes in the animation update packet and pairs observed before/after call sites. It consumes private debugger receipts; it does not attach to a process or modify game memory.

```sh
python3 -m engine.animation_call_trace PRIVATE_EVENTS.jsonl
```

The same functions are callable as `decode_packet(bytes)` and `pair_calls(records)`. Their evidence source is the [verified interface call boundary](ANIMATION_DEBUGGER_BOUNDARY.md). Pairing and validation policies are our inspection-tool design, not recovered engine algorithms.

## Packet interpretation

The context pointer occupies bytes 0–7 but is not exposed by the decoder. Bytes 8–11 hold the float32 interval. Bytes 12–14 are retained as three unnamed status values. The decoder preserves exact interval bits, including negative zero and nonfinite payloads. Nonfinite numerical values are represented as null alongside their original bits and a false finite flag, so JSON output does not silently rewrite NaN payloads or invent a usable duration.

Before/after packet snapshots remain separate. The analyzer does not assume that the callee preserves the interval or that a status byte means success, contact, pose completion or a particular animation mode.

## Pairing rules

Only `call_before` and `call_after` hit events are paired. Each carries a sequence number, thread identity, RDI component identity, RSP caller-stack identity and packet bytes. Thread-local stacks support nested invocations and interleaved threads. A return must match the most recent entry's component and stack on its thread.

Sequence gaps, reported losses, unexpected stops and errors discard pending entries as unmatched. Duplicate entries with the same live component/stack identity are not silently merged. Capture termination leaves outstanding calls unmatched. Decreasing/repeated sequence numbers and malformed packets are rejected. Filtered events for unrelated components do not become selected-player hits.

These checks prevent several false pairings. They cannot detect an event silently omitted by the producer without a gap/loss indicator. A valid pair supports observation of those two sites; it does not recover a scheduler request identity, establish a complete component update or prove that every invocation was recorded.

Elapsed debugger wall time is intentionally absent from the result. Hardware breakpoints still stop execution, so their timestamps cannot be used as uninstrumented callback duration or frame timing.

## Native fixture validation

A synthetic x64 caller preserves a component token in RDI, builds the packet at caller RSP+`0x20`, calls a synthetic update, and restores its frame. It alternates selected and unrelated component tokens. The callee preserves a 0.125 interval and changes status values from `[0, 0, 1]` to `[3, 7, 0]`. These values are invented test data, not recovered gameplay behavior.

The isolated Wine/LLDB test captured three selected-component before/after pairs with no unmatched events, rejected unrelated component hits through the configured filter, and recovered all expected packet values. Code was allocated RW and then made RX before execution. The fixture returned normally; the observer removed its breakpoints and detached successfully. The packet fixture contains no game code or data.

The private observer now checks configured identity guards at setup and at accepted hits, supports RDI filtering, reads only the defined packet bytes and reports the filtered-stop count. Capture remains bounded even if the selected component never appears. The [aggregate receipt](animation_packet_debugger_validation.json) records fixture checks and source/result hashes; raw addresses and debugger logs remain private.

Seven repository tests cover status changes, nesting/interleaving, missing events, unexpected stops, duplicate stack reuse, identity mismatches, capture termination, raw float bits and malformed input. The command-line analyzer was also run on the successful native fixture receipt.

## Original-game observation

A fresh player/world/Kino acquisition and membership check supplied the component filter and identity guards. The hardware-breakpoint window captured one before/after pair on the same thread, component and caller stack, with no unmatched events or reported errors. Both snapshots held interval `1.0` and status bytes `[0, 0, 1]`. Both breakpoints were removed, instruction bytes remained unchanged and LLDB detached successfully. The bounded game session subsequently reached its planned time limit and restored configuration.

The [sanitized receipt](live_animation_call_validation.json) preserves the result and private artifact hashes. Raw addresses, packets and logs remain private. This is live evidence that the selected player's interface call ran and returned. Unchanged status bytes do not establish a particular branch or completed pose evaluation. The capture did not identify the active clip or correlate the invocation to a scheduler request.

The [world-clock producer](WORLD_CLOCK.md) now explains the local interval arithmetic. Why this observed call received `1.0` remains unresolved. Debugger wall time cannot measure the uninstrumented callback or prove normal animation cadence. Safe scheduler stepping remains unproved.
