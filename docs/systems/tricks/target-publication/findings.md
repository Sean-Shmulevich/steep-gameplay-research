> Findings-only publication. Companion assets, datasets, binaries and raw traces are not distributed. Read [current status](../../../STATUS.md) for qualifications. Source provenance is retained in the repository manifest.

# Trick target publication

Run38 closes the constructor-backed entity callback and the selected snowboard component's target notification. The callback copies the submitted matrix into the entity transform. Its notification to the exact PlayerSnowboard component performs no physical body assignment. The route through other attached components and child entities remains unresolved.

This is static evidence. No game, process reader, debugger, hook, input sender, remote operation or instruction emulator ran.

## New evidence

- A base entity constructor and a derived entity constructor install two concrete tables. Their target-publication callbacks share the same locked pre-notify, transform-copy, post-notify sequence. The derived callback then forwards transformed packets to eligible child entities.
- The packet supplies the same 64-byte target matrix through both pointer fields and uses flags 31. The copy installs four 16-byte rows in the entity transform. Pre-notifications occur before this copy; post-notifications occur after it.
- The selected component's constructor-backed player table and its base snowboard table both bind the post-notification to the same gate/dispatch leaf. That leaf requires component flag bit26, an unset suppression byte and packet flag bit3. Packet bit4 selects one of two further component slots.
- Both selected slots in both snowboard tables point to an exact three-byte `ret 0`. For flags 31, the selected snowboard notification therefore returns without writing its runtime or physical body. Its pre-notification is also that no-op.
- The entity also updates a cached transform packet and, when an optional parent-transform record exists, visits its hierarchy. These stores identify entity and transform-cache consumers. They do not establish that rendering is their only use.

The concrete functions, table entries, bytes, gates and field ownership are in [private/EVIDENCE.md](evidence.md). private/bindings.json (`private/bindings.json`; source artifact, not distributed) preserves table/data and instruction anchors.

## What remains open

The actor's owner pointer is dynamic. The player constructor clears that pointer through its shared base constructor; it does not construct its owner entity. The recovered entity tables are constructor-backed implementations compatible with the already-recovered owner collection/query layout. A saved actor-to-owner equality does not itself prove that a particular live owner has either table. The callback result is conditional on these concrete entity types, and the snowboard no-op result is conditional on the exact component tables.

The entity's component array can contain additional types. Their pre/post callbacks may act on physical objects or render state. Child receivers are likewise dynamic. This pass stops at those receivers and at the next snow virtual dispatch; the latter can be classified as a no-op from checked table data and its return bytes without tracing another consumer.

No equality between trick-controller angular output and main-body angular velocity follows. The earlier indexed physical-pose follower remains a separate branch. No new connection to the main body's guarded angular field, torque, impulse, constraint drive or pose follower was found in this selected snowboard callback.

## Verification

`private/verify.py` passed 2,594 instruction-span checks across 39 exports against the unchanged image. `private/build_proofs.py` passed 12 table-entry checks and 14 exact byte-anchor checks, and wrote five synthetic branch receipts. Export verification proves artifact consistency, not runtime execution or complete component membership.

Two concrete entity tables and nine publication-route consumer functions were selected. Constructor/query discovery exports and rejected short data-object tables remain in private evidence; they are not entity callback bindings. Each function export stays below the 24 KB cap. The trace follows entity publication and component notification, two indirect dispatch levels. It does not continue into additional dynamic component or child receivers.
