> Findings-only publication. Companion assets, datasets, binaries and raw traces are not distributed. Read [current status](../../../STATUS.md) for qualifications. Source provenance is retained in the repository manifest.

# Contact and landing proof receipts

All addresses refer to the RVA-aligned offline image at base 0x140000000. `byte-proof.json` records its SHA256 and checks every emitted instruction byte against the image. No process was accessed. `field-inventory.json` is a bounded displacement candidate inventory, not an exhaustive alias or writer proof. It covers pdata instruction streams, excludes leaf routines without pdata, and may stop disassembly on invalid instruction bytes. The actor +230 inventory is restricted to RVA 1370000..13d0000 because the unfiltered 1736 candidate ranges exceeded the 256-range cap. Unrelated objects share offsets.

## Newly joined producer and consumer edges

1. `14140d680.asm`, 14140d8a0..14140d8e9: runtime in RSI; cell array runtime+6a8, cell stride140. Build a 32-byte descriptor with +10=cell+d0 and append to runtime+1538 using1413ed520. `1413ed520.asm`,1413ed649..665 copies both16-byte halves to array +20 and increments count+18. This closes the descriptor→cell-plane identity. A second descriptor family at14140d997..9c7 uses face+70 and stride d0. Do not parse these as cell records.
2. `141407230.asm`,14140731f..341: query141405bb0 receives runtime+1538 and selected geometry update buffer. It then tail-jumps141408c10 at141407377. `141405bb0.asm`,141405d18..d33 clears each descriptor destination's plane+30 profile and +38/+3c thickness values before query.141405df4 installs vtable14291a1c0. Prior pass4 evidence already identified the callback vtable and hit/material getters; this run newly joins it to the exact cell destination and downstream summary.
3. `141407a90.asm`,141407abb..b13: hit backend material getter14062c730; getters14139cb80/14139cba0 supply thickness/range; resource weakref material+18 resolves only with sign bit of descriptor+0xc set, then resource+30 decoded profile. Callback writes selected plane+30=profile, +38=effectiveThickness, +3c=range or observed gap. Backend object path1418a87d0→1418ac3c0 writes plane+40 mask before geometric acceptance. Therefore a mask can be present after a rejected geometric candidate. Profile nonzero was reset at query entry and indicates a selected profile-bearing hit on this query branch, assuming completed same update and identity. Callback can geometrically accept with null profile, so null profile does not mean no backend hit.
4. `1413fca30.asm`,1413fca4a and1413fcae0 passes cell+d0 to1413fc4c0. `1413fc4c0.asm`,1413fc73c..754 and1413fc868..880 loads plane+30 into the coefficient evaluators. Alias: cell+100=profile, +108=effectiveThickness, +10c=range/gap, +110=backend mask. The mask is NOT a resource pointer. Cell+a4 is the clipped-volume validity byte, cleared every update at141408fa3 before geometric dispatch and tested by the impulse and summary consumers.
5. `141408c10.asm`,141409091..0c1: map runtime+ab8 is keyed by cell+100 with float accumulated volume; map+af8 is keyed by cell+110 with integer occurrence count. `1413edb30.asm`/`1413edc20.asm` confirm pointer-sized keys and payload+8. At141409120..13f, choose key for maximum count with >=, so equal counts replace the current winner in map traversal order. Store runtime+b38 only if winning key nonzero; otherwise retain prior. `14140a880.asm`,14140ab6f..abf2 resets both maps each selected geometry update. The earlier decompiler marked its second-map reset unreachable; current bytes contain the reset call and tail jump. No dynamic validation of that helper's return behavior is claimed.
6. `1413f8700.asm`,1413f8bc0 passes retained+b38 in RDX to14140ef60; `14140ef60.asm`,14140ef66..80 returns `(key &3)==0`. This closes a real mask consumer and disproves treating+b38 as current fluid profile.

## Timer, cached skip and alternate writers

