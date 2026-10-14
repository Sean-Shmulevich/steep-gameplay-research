# Animation sampling dispatch

## Recovered control flow

Static inspection of `0x14075ad60`, 206 bytes, establishes a recursive sampling
wrapper. Image identity is recorded in
[Evaluator preparation](ANIMATION_EVALUATOR_PREPARATION.md). The previously
recovered [routing predicate](ANIMATION_ENDPOINT_MOTION.md#alternate-resource-routing)
is applied at each resource, not just at the first caller.

```python
def native_sample(resource, index, time, hint_ptr, output, cursor_ptr, extra):
    if resource.flags & 8 and alternate_channel_candidate(resource, index):
        if resource.alternate is not None:
            native_sample(resource.alternate, index, time,
                          hint_ptr, output, cursor_ptr, extra)
            return
    channel = resource.channels[index]
    descriptor = descriptors[channel.encoding_byte]
    descriptor.sample(channel, output, descriptor.output_width,
                      address_of_local_time, hint_ptr, cursor_ptr)
```

Index and time are unchanged across recursive hops. Output, hint and cursor
pointers are forwarded unchanged. The extra byte is forwarded recursively but
not read by the terminal decoder branch. Time is a float32 argument copied to
local storage. A terminal decoder receives a pointer to that local copy; it
does not receive a pointer to the endpoint caller's original time field.

Terminal dispatch reads width from descriptor +8 and function pointer +0x10.
This differs from the endpoint routine's direct ordinary branch, which supplies
16 explicitly. The wrapper is not itself an interpolation or decompression
algorithm. Those operations remain in the descriptor callback.

The wrapper does not test for cycles, bound recursion depth, or validate the
terminal channel index. A resource with an out-of-range index may still route
to a valid alternate because the routing predicate returns true for that case.
That behavior must not be mistaken for safe terminal indexing.

## Independent adapter

`engine.animation_sampling.sample_channel` implements the routing loop over
caller-owned Resource and Channel objects. It invokes a supplied decoder with
descriptor, payload, width, float32 time, output and mutable SampleState.
Resource/Channel/SampleState classes are our API, not native object layouts.

Output and SampleState preserve caller identity, so hint/cursor writes remain
visible after the call. The adapter provides time by value; it does not model
decoder writes to the native temporary time pointer. Such writes are not exposed
by this wrapper to its caller. The decoder's return value is ignored. The API
returns a diagnostic hop count, which is not a recovered native return value.

The adapter rejects cycles, invalid terminal bounds, nonfinite times and invalid
field widths. These are public API safeguards. It does not decode a channel,
load game files, synthesize absent keyframes or change gameplay state.

Tests exercise three-hop routing, changed routing at an intermediate resource,
terminal descriptor width, shared mutable output/cursor state, forwarding from
an initially out-of-range channel to a valid alternate, and cycle/bounds guards.
All test resources are synthetic.

## Remaining integration

Connect terminal descriptor identities to existing asset decoders before using
this adapter for private clip sampling. The ordinary endpoint path must preserve
its explicit width of 16. Proving the decoder, resource producer and downstream
consumer is still required before claiming native pose or root-motion parity.

## Descriptor registration map

The saved image's descriptor table is zero, so reading its pointer slots cannot
identify decoder implementations. Static initialization at `0x140d51560` instead
provides 72 explicit registrations for encoding indices 0 through 71. The
[payload-free descriptor catalog](animation_descriptor_catalog.json) records the
registration instruction, descriptor object, output width and sample callback.
These addresses are evidence anchors for this image, not portable runtime IDs.

The initializer first zeroes 253 pointer slots, then performs guarded descriptor
initialization and stores each descriptor into its encoding slot. Catalog
extraction follows RIP-relative address construction and immediate/pointer writes
in this routine; it does not infer callbacks from nearby function names. Only
entries with both explicit output-width and callback assignments are included.
The static map does not prove initialization occurred in a live session or rule
out later replacement of a table entry.

Encoding zero is assigned descriptor `0x1432dca00`, width 16 and callback
`0x140d3dac0`. The callback reads its sampling hint and calls `0x140d57ff0` to
select keys. It finds float4 samples at the channel base plus
`(channel.byte1 + 16) & 0xfffffff0`, then indexes them by sixteen-byte stride.
A single-key branch copies a float4 directly. The two-key path computes a
clamped interpolation fraction and performs quaternion interpolation with
normalization in selected branches. Full key-selection and interpolation
formulas need a dedicated comparison against existing decoder research before
this callback is exposed as a decoded track implementation.

This establishes a concrete descriptor-to-quaternion-sampler connection. It does
not establish that encoding zero is used by a particular player clip. The 72
callbacks should be joined to asset-format evidence individually; output width
alone does not identify translation, rotation, scale or auxiliary semantics.

Encoding zero's [byte-time key selection](ANIMATION_KEY_SELECTION.md) is now
implemented, including cursor reuse, rewind search and packed tick outputs.
Interpolation and other timestamp-format selectors remain separate work.

The [encoding-zero interpolation branches](ANIMATION_QUATERNION_SAMPLER.md)
now have a sampler-specific executable helper. The encoding-zero decoder now connects its time scale and payload layout to
key selection and interpolation; other encodings remain unconnected.

[Encoding 27](ANIMATION_VECTOR_SAMPLER.md) now has a connected vector decoder and
a scoped comparison against 835 privately decoded tracks. This comparison uses
reserialized keys, not original channel slices.

[Encoding 21](ANIMATION_PACKED_SAMPLER.md) adds a two-byte restricted quaternion
path with serialized-byte validation on 170 private tracks.

[Encoding 9](ANIMATION_SMALLEST_THREE_SAMPLER.md) provides general three-axis
quaternion decoding through the same dispatcher and serialized adapter.
