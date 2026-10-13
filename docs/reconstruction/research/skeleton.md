# Skeletal reconstruction: checked joins and a corrected boundary

This pass inspected existing binary decompilation and decoded-data references. It did not launch or attach to the game, acquire new asset payloads, or inspect Studio substitutes. No original hierarchy, bind-pose array or mesh weights are reproduced here.

## Main correction

The original hierarchy chapter predates the skinning and equipment chapters. Its statement that the final palette and mesh remapping remain wholly unknown is superseded. The reconstruction overview and latest conversational answer accidentally repeated that old boundary.

Already recovered and newly rechecked: the runtime name lookup, mesh remap fallback, local palette branches, four/eight-influence position kernels, selected equipment resource relationships and foot/hand ancestry. Not closed: the active rig's addon merge policy, packed vertex-to-float resource conversion, full runtime selection, or full-body procedural ordering.

Sources: `analysis/snow_game/animations/{skeleton,skinning,equipment,ik-solve}/CLIENT_GUIDE.txt` and adjacent references. Public equivalents reside under `docs/systems/animations/`.

## New focused check: name lookup is a sorted-key join

Directly inspected `analysis/sixth-pass/skinning/functions/140d49a80.c`. The lookup performs an unsigned 32-bit lower-bound search of fixed-size entries, checks equality, then returns the low 16 bits of the second word. No string comparison occurs. A missing table or missing key returns the missing-index sentinel.

```python
def lookup_bone(sorted_entries, name_hash):
    # entries are (u32 hash, encoded_index); table already constructed elsewhere
    lo, hi = 0, len(sorted_entries)
    while lo < hi:
        mid = lo + (hi - lo) // 2
        if sorted_entries[mid].hash < name_hash:
            lo = mid + 1
        else:
            hi = mid
    if lo == len(sorted_entries) or sorted_entries[lo].hash != name_hash:
        return MISSING
    return sorted_entries[lo].encoded_index & 0xffff
```

Consequences: actor rig index, mesh slot and bone-name identity must be separate types. Lookup does not resolve hash collisions semantically. If duplicate equal keys reach this table, this routine returns the first equal entry in sorted order. That is a code consequence, not proof of a collision or duplicate in the live rig. Table construction and duplicate ordering remain open.

## Rechecked: missing-joint fallback and a useful diagnostic

Direct inspection of `analysis/sixth-pass/skinning/functions/140e97780.c` confirms that every mesh joint is resolved by name first. When some entries resolve, missing entries are replaced by the first resolved index in mesh order. When none resolve, the mapping is cleared. The scan mutates earlier missing entries; they copy the same first originally resolved index, so the compact reference is equivalent:

```python
resolved = [lookup_bone(active_rig_table, joint.name_hash) for joint in mesh.joints]
first = next((i for i in resolved if i is not MISSING), MISSING)
map = [] if first is MISSING else [first if i is MISSING else i for i in resolved]
```

A reconstruction should record unresolved names BEFORE this fallback, or successful rendering can hide an incorrect active rig. This can explain a deformed mesh without a crash: fallback is not a proof of correct binding.

New local metadata cross-check: each ski addon has 18 CRC-matched human spellings in common with its corresponding base rig; each snowboard addon has 7. These are shared spellings, not proof that the runtime merges them. They make duplicate handling a concrete research target rather than a hypothetical edge case. The addon sets contain 34 and 29 bones respectively. A union-by-name implementation would be an invented policy until the table builder is traced.

## Palette: known arithmetic, narrower missing boundary

Inspected `analysis/sixth-pass/skinning/functions/140f74e90.c`, including the absent-pose branch, scale gate, scaled missing-index guard and unguarded unit-scale index reads. Existing source guide supplies decoded constants and matrix interpretation:

```python
if pose is None:
    return repeated_affine_diagonal(scale)  # no inverse bind or origin shift
for mesh_slot, bone_index in enumerate(joint_map):
    if abs(scale - 1) > 9.999999747378752e-6:
        M = diagonal_scale(scale) if bone_index is MISSING else (
            root * model_pose[bone_index] * diagonal_scale(scale) * inverse_bind[mesh_slot])
    else:
        # native unit-scale branch requires a valid mapped index
        M = root * model_pose[bone_index] * inverse_bind[mesh_slot]
    M.translation += origin_shift
    palette[mesh_slot] = first_three_rows(M)
```

The scale is between posed world bone and inverse bind. Moving it after the inverse bind changes translations. The position program subsequently sums exactly four or eight weighted affine positions without renormalizing weights. The final missing boundary is packed-position decoding, byte-weight resource-view conversion and complete allocation/upload constraints, not the absence of palette math.

## Re-executed evidence checks

Executed all four local references: equipment, skinning, skeleton and IK-solve. They passed their embedded assertions and examples.

- 126 addon bones recompose with maximum translation error 1.0818994549133265e-6 runtime units; descendant counts and selected foot/hand ancestry pass.
- Male board comparison frame reproduces identity palettes within 7.996093540469669e-7. This is a bind-data comparison, not a live addon merge rule.
- Eight matched mesh inverse binds reproduce identity within 6.341838491825646e-7.
- 207 hierarchy bones recompose with maximum translation error 1.3240067572306558e-6 and quaternion error 1.0975897742904195e-6.
- IK target, weighted orientation and mapped-scatter examples execute. Their illustrative anatomical labels are not recovered rider effector bindings.

These are independent reruns of existing reference checks, not new gameplay observations or native equivalence tests.

## Exact public overview corrections proposed

In `ANIMATION_PIPELINE.md`, replace "final skinning palette" in the final open-joins sentence with "active-rig addon merge policy and packed vertex/weight resource conversion". Add a link to the skinning chapter and explain that palette math, scale gates and remap fallback are recovered.

In `ASSET_PIPELINE.md`, replace the paragraph beginning "A mathematically plausible skinning palette" with:

> The binary-derived skinning chapter specifies the runtime palette equation, scale and missing-pose branches, joint-name remap fallback, and four/eight-influence position arithmetic. Use those rules rather than treating the palette as a textbook guess. Establish the active rig and mesh-slot mapping for each resource separately; packed position decoding, byte-weight conversion and addon merge policy remain open. Resource UID, runtime handle, selected graph output and active instance also remain separate joins.

Retain the original hierarchy source document and its manifest unchanged; add a visible supersession note in the overview instead of quietly rewriting historical evidence.

## Best next experiment / engine value

First trace the producer of the sorted hash-to-index table consumed by the lookup. Compare base-only, ski-addon and board-addon construction and duplicate handling using static call sites. This is the highest-value unclosed skeletal boundary.

A subsequent explicitly authorized live capture can sample the active rig table, joint map, root, selected model transforms and output palette before/after an equipment change. Compare predicted and observed palette entries, but capture generation/version identity around the read because sequential reads are not atomic. Use only aggregate errors and binding diagnostics in public outputs.

For an independent engine now, implement a synthetic rig inspector exposing local/model bones, mesh-slot map, unresolved-name list, pre/post-IK poses, inverse-bind residuals, and palette results. That makes mods and probes easy in OUR engine: replace a mesh, inspect why it stretches, isolate an IK stage, change one constraint. It does not establish that the original engine will accept a mod or make an unknown graph policy known.
