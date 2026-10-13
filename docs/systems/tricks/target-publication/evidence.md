> Findings-only publication. Companion assets, datasets, binaries and raw traces are not distributed. Read [current status](../../../STATUS.md) for qualifications. Source provenance is retained in the repository manifest.

# Static evidence

Image `analysis/steep-memory-image.exe`, RVA-aligned at base `0x140000000`, SHA256 `32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`. Function exports use the existing exception-root/fragment exporter, 24 KB cap. The complete short snow leaf has an explicit 62-byte window because the generic leaf exporter stops at its first tail jump and otherwise omits the alternate branch. All its instruction bytes are verified.

## P1. Actor owner and receiver limits

`1404de010.asm` calls `14136ca00` on the same receiver, then installs table `141e7a350`. The base snowboard constructor reaches `141368e60 ->14084f610`. `14084f610:84f62e` initializes actor+10 to zero. This is the dynamic owner/entity pointer, not an embedded entity constructor.

`1405266f0:5268fa..526909` supplies `[[state+40]+10]` and the target matrix to `14124d0f0`. `14124d0f0:24d0f7/24d0fc` stores the same pointer twice in a 24-byte packet, `24d106` stores flags31, and `24d10e` calls entity virtual+90.

Discovery used prior `14087bb80` owner query layout: owner+88 pointer array, u16 count+92, virtual+198 query. Fresh export confirms it. Matching that layout finds the constructor-backed entity implementations below. No saved live entity vtable was used or invented.

## P2. Two constructor-backed entity tables

`140850910:850922` calls base transform ctor `141243ef0`. At `850927`, RIP-relative LEA resolves to `141ebbf78`; `85093b` installs it at the primary receiver pointer. It constructs the collection at entity+88 and initializes the recursive lock at +160/+164/+168, among other fields. Table+90 is `1408841f0`; table+198 is `14087bbd0`.

`140850ff0:850ff9` calls that constructor on the same receiver. LEA `850ffe` resolves to `141ebcbd8`; `851007` replaces the primary table. It initializes the managed child-record collection at entity+210. Its table+90 is `140884290`; table+198 is also `14087bbd0`. Every cited table pointer and slot value is checked in `bindings.json`.

Several short serialized data-object tables in the nearby code initially looked like entity candidates. Their +90 address lies in another table or is a serialization/destructor function. Their exports remain as rejected discovery context, not published entity candidates. The two long tables above have the owner collection/query layout and explicit entity construction.

## P3. Target copy and callback order

`1408841f0:8841ff..884239` takes the entity+160 recursive lock using thread identity `141dc3340`. At `884242` it calls `14088e050`, at `88424d` calls `14124d080`, at `884258` calls `14088dfb0`, and then releases the lock. The same packet remains RDX through these calls.

`14088e050` clears entity+1f8, loops array+88/count+92, and passes the packet to each component virtual+118 at `88e0a9`. Components are raw stored pointers in this particular loop.

`14124d080:24d08a..24d0ae` reads packet+0 then copies its four aligned 16-byte rows to entity+20/+30/+40/+50. It checks optional entity+18, packet bit0 and bit2. With packet31 and a nonnull +18, bit2 bypasses the preliminary `14124a850` check and calls `14124a980`.

`14124a980` updates the optional transform record under its own lock. Internal parent composition is not completely transcribed: it uses `141248d30`, `14023fe10`, `1402ec780`, then visits record+48/+50 links through `14124bcd0`. This branch is not a proved main-body setter.

`14088dfb0:88dfc4..88dfe0` passes entity+20, optional entity+158 and Boolean entity+f0==2 to `14086fbd0`. It sets entity+11a and loops the same component collection, passing the packet to component virtual+120 at `88e029`. Thus component pre-callbacks precede the entity copy, and post-callbacks follow it.

## P4. Transform-cache consumer

`14086fbd0` requires entity+138 nonnull. Unless forced by the mode Boolean, it compares that object's transform at +40 with the new target using `1401e4380`; equal data returns. It gets a writable cache packet through `14087f720`, copies the target's four rows to packet+0..30, sets flag bit1 at packet+a8, optionally copies entity+158's four rows to packet+40..70 and sets bit2, or clears bit2 when absent. It also refreshes bounding data at packet+80/+90 under the observed dirty/force gate. This is transform/cache publication. Its later consumer and exclusive renderer use are not proved.

## P5. Exact snowboard component notification returns

Both constructor-backed component tables `141e7a350` and `1429145a0` bind virtual+118 to `14075e600` and virtual+120 to `1413a9670`.

`1413a9670-complete-leaf.asm` checks component+8 bit26, component+2b==0, packet+10 bit3. Failing any gate returns at `1413a96ad`. It loads packet+8 as RDX. Packet bit4 selects tail jump `[component.vtable+280]` at `1413a969f`, otherwise `[component.vtable+288]` at `1413a96a6`.

Both tables' +280 and +288 entries equal `14075e600`. Its exact bytes are `c2 00 00`, decoded as `ret 0`. This classifies the next snow dispatch from checked table data and three return bytes; no further dynamic dispatch implementation was followed. Publication flags31 select +280 whenever the component gates pass. No target-to-main-body assignment occurs through this selected component notification. The direct pre-callback likewise returns immediately.

This does not classify additional entity components. Their table types are dynamic and no equality to the selected snowboard table is assumed. It also does not identify every live owning entity with one of P2's tables.

## P6. Derived child publication and stop boundary

`140884290:8842a0` calls P3, then tail-calls `14089fc00` at `8842b5`. The helper loops managed child records from entity+210/count+21a. It uses `14119f8d0` plus sign-mask flag decoding to select a child receiver, checks child+98 bit0 and a parent-transform predicate through `141248b60`/`14124a850`, and skips rejected receivers.

At `89fcb0..89fd3a`, it copies packet+8 and packet+0 into separate matrices and composes each through `1402ec780` with the per-child matrix at entity+238 + index*64. It preserves packet flags at `89fd44`, supplies the transformed packet to child virtual+90 at `89fd65`, and continues. Matrix multiplication order is not named without a fresh composition-helper convention proof.

Stop edges are the other component virtual+118/+120 receivers and child virtual+90. Their concrete constructors/membership and physical or render ownership remain open. The selected snow leaf's further dispatch is identified as a no-op only for the two checked snow tables. No main-body angular setter, indexed pose follower or torque/constraint formula is inserted into this ownership chain.

## Proof receipts

`build_proofs.py` checks 12 table entries, 14 exact byte anchors and the no-op bytes. `verify.py` checks all exported instruction strings against the image and writes `verification.json`. `branch-receipts.json` gives five synthetic flag/gate cases, not game runs. Two entity tables and nine actual publication-route consumers were selected, with constructor/query discovery exports kept separately in interpretation. No full-program Ghidra analysis ran.
