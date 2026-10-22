> Findings-only publication. Companion assets, datasets, binaries and raw traces are not distributed. Read [current status](../../../STATUS.md) for qualifications. Source provenance is retained in the repository manifest.

# Offline ownership receipts

Image `analysis/steep-memory-image.exe`, preferred base `0x140000000`, SHA256 `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`. `verify.py` independently checks byte spans and instruction text with Capstone. All paths are local files. No runtime operation occurred.

## Inventory and bounds

`trace.py` uses the existing run14 focused exporter. `global-references.json` scans unwind fragment starts in `140900000..140a00000` and `140300000..140700000`. There are eight references, below the 64-candidate ceiling, across 30,672 fragments. Roots are `14044aeb0`, `140452770`, `14047cf70`, `140952eb0`, `14096f5a0`, `1409716b0`, `1409f0a60`. The only direct store clears the global at `140952ed2`.

`table-references.json` scans the same coverage for table `141edc620`. Only the deleting destructor binds it in that coverage. `gap-references.json` checks self-relative displacement candidates ending an instruction in the same two ranges, outside unwind coverage. This supplemental search is not a complete arbitrary instruction scan. It finds constructor LEA `14094c803` and global store `14094c814`. Their alignment is proved by direct call `140444ee6` and the complete leaf decode starting at `14094c800`.

`constructor-callers.json` checks bounded E8 candidates in the same ranges for the exact constructor and finds one, `140444ee6`, inside `140444e40`. That caller is exported and byte checked, making this candidate an actual aligned direct call.

Eight roots were exported, each below 24,000 instruction bytes: `140952eb0`, `14096f5a0`, `1409716b0`, `14094c800` leaf, `140444e40`, `14047cf70`, `14043f5c0`, `140ce4f50` leaf. The last is a rejected adjacent scalar candidate. The large string-oriented roots `14096f5a0` and `1409716b0` use other callable slots and do not establish vector storage. No further root was exported after the ceiling.

## Constructor and manager join

1. Deleting destructor `140952eb0` installs table `141edc620` at `140952ec4`, destroys owner+10 through `1406b1cb0`, clears global `143138fc0` at `140952ed2`, and conditionally frees `0x2e0` bytes. This supports the table and owner extent, without proving a complete destruction/lifetime protocol.
2. Leaf constructor `14094c800` has no unwind entry. `14094c803..80a` installs that same table on its RCX receiver. `14094c814` stores that RCX into global `143138fc0`, the run37 sampler callback-owner global. The rest initializes owner fields and clears every 16-byte callable region's first and third qwords through `+2d0`, then returns at `14094c97e`. Publication precedes these remaining writes.
3. Enclosing manager constructor `140444e40` keeps its original RCX in RBX, installs its own table and publishes manager RCX to global `14312bb00` at `140444e53`. It requests `0x2e0` bytes with alignment argument 8 through the selected allocator calls at `140444ec7` and `140444ed9`. On nonnull RAX it invokes `14094c800` with RCX=RAX at `140444ee6`.
4. At `140444eeb..eee`, RCX is restored from manager RBX and sent to `14047cf70`. Thus the callable owner is a separate allocation, and the binder's incoming receiver is the constructing manager. A following direct call to `14047c660` remains further setup, unexported in this pass. Allocation-failure branch still reaches the binder; it supplies no valid-owner guarantee.

## Vector callable binding and invocation

`14047cf70` loads global `143138fc0` into R9 at `14047cf79` and preserves its incoming manager RCX in R8 at `14047cf80`. R8 and R9 remain those values throughout this call-free binder.

The stack lifetime is essential:

- `14047d07b` sets RDX to `14046f200`. `14047d077` has already placed the previous target into stack `rbp-20`, so that preceding stack value belongs to the preceding callback.
- At `14047d0cc`, the now-current RDX=`14046f200` is placed into `rbp-20`. At `14047d0f5`, `rbp-18` is zeroed. `14047d100` loads this pair into XMM0.
- `14047d0f9` computes invoker `14043f5c0`; `14047d104` stores it into `rbp-8`. Receiver tagging in `14047d0db..120` incorporates manager R8 into `rbp-10`. `14047d10a` loads the tagged-receiver/invoker pair into XMM1.
- `14047d150` copies the already captured XMM0 to owner R9+`1a0`. `14047d189` copies the already captured XMM1 to owner+`1b0`. Therefore owner+`1a0`=`14046f200`, +`1a8`=0, +`1b0`=tagged constructing-manager receiver, +`1b8`=`14043f5c0`.
- RDX changes at `14047d0d4` to `140ce4f50`, but that value reaches stack `rbp-20` only at `14047d112`, after XMM0's vector pair was loaded. It belongs to the subsequent callback written at owner+`a0`, not vector+`1a0`. `140ce4f50` simply returns dword receiver+94. It is rejected as a vector-source or freshness field.

Prior complete sampler wrapper `14096cf20` sets R9D=action R8D, R8=owner+`1b0` masked with `~3`, RCX=temporary output, RDX=owner+`1a0`, then calls owner+`1b8` at `14096cf43` and copies the returned vector. Verify rechecks that selected indirect call and all four snow global loads.

New complete invoker `14043f5c0` reads `[RDX]` into RAX at `14043f5c6`, thus selecting `14046f200` from callable+0. It keeps output RCX in RBX, sets RCX to incoming captured receiver R8, RDX to temporary output, R8D to incoming action R9D, then calls RAX at `14043f5da`. It copies the returned vector to its caller's output. The resolved function thus receives the constructing manager as RCX and the action ID as R8D. The pointer's low two bits are removed by the outer wrapper; ordinary manager alignment is the condition for exact address equality.

## Precise unresolved edge

Next function is `14046f200`, called from `14043f5da`, selected by constructor-bound owner+`1a0`. Export it next. Do not substitute the adjacent scalar target. Compare its actual receiver adjustment and action-object read with prior `14046f140 -> manager+50 -> 14046f150 -> 1404748a0 -> action+20/fallback`, and vector helper `14062ca40`'s adjustment, using receiver ownership.

No new vector field writer, sample generation, timestamp, units or commit order was recovered. The manager's constructor global `14312bb00` is a new identity seed, not yet a proved live ingestion-object join. Subsequent setup `14047c660` and later rebinding are not excluded. The state-vector override and ingestion/physics dependency remain as run37 documented them.

## Follow-up: getter target resolved

The previously unresolved `14046f200` target is now inspected and validated in
48 original-instruction cases. It forwards the unchanged manager and selected
index to `14046f150`, then copies returned object `+40`. Motion's borrowed view
reaches the same field, selected action `+60`. The ingestion global also matches
the constructor-published manager global. See the
[getter/view join](../../../reconstruction/MOTION_MEMBERSHIP_OBSERVATION.md#copy-getter-and-ingestion-view-join)
for exact scope and limitations. Earlier open-edge text above is retained as
historical evidence; live rebinding, subtype and freshness remain unresolved.
