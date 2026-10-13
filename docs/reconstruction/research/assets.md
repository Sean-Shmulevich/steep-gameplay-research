# Asset interfaces for a reconstruction

This pass inspected the existing local Studio documentation snapshot and local research. No Studio checkout was modified, no game launched, and no payload was copied to the public repository. Studio census claims below were not rerun. Existing local reference checks were rerun as described below.

## Concrete correction: the palette arithmetic is already known

Studio `skeleton.md` sections 7.2–7.3 and `mesh.md` section 5 leave the runtime skin matrix unverified. Later local `analysis/snow_game/animations/skinning/CLIENT_GUIDE.txt`, “Actual final palette production,” gives the binary-derived local producer and shader consumer. The public asset guide should distinguish these evidence dates rather than continue calling the entire final palette unresolved.

For a resolved joint, the documented producer is:

```text
world = global_pose_root * model_pose[joint]
if abs(scale - 1) > 0.000009999999747:
    matrix = world * uniform_scale(scale) * inverse_bind[mesh_slot]
else:
    matrix = world * inverse_bind[mesh_slot]
matrix.translation += render_origin_shift
palette[mesh_slot] = first_three_rows(matrix)
```

No model pose produces diagonal scale matrices with neither inverse bind nor origin shift. Missing joints in the scaled branch produce scale plus origin shift; the unit-scale branch has no such guard. This is narrower than proving the entire renderer or data upload path.

The shader performs exactly four or eight weighted affine transforms, including lookups for zero-weight entries; it does not normalize weights. Dispatch uses groups of 128 and ceiling division; shader-side final-group bounds are absent. Buffer padding/dispatch safety remains an external requirement.

The remapper aliases missing mesh joints to the first resolved joint in mesh order, clearing the map when none resolve. That must not be applied to the base skeleton and called the active character's result: the live actor may include addons.

## Exact resource joins and their boundaries

| Join | Evidence | Missing interface |
|---|---|---|
| Archive record ID → highest patch payload | Studio forge documentation | Versioned importer, conflicting-copy diagnostics and locally supplied assets |
| Vertex influence byte → submesh palette → mesh bone entry → name CRC | Studio mesh section 5 | Runtime packed-buffer conversion not proved by successful offline decode |
| Mesh bone CRC → active actor joint | Local skinning remapper | Construction and ordering of the active merged rig |
| Equipment selected row → graphic plus addon skeleton | Local equipment guide, actual BuildTable rows | Upstream tag registry and row-match policy |
| Addon root → base-body attachment | Studio skeleton sections 7.3, local equipment bind comparison | Duplicate human-bone override and runtime merge policy |
| Animation track identifier → bone or auxiliary channel | Studio animation and local animation research | Unbound semantic channels must stay visible; positional matching is invalid |
| Authored graph output → runtime output descriptor → selected timeline | Local conversion guide | Authored-to-runtime conversion and resource UID → runtime handle join |
| Entity → LOD selector → mesh → material | Studio mesh sections 6–7 | Exact LOD switch semantics and unresolved/null material refs |

The Studio census makes the need for a rig-assembly interface concrete: only 89 of 2,893 skinned meshes have exactly one skeleton candidate under CRC-set containment. 844 have no single candidate; the document attributes these to body-plus-addon compositions. This is a reported offline corpus result, not live actor proof. Choosing the smallest candidate or lowest resource ID is an explicit Studio converter heuristic, not an original selection rule.

Studio reports inverse-bind matrices as column-major and 157 of 226 live skeletons rooted at a body bone. Most such addon roots are identity in their attachment frame. Matching a mesh at bind pose is necessary but insufficient: using inverse(IBM) as a fabricated per-joint bind can always make an initial pose look correct while concealing the wrong hierarchy.

Local equipment evidence is stronger for specific ski/board families: authored rows pair graphics with the corresponding male/female addon rig; ski mesh joints descend from feet and pole mesh joints from hands. Snowboard has a small cross-foot weighted bridge, whereas skis have no cross-side weighted vertices. That is a deformation relationship, not a recovered constraint enforcing a rigid board in physics.

## What reconstruction enables

A deliberately designed resource interface can support user-supplied asset import, synthetic replacement clips, hot replacement of materials or equipment, skeletal debug views, per-bone pose inspection, layer disabling, and deterministic headless deformation tests. These are proposed capabilities of our implementation. They do not require a full engine first: a rig-and-clip workbench can deliver them earlier.

An effective boundary would expose `resolveResource(id, patchPolicy)`, `assembleRig(base, addons, explicitPolicy)`, `bindMesh(mesh, rig)`, `bindClip(clip, rig)`, and `evaluatePose(inputs, dt)`. Every result should retain provenance, unresolved channels and chosen fallback policies. Never silently mix Studio-authored clips or video-fitted timing with asset-decoded tracks; preserve a category on each asset and parameter.

This does not establish original-game mod injection. A replacement engine's hot-reload API cannot load a changed archive into the original executable. Original-game replacement still needs proven writable archive serialization or a loader interception boundary, identity/checksum behavior, lifecycle/reload policy and a reversible deployment method. None of these was verified in this pass. In particular, having a decoder is not having a safe repacker.

## Most useful next tests

1. Build a synthetic base rig and two overlapping addons. Make duplicate CRC policy explicit and test that switching addon order cannot silently change output. Keep candidate policies configurable until runtime evidence identifies the original rule.
2. Add a nonidentity submesh palette fixture so direct indexing demonstrably fails. Include an unused zero-weight slot with an invalid index: CPU validation must reject it before dispatch because the documented shader still dereferences it.
3. Exercise the recovered palette branches with nonunit scale, nonzero inverse-bind translation and render-origin shift. This catches multiplication-order errors hidden by identity fixtures.
4. Use a synthetic rigid board and a split weighted board under the same foot motion. Display deformation separately from physical collision geometry. This isolates visible bending from snow-contact behavior.
5. Pursue the runtime rig-merge producer and packed position/weight view setup in the binary. Studio gives an offline position/weight decode; that is an excellent candidate formula to compare at the upload boundary, not proof that boundary is closed.
6. Keep an authored replacement clip in a separate resource namespace and stamp it `studio-authored-substitute`. Run the same bindings and output capture against decoded clips locally without publishing tracks.

## Checks performed

`analysis/snow_game/animations/equipment/reference.py` passed: 126 addon bones reproduced stored model translations with maximum error 1.0818994549133265e-6; male board bind alignment error 7.996093540469669e-7; foot/hand ancestry and selected-row pair checks passed.

`analysis/snow_game/animations/skinning/reference.py` passed: eight matched inverse-bind identities had maximum component error 6.341838491825646e-7; shader examples, remap fallback, attachment and null-pose checks passed.

These checks validate local references and decoded data consistency. They did not run a GPU shader, establish live selection, or rerun Studio's corpus census.

## Source scope

- `publication-review/studio/skeleton.md`, sections 7–8.
- `publication-review/studio/mesh.md`, sections 4–7.
- `publication-review/studio/animation.md` and existing public asset guide for channel clocks/provenance distinctions.
- `analysis/snow_game/animations/skinning/CLIENT_GUIDE.txt` and `reference.py`.
- `analysis/snow_game/animations/equipment/CLIENT_GUIDE.txt` and `reference.py`.
- `analysis/snow_game/animations/conversion/CLIENT_GUIDE.txt`.

No new original binary disassembly was performed in this bounded pass. Its new contribution is reconciling older Studio uncertainty with stronger local findings and identifying the still-missing interface boundaries precisely.
