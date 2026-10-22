# Executable references

Standard-library Python implementations of selected local rules. Provenance and adaptations are recorded in [REFERENCE_MANIFEST](../REFERENCE_MANIFEST.json). These are not a full simulator or original engine source. Valid authored-domain inputs are assumed unless a function documents rejection; mathematical equivalents are not necessarily SIMD/bit-exact.

| Module | Scope |
| --- | --- |
| ik | Limb intermediate target and weighted orientation kernels |
| camera | Local camera springs, projection and selection helpers |
| snow | Contact forces, clipping, pressure, stick, shaping, springs and point impulses |
| input_cooker | Float32 cooker with explicit decay lookup; 384 original-instruction cases |
| snow_charge_release | Saved charge, release clock and cooked-zero transition; 1,536 exact original-instruction cases |
| snow_jump_step | Stateful jump gates, float32 factor order and ordered body requests; 288 original-instruction cases with synthetic curves |
| central_impulse | Native-checked central momentum update; separately labeled equal-delta-v coupled-body policy |
| response_delay | Delayed trick response and its domain guards |
| animation_blending | Ordered weights, quaternion paths, masks and phase helpers |
| animation_playback | Phase, markers, sampling and transition precedence |
| landing_pose | Alignment, delayed tilt and translation shift |
| skinning | Palette branches, remapping, bone anchors and four/eight-influence position math |
| skeleton | Hierarchy math; asset-dependent entrypoint removed |
| animation_codec | New minimal decoder primitives from Studio documentation; synthetic tests only |

Run `python3 -m unittest discover -s tests -v` from the repository root. Tests verify local rules and invariants, not original-game parity. All fixture poses and encoded test bytes are invented. Historical chapters' companion files remain outside this repository unless explicitly listed here.

The composed ground-response helper is in `ground_response.py`; its compiled
slope/intercept curve evaluator is in `runtime_curve.py`. See the
[composed helper contract](../docs/reconstruction/CENTRAL_IMPULSE.md#composed-helper-contract)
for supplied inputs, update order and native-validation limits. These refine the
earlier simplified ground-stick reference without replacing its provenance.

`skeleton_parent_transform.py` prepares guarded-refresh bank parents from a
caller-supplied owner matrix, explicitly clearing translation W. Its joined
instruction receipt covers the actual quaternion conversion and bank writes;
accessor freshness, locks and bank rotation remain supplied service boundaries.

`decay_table.py` builds the cooker decay lookup from 257 caller-supplied samples.
See [decay lookup construction](../docs/reconstruction/CENTRAL_IMPULSE.md#decay-lookup-construction)
for exact float32 ordering and the unresolved exponential sample producer.

`decay_exp.py` reconstructs both packed exponential lane paths on [-10, 0].
Its mantissas are mathematically generated. See
[decay exponential lanes](../docs/reconstruction/CENTRAL_IMPULSE.md#decay-exponential-lanes)
for instruction comparison, rounding mode and the remaining scalar endpoint.
