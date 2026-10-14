> Findings-only publication. Companion assets, datasets, binaries and raw traces are not distributed. Read [current status](../../../STATUS.md) for qualifications. Source provenance is retained in the repository manifest.

# Exact next edge

Export1412f8ce0 first. Known caller14127a140 at14127a1dc..1e7 passes destination+80, source+78, and zero. Existing141296c60 at141296c96..ca4 passes the same field pair when serialization-context[0]+c is nonzero. Identify assignment into handle+10, the key compared with provider-row+8 by1412fc8d0. Do not equate source+78 with a UID until that assignment and source producer are proved.

For the incoming producer use descriptor14307f170, local member14307b878, source offset78, opaque member hash6b798c5d, raw type worda00 and flags2001. Runtime class CRCdea49ff5 names AnimationDataNode; authored class CRC8028de84 names AtomAnimationDataNode. The previous factory wrapper14134f7f0 is object registration and must not be retraced as the authored decoder.

Input witness is Steep_Graph.block1.bin node3092337, owned output3092637, UID3092677, value377807682600. GUID is16 bytes at3092657..3092672. Record hash66f26495a3ccfe02557ec649613eaf21e00e56dea0e8ccfc695525a0eeef3701. Preserve GUID versus UID.

Bound four new function candidates total, 24,000 pdata-linked bytes each, 24 descriptor/member candidates. Select dependent functions from the helper's actual key assignment and the member reader/writer, rather than exporting unrelated vtable entries. Stop on missing source grammar or unresolved indirection within this bound. No live experiment, process access or remote export is authorized.

## Callback installer follow-up

Static evidence from the same image, SHA-256
`32646ca74ffb077d0a4e6def5b269a2c093dfc96cbcfc6ceedcc150e25dd60d2`:

- Handle initializer `1412f8ce0` loads global `143310280` at `1412f8cf9`,
  passes the key in RCX, then calls table slot `+8` at `1412f8d03`.
- Parent constructor `1412618b0`, 357 pdata-linked bytes, passes
  `owner+278` at `14126193d` to constructor `14125e800` at `141261944`.
  The acquire slot is therefore `owner+280` for this layout.
- Table constructor `14125e800` publishes RCX to `143310280` at
  `14125e812` and zeros table slot `+8` at `14125e821`.
- Its name registry is a different global, `143310288`, loaded at
  `14125e91a`. The string referenced at `14125e926` is exactly
  `AcquireAnimationResourceById`. The name-hash/insertion sequence ends
  with helper `141265120`; `14125e9a0` loads setter `14124fda0`, and
  `14125e9a7` stores that setter into the returned registry entry.
- Leaf setter `14124fda0` has no containing pdata entry. Its complete
  straight-line 12-byte body loads `143310280`, writes incoming RCX to
  `[table+8]`, and returns. This is a callback installer, not the callback.
- Teardown `1412644a0` zeros RSI at `1412644f1` and clears global
  `143310280` at `1412645d9`. This establishes a clear, not a drain.

Next bounded search: find the name-registry invocation that supplies the
acquire-by-ID function to this setter. Preserve the distinction between registry
entry, installer, callback table and installed lookup function. Inspect at most
four new dependent function bodies, each at most 24,000 pdata-linked bytes;
leaf functions require a verified entry and bounded return path. Stop if the
binding is supplied through an unresolved external interface. Do not repeat
constructor scans as evidence for the authored UID conversion.

## Installed acquire target and entry wrapper

The next four inspected pdata-linked bodies were:

| Function | Bytes | Finding |
| --- | ---: | --- |
| `140ddd730` | 1074 | Supplies acquire-by-ID name and function `140dd2b40` to dispatcher |
| `141297690` | 97 | Unsigned lower-bound name-key search and invocation of installer |
| `140dd2b40` | 70 | Eight-byte allocation request, forwards unchanged key to wrapper initializer |
| `140dd07b0` | 145 | Entry lookup, atomic reference handling and wrapper return |

