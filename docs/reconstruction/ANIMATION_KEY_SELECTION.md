# Byte-time animation key selection

Static evidence: `0x140d57ff0`, 248 bytes, called by encoding-zero sampler
`0x140d3dac0`. Image identity and the callback registration chain are in
[Sampling dispatch](ANIMATION_SAMPLING_DISPATCH.md). This is byte-time selection;
it does not establish the other timestamp formats' algorithms.

## Inputs and outputs

Channel byte +1 is key count N. The first key has implicit tick zero. The N-1
remaining timestamps occupy bytes +2 through +N. The caller passes an unsigned
32-bit hint, a pointer to a uint32 cached key index and a uint32 result pointer.
Both outputs are written. No float time or tick-to-seconds conversion occurs here.

For N below two, the helper sets both outputs to zero and returns. A count of
zero is not rejected by this helper, though the subsequent sampler may require
at least one payload. This must not be treated as proof that a zero-key track is
valid for the full decoding pipeline.

For other counts, let T be the implicit zero followed by stored timestamps:

```python
if cursor < N and hint >= T[cursor]:
    after = cursor + 1
    while after < N and T[after] <= hint:
        after += 1
else:
    after = upper_bound(T[1:], hint) + 1
cursor = after - 1
packed_ticks = T[cursor]
if after < N:
    packed_ticks |= T[after] << 16
```

Comparison is unsigned. The cached path works only when its current key is not
later than the hint. A rewind or out-of-range cursor starts an upper-bound binary
search over stored times, excluding the implicit zero. Equality consumes a key;
duplicate timestamps select the last equal key. An all-ones cursor therefore
requests binary lookup. An all-ones hint is a large unsigned time, not negative.

The packed output contains current tick in low16 and next tick in high16. After
the final key it has only the current tick. The encoding-zero sampler compares
this word with 65535: a larger word takes the two-key path, otherwise it copies
the selected float4. The caller's key index is an index into sample data, not a
byte offset or a timestamp. Selection itself does not interpolate.

## Public implementation and tests

`engine.animation_key_selection.select_byte_key` returns the updated cursor,
packed tick word and a diagnostic path label. It accepts stored timestamps
without the implicit first zero. Validation of count, widths, lengths and
nondecreasing times is our public API safeguard; the native helper assumes its
channel data contract.

Tests cover exact boundaries, duplicates including tick zero, rewinds, invalid
cached indices, empty/single counts and unsigned hints. An independent bisect
oracle checks 257 hints against nine cursor positions for one synthetic sequence.
These tests validate the reconstructed algorithm, not native memory safety or
an entire clip decoder. No game keys or samples are included.

The existing reference time-key reader describes compatible implicit-first-zero
storage. This pass supplies the binary-derived selection/cursor behavior. The
next task is joining key selection to verified interpolation formulas and
sampling units, preserving the distinction between hint ticks and float time.