`141408c10.asm`,141409101..196 writes total positive clipped volume/hull+164 into runtime+9f0, then compares with float32 .001 at141e25210. Positive branch zeroes+a70, then adds+1520 to+a6c. Insufficient branch clears+9f0/+a6c then adds+1520 to+a70. All arithmetic is scalar float32.

Immediately afterward1414091b0 calls1413fd1d0. `1413fd1d0.asm`,1413fd515..5ef sums valid-cell volume-weighted terms into+9f4; when that accumulated term <=0 it clears+9f0, without updating either timer. This is an alternate immersion writer after timer classification, not a timer reset writer.

`1413bf300.asm`,1413bf3c3..3ff reads actor+168 runtime, compares+a70 with float32 .04 at141ea96d0, caches result in R14B and then actor+230. It also compares the old cached skip to the new value to form a transition signal R15B. Later virtual calls consume that signal at1413bf7a7. No invocation ordering between this actor function and the physics update has been recovered.

`1413bba20-leaf-window.asm` performs the same live timer threshold comparison for landing entry. It does not read cached actor+230. The cached skip and current landing timer predicate can therefore disagree until actor refresh, or during separate reads.

Alternate actor+230 writers in verified functions:1413a1940 reset clears at1413a197d;1413a97d0 copies input record+40 at1413a9872. Caller/source semantics of the record copy remain unbound. Runtime constructor1413cfa50 clears+9f0, +a70 and the overlapping qword+a68 that covers+a6c, as well as+b38. Whole-object copies and leaf writers remain outside the displacement inventory's completeness claim.

## Landing path

Prior findings, re-exported here:14053d860 gets live absence predicate1413bba20 and direction14139bf40; dot4 motion+2f0 and normalized direction must be negative on ordinary route. Getter chooses actor+210 if actor+1fa==0, runtime+a40 otherwise. `14139bf40-complete-window.asm` byte-verifies both branches. The ordinary leaf-window export ends at the first ret.

Query1405e7a80 can update category output before rejecting category outside21..23, including fallback entries. Success copies hit direction+10, then caller updates actor+1f0 regardless of success. Its hit material handle+48 resolves object+20 category. This category differs from fluid profile and backend mask.

14053dc40 computes acos(clamp(dot3(targetUp+190,selectedDirection),-1,1))*180/pi and abs(dot3(storedMotion+2f0,direction)). Virtual selector actor vtable+458 chooses base/scale; actor+fd4=base+scale*normalMotionMagnitude. This route includes further grab/upright gates, amount publication, state resets and first-entry snapshot. Full classifier and sport mapping remain open. Animation sibling owns graph outputs and clips; these physical values are not named animation outputs without a separate join.

## Sample131 preserved

Original receipt `run36/session-1/forward/transition-race-audit.json` has skip1 at1.6361..1.6622ms, timer0 at1.6771..1.6942ms, immersion .2021016627550125 at1.7271..1.7395ms. First-to-last span .1034ms inside request4.017416998976842ms. contact_elapsed and update_elapsed both .010050700046122074. This equality is compatible with a first positive-immersion update after absence; it does not prove which update each read observed.

A concrete permitted sequence is actor threshold refresh while timer>=.04, then physics contact update resets timer before recorder reads it, with cached skip still1. No shared scheduler edge proves this sequence happened. A read crossing writes, record-copy writer, or untraced scheduling path remains possible. The later immersion-clearing writer explains another possible non-equivalence, but does not itself produce positive immersion with timer0/skip1. sample132 has a different stored motion despite skip1, proving that sparse endpoints cannot establish uninterrupted snapshot freezing.

## Weather boundary

Inspected current packaged materials/terrain-binding/impulse-coupling guides and snow/environment/WORLD_AND_WEATHER.txt. Authoring binds terrain collision resources to profiles; Foggy season binds weather/TOD/wind controller tracks and LayeredSky. No inspected producer mutates a collision material, decoded fluid coefficient or selected profile from those tracks. The missing edge is weather property destination→collision/profile mutation or coefficient consumer, not a profile-name guess. Absence of that edge is not proof that weather never affects physics.
