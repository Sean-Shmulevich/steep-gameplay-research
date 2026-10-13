# Executable references

Standard-library Python implementations of selected local rules. Provenance and adaptations are recorded in [REFERENCE_MANIFEST](../REFERENCE_MANIFEST.json). These are not a full simulator or original engine source. Valid authored-domain inputs are assumed unless a function documents rejection; mathematical equivalents are not necessarily SIMD/bit-exact.

| Module | Scope |
| --- | --- |
| snow | Contact forces, clipping, pressure, stick, shaping, springs and point impulses |
| response_delay | Delayed trick response and its domain guards |
| animation_blending | Ordered weights, quaternion paths, masks and phase helpers |
| animation_playback | Phase, markers, sampling and transition precedence |
| landing_pose | Alignment, delayed tilt and translation shift |
| skinning | Palette branches, remapping, bone anchors and four/eight-influence position math |
| skeleton | Hierarchy math; asset-dependent entrypoint removed |
| animation_codec | New minimal decoder primitives from Studio documentation; synthetic tests only |

Run `python3 -m unittest discover -s tests -v` from the repository root. Tests verify local rules and invariants, not original-game parity. All fixture poses and encoded test bytes are invented. Historical chapters' companion files remain outside this repository unless explicitly listed here.