The binding caller loads `140dd2b40` into R8 at `140ddd73b`, loads name
`141f296a0` into RDX at `140ddd742`, and calls `141297690` at
`140ddd749`. Dispatcher loads registry global `143310288`, computes a key
through `141274eb0`, searches node keys at `+20`, and invokes matched
node function `+28` with saved R8 moved into RCX. The name-key helper remains
unexpanded; no hash value is invented.

Acquire target calls allocation helpers `14115de60` and `14114a540` with
RCX/RDX both eight, checks the latter result for null, and tail-calls
`140dd07b0` with wrapper in RCX and original key in RDX.

Wrapper initializer writes initial entry `143301d40`, calls shared lookup
`1411925a0` with manager `143301d80`, original key and R8=0, increments
returned entry counter `+8`, exchanges the wrapper pointer, then decrements old
entry and returned entry counters in that order. Each decrement conditionally
calls `141194350` only when pre-decrement count equals one and flags at
`+c` have no low-24 bits set. No null check follows shared lookup.

Next four-function bound: lookup `1411925a0`, release `141194350`,
name-key helper `141274eb0`, then one evidence-selected consumer joining the
wrapper to the provider rows. Preserve unknown lookup/ownership contracts until
those bodies are inspected. This pass did not access a running game.

## Shared lookup and name-key pass

Four pdata-linked bodies inspected: `1411925a0` (147 bytes), `141194350`
(81 bytes), `141274eb0` (116 bytes), and `141192640` (627 bytes).

Outer lookup's zero-key/zero-record branch increments `143301d48` and returns
sentinel `143301d40`. Otherwise guard `manager+b8` brackets inner lookup
`141192640` and returned entry counter `+8` increment. Release wrapper guards
inner `1411943b0` with the same enter `141c3a280` / leave `1412213c0`
helpers. Their platform semantics are not asserted.

Inner lookup uses record helper `14119ed60` when no record override is given.
Record `+8` low 19 bits encode index+1. Manager block descriptors at `+e8`
have stride 16; block index is `(encoded-1)>>14`, entry index is
`(encoded-1)&3fff`, entry stride 24. Key map at `manager+100` uses
`14109a650` find and `14109aef0` insert. Record binding is `1411b8d40`;
existing-entry rebinding requires a differing record and either the explicit
record override or `1411dbfc0()==3`. New block initialization is `1411a1f40`
with count `4000`; block free-head word is `+c` and sentinel is `ffffffff`.
Entry fields are record `+0`, counter `+8`, flags `+c`, key `+10`.

Name-key helper calls `141347210`, computes byte length excluding NUL, then
calls `1413471b0` with seed, name pointer, length, matching the registration
call shape. This does not establish seed stability across initialization.

Next bounded candidates: inner release `1411943b0`, record lookup
`14119ed60`, record binder `1411b8d40`, and one dependent consumer if it
closes the wrapper-to-provider-row relationship. Keep authored UID conversion
separate. Four functions, at most 24,000 pdata-linked bytes each.

## Binding and release follow-up

Four pdata-linked bodies: `1411943b0` (352 bytes), `14119ed60` (168),
`1411b8d40` (370), `1411afb10` (159).

Inner release rejects entry flags bits 26/24, nonzero counter and nonzero low
24 flag bits. It clears record `+8` low 19 bits, optionally calls `141194510`
when that record word has bit 28, clears entry record pointer and bit 31, then
sets entry bit 26. Nonzero keys optionally erase through `1411ae050` unless
reserved-range or entry bit 28. `14119e460` finds the block; entry counter
word receives old free head, block free head receives signed entry offset /24.
The block at `141194400` setting bit 31 is bypassed by the observed initial
jump to `141194412`; no entry-route execution of that block is claimed.

