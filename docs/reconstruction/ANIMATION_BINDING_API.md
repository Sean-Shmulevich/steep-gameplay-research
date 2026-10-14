# Animation binding inspection API

These standalone helpers implement recovered local operations over caller-supplied
synthetic records. They do not load game assets, build a complete rig or connect
the original scheduler. Evidence is in [animation binding research](research/animation.md)
and [CRC-matched channel names](animation_binding_channels.json).

Run from the repository root with Python. All values in this example are synthetic
except the documented Reference channel identifier.

```python
from engine.animation_binding import (
    matching_channel_type, encode_channel_binding, inspect_channel_binding,
    swap_binding_indices, resolve_binding_masks,
)

assert matching_channel_type(2) == 5
record = encode_channel_binding(
    source_index=0x1234,
    matched_target_index=9,
    channel_hash=0x2c52cbb0,  # CRC-matched Reference spelling
    second_variant=True,
    remap_word=(37 << 3) | 5,
)
assert record == {'target_index': 37, 'source_word': 0xd234}
fields = inspect_channel_binding(**record)
assert fields == {
    'target_index': 37, 'source_index': 0x234,
    'remap_bits': 5, 'special_bit': True,
}

# Separate eight-byte special mapping records have a packed word at +4.
assert swap_binding_indices([0xa123, 0xb456], [(0, 1)]) == [0xa456, 0xb123]
# Their +6 word is a class label before preparation and a mask afterward.
assert resolve_binding_masks([1, 2, 3, 4], [0, 3, 15]) == [1, 8, 32768, 4]
```

## Contracts and limits

`matching_channel_type` consumes a byte and returns the decoded matching type.
Raw values above7 return8; do not truncate that result to three bits before the
hash/type lookup. Later packed fields have their own masking rules.

`encode_channel_binding` applies after a target hash/type match. A supplied
`remap_word` models the first variant's remapping: high13 bits replace the matched
target index and low3 bits enter packed bits12..14. With no remap word, the
original target index remains and those bits are zero. Source indices truncate
to low12. The second variant contributes bit15 only for hash2c52cbb0.

`inspect_channel_binding` exposes the four-byte main record's fields. It does not
validate rig indices, explain the three remap bits or resolve a hash collision.
The source index has already lost any high bits discarded during packing.

`swap_binding_indices` works on the distinct special mapping array's word+4.
Callers supply pairs in native order; the helper does not assume human joint
names. `resolve_binding_masks` works on word+6. Supply the three group indices
from the matched target descriptors. The class labels are1 for the foot-selected
group,2 for RightHand-selected group and3 for LeftHand-selected group, subject to
the CRC-match evidence and traversal overwrite behavior. Group indices are not
proven bone indices. Class conversion is not generally safe to repeat.

All helper input checks are reconstruction API safeguards. Native allocation,
concurrency, lifetime, ordering and overflow assumptions are documented separately.
No supplied or returned value is a pointer into the original game.

Still missing for full binding: target-list production and ordering, complete
channel schema, special pair names, mapping consumers, active rig selection and
pose integration. Do not manufacture those dependencies from these examples.

The next native initialization stage is documented in
[Evaluator preparation](ANIMATION_EVALUATOR_PREPARATION.md), including channel
eligibility, identity comparisons and compact sample masks.

## Endpoint source selection

`find_typed_channel(hashes, descriptor_types, requested_hash, requested_type)`
implements sorted hash lookup with duplicate-hash type matching.
`select_endpoint_channels(binding_source_words=None, hashes=(), descriptor_types=())`
uses two binding words when supplied, otherwise searches hash zero for types 5
and 6. Its missing results are `None`. A present-but-missing binding channel
suppresses fallback. See [endpoint motion](ANIMATION_ENDPOINT_MOTION.md) for
source evidence and input contracts.
