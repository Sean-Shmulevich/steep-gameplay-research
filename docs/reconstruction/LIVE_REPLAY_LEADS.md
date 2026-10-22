# Live-replay reader: initial static findings

Scope: focused inspection of the existing private unpacked TU7 image, prompted
by [Powder's replay storage](POWDER_REVIEW.md). This is a reader-boundary finding,
not a complete saved-ghost format. No payload or original executable bytes are
included. Private string references and disassembly remain outside this repository.

## Observed prefix

The code associated with `LiveReplayService::ReadNewChunk` checks a nonnull
buffer and nonzero length, then copies three consecutive 16-byte blocks into a
local 48-byte prefix and initializes its next pointer to buffer + 48.
The inspected entry does not itself show a length >= 48 check; callers and
transport validation still require inspection. A future independent parser must
reject truncated inputs rather than reproduce an unchecked memory access.

| Prefix offset | Width | Observed use | Confidence boundary |
| --- | --- | --- | --- |
| 0 | 4 | Compared with a version global; mismatch follows rejection path | Global equals 94 in the inspected mapped snapshot |
| 4 | 4 | Forwarded to a later payload/entity routine | Meaning and units unresolved |
| 8 | 8 | Converted from unsigned integer to float on one creation branch | Candidate time-like quantity; units unproved |
| 16 | 8 | Logged as WorldID and compared with current-world query | World identifier established by diagnostic and consumer |
| 24 | 4 | Chooses local-player versus other-entity resolution paths | Identifier/sentinel role; exact schema unresolved |
| 28 | 4 | Inside copied prefix | No meaning established in this pass |
| 32 | 8 | Converted from unsigned integer to float on another creation branch | Candidate time-like quantity; units unproved |
| 40 | 1 | Selects one of two entity-state operations after payload decode | Boolean-like flag; semantic name unresolved |
| 41..47 | 7 | Inside copied prefix | No meaning established in this pass |

These are offsets relative to the reader's supplied buffer. Compression, framing,
encryption or container bytes before this boundary have not been established.
Do not apply these offsets directly to downloaded ghost files yet.

## Control flow expressed without process addresses

```text
read_live_chunk(buffer, supplied_length):
    if buffer is null or supplied_length == 0:
        return
    prefix = copy_48_bytes(buffer)
    cursor = buffer + 48
    if prefix.u32_at_0 != expected_version:
        reject_stream()
        return
    if prefix.u64_at_16 != current_world_identifier():
        remember_requested_world(prefix.u64_at_16)
        mark_world_change_pending()
        return
    entity = resolve_or_create_entity(prefix.u32_at_24)
    cursor = decode_first_payload_stage(cursor, entity)
    cursor = decode_second_payload_stage(
        entity, cursor, prefix.u32_at_4, prefix.u32_at_0)
    inspect_entity_records_and_apply_state_flags()
    if entity_was_created:
        dispatch_creation_notification_using_prefix_fields()
    remaining = supplied_length - consumed_bytes
    if remaining != 0:
        read_live_chunk(cursor, remaining)
```

The two decode-stage names above describe call ordering only. They are not decoded
record schemas. Creation notification branches use different prefix fields.
The recursive remainder path suggests concatenated units at this reader boundary;
its validity and progress guarantees still need caller/payload inspection.

## Playback timing lead

The separately named `ReplayPlaybackService::StartReplay` receives a float,
stores it in two playback fields, records a Boolean option, captures a clock-like
object and copies its current value into two fields, then sets an active byte.
Diagnostics label playback positions in milliseconds. No conversion to physics
time or link to the simulation scheduler was established here. A playback pause
is not evidence of physics pause or deterministic input resimulation.

## Next highest-value checks

1. Trace the first payload-stage reader and identify record type/length dispatch.
2. Trace the second stage and determine whether it consumes transforms, animation
   values, controller inputs, or references to separately recorded data.
3. Inspect `LiveReplayManager::WriteNewChunk` to pair the producer with these
   prefix fields, particularly the two unsigned-to-float quantities.
4. Trace `OnlineTrailService`'s downloaded ghost consumer to establish whether
   saved rides share this live-chunk format or wrap a different stream.
5. Acquire controlled private payload pairs only when execution is restored.
   Use identical sport/location and one varied action; keep the source payloads
   private and publish synthetic fixtures after the format is verified.

The bounded filename search found no saved ghost payload in the existing
analysis/runtime trees. That is not proof that none exists elsewhere on disk.

## Byte-column compression

The second payload stage has a versioned container reader. It first reads four
little-endian uint32 values: an embedded version, an unresolved field, a record
count, and a compressed byte length. The returned cursor is after this declared
compressed block. For incoming versions >=45 the embedded version becomes the
record version. Older incoming versions retain their supplied version. The
version >=70 branch implements the byte-column decoder below; versions 68..69
and earlier use different paths and are not supported by this decoder.

For nonzero record count, the compressed block begins with a uint32 record width.
It allocates record_count * record_width output bytes and fills each byte-column
across all records before moving to the next column:

```text
width = read_u32_le()
output = zero_bytes(record_count * width)
for column in range(width):
    literal = read_u8() != 0
    remaining = 0
    for row in range(record_count):
        if literal:
            value = read_u8()
        else:
            if remaining == 0:
                value = read_u8()
                remaining = read_u8()
            remaining = (remaining - 1) & 255
        output[row * width + column] = value
```

Zero stored run count therefore represents 256 repeats. Runs can extend beyond
the final row: decoding stops after record_count outputs for the column. Every
nonzero mode byte chooses literal data, not only mode byte 1. After reconstruction,
the native reader passes each fixed-width record to one record consumer with the
effective version and a caller-supplied mode. A spatial sub-block is now decoded below; the complete record layout
and its channel identities remain unresolved. The first payload stage also invokes a string-reading helper
before a separate structured reader; it should not be mislabeled a motion record.

`engine.replay_columns.decode_columns(payload, record_count)` implements only
this compressed-block layer, returning row-major bytes and consumed byte count.
Its allocation bound, overflow rejection and truncation errors are authored
validation guards; malformed native behavior is not emulated. It does not infer
record count from an arbitrary ghost file and does not require stream exhaustion,
since outer framing owns the block boundary.

An isolated native-loop comparison matched output and consumed bytes for 100
synthetic cases, with widths 1..9, counts spanning 1..600, mixed literal/RLE
columns, zero-count 256-runs and partial final runs. No external calls were
stubbed inside the compared loop. This validates the compression reconstruction,
not a saved-ghost parser, network framing, or original-game playback integration.

## Spatial block

The decompressed-record consumer invokes a larger state decoder, which in turn
reads the following spatial block. Its offset within a whole record is not yet
exposed by the independent parser. The implementation explicitly accepts only
version 94; older branches require separate validation.

| Block byte offset | Encoding | Decoded operation |
| --- | --- | --- |
| 0 | Three float32 | Shared anchor |
| 12 | Five signed-byte triplets | Each scaled by float32(1/127), then added to anchor |
| 27 | Two bytes | Zero selects positive missing rotation component; nonzero negative |
| 29 | Two signed-byte triplets | First three components of two rotations, scaled by float32(1/127) |
| 35 | Three float32 | Additional vector |
| 47 | Four signed bytes | Additional rotation, scaled then normalized |

The block consumes 51 bytes. The five relative points are returned in serialized
order. Their native destination order is not consecutive. No board, rider, joint,
world/local coordinate frame, or physical unit is assigned to these channels yet.
These spatial values establish stored state in this path; they do not establish
whether controller inputs are also recorded elsewhere.

For each three-component rotation, using float32 operations:

```text
s = ((x*x + 0) + y*y) + z*z
if s > 1:
    (x,y,z) /= sqrt(s)
    w = 0
else:
    w = sqrt(1-s) * (-1 if sign_byte != 0 else 1)
```

For the four-component rotation, first scale signed bytes by float32(1/127),
then evaluate the pairwise sum `(x*x + z*z) + (y*y + w*w)`. The native code uses
RSQRTPS followed by one refinement:

```text
seed = reciprocal_sqrt_instruction(s)
factor = (3 - (seed*s)*seed) * (0.5*seed)
rotation *= factor
```

Each arithmetic operation rounds to float32. The independent
`engine.replay_spatial.decode_spatial` requires an explicit `rsqrt_seed` callable.
Supplying exact `1/sqrt(s)` is an authored approximation to the instruction seed,
not hardware equivalence. Bounds, version rejection, finite-coordinate checks
and zero-quaternion rejection are authored guards, not recovered malformed-input
behavior. Trailing bytes are allowed because the larger state record continues.

Validation: 120 synthetic inputs matched all decoded spatial fields bit-for-bit
and matched consumed length against the native routine under emulation, including
its called square-root helper without stubbing external calls. The comparison
captured the emulator's RSQRTPS seed and supplied that seed to the reconstruction.
This checks the subsequent arithmetic, not the emulator's equivalence to every
physical CPU. See the [validation receipt](../../native/snow_host/replay_spatial_validation.json).

Next: decode the surrounding flags/scalars and follow the state consumers to
identify these channels. A complete ghost-file parser and original-game playback
remain unimplemented; live validation remains necessary.

## State record

The version-94 state subrecord is now parsed by `engine.replay_state.decode_state`.
It consumes 259 bytes. Its spatial block begins at byte 36 within this subrecord,
following 24 individually serialized flags and one float32 triplet. This is not
the start of a whole decompressed record: the caller also reads metadata first.

The state contains 25 flags, five additional float32 triplets, the spatial block,
48 signed-int16 scalar channels, 15 byte tags and three raw four-byte words.
Flags use each source byte's low bit, not a nonzero test. Scalars use float32
conversion and division by 10, 100, 1000 or 10000; the serialized-order divisor
list is explicit in the module. Raw words retain their bits rather than assuming
integer or float semantics. Coordinate units, tag meanings, scalar names and
body/bone identities remain unresolved. No decoded channel is wired into gameplay
under a guessed meaning.

A 120-case comparison matched every serialized field and the consumed length
against the native reader under emulation. The state initializer was skipped;
its defaults and preserved bits are outside this comparison. The spatial helper
and square-root calls executed, with the emulator's reciprocal-square-root seed
supplied to the independent implementation. These are synthetic records, not
captured rides. See the [state validation receipt](../../native/snow_host/replay_state_validation.json).

## Integrated second-stage inspection

For effective version 94 the record consumer reads a 23-byte metadata prefix:
four byte tags, three flag-like bytes, three raw four-byte words, then two unsigned
16-bit scalars divided by 10 and 100 respectively. Their semantics and units are
unresolved. The flag-like bytes are retained verbatim because downstream branches
include equality-to-one tests; they must not be indiscriminately coerced to Boolean.
The consumer then invokes the 259-byte state reader and eventually returns its
end pointer. Together these consume 282 serialized bytes.

`engine.replay_inspect` connects the stage header, byte-column decompression,
metadata and state readers. It accepts a buffer beginning at the second payload
stage, not an arbitrary ghost-file header:

```sh
python3 -m engine.replay_inspect private-stage.bin \
  --supplied-version 94 --normalization authored-exact-sqrt \
  --output private-inspection.json
```

The explicit normalization flag acknowledges the authored reciprocal-square-root
seed. The API accepts a caller-provided seed instead. Outputs include the declared
stage boundary, bytes consumed by compression, compressed trailing bytes, and
per-record uninterpreted tail lengths. A record wider than 282 bytes is not silently
claimed fully understood. Unsupported versions, zero-record stages, truncation,
undersized record widths and excessive allocation/counts are rejected. These
bounds are authored inspection policy. Keep real inputs and decoded outputs
private because they can contain recorded game state and pose data.

Ten focused tests pass across these layers, including a two-record compressed
synthetic stage, metadata scales, trailing boundaries and malformed input guards.
The command also produced a JSON inspection of that synthetic stage. This is
integration evidence, not live ghost-file validation or replay playback.

## First vector: replay distance and spatial bounds

Following the state consumer establishes a concrete use for decoded `vectors[0]`.
The state is copied into a larger replay entry with a 16-byte prefix. The entry
append path compares this vector with the last entry's corresponding vector and
updates componentwise bounds. A separate auxiliary-object path passes the same
vector into a transform setter, which preserves XYZ and constructs the homogeneous
lane before notifying the object. This supports a position-like interpretation,
without proving the player's main-body identity, world/local frame, or units.

The local metric formula and gates are now implemented in `engine.replay_metrics`:

```text
distance = 0
if existing_record_count > 1:
    d = current_vector - last_record_vector
    distance = sqrt((d.x*d.x + d.z*d.z) + (d.y*d.y + d.w*d.w))
append_record()  # allocation/ownership operation outside the arithmetic helper
if optional_callback_enabled:
    notify_last_record()
if all_four_lanes(lower) == 0 and all_four_lanes(upper) == 0:
    lower = current_vector
    upper = current_vector
else:
    lower = componentwise_min(lower, current_vector)
    upper = componentwise_max(upper, current_vector)
return distance
```

Operations round to float32. The decoded fourth lane is zero, although the native
metric operates on all four lanes. The strict `>1` count gate means a one-entry
history reports zero distance for the next append in this path. The all-zero
bounds sentinel also remains active after an origin-only sample. These behaviors
are retained rather than replaced with a conventional first-sample Boolean.
Neither distance nor the metadata scalars should be called speed or seconds yet.

One hundred synthetic emulator cases matched local distance, count gating and
bounds. The append call was skipped and the optional callback disabled; record
allocation, callback behavior and runtime object identity are not validated by
this comparison. See the [metric receipt](../../native/snow_host/replay_metrics_validation.json).

The other spatial channels still need consumer/producer tracing. This finding
narrows the next live capture: correlate `vectors[0]` with a separately observed
player position and auxiliary-object position during one controlled displacement.
