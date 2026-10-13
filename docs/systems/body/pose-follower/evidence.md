> Findings-only publication. Companion assets, datasets, binaries and raw traces are not distributed. Read [current status](../../../STATUS.md) for qualifications. Source provenance is retained in the repository manifest.

# Static proof record

Binary is RVA-aligned `analysis/steep-memory-image.exe`, base `0x140000000`, SHA256 `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`. No game launch, debugger, process reads, hooks, input injection, process-memory writes, remote work, original-instruction emulator or Ghidra analysis ran. All changes are in this task directory. Fresh Capstone exports include exact bytes; `verification.json` checks 4,965 spans in 24 exports against the image.

## Prior evidence used

Read all nine guides in PLAN.md. In particular, `analysis/twelfth-pass/trick-dynamics/private/EVIDENCE.md` already proves output assembly, unsigned history and matrix publication. `analysis/sixteenth-pass/private/EVIDENCE.md` already proves landing setter semantics and resets. `analysis/seventeenth-pass/private/EVIDENCE.md` already proves delayed tilt as a procedural angle. `analysis/snow_game/animations/physics-pose/CLIENT_GUIDE.txt` already explains the impulse-drive formulas and that some branches prescribe poses. The old decompilations `analysis/sixth-pass/ragdoll/functions/1413f7a10.c`, `analysis/fifth-pass/physics-pose/functions/1408dc4f0.c`, and the two loop consumers were context, not fresh output. This pass newly joins and spells out the prescribed-pose setter, its cap initializer, body provenance and exact open player edge.

## P1. Existing trick publication rechecked

`1405266f0.asm` active branch: state is `[receiver+10]`; require state+68. Target comes from `1404f2650`. At `140526882..68a5` state+610 becomes source for `14153e470`, fixed Z axis and heading radians in XMM3. Store assembled rate at state+a0. Add state+300 to Z only when state+b9; add state+48c unconditionally. `1405268f5` calls unsigned history. At `1405268fa..6909`, entity is `[[state+40]+10]` and target matrix is RDX to `14124d0f0`.

`14124d0f0.asm` packages two equal target pointers and flags31 at stack+30, then calls `[entity.vtable+90]`. No body setter occurs in this wrapper. The concrete entity vtable is not recorded by the inspected run36 membership receipts. Actor/entity equality guards do not identify this callback. `1404f2650.asm` verifies the existing basis rotations and translation builder. This fresh export does not close physical actuation.

## P2. Prescribed-pose follower to body angular assignment

`1413f7a10.asm` arguments: RCX points to a body pointer, RDX target translation, R8 target quaternion, XMM3 h; fifth stack argument controls force. At `7a4b` compute `1/h`, without local positive/zero guard.

`1418aa200.asm` returns body-local COM at body+128..130, refreshing a dirty cache when descriptor bit10 is set. `1413f7a10:7a62..7acb` rotates this COM by target quaternion and adds target translation. `1414073d0.asm` obtains current body transform from `1418a8860` and transforms the same local COM, returning current physical COM. `7ae4..7aef` forms `(targetCOM-currentCOM)/h`.

At `7af3` current body basis arrives from `1418a8860`, which copies body+40,+50,+60 and translation+70. `7af8..7b60` transposes/repackages nine basis floats for `140db32e0`. The conversion's exact approximation was not reimplemented here; relative quaternion input convention is retained. `7b65` obtains current quaternion. `7b7e` calls `1408dc4f0(currentQ,targetQ,1/h,rate,epsilon)`, epsilon `141df3300` = float32(1e-5).

`1408dc4f0.asm`: `c518..c574` computes inverse current quaternion as conjugate divided by norm squared. `c598..c5c3` is Hamilton `targetQ * inverse(currentQ)`, not reversed. `c5c6..c5fc` normalizes the result using rsqrt refinement. `c607..c61a` calls acos(w), then doubles it. `c627..c642` compares all four components to identity within supplied epsilon. Near identity select axis `(0,0,1,0)` at `c644..c64e`; otherwise `c653..c6af` normalize vector part with W=0. `c6c2..c6d7` multiplies axis by `2*acos(w)*1/h`.