Record lookup checks key and global enable byte, enters its global guard, tries
`14119e730` (slot+8), then `14119e3f0`, then key-map `14109a650`.
Binding calls `1411931f0` for the key and `14119d3c0` for index before
publishing `(index+1)&7ffff` into record+8 by CAS. Context `1411dbfc0()==3`
and global mode `143301dd8 != 1` select deferred queue `1411afb10`.
Otherwise an initially empty entry receives the record and bit 31 is set.
Existing non-null entries are not directly overwritten by these local branches.

Queue fields at manager base: storage+0, count+8, write+c, capacity+14,
notification+54. Triple is key/record/entry, each eight bytes. Growth helper
`1411af230` receives capacity+800 and preserve=true. Notification increments
at `1411afba5` even if growth failed the room test. Consumer and synchronization
remain open. Next bounded pass: queue consumer, `1411931f0`, `14119d3c0`,
and one dependent reader; four bodies, each <=24,000 pdata-linked bytes.

## Manager processing route

Four new pdata-linked bodies: `1411931f0` (139 bytes), `14119d3c0`
(129), `1411b89a0` (146), `141198820` (369).

`1411931f0` preserves R8 as record, tests record+8 bit 28, and conditionally
calls `141099e40` with owner+8/record then owner/key under its global guard.
The earlier abbreviated key-only pseudocode is corrected; operation semantics
remain opaque. `14119d3c0` scans manager+e8 block descriptors using count+f2,
signed divide-by-24 followed by unsigned low32 comparison with block+8 count;
returns block<<14 plus quotient, or ffffffff.

`1411b89a0` writes manager+58 before testing old=0/new=1. It polls loading
thread+288 and +290, calls `141198820`, and polls both again. It returns the
old mode. The manager is selected by direct global-address use `143301d80`
in caller `1400d2940`; this call-site lead selected the setter for inspection.

`141198820` enters manager+60, loading-thread+1d8, manager+b8 guards; calls
`141198740` then `141198a40` with a temporary output collection. Leaves
loading-thread+1d8, manager+60, manager+b8 in that order. Re-reads manager+58;
mode 1 destroys/free each non-null temporary object through the observed virtual
and allocator calls. `141198a40` is the existing staged-destruction publication
caller from the loading-thread research.

Next bounded candidates: `141198740`, its evidence-selected triple consumer,
and at most two directly dependent helpers. Do not treat broad references to
`143301d80` as animation-specific: this shared manager has many resource clients.
Four new function bodies maximum, each <=24,000 pdata-linked bytes.

## Triple consumption and dispatch

Four pdata-linked bodies: `141198740` (220 bytes), `1411989a0` (160),
`1411a8bd0` (240), `1411b9270` (166).

`141198740` guards manager+b8 and exchanges manager+50 into EDI. Each
iteration pops from ring storage+0, count+8, read+10, capacity+14. Key and entry
are taken from triple+0/+10; triple+8 is not used after copy. Entry+10 key match
precedes bit31 CAS on entry+c, current record reload and `1411a8bd0` call.
Producer `1411afb10` increments manager+54, not +50. Publication still open.
No generation or recycled-bit check is present at this consumer boundary.

`1411a8bd0` guards registry+8, obtains a temporary entry via `141192640`
with key zero/record override under the resource global guard, looks up its key
in registry+0, decrements/releases the temporary entry, then calls `1411b9270`
when a registry value exists.

`1411b9270` reads entry from receiver+8 and TLS word at TLS+48. It ORs
that word with sign-extension of entry+c bit31 and tests against raw entry+0
record pointer bits. Item count is receiver+1a; state-byte array pointer is
receiver+1c. Zero state calls `14066b790` with receiver+48 context; nonzero
return writes state=1. Nonzero state calls `14068f610` with receiver+28 context.
Count is re-read each iteration. The unaligned state-array pointer field is
reported as observed, not normalized into a guessed class layout.

