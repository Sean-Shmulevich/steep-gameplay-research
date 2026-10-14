# Serialized channel adapter

The sampler consumes an in-memory channel layout. Original serialized track
records use a different header and no sample alignment padding. The observed
encoding-zero/21/27 byte-time layout is:

| Field | Bytes |
| --- | --- |
| Encoding | 1 |
| Opaque allocation metadata | 4, little endian |
| Key count | 4, little endian |
| Stored timestamps after implicit zero | count minus one |
| Samples | count times sample stride |

Encoding zero uses float4 stride 16; encoding 21 uses packed quaternion stride 2;
encoding 27 uses float3 stride 12. The runtime
layouts are established by the inspected callbacks described in
[quaternion sampling](ANIMATION_QUATERNION_SAMPLER.md) and
[vector sampling](ANIMATION_VECTOR_SAMPLER.md). Serialized field interpretation
comes from the earlier private serializer/track parsing research and is checked
here against original serialized clip-body slices. This pass does not independently
reconstruct the whole clip container serializer.

`engine.animation_decoder.unpack_serialized_channel` accepts bytes plus an
explicit track offset. It preserves raw sample bytes, moves count into the runtime
byte field, copies time bytes, and inserts runtime alignment padding. It returns
the adapted payload, consumed byte count, encoding and opaque allocation value.
The allocation value is retained without assigning semantics or using it as a
trusted allocation size. Counts outside 1..255, unsorted times, unsupported
encodings and truncated records are rejected. Shared-reference tag 254 is not
resolved by this adapter. Trailing records are permitted.

## Original-byte check

Six existing private serialized clip bodies supplied 506 encoding-27 tracks.
For every track the adapter's consumed length exactly matched the previously
recorded serialized start/end offsets. Raw sample bytes were copied directly
from those bodies, without reconstructing samples from decoded JSON values.
Seven sample times per track included forward traversal and rewinds.

Across 3,542 outputs, maximum absolute xyz component difference against the prior
pose-assembly decoded-key reference was `9.5367431640625e-07` authored units.
The [aggregate receipt](animation_serialized_validation.json) contains original
body hashes and counts, without track bytes, samples or poses.

This verifies the adapter and sampler against those extracted bodies and an
existing reference. It is not a native execution comparison, a fresh archive
extraction check, or an independent proof of all clip-container offsets. Encoding
zero's serialized adapter currently has synthetic validation only. Rig binding,
shared-track resolution, other encodings and active graph selection remain open.

[Encoding-21 packed quaternion validation](ANIMATION_PACKED_SAMPLER.md) adds
170 original serialized rotation tracks to this adapter's checked corpus.
