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