No local shortest-arc sign flip, clamp of acos input or nonfinite repair was observed in this helper. q and -q can produce different rates. Exact negative identity has undefined axis normalization. The host receipt checks finite, normalized nonsingular inputs and does not invent a native safe fallback.

`1413f7a10:7b88..7be9` clamps angular XYZ separately using `143315970/974/978` lower and `14331597c/980/984` upper. `7bf7..7c5c` clamps linear XYZ separately using `143315958/95c/960` lower and `143315964/968/96c` upper. W becomes zero. `7c5f..7c91` sets force iff fifth argument equals1, calls linear setter `1418aa520`, then angular setter `1418aa360`.

`1418aa360:aa364..aa396` rejects body kind2 unless force, then directly assigns body+1ac/+1b0/+1b4. World-present plus force requests `1418b8380`. This is not a torque, additive impulse or inertia division. The ordinary clamp has finite-input semantics; SSE COMISS exceptional behavior is not claimed identical to Python min/max.

## P3. Cap initializer, newly joined

`cap-refs.json` is a capped displacement-candidate inventory, 100 decoded references, not exhaustive alias-aware writes. The final script collects raw displacement candidates and decodes at most250 candidate fragments. Its first draft decoded exception fragments directly before it was replaced; neither version did Ghidra whole-program analysis. It reveals writer root `1413ea620`. Selected fresh export is 506 bytes.

`1413ea620:ea6b6` reads120 from `141e4a8e8`; `ea6d9` reads-120 from `14291a3f4`; `ea6ef` reads+100.53096771240234 from `14291a3e0`; `ea705` reads its negative from `14291a3f0`. Stores `ea6e1/ea6f7` initialize linear XY upper/lower; `ea724/ea736` initialize linear Z to immediate +/-120. Stores `ea70d/ea75d` initialize angular XY upper/lower; `ea74b/ea765` initialize angular Z to immediates float32 +/-32*pi. `cap-initializer-values.json` records literals. Zero values in frozen BSS (`constants.json`) are pre-init contents, not usable runtime caps. Invocation and later writers are not proved; report these as initializer-installed defaults.

## P4. Confirmed body provenance and selection limits

`14138bd50.asm` loops an indexed physical-body descriptor set, count from owner+8+92, getting each body pointer into stack+40. At `14138c520..c543`, translation is target-array[index*32], quaternion the next16 bytes, h is XMM9, RCX stack+40 contains the selected body pointer; outer force flag becomes Boolean. This call is in an alternative to direct matrix assignment plus zero velocities, selected by global byte `143092257`. Prior decompilation `analysis/fifth-pass/physics-pose/functions/14138bd50.c` shows that surrounding mode branch. It is not the main-body link runtime+6e8.

`14138b270.asm` also calls follower at `14138b902` and `14138b9f0`; those are pose-drive branch bodies, target translations/quaternions from its indexed/synthesized pose path. The full selector and identity to this game's active player bone set remain open. Do not transfer their physical-pose branch to every snow main body.

`caller-inventory.json` checks decoded E8 sites inside exception fragments. It excludes unowned leaf wrappers and E9 tail edges; not an exhaustive call graph. Explicit leaf export `141397ba0` demonstrates this limitation: actor+168 runtime nonnull branches to `141404910`, carrying the supplied linear velocity. Fresh `141404910` assigns runtime+6e8 body linear velocity and zero angular velocity under lock with force1. Its input third argument controls additional refresh, not the force passed to body setters. This is the already-known landing reset, rechecked here. New prescribed-pose follower is a separate consumer.

## P5. Remaining decisive edge

Exact missing edge: `1405266f0 ->14124d0f0 ->[entity.vtable+90]` must be resolved to the constructed entity type, then followed to any `runtime+6e8` angular writer, pose target or constraint drive. No equality between main trick output+a0 and body+1ac is established. Existing run36 body angular observations have unrecorded input, motion and clip selection; they cannot fill that ownership gap.

`math-receipts.json` contains eight synthetic finite-domain checks, including quaternion product order with noncommuting axes, timestep doubling, component saturation, transformed COM and q-sign sensitivity. These check the mathematical transcription only.
