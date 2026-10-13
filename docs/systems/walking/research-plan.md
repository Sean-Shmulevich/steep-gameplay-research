> Findings-only publication. Companion assets, datasets, binaries and raw traces are not distributed. Read [current status](../../STATUS.md) for qualifications. Source provenance is retained in the repository manifest.

# Walking and walking in snow

User explicitly requested on-foot movement and walking in snow in addition to existing sports. This is a separate movement mode; do not apply the snow-board body chain or fluid model to a pedestrian without proof.

## Existing inspected leads

- analysis/fifteenth-pass/private/studio/docs/specs/gameplay/db_player_walk.ksy describes a locally copied DBPlayerWalk record schema: surface groups with50 values, several scalars, a referenced three-key curve spanning-90..90, and walk FX references for carried ski/snowboard equipment, wingsuit and paraglider. Field values and references are documented; slope-limit and speed-factor interpretations remain unverified. This imported schema is evidence of previous asset research, not a new byte verification.
- The same schema points to PlayerDataMoveSpeeds / Mover_Player for movement speeds. This lead needs independent consumer recovery.
- analysis/snow_game/animations/paths/CLIENT_GUIDE.txt identifies authored scalar remaps for walk slope and walking-stick length. Existence of a remap does not prove active selection.
- animations/corpus/catalog.json contains WALK_ARM_STAND, WALK_ARM_UP and WALK_ARM_DOWN metadata. Catalog membership alone does not provide decoded motion tracks or runtime selection.

## Binary/data investigation

1. Recover on-foot controller construction, body ownership and movement-speed consumers. Trace input smoothing, acceleration/deceleration, turning and idle/walk/run selection.
2. Trace DBPlayerWalk surface table and curve consumers. Prove angle convention, units, limits and whether curve output is speed, multiplier or another scalar.
3. Establish whether snow depth/type affects speed, traction, sinking or step height. Keep actual movement physics distinct from footprints, particles, carried-equipment FX and visual foot sinking. No assumed powder slowdown.
4. Trace authored walking clips and walk-slope inputs to selected graph nodes, playback speed, foot contacts, IK/pelvis correction and walking-stick placement. Separate root motion from controller-driven translation.
5. Trace transitions between walking and equipped sports, including carried equipment, reset of momentum, steep-slope sliding, falls and recovery.

Deliver address-free pseudocode/examples with private provenance and confidence labels. Start with constructor/type-backed consumers; cap each initial trace to8 selected functions and stop at the first unresolved dispatch ownership. Preserve other agents' work; no live changes for a static pass.

## Future testbench extension

Prove fresh on-foot ownership before defining read ranges. Observe flat/no-input, walk/stop, uphill/downhill, and surface comparisons with the same documented controls. Snow-depth comparisons require verified surfaces/depth and slope matching; appearance alone is insufficient. Record input, body velocity/pose, selected movement mode, contact normal/material, speed target, clip identity/phase and foot/pelvis transforms only where their producers are established.

The run39 contact recorder can supply bounded reads once ownership and field layouts are recovered. Its existing board-specific contact_fields must not be reused for walking. No walking test, binary recovery or snow-effect validation has yet been performed by this plan.
