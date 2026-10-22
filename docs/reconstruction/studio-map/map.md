<!-- Imported authored research, not game payloads. -->
> Source: Studio `steep-wasm`, commit `1344bca03985eb1540236fb2ecd3cbbe8ecdcf14`, `docs/specs/world/map.md`.
> Evidence labels and validation counts below are the source agents' reports;
> the asset-level checks were not rerun for this import. Local source links were
> converted to plain references; their files may not be included here. Historical
> superseded sections remain labeled. Studio-authored runtime policies are not
> evidence of original game behavior.

# Mountain map: drop zones, POIs, map UI, region bounds — G-05

Clean-room spec of the data behind Steep's zoomed-out mountain view ("Mountain View"). It was written
only from the owner's `DataPC*.forge` files, read-only. It builds on
`world-gameplay.md` (Studio source: `../formats/world-gameplay.md`) (P2-09: MapMarker `0x6b3367e4`, positions),
`localization.md` (Studio source: `../formats/localization.md`) and `ui-assets.md` (Studio source: `../formats/ui-assets.md`) (P2-10b), and
`floor-height.md` (Studio source: `../formats/floor-height.md`) / `cache/terrain/<R>/ground.json` (P4-04/P4-10).
The Kaitai layouts of the new records are in `drop-zone.ksy` (Studio source: `drop-zone.ksy`).

Evidence tags: **VERIFIED** means a command was run on Steep data here and its output is quoted.
**UNVERIFIED** means an inference or an outside source. Lab scripts: `tools/lab/G-05/{dz,poi,ui}/`
(read-only). Oracles: `$STEEP_DATA/shared/map-lab/` (see `docs/shared-data.md`).

## §1 Summary

- 465 map markers: 147 drop zones, 46 exit points, 272 POIs (§2, §3). Every one has a non-empty
  English display name through its LocString id (§3.1).
- **No data record lists the sports a drop zone allows** (§2.8). Unlocks are an XP level on the Global
  track (`0xadeae73c`) for 31 markers; category 1 = "Legendary" = level ≥ 2 (§2.4, §2.9).
- Sub-regions (Aravis, Mont Blanc, …) come from name tokens (§3.3). In the Alps the token of every marker
  is cross-checked against the `CellData_Region_*` cells (255 of 259 agree). In Japan DZ/EPs carry a token;
  Japan POIs have none and take the nearest tokenised DZ/EP (an inference, UNVERIFIED). Alaska is a single
  region by rule (one `CellData_Region_Alaska`).
- Steep has no 2-D map image: the map is the 3-D terrain seen from far away, with world-space icons.
  The icons are TextureMaps picked by name (§4).
- Region bounds: the terrain square [−8000, 8000]² in all three regions (§5).
- The ground position of a marker is FloorHeightData sampled at its (x, y) (bilinear,
  `ground.json`), done by the Summit `map` cache stage (`docs/summit-map.md`).


## §2 Drop zones and exit points

Clean-room spec of the 193 drop-zone (DZ) and exit-point (EP) markers, written only from the owner's
`DataPC*.forge` data (read-only), through the P2-09 pickle cache. It builds on
`../formats/world-gameplay.md` (Studio source: `../formats/world-gameplay.md`) (G.1–G.3: MapMarker `0x6b3367e4`, region
binding, position from the EntityGroup) and does not repeat it. Machine-readable layouts:
`drop-zone.ksy` (Studio source: `drop-zone.ksy`).

Evidence tags: **VERIFIED** means a command was run here (2026-10-11) and its output is quoted, mostly in
§2.13. **UNVERIFIED** means a reading inferred from names, values or shape.

Lab scripts (read-only, Python): `tools/lab/G-05/dz/`. They read the P2-09 caches
(`$STEEP_DATA/P2-09/cache/*.pkl`, `idindex.pkl`) through `dzlib.py`, and they do not need the forge
readers. Outputs go to `$STEEP_DATA/G-05/dz/`. Oracle CSV: `$STEEP_DATA/shared/map-lab/dz_oracle.csv` (§2.11).

### §2.0 Short answers