Rejected consumer candidate `1411989a0` uses receiver+318 callback array,
+322 16-bit count, +324 saved index and +2e8 guard. It is a separate incremental
callback phase, not the triple ring.

Next: find manager+54 to +50 publication, inspect `14066b790` and `14068f610`,
then one directly dependent result reader. Bound four new bodies, each <=24,000
pdata-linked bytes. Native queue lifetime and original clip selection remain open.

## Item helper and guarded-branch pass

Four pdata-linked bodies: prepare `14066b790` (272 bytes), process
`14068f610` (316), guarded prepare `14066f1e0` (139), guarded process
`140695890` (139).

Both item helpers call mask helper `14119f8d0`, combine its result with
entry+c bit31 sign extension and entry+0, then call temporary resolver
`1411c6410` with current masked record and selected descriptor
`receiver+10 + item_index*24`. Temporary row pointer is local+18, 16-bit
count local+22, stride 40 hex. Optional handle row+30 is tested; when non-null,
its first pointer must be non-null. Zero row count fails. Output slot helper
`14118c510` takes caller context and item_index+1.

Preparation dispatches first row only, using predicate `1411cc130`, then
`1411d7b60` for false or `14066f1e0` for true. Processing loops all rows,
using `1411ec030` for false or `140695890` for true. False branches receive
row+20 dword and true byte. Both return true without inspecting operation result;
normal cleanup uses `1411c9de0`.

The two guarded helpers use the same global guard at `143073040`, owner+4,
depth+8. Owner helper is `141dc3340`; operations are `1411db0f0` and
`1411ed7a0` respectively. They pass dereferenced input handle and output context,
with same-owner nesting bypass and depth-zero release. No exception cleanup or
platform owner identity is established.

Next bounded pass: resolver `1411c6410`, predicate `1411cc130`, then at most
two evidence-selected helpers. Alternatively inspect the guarded operations if
the resolver remains generic. Keep producer+54 to consumer+50 publication open;
do not infer it from this dispatch path. Four new bodies <=24,000 bytes each.

## Resolver and mode-zero branch narrowing

Inspected constructor `1411c6410` (172 pdata-linked bytes), predicate
`1411cc130` (20-byte leaf including both returns through `1411cc143`),
resolver wrapper `1411c22c0` (486), row assembly `1411c2030` (645).

Predicate reads `[RCX]`, then `[that pointer]`, returning false if either is zero.
Constructor initializes output+18 to output+28, output+20 packed word 8004,
and calls record virtual+30 before resolver wrapper. Wrapper initializes 400 hex
scratch records of stride 90 hex, calls `1411e8960`, and invokes row assembly
only when AL is nonzero. Constructor returns output without testing wrapper AL.

The item callers supply zero stack mode. Constructor forwards that dword at
its outgoing stack+30; wrapper preserves it into R9D for row assembly. Assembly
stores it in R15D, tests at `1411c20e9`, and skips handle acquisition when zero.
Local optional handle starts null; appended row+30 receives that null. This closes
the generic predicate's false branch for the traced mode-zero construction path,
subject to unresolved helper side effects and external synchronization.

Row source mapping after normalize `1411dd420`: source+28 contributes row+0,
source+30 row+8, source+38 low byte row+10, source+20 row+18,
source+58 dword row+20, source+8 row+28. Row+30 is optional handle,
row+38 its flag. Variant bit0 at source+38 chooses a 32-bit versus 64-bit copy
into row+0. Source+50 is written through the supplied output-pointer argument.
Nonzero modes may call `1411e65d0` and adjust handle+48/+4c counters;
full general-mode ownership is outside this pass.

Next bounded candidates: direct prepare `1411d7b60`, direct process
`1411ec030`, and up to two dependent functions. Traversal `1411e8960`
and normalization `1411dd420` remain leads for descriptor grammar. Do not
promote guarded optional-handle dispatch to active mode-zero behavior.
