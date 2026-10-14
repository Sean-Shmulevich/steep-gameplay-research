# Runtime identity bindings

A separate compile path exists beside [output descriptor addressing](ANIMATION_OUTPUT_API.md). Runtime binding class 0 takes a 128-bit identity, looks it up in a map and replaces the variant payload with a 32-bit result while retaining class 0. Successful results are added to an optional duplicate-free dependency collection. This is a runtime identity-to-value join; its map population and relationship to authored graph identities remain unproved.

## Recovered behavior

```text
compile_class_zero(identity, optional_dependencies):
    value = UINT32_MAX
    found = lookup_identity(identity, value)
    if found and optional_dependencies exists:
        append value only if not already present
    replace variant payload with value
    preserve binding class 0
    return error = not found
```

An all-zero identity returns failure without changing the supplied output value. A nonzero identity absent from the map returns failure and writes zero. The compiler therefore produces different failed payloads for these two cases. Neither payload is valid merely because it is an integer: callers must honor the compile error.

The map has 24-byte rows: a 16-byte identity followed by a uint32 result and four bytes not consumed here. Key comparisons use both 64-bit words. Hashing uses two word-wise multiply/XOR rounds, not byte-wise FNV:

```text
h = 0x811c9dc5
for word in little_endian_uint64_words(identity):
    h = ((h * 0x1000193) XOR word) modulo 2^64
h = h AND 0x7fffffff
q, r = divmod(h, 127773)
m = r * 16807 - q * 2836
if m < 0: m += 0x7fffffff
bucket = m AND (capacity - 1)
```

Collisions visit `bucket+1`, then `bucket+3`, then `bucket+6`, and so on, masking by `capacity-1` at each step. An empty-key sentinel terminates failure. A deleted-key sentinel is skipped when its gate is enabled. Two native counters also gate the search; equality bypasses it and returns failure with output zero. The counter meanings are deliberately unnamed in the adapter.

`engine.animation_identity` exposes `identity_bucket`, `lookup_identity` and `compile_identity`. Keys are exactly 16 bytes. Rows and sentinel keys must be supplied explicitly. The adapter validates power-of-two capacity and integer widths, and raises on a full unsuccessful probe cycle. These guards are designed safety checks; the native loop has no corresponding bound in the inspected function. Python list mutation replaces native dependency-array allocation.

## Consumption lead

The scalar getter's class-0 branch uses the compiled value as an index into a separate context-owned parameter system. Before reading, it invokes a preparation helper. That helper reads an index-to-group byte; `255` skips preparation. Otherwise it selects a 72-byte group record. A group flag suppresses repeated calls. If clear, it calls a virtual callback and then sets the flag. The reset loop and its conditional update-tail placement are now described in [parameter lifecycle](ANIMATION_PARAMETER_LIFECYCLE.md). Callback implementation and frame cadence remain open.

The subsequent scalar read has atomic access accounting and a wait path. The preparation helper alone does not prove input freshness, synchronization, or a particular input-ingestion phase. This gives a more specific next lead: find the identity-map producer, then trace the selected group callback and the outer update caller. A match to an authored GUID is still required before connecting these bindings to grab, landing or steering parameters.

## Evidence and validation

The original lookup and its original signed-division helper passed 400 isolated emulation cases against the portable implementation. Cases used synthetic maps with direct matches, collisions, tombstones, absent keys, zero identities and equal-counter early exits. See [validation receipt](animation_identity_validation.json). No game process was launched or attached. Four repository tests cover failure output retention, collision traversal, malformed/full snapshots and compile/dependency behavior. The compiler wrapper and downstream preparation lead were statically inspected, not emulated end to end.

Static anchors for independent verification are lookup `14128e6b0`, compile resolver `1412a0a40`, dependency insertion `141268a10`, scalar getter `141258920`, preparation `1412e9850`, and guarded read `1412579e0`. Addresses identify evidence only; all portable behavior needed for this adapter is expressed above and in code. The image hash is recorded in the receipt. No image bytes, original maps or authored graph payloads are distributed.
