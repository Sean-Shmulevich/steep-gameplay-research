# Cross-title check: AnvilNext 2.0 notes from Ghost Recon Wildlands, tested against Steep

Draft, 2026-11-04. This page tests facts published for another Anvil title against the analyzed Steep image and the local Steep archives. It was produced offline: the game was not launched, attached to or modified, archives were opened read-only, and no payload bytes are reproduced here.

Third-party source: [GhostReconWildlands-AnvilNext2.0-Documentation](https://github.com/Firejumper93/GhostReconWildlands-AnvilNext2.0-Documentation) by Firejumper93, CC BY-NC 4.0. Only facts (offsets, layouts, names, hash values) are used; the wording here is ours. Each claim cites the file of that repository it comes from, written as `WL docs/NN-name.md`. That project itself warns that Anvil titles often share byte-identical code while struct offsets differ, and that a signature match proves presence, not use. Every value below was re-derived in Steep; nothing was copied across as a Steep fact without a test.

Tags:

- **verified-in-Steep**: re-derived from the Steep image or archives in this pass.
- **contradicted-in-Steep**: Steep evidence disagrees.
- **unverified-Wildlands-only**: plausible and relevant, not tested here. Do not implement from it.

RVAs are for the analyzed image only (base `0x140000000`), as in the rest of this repository.

## 1. Reflection metadata names many engine objects

**Plaintext class names: contradicted-in-Steep.** WL docs/08-reflection.md and docs/10-negatives.md report that their Steam build carries no plaintext gameplay class names and that names exist only as CRC32 hashes (they note a different store build does carry them). The Steep image carries **5,672 reflected class descriptors with plaintext names**. We accepted a descriptor only when a pointer to an identifier string sits next to a dword equal to the CRC32 of that exact string, so every entry is hash-checked.

**Descriptor layout: verified-in-Steep.** Offsets are from the name-pointer field:

| Offset | Content |
| --- | --- |
| `-0x18` | pointer to the first property record |
| `+0x00` | pointer to the class name |
| `+0x08` | CRC32 of the parent class name |
| `+0x0c` | CRC32 of this class name |
| `+0x10` | instance size |
| `+0x38` | constructor or factory entry (5,091 descriptors have one) |

This is the same record our earlier [UIManager audit](ANIMATION_CONTEXT_RETIREMENT.md) used as "constructor metadata". It is the Anvil reflection system that WL docs/08-reflection.md describes. `GR_*` (Ghost Recon) and `ACU*` (AC Unity) class names also ship in Steep, so the code lineage is shared.

**Joining names to our authored labels: verified-in-Steep.** For each descriptor we followed the constructor and recorded the table it stores at `this+0`. Every RVA cited in this repository was then looked up three ways: as an installed table, as a descriptor constructor, and as a virtual slot inside exactly one named primary table. Slots bound to generic stubs shared by many tables were discarded.

| Our document and label | Reflection class | Evidence |
| --- | --- | --- |
| [Central impulse](CENTRAL_IMPULSE.md), [motion membership](MOTION_MEMBERSHIP_OBSERVATION.md): "owned component", table `0x1e789b8` | `GR_cPlayerComponent` (size `0x7e0`, parent `GR_cBrainedComponent`) | constructor installs the table; our cited slots `0x270`, `0x278`, `0x470`, `0x488`, `0x4a0`, `0x4b0`, `0x4b8`, `0x4c0` belong to it |
| [Motion membership](MOTION_MEMBERSHIP_OBSERVATION.md): "acquired actor", table `0x1e7a350`; [target publication](../systems/tricks/target-publication/evidence.md) constructor `0x4de010` | `PlayerSnowboardComponent` (size `0x1cd0`, parent `SnowboardComponent`) | table and constructor both match |
| Motion membership: owned component, table `0x1ee5a40` | `BipedComponent` (parent `BipedComponentBase`) | table match |
| [Input-to-action route](INPUT_TO_ACTION_ROUTE.md): service owner, constructor `0x444f20`, table `0x1e67338` (previously "semantic class name has not been established") | `mManagerFactory` (size `0x448`, parent `MandatoryUniverseComponent`) | table and constructor match; slot `0x90` is the cited initializer |
| [Runtime-binding trace recipe](../systems/animations/runtime-binding/trace-recipe.md): candidate constructor `140d28e10`, table `141f1fad8` | `AnimComponent` (size `0x760`, parent `IAnimationComponent`) | table and constructor match |
| [Environment runtime evidence](../systems/world/environment-runtime/evidence.md): tables `141eb65f8`, `141eb6660`; constructor `1408ad1d0`; `1409138c0` | `TimeOfDayPropertyController`, `WeatherPropertyController`, `Season` constructor, `TimeOfDayManager` slot `0x118` | table, constructor and slot matches |
| [Pose follower evidence](../systems/body/pose-follower/evidence.md): `14138b270`, `14138bd50` | slot `0x78` of `ClassicRagdollController` and `PinocchioRagdollController` (parent `RagdollController`) | single-table slot match |
| [Animation event registry](ANIMATION_EVENT_REGISTRY.md): `0x851060` | `EntityManager` constructor | constructor match |
| [Context retirement](ANIMATION_CONTEXT_RETIREMENT.md): `0x892300`, `0x892720` | slot `0x48` of `DominoScriptExecutionContext`; slot `0x48` of `EntityGroup` / `WorldEntityGroup` | slot match |

A name identifies a class. It does not prove what the class does in gameplay. WL docs/08-reflection.md makes the same caution about recovered names.

**Physics solver objects: contradicted-in-Steep (no names).** The [link solver](LINK_SOLVER.md) objects get no name from reflection. These include the body table `0x29c99a8`, the kind-7 grid resource table `0x29ca138`, the resource table `0x29c9ac8`, the pair-handler table `0x29ca780`, the kind-4 table `0x29caa30` and the dispatch at `0x1994970`. None of them has a descriptor or MSVC RTTI, and no named constructor or virtual method appears within three direct-caller levels. They live in a separate code region whose only strings are module labels, for example a multi-threaded broad phase, an island manager and a motion worker thread. Our authored labels for these objects therefore remain necessary.

## 2. Property records

**Stride `0x38`, name CRC at `+0x04`, type CRC at `+0x08`, kind in the high half of `+0x0c`: verified-in-Steep.** Source: WL docs/08-reflection.md. Records for `EngineOptions` (class CRC `0xb4e69fa1`, which matches WL as expected for the same name) contain hashes of `ShowHud`, `DisplayIKDebug`, `DisableHumanIK`, `ActivateGroundIK` and `DisplaySkeletonStates`. None of those names appears as plaintext in Steep. WL's low-half decode gives the same relative offsets for the first three as WL reports (`0x00`, `0x18`, `0x1c`). The Steep instance size differs: `0x70` against WL's `0x88`.

**Byte-offset packing: contradicted-in-Steep for ordinary fields.** WL docs/08-reflection.md withdraws the AC Unity rule `packed >> 18` and replaces it with `(packed & 0xffff) >> 3`. In Steep the replacement gives zero for almost every ordinary field, which is impossible. The AC Unity rule instead gives seven distinct in-bounds offsets for `Skeleton` (size `0xb0`): `0x10`, `0x20`, `0x30`, `0x40`, `0x48`, `0x50` and `0x8c`. The Skeleton constructor at `0xd7ef60` initializes exactly those seven offsets, with an all-zero vector at `0x10` matching kind `0x0d`. For flag tables such as `EngineOptions`, the low half increments while the high half stays constant, so their absolute member offsets are **unresolved**. Unbounded table walks overrun into the next class in Steep too, which confirms WL's closure warning (WL docs/09-methodology.md).

Fields this exposes include `Skeleton.Bones`, `Skeleton.BodyPartMapping`, `PhysicsWorldComponent.Gravity` and `KinoComponent.ContactTable`, with a `DBSnowboardConfig`-typed field in `PlayerSnowboardComponent`. Field names were recovered by matching CRC32s against a dictionary built from Steep's own strings, as WL docs/08-reflection.md suggests.

**Enum terminator: partly contradicted-in-Steep.** WL docs/08-reflection.md proposes `crc32("ID_Enum")` as the anchor for scanning every enum. Steep has 103 sites where `Count` is followed by `Invalid` and a type hash, but `ID_Enum` occurs once. Use the `Count`/`Invalid` adjacency in Steep.

## 3. Archives and compression

**Codec byte meanings: partly verified-in-Steep.** Source: WL docs/02-formats.md. Steep stores a codec table at RVA `0x3074200`, stride `0x30`, indexed by the block-header codec byte, with the name pointer at record `+0x20`:

| Codec byte | Steep name | WL statement |
| --- | --- | --- |
| 0 | `LZOPRO_LZO1X_W03_15` | LZO1X: consistent |
| 1 | `LZO1X_999` | LZO1X(-999): consistent |
| 2 | `LZO2A` | LZO1A: contradicted |
| 3 | `LZ4` | not stated |
| 4 | `LZ4_HC` | not stated |
| 5 | `ZSTD` | LZO1C: contradicted |
| 6 | `COPY` | not stated |

**Codec 5 in shipped data: verified-in-Steep.** A header census of all 27 local archives, 165,021 entries, found every data block at version 2 / codec 5 / chunk size `0x40000`. The exceptions are one codec-0 `PrefetchingFileInfos` per archive and one magic-less `GlobalMetaFile` per archive. No codec-1 block exists. This agrees with the [asset pipeline](ASSET_PIPELINE.md).

**"The shipped compressor is LZO1X-999": contradicted-in-Steep.** Source: WL docs/02-formats.md and docs/10-negatives.md. Steep's only LZO-family data is 70 compressed codec-0 chunks:

- All 70 decode with standard LZO1X decompression.
- Re-encoding with LZO1X-999 reproduces 0 of 70, and its output is about 30% smaller.
- LZO1X-1 reproduces 3 of 70 byte for byte and comes within 0.3% of the total size.

The data matches a fast LZO1X-1-class encoder, which fits the LZO-Pro codec name.

**Block-size fields are u16 and blocks are `0x8000`: contradicted-in-Steep.** Source: WL docs/02-formats.md and docs/11-other-anvil-titles.md. Steep's block header carries a u32 flags word holding the layout bit and a `0x40000` chunk size, followed by u32 per-chunk sizes. 124,371 chunks have sizes above `0xffff`. Steep is the u32 variant that WL attributes to other titles.

**Chunk checksum is Adler-32 with both sums starting at zero: verified-in-Steep.** This was already known locally. It held for 70 of 70 codec-0 chunks; standard Adler-32 matched none.

**Archive size padded to `0x8000`: contradicted-in-Steep.** Source: WL docs/02-formats.md. Steep archives end at the last payload byte; only 1 of 27 ends on a `0x8000` boundary.

**Resource class hash is CRC32 of the class name: verified-in-Steep.** Source: WL docs/02-formats.md. Type hashes from our archive notes resolve through the descriptors:

| Hash | Class |
| --- | --- |
| `0x0fa3067f` | `Animation` |
| `0xe5a83560` | `GameBootstrap` |
| `0xa97216a6` | `InventorySportPreset` |
| `0x0165ae97` | `XCurve` (the same value WL lists) |
| `0x24aecb7c` | `Skeleton` |
| `0x95741049` | `Bone` |

**A patch supersedes per record, not per archive: verified-in-Steep (already known).** Source: WL docs/02-formats.md. Local archive-override experiments found patched animation records resident while older base copies of the same records were not.

**`PrefetchingFileInfos` cannot be decompressed: contradicted-in-Steep.** In Steep it is a regular layout-B codec-0 stream that decodes.

## 4. Skeleton, pose and middleware

- **Bone identity is CRC32 of the bone name: verified-in-Steep.** Source: WL docs/03-skeleton.md. The engine also loads bone hashes as call-argument immediates, as WL describes: `Head` 9 times, `LeftToeBase` 8 times.
- **Pose bone records have stride `0x20`: verified-in-Steep. Buffer pointer at `Pose+0x178`: contradicted-in-Steep.** Source: WL docs/04-pose.md. Steep has a single accessor at `0xda9b60` that computes index shifted left by 5, plus the pointer at `+0x198`. WL's statement that the record holds translation before quaternion was not re-derived.
- **Sorted hash-to-index name lookup: verified-in-Steep (already known).** See the [skeleton research](research/skeleton.md).
- **HumanIK is statically linked: verified-in-Steep (new lead).** Source: WL docs/03-skeleton.md and docs/01-binary.md. Steep contains the five HumanIK data tags and an effector name table beginning with `HipsEffector`. WL's characterization pass, live-rig rules, `BoneHandle` layout, pose flags and write window are **unverified-Wildlands-only**.

## 5. Binary and build properties

- **ASLR off: contradicted-in-Steep.** Source: WL docs/01-binary.md. The analyzed image header sets dynamic base. Control-flow guard is not enforced in either title.
- **Every engine call passes through a 5-byte jump thunk: contradicted-in-Steep.** Source: WL docs/01-binary.md and docs/11-other-anvil-titles.md. About 2.4% of direct call targets in Steep land on a jump thunk. Thunks exist for selected paths, such as the constructor thunks above, but are not universal.
- **MSVC RTTI covers only infrastructure: verified-in-Steep.** Source: WL docs/01-binary.md. Steep's 307 RTTI names are library and infrastructure types.
- **Up axis +Z: verified-in-Steep (already in our guides).** Source: WL docs/01-binary.md and docs/11-other-anvil-titles.md. **+Y forward, right-handed, 1 unit = 1 metre: unverified-Wildlands-only.** Steep has no Ansel import from which to read a declared basis.

## 6. Input and methodology

- **The active input context is one integer index on a dispatcher, separate from the per-context cache: unverified-Wildlands-only.** Source: WL docs/12-input.md. The shape matches the "current context selector" bounds-checked against a context count in our [input probe research](research/input-probes.md). WL's Steam Input action-set route has no supporting strings in Steep.
- **The game consumes the pressed-since-last-call bit of the Windows key-state API: unverified-Wildlands-only.** Source: WL docs/10-negatives.md. This matters for any future live probe tooling: read the key-down bit and detect edges yourself.
- **Method rules adopted:** bound every table walk by its owner, check that claimed offsets fit the class size, run a positive control in the same pass, and use exception-table bounds instead of backward disassembly. Sources: WL docs/09-methodology.md and docs/11-other-anvil-titles.md. These agree with [our evidence rules](../EVIDENCE.md).
- **Not relevant to Steep:** weapons, projectiles and attachments (WL docs/06-weapons.md); VR and camera injection specifics (WL docs/05-camera.md); renderer slots (WL docs/07-rendering.md); protection and developer-scaffolding censuses (WL docs/01-binary.md and docs/10-negatives.md).

## Remaining work

1. Resolve flag-table offset packing (`EngineOptions`) against a constructor or reader.
2. Use the named classes to replace authored labels in the linked documents. Keep the old label in the text as provenance.
3. Walk property tables, bounded by owner, for `GR_cPlayerComponent`'s parents and for `SnowboardComponent`, then compare field offsets with our cited member offsets.
4. Look for a HumanIK characterization pass in Steep, starting from the `LeftToeBase` hash immediates.
