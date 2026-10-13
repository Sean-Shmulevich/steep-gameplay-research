# Physics-world optional child types: serialized boundary

The exact concrete subclasses of the two optional physics-world children remain unknown. This pass establishes a useful exclusion: the inspected ordinary `PhysicsWorldComponent` deserializer does not read or assign either child. Searching its fixed scalar payload for a child factory identifier would therefore be the wrong next step.

## Verified parent metadata

The installed component virtual table joins to the metadata name `PhysicsWorldComponent`, its factory and its constructor. CRC32 of that exact name is `0xd0b67579`, matching the inspected class-name CRC. This identifies the parent class; it does not identify the dynamically selected children.

Candidate adjacent member-description records in this frozen image do not supply a validated child-field name/type/factory assignment. Several are zero-filled. Their placement beside the parent metadata is not sufficient to label them as either child descriptor, nor is a guessed packed-record interpretation evidence of the child type. The component's owned-polymorphic clone path is established separately in the [child lifetime audit](SCHEDULER_CHILD_LIFETIME.md).

## Newly closed ordinary deserialization path

The component-specific reader begins by calling a base-reader thunk. That thunk jumps through one further thunk to a no-op return. There is consequently no hidden child assignment in that particular base-reader call.

The component reader then ensures room for 40 bytes in its input cursor and consumes exactly:

1. A 16-byte block copied into the component's vector storage.
2. A 12-byte triple copied into one component triple.
3. A second 12-byte triple copied into another component triple.

```text
read_physics_world_component(component, reader):
    no_op_base_reader(component, reader)
    if reader.cursor + 40 > reader.end:
        reader.refill_or_extend()  # exact refill semantics not traced here

    component.vector_block = reader.read_16_bytes()
    component.first_triple = reader.read_12_bytes()
    component.second_triple = reader.read_12_bytes()
    # No writes to optional child A or B.
    # No child type discriminator read.
    # No child factory call.
```

This is a scoped statement about this reader, not every serialization or fixup system in the engine. Out-of-line pointer fixups, generic reflection paths or runtime assignment may still populate the children. The vector and triple values do not disclose a polymorphic type.

The runtime clone later obtains each child's concrete clone through the source object's virtual method. That remains the strongest proved child-type dispatch edge: the source object must already exist. Its factory or assignment into the source component has not yet been joined.

## What the local assets can provide without launching the game

The local archive inventory includes base and two patch versions of each of the main world records. Their stable record identities are:

| World record | Stable resource identifier |
| --- | --- |
| STP_Alpes | `0x0000007a954c6bd0` |
| STP_Alaska | `0x0000010af88fa9e4` |
| STP_Japan | `0x000000d6ce6d6c20` |

Those records can support an offline follow-up: select the winning patch by resource identity; decode the enclosing object grammar; identify a structurally valid physics-world component record; and examine its out-of-line object-reference/fixup records. A component-name CRC byte match alone is not a validated object boundary. The records were inventoried here, not fully decoded in this pass, and no game payload is published.

Success requires a traceable relationship of this form:

```text
validated parent component record
    -> typed child reference or fixup for the specific child field
    -> concrete child class descriptor
    -> child factory and installed virtual table
    -> actual lifecycle and destruction implementations
```

If those records contain only the fixed scalar payload and no corresponding child linkage, the next source is a runtime setter or generic object-fixup writer. Do not invent child objects from nearby type names or infer that the optional children are ordinary resources just because they are cloned.

## Consequence for scheduler control

Neither child's concrete lifecycle method is available for a wait/cancel/unregister classification yet. This prevents using the optional-child cleanup order as proof of submission exclusion. The previously recovered scheduler teardown remains real, but its exclusion precondition must be demonstrated in the actual selected child or an upstream caller.

This result narrows the search: the ordinary 40-byte deserializer is closed and cannot answer child selection. Further work should target typed out-of-line linkage or the first writer supplying the source child instance, rather than repeatedly inspecting the parent constructor.

## Evidence receipt

The ordinary reader was inspected within its exception-table function bounds. Both five-byte tail-jump thunks and the final one-byte return were inspected explicitly because they lack ordinary function unwind entries. The class-name string and CRC were independently checked. No game, debugger or live-memory operation occurred.

| Checked item | Bytes | SHA-256 |
| --- | ---: | --- |
| Component ordinary reader | 158 | `3253eda5b8a2c23a0abdaabbd699a60352d396c24bf3aac896ec412fe084466d` |
| First base-reader thunk | 5 | `4a6ab1ab51e93dbd6944945139111a72e615eb0ae9bd992b4bb403d9fbbaf95b` |
| Second base-reader thunk | 5 | `7e8ef31bba3daf47a824e496c6991fcc11ad717c4b44688106c955f00030fcf6` |
| No-op return | 1 | `c557e71380112b980eaf1145fa80621130dfbdfa1e375d87ae0018b7c60ac16b` |

The studied image identity and surrounding lifecycle evidence are retained in the linked audits. No complete child-type resolution or safe original-engine stepping claim is made.
