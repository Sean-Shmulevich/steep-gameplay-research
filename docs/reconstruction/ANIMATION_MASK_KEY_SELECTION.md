# Bit-mask animation key selection

Static evidence: encoding-14 callback `0x140d3ff00` calls selector `0x140d580f0`.
The selector's rank helper is `0x140d56c20`; all 256 bytes of its lookup table
match byte population count. The callback uses six-byte quaternion samples,
the same value format as encoding 12, but a different timestamp header.

Runtime byte +1 contains a mode: low six bits are mask byte length L, high two
bits are shift S. The L mask bytes start at +2. A set bit at position i denotes
a key at tick `i << S`. Sample data for encoding 14 begins at
`(L + 3) & 0xfffffffe`. This is mask length, not key count.

```python
limit = L * 8
position = min(unsigned_hint >> S, limit - 1)
previous = position
while not bit(mask, previous):
    previous -= 1
following = position + 1
while following < limit and not bit(mask, following):
    following += 1
packed = previous
if following < limit:
    packed |= following << 16
packed_ticks = uint32(packed << S)
selected_sample = popcount(mask bits strictly before previous)
```

The search for the following key starts after the original clamped position,
not after the selected prior key. Equality selects the key at that bit. Beyond
the mask range, the hint clamps to the last bit before searching backward.
The result writes the selected sample index to the supplied cursor pointer, but
never reads its old value. This differs from byte-time cached forward lookup.

Native backward scanning has no lower-bound check. A nonempty mask with initial
bit set is therefore a required data contract for hints near zero. The public
`select_mask_key` validates that contract and mode/length widths before scanning.
It does not infer a sample count or parse a clip container. The largest supported
bit range is 504 positions before the shift.

Four tests cover holes, exact key equality, beyond-end hints, byte-boundary rank,
all four shifts and invalid masks. A separate expanded-timestamp bisect oracle
checks 520 hint/shift combinations. This pass establishes the selector; complete
serialized encoding-14 adaptation and sampling remain next work. Corpus support
therefore remains 944 of 1,052 tracks.

## Connected encoding-14 decoder

`sample_encoding_14` now combines this selector with the verified 48-bit value
reader and quaternion interpolation. Its cursor argument is accepted for the
shared callback interface but intentionally ignored. The new cursor is the rank
returned by mask selection. Float time remains separate from the integer hint.

The serialized record has encoding, uint32 opaque allocation, uint32 sample count,
then a mode byte, L mask bytes and count six-byte samples. The adapter checks the
mask population count against the serialized count, creates the runtime two-byte
header, inserts alignment and copies sample bytes. Unlike byte-time encodings,
key count is not stored in runtime byte +1. It is derived from the mask. Empty
masks, missing first key, count mismatch and truncated samples are rejected by
the independent adapter.

Original serialized slices now validate all 24 encoding-14 tracks in the six-body
corpus. Total supported tracks rise to 968/1,052, with 6,776 cached/reset sampling
checks and no failures. This establishes parsing and internal consistency on
those records, not independent numerical or live native equivalence. Earlier
selector-only coverage statements above describe the preceding checkpoint.
