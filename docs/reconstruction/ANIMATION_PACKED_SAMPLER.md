# Encoding-21 packed quaternion sampler

Static evidence: encoding 21 maps to `0x140d3de00`, 952 bytes; paired value decoder
`0x140d71f30` independently reconstructs both adjacent values. The callback uses
the byte-time key selector, float32 1/60 time conversion and the same quaternion
interpolation branches established for encoding zero.

Runtime samples start at `(count+2) & 0xfffffffe` and have two-byte stride. For
unsigned word w, the reconstructed xyzw value is:

```python
v = float32(float32((w & 32767) * float32(4.316100603318773e-05))
            - float32(0.7071067690849304))
m = float32(sqrt(float32(1 - float32(v*v))))
q = (0, 0, m, v) if w & 32768 else (0, 0, v, m)
```

The high bit swaps the stored and reconstructed Z/W components; it is not a
quaternion sign bit. X/Y are zero. Single-key sampling decodes this value without
an additional normalization stage. Two-key sampling decodes both values before
the established branch-sensitive quaternion blend. No full three-axis rotation
capability is implied by this encoding.

`quaternion_z16` and `sample_encoding_21` implement the value and channel paths.
The serialized adapter and shared dispatcher now support IDs 0, 21 and 27.
Bounds/finite/count checks and failure atomicity are public adapter safeguards.
Scalar square-root and reciprocal-seed policies remain independent implementation
choices; native hardware/CRT bit equality is not claimed.

## Private original-byte comparison

Six existing extracted clip bodies contain 170 encoding-21 tracks. Every adapted
record length matched its prior serialized boundary. Seven sample times per track,
including rewinds, produced 1,190 comparisons against the older decoded-key
reference. Maximum sign-invariant component difference was
`1.1199491845026444e-07`. The [aggregate receipt](animation_packed_validation.json)
contains body hashes and no payloads.

This extends original-byte coverage to one compressed rotation encoding. It is
not a native playback comparison, fresh archive extraction check or proof that
the complete rig selects these tracks. Other rotation formats and shared-track
references remain unsupported by this decoder. Synthetic tests separately cover
both high-bit states, word extremes, serialized dispatch, rewind and truncation.
