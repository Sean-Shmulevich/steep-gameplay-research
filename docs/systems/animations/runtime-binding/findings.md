> Findings-only publication. Companion assets, datasets, binaries and raw traces are not distributed. Read [current status](../../../STATUS.md) for qualifications. Source provenance is retained in the repository manifest.

# Animation binding investigation

The chosen ownership join remains open. This pass corrects the proposed clone edge and identifies the actual compiled-node resource construction call. It used the local image and authored graph bytes only. No game process, remote machine or live memory was accessed.

## New evidence

The factory call previously described as a metadata-aware clone does not clone node members. Its wrapper tests a two-word identity. If either word is nonzero, it forwards the destination object and that identity to an object registry. The registry validates the destination's metadata, looks up existing object and identity mappings, and records the destination under the identity. It never assigns the DataNode's embedded resource handle. An all-zero identity returns from the wrapper without registration. This corrects the run37 interpretation, without changing its observed factory call.

The concrete runtime DataNode descriptor contains one local member record. That record names an opaque member hash and offset 120. The runtime object is 152 bytes. The descriptor's name CRC agrees with `AnimationDataNode`; the authored record's CRC agrees with `AtomAnimationDataNode`. These are separate classes. A compiled descriptor offset cannot be treated as a byte offset in the authored Atom record.

The actual virtual clone copies the source node's 64-bit field at offset 120 into the destination, then calls a handle initializer with the destination's embedded handle, that source field, and zero. The embedded handle begins at offset 128. This is a concrete compiled-node source-field-to-handle call, rather than an inferred generic clone. The helper's implementation and the provider comparison key inside the resulting handle remain untraced.

The first owned idle record was reread and its complete 377-byte hash matched run37. Its owned-output GUID and resource UID remain separate values. The resource UID is at graph byte 3,092,677, within the output record, while the GUID occupies the preceding 16-byte field. The registry wrapper takes a 128-bit identity; this alone cannot establish that it consumes this output GUID, and certainly cannot establish that it consumes the 64-bit resource UID.

The selected reset function only clears cached-ready and another scalar, then sets an enable byte in the instance arena. The selected phase function consumes duration and cache state. Neither supplies the missing authored resource decoder. The metadata registration function registers the runtime DataNode descriptor in a type registry and has no authored record interpretation.

## Boundary and unresolved edges

Six new concrete function candidates were inspected, with no function larger than 24,000 pdata-linked bytes. Two leaf functions were completed with bounded windows ending at their known returns. The member inventory has one row. Every exported instruction was compared with the original image bytes. The exact candidate list, instruction addresses and descriptor bytes are in private/PROVENANCE.md (`private/PROVENANCE.md`; source artifact, not distributed), private/metadata-inventory.json (`private/metadata-inventory.json`; source artifact, not distributed) and private/image-receipts.json (`private/image-receipts.json`; source artifact, not distributed).

Success still requires both joins: authored owned-output UID to the compiled source field, and source field to the embedded handle's provider key. The first has no proven decoder or assignment. The second has an exact helper call, but its internal assignments remain unknown. No landing selector was pursued because the plan required resource binding first. The decoded landing payload remains distinct from a selected graph resource.

The actor-to-controller ownership path and the backend phase-advance callback remain separate blockers. This pass provides no authority to search live memory or run the previously proposed idle observation.

Reproduce the source and image checks with `python3 runtime/testbench/run38/animation/private/inspect_image.py` from the repository root.