- **Sports per drop zone: no such field exists.** The marker, its definition, its XP-unlock record and the
  drop-zone component of its EntityGroup are parsed byte for byte (§2.2–§2.5; every record ends exactly
  where the layout says, VERIFIED). None of them has a sport enum or sport list. No reference from them reaches a
  sport profile `0xa97216a6` either (§2.7, VERIFIED). What the data does carry:
  - a component **class**: `0x32c7f7b9` (138, "drop zone") or `0xb96f89fc` (55, "exit point / launch
    point");
  - a component **kind** u32: 13 in 186 records, 11 in the 7 `ALA_DZ_BaseJump_*` markers. The marker tail
    u32 at end-41 is 3 in exactly those 7 (193/193 agreement);
  - **name tokens**: `Wingsuit` in 23 EP names, `BaseJump` in 7 DZ names, so 30/193 = 15.5% carry a
    sport-like token. `Balloon` is in 8 names.

  So the CSV `sports` column is empty for every row. A Summit importer should treat every DZ/EP as
  open to every sport. It may tag the 7 kind-11 markers as base-jump spots and the `Wingsuit` EPs as wingsuit
  launch points from the name only (UNVERIFIED as game behaviour).
- **Unlock and discovery.** Three exclusive cases, decided by the marker's definition ref (VERIFIED counts):
  1. **XP-level gated (18)**: the definition is an `0xadeae73c` record with level ≥ 2 on the Global track.
     This is exactly marker category 1 (193/193). These are the 9 `*_Legendary` / Kahiltna Queen DZs and the
     9 `*_Balloon` / `Alps_EP_Cervin_Wingsuit_Unlocked` EPs; required levels are 4–30. All 18 also have a
     `LegendaryDropZoneFirstSpawnMemorableMoment` record.
  2. **Level-1 gate (13)**: `0xadeae73c` with Global level 1 (`Type_XP_Global_Level_1_<DZ>`). Reading:
     open from the start (UNVERIFIED). Japan's 4 (one per sub-region) and Alaska's `ALA_DZ_Huntington` look
     like region start points (UNVERIFIED).
  3. **No condition in data (162)**: a `0x5502fe93` DropZoneDefinition (160) or no definition (2). These
     are, presumably, discovered in the world ("EXPLORER – New … DROP ZONE unlocked" banner,
     `docs/specs/behavior/crosscheck.md` PG-03). No discovery radius or "initially unlocked" flag was
     found. The `Locked`/`Unlocked` name tokens do **not** match any data field (§2.9).
- **Legendary = category 1.** The marker category u32 at end-6 equals the component byte `is_level_gated`
  (193/193). It also equals "XP level ≥ 2" (193/193), and it matches the 18 Legendary first-spawn records.

### §2.1 Data chain

```
Game Bootstrap Settings (DataPC* entry 0x800, effective = DataPC_patch_02)
  0xa1a8ea23 region manifest "Alpes"/"Alaska"/"Japan"   (§2.6)
     list 6 ──► 0x6b3367e4 MapMarker (DZ/EP)            (§2.2, world-gameplay.md G.3)
     list 0 ──► 0x5502fe93 DropZoneDefinition           (§2.3)
  MapMarker
     def ref ──► 0x5502fe93 DropZoneDefinition  (160)   ──► EntityGroup (+ back-ref to marker)
             └─► 0xadeae73c XP-level unlock     (31)    (§2.4)
             └─► none                           (2)
     end-32 ──► WorldRoot (region)
     end-23 ──► 0x3f742d26 EntityGroup in DataPC_STP_<Map>[_patch_02] Cell21844_DataBlock (0x1f48e86884)
                  └─ drop-zone component 0x32c7f7b9 / 0xb96f89fc (§2.5): radius, heading, kind,
                     flags, weather preset, hour, 2 sound cues
     end-14 ──► 0x173e2fa7 Quest (35) or 0
```

### §2.2 MapMarker fields specific to DZ/EP

The layout is in world-gameplay.md G.3. G-05 adds the following (VERIFIED over the 193 DZ/EP markers,
`dz_extract.py` checks, §2.13):

| Off | Type | Field | Census / meaning |
|---|---|---|---|
| +0x0f | u32 | `marker_index` | For DZ/EP: dense 0..192, unique (193). For POIs: 0..271, unique (272). The UnlockableManager holds the u32 values 272 and 193 next to each other (§2.7). Reading: a per-kind discovery or save-bit index (UNVERIFIED). |
| p+1 | u32 | n defs | 1 in 191, 0 in 2 (`ALA_DZ_BaseJump_Unlocked_01`, `Alps_EP_Artavis_Wingsuit_Onboarding`) |
| p+5 | n × {u8 0, u64} | definition ref | `5502fe93` 160, `adeae73c` 31 |
| p+5+9n | u64 | `handle` | Not a record id in any pack (no hit in `idindex.pkl`, 375,442 ids). It appears in no other cached record. Unique over the 193. Sometimes it is def id + 1. Role UNVERIFIED (instance handle). |
| p+13+9n = end-45 | | tail | This is the anchor `0x72873a8e`, so the head is fully accounted for (193/193). |
| end-41 | u32 | `tail_u32_41` | 3 in the 7 kind-11 BaseJump DZs, 0 in all others (193/193) |
| end-15 | u8 | 0 | 193/193 |
| end-14 | u64 | `quest_ref` | `0x173e2fa7` Quest in 35 (19 with a DZ definition, 16 with an XP definition), else 0. All 8 Legendary DZs have one. Role (quest that starts there or unlocks it) UNVERIFIED. |
| end-6 | u32 | `category` | 0 (175) / 1 (18) = level-gated "Legendary" |
| end-2 | u8 | `end2` | 1 only in `ALA_DZ_BaseJump_Unlocked_01` |
| end-1 | u8 | `end1` | 1 in every EP (46), in Japan DZs 39/48 and in Alaska DZs 7/19 (the BaseJump ones); 0 in all 80 Alpes DZs. Meaning UNVERIFIED. |

The marker's localized name (`loc_id`) is the same as the component's (193/193). Its text is designer text,
present in some records (e.g. `LA DAME BLANCHE`, `Mount Wild Horse`).

### §2.3 `0x5502fe93` DropZoneDefinition

160 records (105 × 56 B, 55 longer). The size is `56 + 2·nchars + 2·(nchars>0)` in 160/160. The record
ends right after `marker_id` in 160/160 (VERIFIED). Kaitai: `dz_definition`.

| Off | Type | Field | Census |
|---|---|---|---|
| +0x00 | u64 | object id | |
| +0x08 | u32 | type `0x5502fe93` | |
| +0x0c | u8 | 1 | 160 |
| +0x0d | loc_string | `{u64 sub id, u32 0x81a7045d, u32 loc_id, u32 nchars, u16 text[n], u16 0 if n}` | Text present in 55 (e.g. `Mount Wild Horse`) |
| p | u8 | 0 | 160 |
| p+1 | u32 | `index` | 0..486, 160 unique values (sparse). Role UNVERIFIED |
| p+5 | u8 | 0 | 160 |
| p+6 | u64 | EntityGroup id | Equals the marker's end-23 (160/160) |
| p+14 | u8 | 0 | 160 |
| p+15 | u64 | MapMarker id (back-ref) | 159/160. It is 0 in `JAP_EP_Hakuba_KurobeLake`, although that marker does point to this definition. |

(p = 0x21 + 2·nchars + 2·(nchars>0). For 56-B records this means index @0x22, group @0x27 = end-17, marker @0x30
= end-8, as in G.3.)

There is **no** sport, unlock or discovery field. All 160 definitions are referenced by a DZ/EP marker. Their
markers are the ones whose name tokens include `Locked`, `Unlocked`, `BaseJump`, `GrindPark`, `Wingsuit`, or no
token at all (§2.9).

### §2.4 `0xadeae73c` XP-level unlock condition

59 records (53 × 62 B, 5 × 100 B, 1 × 162 B), all named `Type_XP_<track>_Level_<n>[_<DZ name>]`. Each record
ends right after the condition list (59/59, VERIFIED). Kaitai: `xp_unlock`.

| Off | Type | Field | Census |
|---|---|---|---|
| +0x00 | u64 | object id | |
| +0x08 | u32 | type `0xadeae73c` | |
| +0x0c | u8 | 1 | |
| +0x0d | loc_string | name. Text `UNLOCK AT LEVEL 26..30` in the 5 × 100 B records, otherwise empty | |
| p | u8 | 0 | 59 |
| p+1 | u32 | `index` | 609..667, consecutive in record order |
| p+5 | u32 | k = number of conditions | 1 (58), 6 (`Type_XP_GradeMax_Level_6`) |
| p+9 | k × 20 B | `{u64 sub id, u32 0xb0a79f0a, u32 level, u32 track}` | 64 conditions, class 64/64 |

`track` values come from the record names (the mapping is VERIFIED by name; game semantics are UNVERIFIED):
0 Explorer, 1 BoneCollector, 2 ExtremRider, 3 FreeRider, 4 FreeStyler, 5 Competitor, 6 Global.
`Type_XP_GradeMax_Level_6` lists tracks 1, 5, 0, 3, 4, 2 at level 6.

The 31 DZ/EP markers that reference this type all use track 6 (Global). Their levels are 1 (13 markers) and
4, 5, 7, 8, 10, 11, 12, 14, 15, 16, 18, 20, 21, 23, 24, 27, 29, 30 (one marker each). The other 28 records
are referenced by UnlockableManager `0x970fb15b` (all 59 are; §2.7). They gate other unlockables (gear, the
helicopter `Type_XP_Global Level_25_helico`, levels 42/76/99), not map markers (UNVERIFIED for anything
beyond the reference itself).

### §2.5 Drop-zone component (in the marker's EntityGroup)

Each marker's EntityGroup (`0x3f742d26`, region pack `Cell21844_DataBlock`, patch_02) holds exactly one
sub-object that contains the marker id. The id occurs once per group (193/193). That sub-object is the drop-zone
component. The component itself is anchored; the other components and child Entities of the group (props,
meshes, decals `STP_MAT_DZ_projection`, physics) are not decoded here. Kaitai: `dz_component` (input = bytes from
`c` to the end of the trailing string).

Locate it: `i` = offset of the marker id in the group; `s` = last `0x81a7045d` before `i`, minus 8 (start of
the string sub-object); `c = s − 16`. Equivalently `c = i − 38 − 2·n − 2·(n>0)`, where n is the string's nchars.
The byte at `c−1` is 0 (110) or 4 (83); it belongs to the preceding data.

| Off | Type | Field | Census (193) / meaning |
|---|---|---|---|
| c+0 | u64 | sub-object id | |
| c+8 | u32 | class | `0x32c7f7b9` 138: all 80 Alpes DZs, 12 Alaska DZs, 45 Japan DZs, plus `JAP_EP_Saporo_KojimaIsland`. `0xb96f89fc` 55: all other EPs, the 7 Alaska BaseJump DZs, and 3 Japan DZs whose text reads "Hakuba Exit Point 0n". |
| c+12 | u8 | `flag_a` | 1 (110) / 0 (83). Same split as the lead byte at c−1 (0 ⇔ 1). UNVERIFIED |
| c+13 | u8[3] | `01 00 00` | 193 |
| c+16 | loc_string | name | Same loc_id as the marker (193). In `JAP_DZ_Zao_Jizozao` the text contains a newline. |
| i−2 | u16 | `name_extra` | 0 (191), 1 (2: `ALA_DZ_BaseJump_Unlocked_01`, `JAP_DZ_Saporo_YoteiWest`). UNVERIFIED |
| i | u64 | MapMarker id (back-ref) | 193 |
| i+8 | f32 | `radius` (r0) | 3–70 m: balloons 70 (8); other EPs 5 (29), 3 (8), 20 (1); DZs 3–50 (mode 20). Reading: radius of the drop/landing area (UNVERIFIED; the discovery distance in game is much larger) |
| i+12 | f32 | r1 | 0.4 (146) or 0.0 (47, class `b96f89fc` without balloons) |
| i+16 | f32 | r2 | 10.0 (144), 0.1 (36), 0.5 (11), 15 (1), 20 (1) |
| i+20 | f32 | r3 | 0.1–35 |
| i+24 | u8 | `has_heading` | 1 in 39 (all 7 BaseJump, 7/8 Legendary, 25 others) |
| i+25 | f32 | yaw (rad) | e.g. −2.0944 = −120°, π/2. Yaw or pitch is non-zero in all 39 has_heading records, and also in 2 others (`ALA_EP_Denali_Balloon`, `ALP_DZ_Sotchi_Locked_01`). Role UNVERIFIED |
| i+29 | f32 | pitch (rad) | As yaw. UNVERIFIED |
| i+33 | u32 | `kind` | 13 (186), 11 (7 = `ALA_DZ_BaseJump_*`) |
| i+37 | u8 | `is_level_gated` | 1 ⇔ marker category 1 (193/193) |
| i+38 | u8 | `flag_b1` | 1 in 11: the 9 Alpes/Alaska markers with a level-1 XP gate, the Onboarding EP (no definition) and `Alps_EP_Cervin_Wingsuit_Unlocked` (level 12). The 4 Japan level-1 markers have 0. UNVERIFIED |
| i+39 | u8 | `is_balloon` | 1 ⇔ `*_Balloon` (8/8, 193/193) |
| i+40 | u32 | `tier` | 0/1/2 (94/79/20). Always 0 in Japan; 5/8 Legendary = 2. UNVERIFIED (difficulty?) |
| i+44 | u8 | `one` | 1 (192), 0 (`ALP_DZ_MBlanc_Legendary`) |
| i+45 | u32 | k10 | 10 (192), 22 (`ALP_DZ_MBlanc_Legendary`) |
| i+49 | u32 | k6 | 6 (193) |
| i+53 | u8 | 0 | 193 |
| i+54 | u64 | `weather_id` | `0xf7485e9f` lighting/weather preset (192 resolve, 1 is 0). 46 distinct (`ALP_NEW_PerfectDay_*` 33, `ALP_NEW_Sunset_*` 32, …) |
| i+62 | f32 | `hour` | −1..22 h (mode 12). Reading: the time of day set when the player drops here, with the preset (UNVERIFIED) |
| i+66 | 2 × 62 B | sound cues, class `0x7e42f87f` | Same shape as db-player-canopy.md §4. Event id u32 at cue+44 is non-zero in a few (e.g. `JAP_DZ_Zao_Zao` 0xe828bcbd) |
| i+190 | loc_string | trailing string | loc_id 0xffffffff, nchars 0 (193) |

### §2.6 `0xa1a8ea23` region manifest

There are four records in Game Bootstrap Settings: `Default` (84 B), `Alpes`, `Alaska`, `Japan`. Each is
`{u64 id, u32 type, u8 1, u8 0, u64 WorldRoot id}` followed by **eight** lists. A list is
`{u32 count, count × {u8 1, u8 0, u64 ref}}`. The lists consume each record exactly (4/4, VERIFIED
`region_manifest.py`). Kaitai: `region_manifest`.

| List | Target type | Alpes | Alaska | Japan |
|---|---|---:|---:|---:|
| 0 | `0x5502fe93` DropZoneDefinition | 86 | 19 | 55 |
| 1 | `0x6557bafe` PointOfInterest | 149 | 37 | 86 |
| 2 | `0xc69187e9` ChallengeDropZoneLink | 113 (1 null entry) | 29 | 36 |
| 3 | `0x618ebb44` challenge-beaten / trial condition | 22 | 12 | 10 |
| 4 | `0xa8a572ba` challenge medals | 450 | 204 | 104 |
| 5 | `0x3bfdfb80` quest roots | 38 | 1 | 21 |
| 6 | `0x6b3367e4` **DZ/EP markers** | 110 | 24 | 59 |
| 7 | `0x6b3367e4` POI markers | 149 | 37 | 86 |

`Default` has empty lists except list 4 (3 medals). This is the cheapest per-region enumeration of markers. It
agrees with the WorldRoot-at-end-32 rule (110 + 24 + 59 = 193). The DZ definition lists sum to 160.

### §2.7 Other records that point at DZ/EP markers

A reverse search covered the effective Game Bootstrap Settings plus STEEP_QUESTS, for any u64 equal to a DZ/EP
marker, definition or group id (`dz_backrefs.py`, VERIFIED). Hits by referencing type:
`6b3367e4` (markers → groups 193, → DZ defs 160, → XP defs 31), `a1a8ea23` manifest (markers 193, defs 160),
`5502fe93` (groups 160, markers 159), `ad502db7` (markers 36), `173e2fa7` Quest (markers 35), `970fb15b`
(XP defs 31, markers 8), `f547c674` (markers 7), `bc11bd33` (markers 3: `STEEP_ALP_ONBOARDING_Seq01` …), and
`8b742be5` (1 DZ def: challenge `A19_P_BUTTERFLY`). No sport-profile, gear or activity type references them.

- `0x970fb15b` **UnlockableManager** (1 record, 3,313 B). It refs the 4 manifests, all 59 `0xadeae73c`, item and DLC
  unlock conditions, and the tutorial hint id `LINEAR_UNLOCK_A_DROPZONE` (`0xd793503b`). After the hint id come
  `u32 272`, `u32 193` (the POI and DZ/EP marker counts), `u32 8` and 8 × `{u8 0, u64 marker}`, which end the
  record. The 8 markers are `Alps_EP_Aravis_Wingsuit_Unlocked`, `ALP_DZ_Aravis_Locked_09`,
  `ALP_DZ_Tyrol_Unlocked`, `Alps_EP_Tyrol_Wingsuit_Unlocked`, `ALP_DZ_Suisse_Unlocked`,
  `Alps_EP_MBlanc_Wingsuit_Unlocked`, `Alps_EP_Aiguilles_Wingsuit_Unlocked` and `ALP_DZ_Aiguilles_Unlocked`. Reading:
  the DZs offered by the "unlock a drop zone" tutorial step (UNVERIFIED).
- `0xad502db7` **LegendaryDropZoneFirstSpawnMemorableMoment**: 18 records. The u64 at end-8 is exactly the 18
  category-1 markers.
- `0xf547c674` **BaseJumpUniqueMemorableMoment**: 7 records. The u64 at end-8 is the 7 `ALA_DZ_BaseJump_*` markers.

### §2.8 Sports (evidence for "none")

- The marker head and tail (§2.2), the DropZoneDefinition (§2.3), the XP record (§2.4) and the component (§2.5)
  are parsed with no unexplained bytes, except the few named flags/floats marked UNVERIFIED. None of them takes
  values 1..8 that line up with the sport enum of `sport_profile.ksy` (1 snowboard … 8 base_jump). The only
  small-integer discriminator is `kind` 13/11. It splits BaseJump from everything else, so it is not a sport set
  (a wingsuit EP and a ski DZ share 13).
- No reference from any DZ/EP record reaches `0xa97216a6` sport profiles or gear (§2.7).
- Name tokens: `Wingsuit` 23, all of them Alpes EPs. The 30 Alpes EPs are 23 `Wingsuit` + 7 `Balloon`; the
  onboarding EP `Alps_EP_Artavis_Wingsuit_Onboarding` is one of the 23. `BaseJump` 7 (Alaska DZs). None in
  Japan. 30/193 = 15.5%. VERIFIED (`dz_oracle.csv`: Alpes exit_point rows 30, `Wingsuit` 23, `Balloon` 7,
  `Onboarding` 1; `Wingsuit` rows are all `STP_Alpes,exit_point`).
- Behaviour (UNVERIFIED, general game knowledge): in Steep every sport can be chosen at any drop zone. EPs and
  wingsuit/base-jump spots are launch points, not sport locks.

### §2.9 Unlock / discovery (what the data supports)

| State by data | Rule | Alpes | Alaska | Japan | Total |
|---|---|---:|---:|---:|---:|
| Level-gated ("Legendary", category 1) | def `0xadeae73c`, Global level ≥ 2 | 15 (7 DZ, 8 EP) | 3 (2 DZ, 1 EP) | 0 | 18 |
| Level-1 gate | def `0xadeae73c`, Global level 1 | 8 (6 DZ, 2 EP) | 1 DZ | 4 DZ | 13 |
| No condition in data | def `0x5502fe93` or none | 87 (67 DZ, 20 EP) | 20 (16 DZ, 4 EP) | 55 (44 DZ, 11 EP) | 162 |

Name tokens against data:
- `Legendary` (8) and `Balloon` (8): all 16 are level-gated (category 1). Two more category-1 markers have neither token:
  `ALA_DZ_KahiltnaQueen` (level 27) and `Alps_EP_Cervin_Wingsuit_Unlocked` (level 12).
- `Locked` (66 DZ + 15 wingsuit EP, all Alpes): 76 have a DZ definition; 5 have a level-1 gate
  (`ALP_DZ_Sotchi_Locked_04`, `_Aiguilles_Locked_05`, `_MBlanc_Locked_01`, `_Aravis_Locked_10`,
  `Alps_EP_Suisse_Wingsuit_Locked_02`).
- `Unlocked` (23): 17 have a DZ definition (6 DZ, 5 wingsuit EP, 6 BaseJump), 1 has none (`ALA_DZ_BaseJump_Unlocked_01`),
  4 have a level-1 gate and 1 is level-gated (`Alps_EP_Cervin_Wingsuit_Unlocked`, level 12).
- So the tokens are designer labels. No byte in marker, definition or component separates `Locked` from
  `Unlocked` (§2.13 census, field-by-field). **Discovery radius: not found.** The candidate `radius` field (3–70 m)
  is far smaller than in-game discovery distances, so it is read as the drop area (UNVERIFIED). Discovery state lives in the save.
  `marker_index` (dense 0..192) is the natural bit index for it (UNVERIFIED).

### §2.10 Counts per region (VERIFIED, `dz_census.py`)

| Region | DZ | EP | Legendary DZ | Balloon EP | other cat-1 | `Locked` tok | `Unlocked` tok | `Wingsuit` tok | `BaseJump` tok | `GrindPark` tok | XP lvl-1 | Quest ref |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Alpes | 80 | 30 | 7 | 7 | 1 (Cervin wingsuit EP) | 81 | 14 | 23 | 0 | 0 | 8 | 30 |
| Alaska | 19 | 5 | 1 | 1 | 1 (KahiltnaQueen) | 0 | 7 | 0 | 7 | 0 | 1 | 1 |
| Japan | 48 | 11 | 0 | 0 | 0 | 0 | 2 | 0 | 0 | 5 | 4 | 4 |
| **Total** | **147** | **46** | **8** | **8** | **2** | 81 | 23 | 23 | 7 | 5 | 13 | 35 |

These match the P2-09 oracle (`gameplay_markers.csv`: 147 drop_zone, 46 exit_point). Sports: none in data (§2.8).

### §2.11 Oracle CSV

`$STEEP_DATA/shared/map-lab/dz_oracle.csv` has 193 rows (the file has 195 lines because one quoted
`comp_text` contains a newline), sorted by region, kind and name. Regenerate it (≈1 s; byte-identical on re-run,
VERIFIED with `cmp`):

```sh
source tools/env.sh
cd tools/lab/G-05/dz && $STEEP_DATA/P0-05/venv/bin/python dz_extract.py > $STEEP_DATA/G-05/dz/dz_extract.txt
```

Columns. Raw values; ids are hex. The row's `kind` and x, y, z come from the P2-09 oracle
`$STEEP_DATA/shared/gameplay-markers/gameplay_markers.csv`, joined by marker id.

- Marker: `marker_id, region, kind, name, x, y, z, category, name_tokens, sports` (always empty),
  `marker_index, marker_loc_id, marker_text, handle, tail_u32_41, end2, end1, world_root, group_id, quest_ref, quest_name`.
- Definition: `def_type` (`5502fe93`/`adeae73c`/empty), `def_id, def_name, def_size`. For a DZ definition: `def_index, def_loc_id, def_text`.
  For an XP definition: `unlock_xp_level, unlock_xp_track` (`;`-joined if several).
- Component: `comp_class, comp_lead, comp_A, comp_loc_id, comp_text, comp_u16, r0` (= radius), `r1, r2, r3,
  heading_flag, yaw, pitch, kind_u32, b0` (= is_level_gated), `b1` (= flag_b1), `b2` (= is_balloon), `s_u32` (= tier),
  `one, k10, k6, weather_id, weather_name, hour, cue_events`.

### §2.12 Importer algorithm

Input: the effective Game Bootstrap Settings (entry 0x800, highest patch layer) and, per region, the effective
`Cell21844_DataBlock` (entry 0x1f48e86884) of `DataPC_STP_<Map>`.

1. **Regions.** For each `0xa1a8ea23` record with a non-zero WorldRoot id at +0x0e, parse the 8 lists (§2.6).
   List 6 gives the region's DZ/EP marker ids. Alternatively, take every `0x6b3367e4` whose name contains
   `_DZ_`/`_EP_` and read the region from the WorldRoot at end-32 (G.2).
2. **Marker** (`d` = record data, `L` = len):
   - `marker_index = u32 @0x0f`.
   - Name: loc_string @0x13 (`loc_id` @0x1f, `n` @0x23, text @0x27). Then `p = 0x27 + 2n + (n ? 2 : 0)`.
   - Require `d[p] == 3`; `k = u32 @p+1` (0 or 1); `def = u64 @p+6` if k = 1; `handle = u64 @p+5+9k`.
   - Check `u32 @L−45 == 0x72873a8e` and `p+5+9k+8 == L−45`.
   - `kind_flag = u32 @L−41` (3 = BaseJump), `world_root = u64 @L−32`, `group = u64 @L−23`,
     `quest = u64 @L−14` (0 = none), `category = u32 @L−6`, `end1 = d[L−1]`.
3. **Definition** (look `def` up in the same Game Bootstrap Settings):
   - type `0x5502fe93`: loc_string @0x0d → q; `index = u32 @q+1`, `group' = u64 @q+6` (assert == group),
     `marker' = u64 @q+15` (equals the marker, or 0); end = q+23 = len.
   - type `0xadeae73c`: loc_string @0x0d → q; `index = u32 @q+1`; `k = u32 @q+5`; k × 20 B at q+9:
     `level = u32 @+12`, `track = u32 @+16` (6 = Global).
   - none: no unlock data.
   - Unlock rule for Summit: `level_gate = (def is 0xadeae73c) ? max(level) : 0`. Level ≥ 2 ⇔ category 1
     ("Legendary"). Level 0/1 = discoverable / open per the save (UNVERIFIED game rule).
4. **Position and heading.** EntityGroup `group` in the region's Cell21844_DataBlock: 4×4 f32 matrix at +0x0e,
   translation at +0x3e (G.3).
5. **Drop-zone component.** In the group data, find the unique u64 == marker id at offset `i`. Then
   `c = (last occurrence of u32 0x81a7045d before i) − 8 − 16`, and assert `u32 @c+8 ∈ {0x32c7f7b9, 0xb96f89fc}`.
   Read at `i+8`: `radius f32`, r1, r2, r3, `has_heading u8 @i+24`, `yaw f32 @i+25`, `pitch f32 @i+29`,
   `kind u32 @i+33`, `is_level_gated u8 @i+37`, `flag_b1 @i+38`, `is_balloon @i+39`, `tier u32 @i+40`,
   `weather u64 @i+54` (`0xf7485e9f` preset), `hour f32 @i+62`. Two 62-B sound cues follow at i+66 and a
   loc_string at i+190.
6. **Sports.** None in data. Allow all sports. Optionally tag `kind == 11` as base-jump and names with
   `Wingsuit` as wingsuit launch points (name-derived, UNVERIFIED).

### §2.13 Evidence

All commands run from the repo root after `source tools/env.sh`, on 2026-10-11.

**E1, extractor and layout checks.** `cd tools/lab/G-05/dz && $STEEP_DATA/P0-05/venv/bin/python dz_extract.py`
(real ≈1.5 s; output `$STEEP_DATA/G-05/dz/dz_extract.txt`). Every check is true, except the one known
KurobeLake back-ref:

```
rows 193 -> <HOME>/SteepLab/shared/map-lab/dz_oracle.csv
   ('comp loc_id == marker loc_id', True) 193
   ('component class in DZ_CLASSES', True) 193
   ('component marker right after u16', True) 193
   ('component: marker id found once in group', True) 193
   ('dzdef ends at p+23', True) 160
   ('dzdef group == marker group', True) 160
   ('dzdef marker == marker', False) 1
   ('dzdef marker == marker', True) 159
   ('dzdef size == 56 + 2*n + 2*(n>0)', True) 160
   ('marker handle then tail (q+8 == len-45)', True) 193
   ('marker u8 3 after str', True) 193
   ('quest_ref resolves to 173e2fa7', True) 35
   ('sound cue class 0x7e42f87f', True) 386
   ('sound cue field hashes a2622cf6/83ec6c6d', True) 386
   ('tail anchor', True) 193
   ('trailing locstr loc 0xffffffff, n 0', True) 193
   ('weather resolves to f7485e9f', True) 192
   ('xp cond class 0xb0a79f0a', True) 64
   ('xp ends after conds', True) 59
```

(Excerpt. The other checks in the file, such as `marker hdr 01 01 00`, `dzdef u8 0 before group` and
`component u8 0 before weather`, are all `True` for every unit.)
`cmp` of two consecutive runs of the CSV: `identical`.

**E2, field census.** `$STEEP_DATA/P0-05/venv/bin/python tools/lab/G-05/dz/dz_census.py`
(output `$STEEP_DATA/G-05/dz/dz_census.txt`):

```
kind x region [(('drop_zone','STP_Alaska'),19), (('drop_zone','STP_Alpes'),80), (('drop_zone','STP_Japan'),48),
               (('exit_point','STP_Alaska'),5), (('exit_point','STP_Alpes'),30), (('exit_point','STP_Japan'),11)]
== kind_u32 {'11': 7, '13': 186}      ('11','basejump') 7
== def_type {'': 2, '5502fe93': 160, 'adeae73c': 31}
tail_u32_41==3 <=> kind_u32==11: 193 / 193
b2==1 <=> 'balloon' token: 193 / 193
b0==1 <=> category==1: 193 / 193
category==1 <=> xp level>=2: 193 / 193
handles unique: 193 / 193
marker_index dense 0..N-1: True
sport-ish name token: 30 / 193 {'basejump': 7, 'wingsuit': 23}
STP_Alpes  unlock data {('drop_zone','xp_gated'):7, ('drop_zone','no_condition'):67, ('drop_zone','xp_level1'):6,
                        ('exit_point','xp_gated'):8, ('exit_point','no_condition'):20, ('exit_point','xp_level1'):2}
STP_Alaska unlock data {('drop_zone','no_condition'):16, ('drop_zone','xp_gated'):2, ('drop_zone','xp_level1'):1,
                        ('exit_point','xp_gated'):1, ('exit_point','no_condition'):4}
STP_Japan  unlock data {('drop_zone','no_condition'):44, ('drop_zone','xp_level1'):4, ('exit_point','no_condition'):11}
```

The same file holds the per-field × name-token tables behind §2.5 and §2.9 (e.g. `s_u32`, `b1`, `end1`, `comp_A`).
They show that no field separates `Locked` from `Unlocked`.

**E3, Kaitai.** `PY=$(git rev-parse --path-format=absolute --git-common-dir)/../tools/.venv/bin/python;
$PY tools/lab/G-05/dz/ksy_check.py > $STEEP_DATA/G-05/dz/ksy_check.txt` (0.8 s, exit 0). It compiles
`drop-zone.ksy` and parses every unit, comparing it with the lab parsers:

```
('component', 'ok') 193
('dzdef', 'ok') 160
('manifest', 'ok') 4
('xp', 'ok') 59
```

There are no MISMATCH or ERROR lines. `tools/sv fmt-lab ksy-run --instances docs/specs/world/drop-zone.ksy
$STEEP_DATA/G-05/dz/ksy/samples/<s>.bin` exits 0 for all 13 samples: `comp_32c7f7b9`, `comp_32c7f7b9_text`,
`comp_b96f89fc`, `comp_b96f89fc_text`, `dzdef_56`, `dzdef_text`, `manifest_{Default,Alpes,Alaska,Japan}`,
`xp_62`, `xp_100`, `xp_162`. Example `--tree` on `xp_62`: `index: 609`, `level: 2`, `track: "global_level"`.

**E4, region manifests.** `$STEEP_DATA/P0-05/venv/bin/python tools/lab/G-05/dz/region_manifest.py`
(output `region_manifest.txt`), e.g.:

```
== Alaska 3684 ... u64@0x0e 0x10af88fa9e4 STP_Alaska
   list  0 @0x0016 n   19 bad 0 types {'5502fe93': 19} e.g. ALA_DZ_Wildhorse
   list  6 @0x0bfa n   24 bad 0 types {'6b3367e4': 24} e.g. ALA_EP_Denali_Balloon
   end 0xe64 of 0xe64
```

**E5, back-references.** `$STEEP_DATA/P0-05/venv/bin/python tools/lab/G-05/dz/dz_backrefs.py`
(`dz_backrefs.txt`). The full list is in §2.7.
`$STEEP_DATA/P0-05/venv/bin/python tools/lab/G-05/dz/unlock_refs.py` (`unlock_refs.txt`):

```
UnlockableManager size 3313 LINEAR_UNLOCK_A_DROPZONE @0xc95 u32 272 u32 193 count 8 tags {0} ends at record end True
LegendaryDZFirstSpawnMemorableMoment ad502db7 n 18 end-8 marker categories {1: 18}
BaseJumpUniqueMemorableMoment f547c674 n 7 end-8 marker categories {0: 7}
```

**E6, handle is not a record id.** An ad-hoc check during the census looked the marker `handle` u64 values up
in `idindex.pkl` (375,442 ids) and found none. Ranges around them (e.g. 0x15ebb35fe00..+0x200) were empty.
A byte search over all cached pickles found the value only in the marker itself (in DataPC, patch_01 and
patch_02). VERIFIED as run, but the ad-hoc command was not saved as a script; `dz_census.py` re-checks
uniqueness only.

### §2.14 Open

- Meaning of `tier` (0/1/2, all 0 in Japan), `flag_a`, `flag_b1`, `end1`, r1–r3, `marker.handle`, and the
  DropZoneDefinition / XP `index` fields.
- Where the game keeps "discovered" state and how far away discovery triggers: not in these records. It is presumably the
  save (Phase saves spec) plus engine rules. Watching the game play is the way to measure it.
- Whether the `quest_ref` means "quest starts here" or "quest unlocks this DZ".
- The other components and child Entities of the DZ EntityGroups (decals, props) are not decoded.

## §3 Names, POIs and sub-regions

This section covers the display name of every map marker, the PointOfInterest and DropZoneDefinition
layouts, and the mountain sub-regions (Aravis, Mont Blanc, Hakuba, ...). It builds on
world-gameplay.md (Studio source: `../formats/world-gameplay.md`) G.1–G.3 (MapMarker `0x6b3367e4`) and
localization.md (Studio source: `../formats/localization.md`) (LocalizationPackage `0x6e3c9c6f`). Offsets follow the
world-gameplay.md conventions: they are into a record's object `data`, and `end-N` means `len(data) - N`.

Evidence tags: **VERIFIED** means a command was run on Steep data here and its output is quoted.
**UNVERIFIED** means an inference or a claim that was not re-run.

Lab scripts are in `tools/lab/G-05/poi/` (read-only):
- `forgelib.py`: a self-contained forge, record and LocString reader.
- `regioncells.py`: the CellData_Region census.
- `names.py`: all the censuses below, and it writes the oracle CSV.
- `locref_scan.py`: a scan for LocString references.

Scratch output goes to `$STEEP_DATA/G-05/poi/`. Regenerate from the repo root:

```sh
source tools/env.sh
cd tools/lab/G-05/poi
$STEEP_DATA/shared/lab-venv/bin/python regioncells.py > $STEEP_DATA/G-05/poi/regioncells.txt   # writes regioncells.pkl
$STEEP_DATA/shared/lab-venv/bin/python names.py      > $STEEP_DATA/G-05/poi/names.txt         # writes the oracle CSV
$STEEP_DATA/shared/lab-venv/bin/python locref_scan.py 6820-6826,19227-19231,13695,28270,10510-10512 \
    DataPC_patch_02 DataPC_extra_2 DataPC_extra DataPC_patch_01 > $STEEP_DATA/G-05/poi/locref_regions.txt
```

`names.py` needs these inputs:
- the P2-09 pickles in `$STEEP_DATA/P2-09/cache/`: `DataPC_patch_02_800.pkl` and `DataPC_STP_<Map>_patch_02_1f48e86884.pkl`;
- the P2-10b string dumps in `$STEEP_DATA/extracted/loc/<pack>/LocalizationPackage_<Lang>.tsv` (made by `locdec.py all`);
- the P2-09 oracle `$STEEP_DATA/shared/gameplay-markers/gameplay_markers.csv`, which supplies the positions and map region;
- the P2-03 `$STEEP_DATA/P2-03/lab/records.tsv`.

Output: **`$STEEP_DATA/shared/map-lab/names_oracle.csv`**, 465 rows, md5 `c476c8e945c8c7f7ec0e47f1463df02c`
on 2026-10-11. It has these columns:
- identity: `marker_id, region, kind, name`;
- name: `loc_id, english, inline_nchars`;
- marker and definition fields: `category, def_type, def_id, def_name, def_index, def_loc_id`;
- sub-region: `subregion_token, subregion_cells_alps, x, y, z, subregion, subregion_source, subregion_label_id, subregion_label`.

### 3.1 Display names

**Result.** All 465 markers have a non-empty English display string: 147 of 147 drop zones, 46 of 46
exit points and 272 of 272 POIs. VERIFIED (`names.py`):

```
loc_id in English patch_02 {('drop_zone', True): 147, ('exit_point', True): 46, ('poi', True): 272}
English non-empty {('drop_zone', True): 147, ('exit_point', True): 46, ('poi', True): 272}
also in base / patch_01 English {(True, True): 465}
base text == patch_02 text {True: 465}
```

- The ids span 6827..20443 (`loc_id range 6827 20443`). This is inside the English text range of
  every pack (localization.md §5), so the base pack is enough. Patches change none of these 465 strings.
- There are 464 distinct strings. One string is shared by two markers (`shared by >1 marker: [(2, 'THE KANIKULA SAWMILL')]`).
- Every full text language resolves all 465 ids. The four partial Nordic packages resolve none of them.
  VERIFIED (patch_02 dumps):
  - 465: Brazil, Chinese (PRC), Dutch, English, French, German, Italian, Japanese, Korean, Polish,
    Russian, Simplified Chinese and Spanish (Spain);
  - 0: Danish, Finnish, Norwegian and Swedish.

  So Nordic players need a fallback language, probably English (UNVERIFIED, as in localization.md §5).
- None of the 465 strings contains markup, `[..]` glyph tags, braces or newlines. VERIFIED: the
  markup count is absent from the census.
- Case differs by kind:
  - Drop-zone and exit-point names are almost all upper case: 140 of 147 and 45 of 46.
  - POI names are mostly mixed case: 235 of 272 (for example `Emosson's Dam`, `Glacier de Talefre`).
  - VERIFIED census: `('upper','drop_zone'): 140, ('upper','exit_point'): 45, ('mixed','poi'): 235, ('upper','poi'): 37`.

  Whether the map UI upper-cases POI names is UNVERIFIED. Footage is needed to settle it.
- Examples, VERIFIED (patch_02 English):
  - `ALP_DZ_Aravis_Unlocked` → `TÊTE DU DANAY BASE CAMP`
  - `Alps_EP_Sotchi_Wingsuit_Unlocked` → `THE RAZOR EXIT POINT`
  - `ALA_DZ_Denali_Legendary` → `DENALI`
  - `POI_Alaska_RockCathedral_01` → `THE GRANITIC CROWN`
  - `ALA_DZ_BaseJump_Unlocked_07` → `B.A.S.E. Jump 7`

**Inline text is not the display name.** The marker's LocString at `+0x13` has `nchars > 0` in 329 of
465 markers:

```
marker nchars>0 by kind {('drop_zone', False): 89, ('drop_zone', True): 58, ('exit_point', False): 26,
                         ('exit_point', True): 20, ('poi', False): 21, ('poi', True): 251}
inline == English {(False, False): 136, (True, False): 227, (True, True): 102}
```

The inline text equals the English string in only 102 cases. The rest are designer work names that the
English table overrides. Examples, VERIFIED:

| Record | Inline text | English string |
|---|---|---|
| `Alps_EP_Cervin_Balloon` | `FETTE FRAU II` | `AOSTE AIR BALLOON` |
| `ALP_DZ_Sotchi_Locked_08` | `NEW DZ TO ADD IN OASIS` | `THE REMOTE PLACE` |
| `STP_ALP_POI_Aiguilles_UltraNatural_01` | `UltraNatural 1` | `Ultra Natural d'Emosson` |

So inline text is only a debug fallback. It must not be shown when the id resolves (UNVERIFIED as
engine behaviour, but it is the only reading that gives sensible names).

**Where else the same id appears.** All of these are VERIFIED (`names.py`):
- **PointOfInterest `0x6557bafe` / DropZoneDefinition `0x5502fe93`** (§3.2) carry their own LocString.
  Its id equals the marker's id in 422 of 430 referenced definitions:
  `def loc_id == marker loc_id {('drop_zone', True): 122, ('exit_point', True): 30, ('exit_point', False): 4, ('drop_zone', False): 4, ('poi', True): 270}`.
  - The 8 misses all have definition `loc_id = 0xffffffff` (no id). They are the Alps
    `*_Unlocked` base camps and wingsuit exit points, and `ALP_DZ_Aravis_Locked_09`.
  - Over all records, 272 of 272 POI definitions and 152 of 160 DZ definitions have an id that is in the
    English table. The other 8 are the `0xffffffff` ones.
- **POI Entity** (map pack, L7 cell): the component sub-object at entity `+83` (class `0xcf5a9894`, §3.2)
  holds a LocString with the same id in 272 of 272 cases. It also holds the marker id (272 of 272).
- **DZ/EP EntityGroup** (map pack): it contains `{0x81a7045d, loc_id}` with the marker's id in 193 of 193
  cases (`EG has LocString w/ marker id: True 193`). Its exact offset was not decoded.

The marker is the one source that is complete (465 of 465) and lives in DataPC. Use it.

**Fallback rule** (for a converter; the game never needs it on this data):
1. Use the marker LocString id, looked up in the selected language.
2. If that fails, use the same id in English.
3. If that fails, use the definition record's LocString id when it is not `0xffffffff`.
4. If that fails, use the marker's inline text when `nchars > 0`.
5. Otherwise use the record name.

Steps 3–5 are never reached on Steep data (VERIFIED: 0 markers fail step 2).

#### Importer algorithm (marker → display string)

1. **Load the string table.** Take the newest `LocalizationPackage` record (type `0x6e3c9c6f`) for the
   language, with `kind = 0` (text) and `language` from localization.md §2. "Newest" means
   `DataPC_patch_02`, else `DataPC_patch_01`, else `DataPC`. Decode it per localization.md §3–§4 into a
   map `u32 id → UTF-16 string`. Do the same for English (language 1) as the fallback.
2. **Load the markers.** Take the effective `Game Bootstrap Settings` entry: entry id `0x800`, from the
   highest DataPC layer that has it. Take every record of type `0x6b3367e4`. There are 465.
3. **Parse the name.** For each marker `data`:
   - Check that `u32 @0x1b == 0x81a7045d`.
   - Read `loc_id = u32 @0x1f` and `nchars = u32 @0x23`.
   - The inline text is `UTF-16LE[nchars] @0x27`, followed by `u16 0` only when `nchars > 0`.
4. **Resolve.** `name = table[loc_id]`, else `english[loc_id]`, else the fallback rule above.
   Keep the text verbatim; localization.md §5 markup rules apply, although none occurs here.
5. Marker kind, map region and position come from world-gameplay.md G.2–G.3. The sub-region comes
   from §3.3.

### 3.2 PointOfInterest `0x6557bafe` and DropZoneDefinition `0x5502fe93`

The two definition types share one layout. Every field is fixed except the string:

| Off | Type | Field | Check (VERIFIED, `names.py` over all referenced definitions) |
|---|---|---|---|
| +0x0c | u8 | 1 | `def layout end_ok/hdr/pads {(True, 1, (0, 0, 0)): 430}` |
| +0x0d | LocString | `{u64 sub_id, u32 0x81a7045d, u32 loc_id, u32 nchars, u16 text[nchars], u16 0 if nchars>0}` | 465/465 markers' class OK |
| p | u8 | 0 | 430 |
| p+1 | u32 | `index` | see below |
| p+5 | u8 | 0 | 430 |
| p+6 | u64 | world object: Entity (POI) or EntityGroup (DZ/EP) | `def wobj == marker end-23 {True: 430}` (= G.3 "end-17") |
| p+14 | u8 | 0 | 430 |
| p+15 | u64 | MapMarker id (back-reference) | `def marker backref {True: 426, False: 4}` |
| p+23 | — | end of record | `end_ok` 430/430 |

Over all records (not only the referenced ones), VERIFIED:

```
6557bafe 272 end_ok Counter({True: 272}) idx distinct 272 nchars>0 250 loc in en 272
5502fe93 160 end_ok Counter({True: 160}) idx distinct 160 nchars>0 55 loc in en 152
POI∩DZ idx 0 union 430 min 0 max 572
```

- **`index`.** Its values are unique over the union of the POI and DZ definitions: 430 distinct values in
  0..572, with no overlap between the two types. POIs use 86..572 and DZs use 0..486.
  - It does not equal the marker's `+0x0f` index (`def idx==marker+0x0f` True in only 4 of 430).
  - The marker's `+0x0f` takes 272 distinct values in 0..271 over 465 markers.
  - Meaning: a persistent discovery or save slot id. This is UNVERIFIED and needs a save-file diff.
- The 4 back-reference misses are `POI_Alaska_Glacier_01`, `JAP_EP_Hakuba_KurobeLake` (its definition's
  marker field is 0), `JAP_POI_TsurugiSnowBarrier` and `JAP_POI_SouunkyoRiver`. Their loc ids still agree
  with the marker.
- **No other strings.** There is no description, no region or sub-region name, and no second LocString
  in either type. The layout above accounts for every byte (`end_ok` 432 of 432).
- **No POI fields beyond these.** No discovery radius, POI category or type, icon or texture ref, or XP
  value exists in PointOfInterest (above), in MapMarker (G.3), or in the POI Entity component.
  VERIFIED census of that component:
  - The component sits at entity `+83`, with class `0xcf5a9894` at `+91`, in 272 of 272 POI Entities and
    0 of 193 DZ/EP EntityGroups.
  - After its LocString and marker id, the remaining 147 bytes are constant across all 272 POIs, apart
    from sub-object ids. They hold `u32 2` (matching the marker category 2) and a few flags.
  - A trailing sub-object of class `0x4aec3476` holds `f32[6] = (−1,−1,−1, 1,1,1)` in 270 of 272 POIs.
    The other 2 differ. This is a unit box, perhaps the discovery volume in entity space; UNVERIFIED.
  - The entity matrix bytes (+14..+56) vary in only 2–4 of the 272 POI Entities (VERIFIED byte census), so nearly all are identity rotation and unit scale.

  So discovery size is global or engine-side, not per-POI data (UNVERIFIED reading).
- **POI type.** The only per-POI classifier in the data is the record name. Tokens include `Village`,
  `Glacier`, `UltraNatural`, `Snowpark`, `BigAir`, `GoatHole` (33 in Japan), `Grind`, `Hamlet`, `Shrine`,
  `Gorge`, `Dam` and `Fumarol`. Using them as an icon category is UNVERIFIED.
- The marker `end-6` category (G.3) is 2 for every POI. For DZ/EP it is 0, or 1 for Legendary DZs and
  Balloon EPs. VERIFIED: `('poi','2'): 272, ('drop_zone','0'): 138, ('drop_zone','1'): 9, ('exit_point','0'): 37, ('exit_point','1'): 9`.
- **XP-gated markers.** 31 DZ/EP markers have a definition list that points at a `0xadeae73c` record
  instead of a DropZoneDefinition: 20 DZs and 11 EPs. These records are named `Type_XP_Global Level_NN`
  or `Type_XP_Global_Level_1_<marker>`. Examples: `ALP_DZ_Aravis_Legendary` → `Type_XP_Global Level_04`,
  `ALA_DZ_Denali_Legendary` → `Level_29`. VERIFIED (`names.py`, `def_name` column):
  `definition type by kind {('drop_zone','5502fe93'): 126, ('drop_zone','adeae73c'): 20, ('exit_point','adeae73c'): 11, ...}`.
  - A DropZoneDefinition still exists for these markers and points back to them via its `+p+15` field.
  - Reading the record as an unlock level is UNVERIFIED.
  - 4 markers have no definition reference (empty list): `ALA_DZ_BaseJump_Unlocked_01`,
    `Alps_EP_Artavis_Wingsuit_Onboarding`, and the nested `JAP_POI_Tateyama` and `JAP_POI_TsumagoVillage`.

### 3.3 Sub-regions (mountains)

**Data found.** VERIFIED (`regioncells.py`, `records.tsv`):
- **Alps.** Seven `CellData` records (type `0x067221b7`) are named `CellData_Region_0N_<Name>`:
  `01_Aiguilles`, `02_Mt_Blanc`, `03_Cervin`, `04_Tyrolles`, `05_Aravis`, `06_Suisse` and `07_Exotic`.
  - Each one is a shared object copied into many `CellNNNNN_DataBlock` entries of `DataPC_STP_Alpes*`:
    22–50 cells per region, at quadtree levels L0–L5.
  - In each such cell, a `0xc29a81b3` record names the region and references the CellData by id.
    Examples are `Aiguilles` and `Tyrol`; Aravis and Mont Blanc appear as `Area6 #6` and `Area7 #7`.
  - A matching `SoundAmbienceSet_Region_0N_*` (type `0x3cfd0bbb`) sits beside each one.
  - Census: `('DataPC_STP_Alpes', 'CellData_Region_02_Mt_Blanc') cells 50 levels {0: 2, 1: 3, 2: 18, 3: 21, 4: 4, 5: 2}`.
    Region cells at different levels overlap, so this is a cell-presence map, not a partition.
  - The exact per-texel region map is presumably in terrain cell data indexed by `#N`. It is not decoded
    here (open).
- **Alaska.** There is one `CellData_Region_Alaska`, in the L7 whole-map cell only. Alaska is a single
  region.
- **Japan.** There are no `CellData_Region_*` records. The terrain material bank in the L7 cell has
  `STP_TPS_JAP_Region_01..05` (type `0x2f45393e`). That suggests five painted regions, but their mapping
  to names is UNVERIFIED.
- **No record lists sub-regions with names or bounds.** No sub-region reference exists in MapMarker,
  PointOfInterest or DropZoneDefinition (§3.2: every byte is accounted for). The sub-region label strings
  (below) are not referenced by any LocString in `DataPC_patch_01/02`, `DataPC_extra` or `DataPC_extra_2`.
  VERIFIED: `locref_scan.py` finds only ProgressionManager refs to `ALPS`/`ALASKA` (10510/10511) and the
  Denali DZ (13695).
  - Limit: the scan reads the header and first data block of each entry.
  - The map UI probably binds the labels in UI code. UNVERIFIED.

**Binding rule.** A marker's sub-region is the token right after `POI`/`DZ`/`EP` in its record name.
`names.py` uses this table:

| Token(s) | Sub-region key | CellData region | Label string id (English) |
|---|---|---|---|
| `Aravis`, `Artavis` (one EP typo) | ALP_05_Aravis | `05_Aravis` | 6820 `ARAVIS` |
| `Tyrol` | ALP_04_Tyrol | `04_Tyrolles` | 6821 `TYROL` |
| `Suisse` | ALP_06_Suisse | `06_Suisse` | 6822 `SWITZERLAND` |
| `Sotchi` (DZ/EP), `WTF` (POI) | ALP_07_Exotic | `07_Exotic` | 6823 `THE CURSED MOUNTAINS` |
| `MBlanc` (DZ/EP), `MontBlanc` (POI) | ALP_02_MontBlanc | `02_Mt_Blanc` | 6824 `MONT BLANC` |
| `Cervin` (DZ/EP), `Aoste` (POI) | ALP_03_Cervin | `03_Cervin` | 6825 `AOSTE` |
| `Aiguilles` | ALP_01_Aiguilles | `01_Aiguilles` | 6826 `AIGUILLES` |
| `Hakuba` | JAP_Hakuba | — | 19230 `JAPAN - HAKUBA` (UNVERIFIED binding) |
| `Zao` | JAP_Zao | — | 19231 `JAPAN - ZAO` (UNVERIFIED) |
| `Daisetsuzan` | JAP_Daisetsuzan | — | 19228 `JAPAN - DAISETSUZAN` (UNVERIFIED) |
| `Sapporo`, `Saporo`, `SaporoYoteiEast` | JAP_Sapporo | — | 19227 `JAPAN - SAPPORO` (UNVERIFIED) |
| (Alaska, any) | ALA_Alaska | `CellData_Region_Alaska` | 10511 `ALASKA` (UNVERIFIED as a map label) |

Evidence for the Alps rows. All are VERIFIED (`names.py`):
- **Every Alps marker carries a token.** The token census of all 465 names gives 259 Alps markers, all
  with one of the seven tokens.
- **Tokens agree with the CellData_Region cells.** The test takes the marker's x, y from the P2-09 oracle
  and checks it against the region cells. Cell index `i` at level `L` has its square at
  `col = i % W, row = i // W` from −8192 (types.md, DataBlock). Result:
  `Alps token vs CellData_Region cells {('token in cells','finest==token'): 241, ('token in cells','finest!=token'): 14, ('token not in cells','finest!=token'): 4}`.
  So the token's region has a cell under the marker in 255 of 259 cases. The 4 exceptions are border
  DZ/EPs: `Alps_EP_Suisse_Wingsuit_Locked_01`, `ALP_DZ_Sotchi_Locked_07`, `ALP_DZ_Suisse_Locked_06` and
  `ALP_DZ_Tyrol_Locked_01`.
- **Token → label comes from data.** Each Alps sub-region has one `*_Balloon` exit point. Its English
  name starts with the label: `Alps balloon EP string starts with region label` True for all 7, for
  example `Alps_EP_Cervin_Balloon` → `AOSTE AIR BALLOON` and `Alps_EP_Sotchi_Balloon` →
  `THE CURSED AIR BALLOON`. Ids 6820–6826 are one consecutive block of exactly these seven labels.

Japan POIs have no sub-region token (86 of 86). `names.py` assigns them the token of the nearest Japan
DZ/EP in x, y (`subregion_source = nearest_dz_ep`). This is an inference: leave-one-out on the 59
tokenised Japan DZ/EPs gives `(54, 59)` correct. Treat these 86 assignments as UNVERIFIED.

**Counts per sub-region** (VERIFIED, `names.py`). For the 147 drop zones and 46 exit points of the Alps
and Japan the source is the name token. For POIs it is the name token in the Alps and the inferred
nearest-DZ/EP assignment in Japan. Every Alaska marker is in the single Alaska region by rule (not an
inference).

| Map | Sub-region | Drop zones | Exit points | POIs |
|---|---|---:|---:|---:|
| Alps | Aiguilles | 12 | 5 | 24 |
| Alps | Mont Blanc | 17 | 5 | 34 |
| Alps | Aoste (Cervin) | 10 | 4 | 25 |
| Alps | Tyrol | 10 | 3 | 15 |
| Alps | Aravis | 12 | 5 | 19 |
| Alps | Switzerland (Suisse) | 9 | 4 | 17 |
| Alps | The Cursed Mountains (Sotchi/WTF) | 10 | 4 | 15 |
| Japan | Hakuba | 17 | 2 | 37 (inferred) |
| Japan | Zao | 13 | 3 | 13 (inferred) |
| Japan | Daisetsuzan | 10 | 2 | 24 (inferred) |
| Japan | Sapporo | 8 | 4 | 12 (inferred) |
| Alaska | (single region) | 19 | 5 | 37 |
| **Total** | | **147** | **46** | **272** |

#### Importer algorithm (marker → sub-region)

1. Split the record name on `_`. Find the first part equal to `POI`, `DZ` or `EP`. The next part is the
   token. Look it up in the table above.
2. If there is no token: on Alaska use `ALA_Alaska`. On Japan, either use the nearest tokenised DZ/EP
   (inferred), or leave the sub-region empty until the Japan region raster is decoded.
3. The label is the string id from the table, resolved like §3.1. Only the Alps ids are bound by data.

### 3.4 Open

- The per-texel sub-region raster behind `c29a81b3` "`#N`" layers. It would replace name tokens with
  geometry and settle the 4 Alps border cases and the Japan POIs.
- How the map UI shows sub-region labels: the strings exist, but no data reference was found. Also the
  Japan and Alaska labels.
- The meaning of the definition `index` and of the marker `+0x0f` index (save slots?).
- POI discovery radius: no per-POI data. Look for global settings, for example
  `UIWorldPointOfInterestModule` `0xcef8d50f` or the `HUDLODSettings*` records `0xcd170019` in Game
  Bootstrap Settings. Not examined.
- Whether the UI upper-cases POI names.

## §4 Map UI assets and map-view data

Tags: **VERIFIED** = a command was run here on the owner's install (read-only)
or on caches derived from it, and its output is quoted. **UNVERIFIED** = inference. Lab scripts are in
`tools/lab/G-05/ui/` (Python, read-only, own self-contained forge reader `forgeread.py`). Their outputs are
in `$STEEP_DATA/G-05/ui/` and `$STEEP_DATA/shared/map-lab/`, outside git. Python = `$STEEP_DATA/P0-05/venv/bin/python`
or `$STEEP_DATA/shared/lab-venv/bin/python`. Ids are TextureMap (`0xa2b7e917`) record ids. "Effective copy" means
`*_patch_02` > `*_patch_01` > base.

### 4.1 Headline

- **No 2D map exists.** Steep's map is the *Mountain View*: the live 3D terrain seen from a camera up to about
  10–15 km away (camera node `Steep_MountainView_Root`, `ObservationModeManager`; see
  `../gameplay/camera.md` (Studio source: `../gameplay/camera.md`) §7.8 and §9). Icons are world-space UI (`UIWorld_*` / `HUD*`
  EntityGroups), drawn over the terrain. The only "map" images in the data are region-select pictures
  of a world map (`Steep_UI_MassifSwitch_*`, `STP-UI-Rectangle-*`). There is no per-region overview raster.
  - The name search (E1) finds no texture named like a region overview or minimap except
    `ACVI_Minimap_Tiled_FOG_Map`. That one is 32×32, and its only referrer is the material
    `Steep_UI_GEN_BGBlurred_DizzGauge` (E4). VERIFIED.
  - `WorldAtlas_STP_<Region>_0_DiffuseMap` (1024², BC1) belongs to `WorldAtlasMaterial_STP_<Region>_0` in the
    `STP_<Region>_Fakes` entry. The preview shows a facade/roof atlas for fake buildings, not a map (E5). VERIFIED.
  - `STP_ALA_Heightmap_FogMap` (2048², BC1, 2 copies) is referenced only by WorldRoot `STP_Alaska` (E4). It is
    a fog height texture and its preview is uniform white (E5). VERIFIED that it is not a map image.
  - For a top-down map, a Summit map stage must render one from the terrain caches
    (`cache/terrain/<Region>/colour.ktx2`, `ground.r16`). UNVERIFIED design recommendation.
- **The map-relevant texture set is 539 TextureMap records with 529 unique names, all 539 in the texture cache.**
  The file is `$STEEP_DATA/shared/map-lab/map_textures.tsv` (E6). VERIFIED.
- **Most icon textures are not referenced by record id from gameplay records.** The drop-zone illustrations
  (`SteepUI-DZ-*`), the DZ marker shapes (`STEEP_UI_DZ*`, `DropZoneDiamond*`) and the sport icons have exactly
  one id referrer: their own `<name>Desc` TextureMapDesc. No record references that MapDesc by id either (E4,
  E4b). VERIFIED. The runtime presumably binds them by name or by a string hash. UNVERIFIED. So the importer
  must select them **by name pattern** (§4.5).

### 4.2 Map-relevant textures: counts by category

Selection rule (E6): a TextureMap is in the set if it (a) is reached by the ref walk (E3) from a map-related seed
(module records and map/world UI EntityGroups, listed in `refwalk.py`), or (b) its name matches a category rule
in `map_textures.py`. Category = first matching name rule. If no name rule matches, the seed group decides.

| category | rows | reached from a seed | meaning |
|---|--:|--:|---|
| `dz_marker` | 30 | 15 | drop-zone marker and DZ panel shapes, lock icons, binocular-marked DZ |
| `dz_illustration` | 18 | 2 | per-DZ / legendary-DZ banner art, "unlock a drop zone" tutorial pictures |
| `poi` | 5 | 4 | POI marker, shared-content marker |
| `mountain_view` | 20 | 6 | MV region panel, zoom, slope/altitude pictos, travel icon, gamepad layout pages |
| `photo_map` | 24 | 2 | photo-mode / world-photo map icons (`STP_MV_Photomode_*`, filters) |
| `region_select` | 21 | 0 | massif switch world maps, region postcards, Japan ticket |
| `sport` | 44 | 4 | sport pictograms (ski/snow/paraglide/wingsuit/walk, presence, gamepad sport icons) |
| `challenge` | 306 | 141 | challenge markers/panels (content-selection shapes, medals, difficulty, trial images) |
| `ui_repository` | 64 | 64 | other images in `UITextureRepository` (news, notifications, wheel icons) |
| `generic` | 7 | 7 | white/circle/star fills shared by all UI |
| **total** | **539** | **245** | **529 unique names; 539/539 have a `.ktx2` in `cache/textures`** |

VERIFIED (E6 output). Previews (E5) confirm what the key shapes look like. Note that the cache `.ktx2` previews
appear vertically flipped (text upside down in `Alaska_Map`). Row order is P4-11's tex-orient matter. VERIFIED
appearance; orientation convention UNVERIFIED here.

### 4.3 Key textures

All are fmt 9 (BC7) unless noted. Cache path = `$STEEP_DATA/cache/textures/<name>_<id hex16>.ktx2` (present for every
row). Semantics come from the preview and the referrer. Tag: appearance and referrers VERIFIED (E4, E5);
meaning UNVERIFIED.

| id | name | forge (effective) | size | referrer / seed | role |
|---|---|---|---|---|---|
| `0x00000151016182c8` | `Steep-UI-MapMarker_Map` | DataPC_extra_2 | 256² | EntityGroup `HUDDropZone_V4` | DZ map pin (dark teardrop with a white dot) |
| `0x0000009f77b7fa56` | `marker_Map` | DataPC_extra | 512² | MapDesc only | outline pin (player flag / marked spot?) |
| `0x0000007f04e3f229` | `STEEP_UI_locked_Map` | DataPC_extra | 256² | `HUDDropZone_V4`, `HUDLegendaryDropZone_V4`, `HUD_Challenge`, `UIWORLD_WorldStateSharingIcon` | **locked** padlock |
| `0x0000017587f86774` | `STP-UI-Lock_Map` | DataPC_extra_2_patch_01 | 128² | MapDesc only | lock (newer style) |
| `0x000001510162c070` | `STP-Content_Selection_Challenge_LOCK_Map` | DataPC_extra_2 | 256² | `HUDDropZone_V4`, challenge groups | locked content state |
| `0x0000015101622ae7` | `STP-Content_Selection_Challenge_DONE_Map` | DataPC_extra_2 | 256² | `HUDLegendaryDropZone_V4`, `UIWorld_LegendaryDZ_CS` | done state |
| `0x0000015101622aed` | `STP-Content_Selection_Challenge_TODO_Map` | DataPC_extra_2 | 128² | name | to-do state |
| `0x0000015101622b05` | `STP-Content_Selection_Legendary_Marker_TODO_Map` | DataPC_extra_2 | 128² | name | **legendary DZ** marker (red diamond in black diamond) |
| `0x0000015db6d46338` | `Steep-UI-ContentSelection-Legendary_Map` | DataPC_extra_2 | 512² | `UITextureRepository` | legendary emblem |
| `0x000000991cb7a185` | `SteeUI-DZ-LegendaryHorn_Map` | DataPC_extra | 512² | MapDesc only | legendary-DZ horn art |
| `0x0000007f04e4cba6` / `0x000001140de35fc9` | `STEEP_UI_DropZoneDiamond_Map` / `…OUTLINE_Map` | DataPC_extra | 256² / 512² | MapDesc only | DZ diamond (filled / outline) |
| `0x000000991cb0a570`, `…a56a`, `0x0000007f04e3f23d` | `STEEP_UI_DZ-front/-back/-air_Map` (+ `_top-`, `_bottom-`, `_header`, `_footer`, `-back_pointy`, `-air-color`) | DataPC_extra | 256²–512² | `UIHUD_Panel_DZ` / MapDesc | DZ info-panel pieces |
| `0x000000991cb6eec4` / `…eeca` | `Steep-UI-Binocular-Binoculars_Map` / `-Losange_Map` | DataPC_extra | 256² / 128² | `HUDDropZoneMarker` | DZ spotted with binoculars |
| `0x000000991cb5013f` (+ 14) | `SteepUI-DZ-birdofprey_Map`, `-mountainscrapper`, `-snowmen`, `SteeUI-DZ-Tatzelwurm` (+`Ride`, `V2/V3`) | DataPC_extra | 512×256 (Tatzelwurm 1024×512) | MapDesc only | per-DZ "REWARDS +XP" banners |
| `0x0000016a1cb11140` | `STP-Content_Selection_POImarker_Map` | DataPC_extra_2 | 256² | MapDesc only | **POI** pin ("i") |
| `0x0000015db6d4633e` | `Steep-UI-ContentSelection-Shared_Map` | DataPC_extra_2 | 512² | `HUDPointOfInterest`, `UIWORLD_WorldStateSharingIconPOI`, `HUDDropZone_V4` | shared-content marker |
| `0x000000991cb02a70` | `Mountain_Map` | DataPC_extra | 256² | MapDesc only | mountain pictogram |
| `0x000000991cb12335` | `STEEP-UI-Zoom_Map` | DataPC_extra | 64² | `UIRegionModule` → `HUD_ZoneInfo` | MV zoom (magnifier) |
| `0x000000991cb1231d` / `…232f` | `STEEP-UI-MV-High_Map` / `-slope_Map` | DataPC_extra | 64² | `HUD_ZoneInfo`, `STEEP_WorldSwitchPage` | altitude flag / slope arrow |
| `0x000000991cb12329` | `STEEP-UI-MV-regionpanel_Map` | DataPC_extra | 256×342 | MapDesc only | region panel gradient |
| `0x00000173f94c3619` | `STP-MV_travel_icon_Map` | DataPC_extra_2 | 72² | `HUD_TrailFilters` | travel (globe and plane) |
| `0x0000018498aeee7f` | `STP_MV_Photomode_Icon_FriendsPhoto_Map` | DataPC_extra_2_patch_01 | 32² | `UIWorld_Photo_MapIcon`, `UIWorld_Photo_CS` | photo-map icon |
| `0x0000018498a57f52` | `STP_MV_Photomode_Picto_Camera_Map` | DataPC_extra_2_patch_01 | 64² | `UIWorld_Photo_MapIcon` | photo-map camera picto |
| `0x0000018498a7be2a` | `STP_MV_Photomode_Icon_WorldPhoto_Map` | DataPC_extra_2_patch_01 | 32² | name | world-photo icon |
| `0x000001293861761c` / `…7616` / `0x000001651d20c09b` | `Steep_UI_MassifSwitch_Alps/_Alaska/_Asia_Map` | DataPC / DataPC / DataPC_extra_2 | 512×256 | `ProgressionManager`, `STEEP_WorldSwitchPage` | world map with a region pin |
| `0x0000017edc3a431c` (+`…43cf`, `…43d5`) | `STP-UI-Rectangle-Alps/-Alaska/-Asia_Map` | DataPC_extra_2_patch_01 | 332×132 | `ProgressionManager` | small world-map strip |
| `0x0000007f04e31d5e`, `…1d68`, `0x000000991cb12249`, `…224f`, `…2290` | `STEEP_UI_icon_ski/_icon_snow/_Icon_paraglide/_Icon_wingsuit/_Icon_walk_Map` | DataPC_extra | 128–256 | MapDesc only | sport pictograms |
| `0x0000015db6d462fa` | `STP-Content_Selection_main_shape_Map` | DataPC_extra_2 | 512×1024 | legendary DZ, challenge groups | challenge marker body |

### 4.4 Map-view data records

| record (type) | where | decoded fields | tag |
|---|---|---|---|
| `Steep_MountainView_Root` (`0xd536e933` CameraModeNode), child `Steep_CloseUpView` | DataPC `Game Bootstrap Settings` (0x800) | FOV 55°, points at distance −10,000 m, height −500…−1,000 m, far 1,000 (`camera.md` (Studio source: `../gameplay/camera.md`) §9) | VERIFIED there |
| `ObservationModeManager_0X487B3A880B` (`0xde62b103`) | 0x800, 3 copies | links `ObservationCameraOwner`, `ZoneCollisionLoader`, `STP_ST_DropDirection`, `STP_FlagObservation`; 5 XCurves `XCurve_ObsMode*` (E8); `params_a` = 15000, 20, 15000, 375, 2000, 9200, 10, 1500, 60, 90, 4000, 4000, 200, 12.5, 2500, 100, 1000, 5, 5 (camera.md §7.8); FX `STP_FX_mountainHighlight_CursorLocked` (E7) | refs VERIFIED; meaning (distances m, FOV 60/90°) UNVERIFIED |
| `XCurve_ObsModeMaxCameraDistance` etc. (`0x0165ae97`) | DataPC_patch_02 | normalised keys: MaxCameraDistance (0, 0.1)→(0.491, 1.0); DefaultPitchBlend (0,0)→(0.5,0.338)→(1,0); SpeedDistance (0,0)→(1,1); CameraAcceleration (0,0.004)→(1,1); BlendAcceleration (0,1)→(4,5), y ∈ [1,10] (E8) | values VERIFIED; use UNVERIFIED |
| **`NewUILODManager_0X79338C70F7` (`0xb6f0d5b5`)** | 0x800, 3 identical copies | full layout below; distance thresholds per icon category (E9) | VERIFIED (parse ends at 1642/1642 in all 3 copies) |
| `HUDDropZoneModule` (`0x2d2ecb96`) | 0x800 | `+0x0c u8 1, u32 0, u8 1, u8 0`, then 4 × link10 → `HUDDropZone_V4`, `HUDLegendaryDropZone_V4`, `HUDLegendaryDropZone_V4`, `HUDAirBalloon`, then `01 00` (E7) | refs VERIFIED; slot meaning (normal / legendary / legendary-alt / balloon) UNVERIFIED |
| `HUDDropZoneFocusInfoModule` (`0xd2831e1c`) | 0x800 | link10 @+0x13 → `UIHUD_Panel_DZ` (E7) | VERIFIED |
| `HUDDropzoneAlwaysVisibleMarkerModule` (`0x35435f84`), `HUDDropzoneMarkerModule` (`0x98c78368`, base only) | 0x800 | link10 @+0x13 → `HUDDropZoneMarker`; 153 B with two nested `0x9f36b8f4`/`…f6` sub-objects (class `0x7e42f87f`), not split (E7) | refs VERIFIED |
| `HUDDropzoneOpenViewMarkerModule` (`0x66dfab8b`), `HUDDropzoneAutoMarkerModule` (`0x6713fbd6`, base only) | 0x800 | link10 @+0x13 → `UIWorld_Dropzone_autoMarked` (E7) | VERIFIED |
| `UIWorldPhotoMapIcon` (`0x4a9077c6`) | 0x800 | `+0x0c u8 1, u32 0, u8 1, u8 0, u8 1, u8 0`, link10 @+0x15 → `UIWorld_Photo_MapIcon` (E7). That group reaches `circle_Map`, `Flat_White_Map`, `STP_MV_Photomode_Icon_FriendsPhoto_Map`, `STP_MV_Photomode_Picto_Camera_Map`, `STP-Content_Selection_Tirette_Map`, `Steep-UI-ContentSelection-PointePercee_Map` (E3) | VERIFIED |
| `UIWorldPointOfInterestModule` (`0xcef8d50f`) | 0x800 | link10 @+0x15 → `HUDPointOfInterest` (E7) | VERIFIED |
| `UIRegionModule` (`0x123b9679`) | 0x800 | link10 @+0x13 → `HUD_ZoneInfo`; then `u32 0` @+0x1d and **u32 3,000,000 @+0x21**, then `u32 0` (E7) | bytes VERIFIED; 3,000,000 = display time in µs? UNVERIFIED |
| `UICapitalModule` (`0xa2106774`) | 0x800 | 23 B, no refs (E7) | VERIFIED |
| `TOD_*_MV` (`0xf0c85018` TimeOfDaySettings) | world packs | 23 distinct map-view time-of-day presets (`TOD_ALP_NEW_Morning_01_MV`, `TOD_JAP_Storm_MV`, ...) (E10) | count VERIFIED; contents per `time-of-day.md` (Studio source: `time-of-day.md`) |
| `DBInputContext_mountainView` / `_MountainViewMouseDrag` / `_MouseRotate` and `MountainView_*` actions (ZoomIn/Out, QuickZoom, BungyZoom, SetFlag, Spawn, FocusOnCursor, MoveCamera, RotateCamera) | 0x800 | see `../gameplay/input.md` (Studio source: `../gameplay/input.md`) | VERIFIED there |
| Region borders: `UI3D_RegionBorder` (MaterialTemplate), `STP_MAT_RegionBorderZebra` (Material), FX `STP_FX_UI_RegionHighlight`, `STP_FX_UI_regionPanel_Update` | DataPC | names only (E2) | names VERIFIED; use UNVERIFIED |

**NewUILODManager layout** (offsets in the record data, which starts with its own `u64 id, u32 type`). VERIFIED (E9):

```
+0x0c u8 1
+0x0d u32 n_default (7), then n_default × step
       u32 n_cat (8), then n_cat × category
category = { u8 0, u64 sub_id, u32 0x696a7d5d, u8 1, u32 len, char[len], u8 0, u32 n (7), n × step }
step     = { u8 0, u64 sub_id, u32 0xb6665cf7, u32 lod_index (0..6), f32 distance_m }   (21 B)
```

| category | LOD 0..6 distance thresholds (m) |
|---|---|
| (default) | 0, 1000, 2000, 3000, 4500, 6000, 8000 |
| `Challenges_Mountain` | 0, 10, 50, 750, 20000, 20000, 20000 |
| `DZ_Mountain` | 0, 20, 200, 3000, 20000, 20000, 20000 |
| `DZ_Ride_&_Stare` | 0, 20, 50, 3000, 3000, 13000, 14000 |
| `Challenges_Ride_&_stare` | 0, 10, 25, 750, 3000, 3000, 20000 |
| `LDZ_Stare` | 0, 20, 50, 3000, 3000, 3000, 3000 |
| `Challenges_Override` | 0, 10, 50, 20000, 20000, 20000, 20000 |
| `POI` | 0, 10, 50, 750, 3000, 20000, 20000 |
| `CheckpointScore` | 0, 20, 100, 300, 3001, 3002, 3003 |

Reading (UNVERIFIED): `*_Mountain` = Mountain View (map) mode, `*_Ride_&_Stare` = in-game. Drop zones and challenges
stay visible in the map up to 20 km of camera distance, which covers a whole 16 km region. The LOD index picks
the marker's detail level (EntityGroups named `LOD_FAR ICON_*`, `LOD NEAR …`).

### 4.5 Importer algorithm (map icon set)

Inputs: the forge record index (id, type, name, forge) and the textures stage's
`cache/textures/index.tsv` + `<sanitize(name)>_<id:016x>.ktx2`.

1. **Effective copy.** For every TextureMap id keep the copy from the highest patch layer (`_patch_02` > `_patch_01` > base).
   Several names exist under two or more ids (e.g. `SteepUI-DZ-birdofprey_Map` ×2,
   `STEEP_ALA_MV_BaseJumpOK_Map` ×2). Keep all ids. When a name lookup finds several ids, prefer the one with the
   highest forge layer, then the highest id.
   - Summit decision: `cache/textures/index.tsv` has no forge-layer column, so the Summit map stage picks the
     highest id among the same-name copies (and lists all ids).
2. **Map icon set by name.** Match the record name (case-sensitive, first rule wins) against the rules in
   `tools/lab/G-05/ui/map_textures.py` `RULES`. These are the categories of §4.2. The minimum the map stage needs:
   - DZ pin: `Steep-UI-MapMarker_Map`. DZ diamond: `STEEP_UI_DropZoneDiamond_Map` / `…OUTLINE_Map`.
   - locked: `STEEP_UI_locked_Map` (alt `STP-UI-Lock_Map`). done / to-do / locked states:
     `STP-Content_Selection_Challenge_{DONE,TODO,LOCK}_Map`.
   - legendary DZ: `STP-Content_Selection_Legendary_Marker_TODO_Map` + `Steep-UI-ContentSelection-Legendary_Map`.
   - POI: `STP-Content_Selection_POImarker_Map`. Photo: `STP_MV_Photomode_Icon_FriendsPhoto_Map`,
     `STP_MV_Photomode_Picto_Camera_Map`.
   - sports: `STEEP_UI_icon_ski_Map`, `STEEP_UI_icon_snow_Map`, `STEEP_UI_Icon_paraglide_Map`,
     `STEEP_UI_Icon_wingsuit_Map`, `STEEP_UI_Icon_walk_Map`.
   - zoom / slope / altitude: `STEEP-UI-Zoom_Map`, `STEEP-UI-MV-slope_Map`, `STEEP-UI-MV-High_Map`.
   - region select: `Steep_UI_MassifSwitch_{Alps,Alaska,Asia}_Map`.
3. **Cross-check by refs (optional).** Starting at the module records in `Game Bootstrap Settings`, follow link10
   targets: `HUDDropZoneModule` → `HUDDropZone_V4` / `HUDLegendaryDropZone_V4`, `UIWorldPointOfInterestModule` →
   `HUDPointOfInterest`, `UIWorldPhotoMapIcon` → `UIWorld_Photo_MapIcon`, `UIRegionModule` → `HUD_ZoneInfo`. Then
   follow EntityGroup → Entity → Material/MapDesc → TextureMap. The textures reached must be a subset of step 2's
   set. Treat a miss as a warning, not an error.
4. **Resolve pixels.** Look up the id in `cache/textures/index.tsv` (status `ok`). Path =
   `textures/<sanitize(name)>_<id:016x>.ktx2` (sanitize = keep `[A-Za-z0-9._-]`, map anything else to `_`). Apply the
   P4-11 row-order convention when drawing (the previews look vertically flipped).
5. **Visibility.** Show a DZ / challenge / POI icon in the map when the camera distance is below the
   `NewUILODManager` `*_Mountain` / `POI` thresholds (§4.4). Use LOD index 3 (DZ 3000 m, challenges 750 m) as the
   near-detail switch. UNVERIFIED reading.
6. **Output.** Per region, a list of `{category, name, id, ktx2, w, h}`. It holds no pixels, only references into
   the texture cache.
   - Summit decision: the list is the `icons` key of `cache/map/<Map>/map.json` (docs/summit-map.md), not a separate
     `icons.json`.

## §5 Region bounds

### 5.1 Sources

| source | Alpes | Alaska (`AlaskaTUX`) | Japan | tag |
|---|---|---|---|---|
| WorldRoot grid (`0xfbb63e47`, effective `_patch_02`): cell 128 m × 128 cells from origin | [−8192, 8192)² | [−8192, 8192)² | [−8192, 8192)² | VERIFIED (E11) |
| FloorHeightData `ground.json` `quadtree_square` (terrain authority) | [−8000, 8000]² | [−8000, 8000]² | [−8000, 8000]² | VERIFIED (E12) |
| `ground.json` valid fraction inside the square (strict) | 1.0 | 1.0 | 0.99424 (zero blocks = sea / no-data) | VERIFIED (E12) |
| `ground.json` margin 8000..8192 | "filler, not terrain; use the outskirt" | same | same | VERIFIED (E12) |
| Height range in the square (m) | 116.1 … 6308.8 | 310.9 … 6673.6 | 0.08 … 4916.6 | VERIFIED (E12) |
| Out-of-bounds wall meshes `STP_<R>_Outskirt_OOB_0[1-4]_LOD0` (entities at identity transform) | x,y ∈ [−8002.8, 8002.8]; walls at ±8000 ± 2.9 | [−8002.8, 8002.8]; ±8000 ± 2.8 | [−8002.5, 8002.5]; ±8000 ± 4.1 | VERIFIED (E13) |
| Outskirt (scenery) beyond the square: `outskirt.r16` | [−16384, 16384)², 32 m | same | same | VERIFIED (E12) |
| Marker bbox, all kinds (`gameplay_markers.csv`) | x [−7639.7, 7656.6], y [−7498.9, 7665.0], z [345.1, 6700.0], n=2190 | x [−7330.5, 7493.9], y [−7494.2, 7282.0], z [349.6, 6673.7], n=969 | x [−7339.7, 7729.3], y [−7443.2, 7648.6], z [514.5, 4787.2], n=851 | VERIFIED (E14) |
| Drop-zone bbox only | x [−7033.0, 6972.3], y [−6805.5, 6687.8] (n=80) | x [−3812.9, 3123.5], y [−4159.0, 2356.5] (n=19) | x [−7339.7, 7534.2], y [−6704.9, 7455.7] (n=48) | VERIFIED (E14) |
| Markers outside [−8000, 8000)² | 0 | 0 | 0 | VERIFIED (E14) |

Also present but not decoded: Japan entities `OOB_RSU_component`, `_Sky` and `_Frontier`, all at the origin.
They are probably a smaller out-of-bounds zone for the Olympic (RSU) venue (UNVERIFIED). There are also
`OOB_component` / `OOB_component_Sky` in Alpes and Alaska, and the ScriptGraph `STP_OutOfBounds`. VERIFIED (E13)
that they exist, at position (0,0,0). Their volume shape is not decoded. No record named like world limits,
map bounds or playable area exists beyond these (E2).

### 5.2 Recommendation (map stage "region bounds")

Use the **quadtree square** for all three regions. It equals the OOB wall line and lies inside the WorldRoot grid:

| region | playable / map bounds x, y (m) | z range for camera framing (m) | marker-content bbox (for the initial view) |
|---|---|---|---|
| Alpes | [−8000, 8000] × [−8000, 8000] | 116 … 6309 | x [−7640, 7657], y [−7499, 7665] |
| Alaska | [−8000, 8000] × [−8000, 8000] | 311 … 6674 | x [−7331, 7494], y [−7494, 7282]; DZs only within x [−3813, 3124], y [−4159, 2357] |
| Japan | [−8000, 8000] × [−8000, 8000] | 0 … 4917 | x [−7340, 7729], y [−7443, 7649] |

- Clamp the map camera target to the square. Render the outskirt ([−16384, 16384)²) only as context, greyed or
  fogged. The player cannot reach it: the OOB walls stand at ±8000. VERIFIED wall positions; the gameplay effect
  is UNVERIFIED.
- Do not use the WorldRoot ±8192 extent. Its 192 m margin is FloorHeightData filler (E12).
- Axes: world x east, y north, z up, metres. For the terrain rasters (`ground.r16`, FloorHeightData) row 0 =
  y −8000 (`../formats/world-coords.md` (Studio source: `../formats/world-coords.md`)). The Summit map overview PNG is north-up
  instead: row 0 = y +8000, column 0 = x −8000 (docs/summit-map.md).

### 5.3 Importer algorithm (region bounds)

1. Read `cache/terrain/<Region>/ground.json`. Bounds = `quadtree_square`. Height range = `height_min`/`height_max`.
   (Region dir names: `Alpes`, `AlaskaTUX`, `Japan`.)
2. Assert that the four `STP_*_Outskirt_OOB_0?_LOD0` mesh bboxes in `cache/meshes/index.tsv` lie within ±8000 ± 5 m
   in the wall axis. On mismatch, warn and keep the square.
3. Optionally compute the marker bbox from the world markers (`cache/world/<Region>/markers.json` or
   `gameplay_markers.csv`) to frame the initial map view. Pad it by 5 %. Clamp it to the square.

### Evidence (VERIFIED; run 2026-10-11, read-only)

- **E1** `cut -f2 $STEEP_DATA/G-05/ui/texmaps.tsv | grep -iE "dz|dropzone|worldatlas|mountain|minimap|compass|poi|region|…"`
  over the 16,254 unique TextureMap ids. Map-like hits: `ACVI_Minimap_Tiled_FOG_Map`, `Mountain_Map`, `Alaska_Map`,
  `WorldAtlas_STP_{Alaska,Alpes,Japan}_0_DiffuseMap`, `STP_ALA_Heightmap_FogMap`, `Steep_UI_MassifSwitch_*`,
  `STP-UI-Rectangle-*`, `STEEP-UI-MV-*`. No "compass" or "minimap" overview raster.
- **E2** `grep -iE "mountainview|worldmap|minimap|MapMode|MV_|DropZone|Massif|region|bounds|limit|OOB|PhotoMap|…"
  type_names.tsv` (186,417 type/name pairs from P2-03 `records.tsv`). Hits include `d536e933 Steep_MountainView_Root`,
  `de62b103 ObservationModeManager`, `bcfb3c7a UI3D_RegionBorder`, `85c817c3 STP_MAT_RegionBorderZebra`,
  `824a23ba STP_FX_UI_RegionHighlight`, `0984415e STP_{ALA,ALPS,JAP}_Outskirt_OOB_0[1-4]_00[12]`, `OOB_component*`,
  `e802b9da STP_OutOfBounds`, and 23 `f0c85018 TOD_*_MV`. No WorldLimit / PlayableArea / MapBounds names.
- **E3** `refwalk.py` (seeds = 19 module/manager types + EntityGroups matching `HUDDropZone|HUDLegendaryDropZone|
  HUDPointOfInterest|UIWorld_|UIWORLD_|UIHUD_|LOD_FAR ICON|…`, depth ≤ 5, UI container types only):
  `unique textures reached 246` (`refwalk.tsv` holds 245 distinct ids; the 1-id difference is unexplained); e.g. `seed HUDDropZoneModule_0X75CBAE4F80 textures 17`, `seed UIWorldPhotoMapIcon_0X17C4D42F689 textures 6`,
  `seed UIRegionModule_0X9F77B4EEC8 textures 7`, `seed UITextureRepository_0X14D94D5C61D textures 69`.
  Per-seed lists: `HUDDropZone_V4 → Flat_White_Map, STEEP_UI_AA_LR_Map, STEEP_UI_Air_Map, STEEP_UI_locked_Map,
  Steep-UI-ContentSelection-Shared_Map, Steep-UI-MapMarker_Map, STP-Content_Selection_Challenge_LOCK_Map`;
  `UIWorldPhotoMapIcon → circle_Map; Flat_White_Map; Steep-UI-ContentSelection-PointePercee_Map;
  STP_MV_Photomode_Icon_FriendsPhoto_Map; STP_MV_Photomode_Picto_Camera_Map; STP-Content_Selection_Tirette_Map`;
  `UIRegionModule → bgWhite_Map; Flat_White_Map; STEEP_UI_sliceSharp_Map; STEEP-UI-MV-High_Map; STEEP-UI-MV-slope_Map;
  STEEP-UI-Zoom_Map; UI_Animus_Preloader_Map`. Output `$STEEP_DATA/G-05/ui/refwalk.tsv`.
- **E4** `revscan.py`: all 278,074 non-pixel records of 65,695 entries, every forge; `targets 687 … targets with refs 684 of 687`.
  Sample rows: `SteepUI-DZ-birdofprey_Map 1 989dc6b2:1 SteepUI-DZ-birdofprey_MapDesc`;
  `STEEP_UI_DropZoneDiamond_Map 1 989dc6b2:1 …_MapDesc`; `Steep-UI-MapMarker_Map 2 989dc6b2:1,3f742d26:1 HUDDropZone_V4 | …`;
  `Steep_UI_MassifSwitch_Alaska_Map 3 c25c748b:1,989dc6b2:1,3f742d26:1 ProgressionManager_0X72F4844ABA | STEEP_ProgressionPage`;
  `STP_ALA_Heightmap_FogMap 1 fbb63e47:1 STP_Alaska`; `ACVI_Minimap_Tiled_FOG_Map 1 85c817c3:1 Steep_UI_GEN_BGBlurred_DizzGauge`;
  `STEEP_ALA_MV_01_Map 2 989dc6b2:1,04ce5d48:1 … XTP_Trial01`.
  **E4b** `revscan.py --mapdesc` (436 MapDesc wrappers): `targets with refs 44 of 436`. None of the `SteepUI-DZ-*`,
  `STEEP_UI_DZ*`, `DropZoneDiamond*`, `STEEP_UI_icon_*`, `POImarker` MapDescs is among the 44. Referenced ones
  include `Steep_UI_MassifSwitch_Al{aska,ps}_MapDesc 1 c25c748b:1 ProgressionManager…` and
  `STP_MV_Photomode_Icon_FriendsPhoto_MapDesc 1 3f742d26:1 UIWorld_Photo_CS`.
- **E5** `ktx2png.py` (KTX2 level 0 → DDS → Pillow BCn; previews in `$STEEP_DATA/G-05/ui/png*/`, never in git), contact
  sheets `sheet1.png`, `sheet2.png` inspected: `WorldAtlas_STP_Alpes_0_DiffuseMap` = building texture atlas on a
  magenta background; `STP_ALA_Heightmap_FogMap` = white; `Steep_UI_MassifSwitch_Alps_Map` and `STP-UI-Rectangle-Alps_Map` =
  world map with a red pin; `Steep-UI-MapMarker_Map` = dark pin; `STP-Content_Selection_POImarker_Map` = "i" pin;
  `STEEP_UI_locked_Map` = padlock; `Alaska_Map` = postcard with upside-down "Alaska" text.
- **E6** `map_textures.py`: `rows 539 unique names 529 in cache 539`; `challenge 306 (seed-reached 141)`, `dz_illustration 18 (2)`,
  `dz_marker 30 (15)`, `generic 7 (7)`, `mountain_view 20 (6)`, `photo_map 24 (2)`, `poi 5 (4)`, `region_select 21 (0)`,
  `sport 44 (4)`, `ui_repository 64 (64)`.
- **E7** `dumprec.py 2d2ecb96 123b9679 4a9077c6 cef8d50f a2106774 35435f84 66dfab8b d2831e1c 98c78368 6713fbd6 de62b103`, e.g.
  `HUDDropZoneModule … len 61: ref +0x15 -> HUDDropZone_V4; +0x1f -> HUDLegendaryDropZone_V4; +0x29 -> HUDLegendaryDropZone_V4; +0x33 -> HUDAirBalloon`;
  `UIRegionModule … len 41: 0010 00 01 00 01 00 96 6e 10 60 50 00 00 00 00 00 00 / 0020 00 c0 c6 2d 00 00 00 00 00; ref +0x15 -> HUD_ZoneInfo`;
  `UIWorldPhotoMapIcon … len 31: ref +0x17 -> UIWorld_Photo_MapIcon`; `ObservationModeManager … ref +0xf -> ObservationCameraOwner; +0x19 -> ZoneCollisionLoader;
  +0x23 -> STP_ST_DropDirection; +0x2d -> STP_FlagObservation; +0x84..+0xac -> XCurve_ObsMode* x5; +0x5a5 -> STP_FX_mountainHighlight_CursorLocked`.
- **E8** `obscurves.py`: `XCurve_ObsModeMaxCameraDistance (DataPC_patch_02) keys [(0.0, 0.1), (0.491, 1.0)]`,
  `…DefaultPitchBlendCurve keys [(0.0, 0.0), (0.5, 0.338), (1.0, 0.0)]`, `…BlendAcceleration keys [(0.0, 1.0), (4.0, 5.0)] y_range (1, 1.0, 10.0)`.
- **E9** `lodmgr.py`: for DataPC, patch_01 and patch_02 alike: `default [0.0, 1000.0, 2000.0, 3000.0, 4500.0, 6000.0, 8000.0]`,
  `DZ_Mountain [0.0, 20.0, 200.0, 3000.0, 20000.0, 20000.0, 20000.0]`, `POI [0.0, 10.0, 50.0, 750.0, 3000.0, 20000.0, 20000.0]`, …,
  `parsed to 1642 of 1642`.
- **E10** `awk -F'\t' '$7=="f0c85018" && $14 ~ /_MV$/' records.tsv | sort -u | wc -l` → `23`.
- **E11** `worldroot.py`: `STP_Alaska DataPC_STP_Alaska_patch_02 cell 128 origin (-8192, -8192) cells 128 -> extent [-8192, 8192)`;
  same for `STP_Alpes`, `STP_Japan`; `STP_WhiteRoom … origin (-512, -512) cells 8`.
- **E12** `ground.json` (cache/terrain, per region): `quadtree_square [-8000.0, -8000.0, 8000.0, 8000.0]`, `origin [-8192.0, -8192.0]`,
  `spacing 2.0`, Alpes `height_min 116.08 height_max 6308.78`, AlaskaTUX `310.86 / 6673.63`, Japan `0.075 / 4916.65`
  `strict_valid_fraction_inside 0.99424175`. The authority string: "ground.r16 inside quadtree_square [-8000, 8000)²; … The ground's 192 m margin
  (8000..8192) is filler". Outskirt `origin [-16384.0, -16384.0]`, 1024².
- **E13** `grep -i "Outskirt_OOB" cache/meshes/index.tsv`: e.g. `STP_ALPS_Outskirt_OOB_01_LOD0 … -8002.5117,7997.1387,714.37915  8002.5117,8002.756,4191.757`,
  `STP_ALA_Outskirt_OOB_01_LOD0 … -8002.756,-8001.2905,310.90756  -7997.871,8001.2905,2739.064`,
  `STP_JAP_Outskirt_OOB_01_LOD0 … -8000.0693,-8002.5117,475.52005  -8000.0693,8002.5117,4710.0176`. Their entities in
  `shared/world-entities/entities_*.csv` are at `0.000,0.000,0.000` (e.g. `110e9a30d3d,Entity,STP_ALPS_Outskirt_OOB_01_001,other,0.000,0.000,0.000`).
- **E14** `marker_bounds.py`: `bbox STP_Alpes n=2190 x[-7639.7, 7656.6] y[-7498.9, 7665.0] z[345.1, 6700.0]`,
  `bbox STP_Alaska n=969 x[-7330.5, 7493.9] y[-7494.2, 7282.0] z[349.6, 6673.7]`, `bbox STP_Japan n=851 x[-7339.7, 7729.3] y[-7443.2, 7648.6] z[514.5, 4787.2]`;
  `kind drop_zone n= 80 x[-7033.0, 6972.3] y[-6805.5, 6687.8]` (Alpes), `n= 19 x[-3812.9, 3123.5] y[-4159.0, 2356.5]` (Alaska),
  `n= 48 x[-7339.7, 7534.2] y[-6704.9, 7455.7]` (Japan); `outside [-8000,8000)^2: 0` for every region.

Scripts (`tools/lab/G-05/ui/`): `forgeread.py`, `refwalk.py`, `revscan.py`, `map_textures.py`, `dumprec.py`, `lodmgr.py`,
`obscurves.py`, `worldroot.py`, `marker_bounds.py`, `ktx2png.py`. To regenerate the TSV:
`refwalk.py && revscan.py && revscan.py --mapdesc && map_textures.py` (P0-05 venv python, about 15 min total).
