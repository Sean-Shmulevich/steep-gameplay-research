# KinoComponent activation and direct event membership

KinoComponent has a direct activation path in addition to its [descriptor routes](KINO_EVENT_ROUTES.md). A virtual-table callback requests activation from component flag bit 26. The local activation routine compares that request with its stored active byte, updates selected registry slots and preserves several exceptional states rather than forcing the stored byte to match the request.

## Activation decisions

For the ordinary Boolean active/request states:

```text
change_activation(component, requested):
    if not requested:
        component.interface.slot_140()

    if requested != component.active:
        if requested:
            if owner is not the sentinel and owner.world exists:
                if time_group.find_context(owner) == NOT_FOUND:
                    register_unique(component, slot=16)
                register_unique(component, slot=37 if owner.flags.bit36 else 19)
                register_unique(component, slot=17)
                component.active = true
                if component.auxiliary exists:
                    component.auxiliary.flags |= 0x200
        else if owner.world exists:
            remove(component, slots=[16, 37, 19, 17])
            component.active = false
            post_unregister_helper(component, float32(0.2))

    if not requested:
        component.flags_byte &= ~1
```

The routine passes the component itself as the listener. The group search instead looks for its owning context pointer. It scans context lists and returns the first list index, or `0xffff` when absent. These are different identities. A successful group search suppresses direct slot-16 insertion; it does not prove that a particular live component is already present in the slot-16 event array.

The indexed insertion/removal variants used here acquire a registry-wide guard, then the entry guard. Their inspected bodies update the entry immediately rather than only enqueueing a future request. Native lock implementation and lifetime safety remain outside the portable model.

Slot 37 versus 19 depends on owner flag bit 36. This is separate from the mode-byte predicate selecting descriptor slots 22/23. The standalone activation routine does not add or remove 22/23. The separate attach/detach-shaped methods do handle those slots, so neither route plan is a complete substitute for every lifecycle operation.

## State details relevant to a testbench

- Repeating an enable request when already active performs no local registration work.
- Every disable request invokes interface slot `0x140`, even when already inactive.
- A missing world during disable leaves the active byte true, while still clearing bit zero of the component's separate flag byte.
- A sentinel owner or missing world during enable leaves the active byte unchanged.
- Cleanup removes both 19 and 37, so it does not depend on the owner flag retaining its earlier value.
- Auxiliary flag `0x200` is set after successful activation when the auxiliary exists. This local routine does not clear that flag on disable.

The post-unregister argument is the binary32 value nearest 0.2. Its units and helper behavior are not inferred here. Likewise, the interface slot call is retained as an opaque effect rather than renamed as an animation reset, stop or completion barrier.

## Portable inspection API

`engine.kino_activation.plan_kino_activation` accepts explicit observations and returns the resulting active/component/auxiliary flags plus an ordered effect trace. It does not call native functions or mutate the supplied world registry automatically.

```python
from engine.kino_activation import plan_kino_activation

plan = plan_kino_activation(
    requested=True, active=False,
    group_contains_owner=False,
    owner_flags=1 << 36,
    auxiliary_present=True,
)
assert [event['slot'] for event in plan['events']] == [16, 37, 17]
assert plan['active'] is True
assert plan['auxiliary_flags'] == 0x200
```

`register` and `remove` effects can be applied to the serial event-registry adapter with an explicitly supplied component token. `interface_140` and `post_unregister` identify external work that must remain visible in an implementation. Omitting their internals is a stated fidelity boundary, not evidence that they are no-ops. Flags are width-checked; active/request values outside Boolean states are rejected rather than modeling arbitrary native byte values.

## Caller and separate lifecycle methods

The installed KinoComponent table's slot `0x220` selects a callback that extracts flag bit 26 and passes it to the standalone activation routine. After that call, it can perform additional interface work based on owner identity, interface readiness and another component flag. The local planner does not reproduce that additional work.

The table's slots `0x1d0` and `0x1d8` select separate methods with insertion/removal work. The first has a bit-26 activation gate, the same context-list check and direct 16/19-or-37/17 insertion, then separately inserts 22 or 23 according to owner mode. The second invokes a time-group helper, removes 22/23, and conditionally removes 16/37/19/17 before additional cleanup. Exact lifecycle names and the callers invoking these slots remain to be established; their table bindings do not prove a particular live transition occurred.

## Validation

The complete standalone activation routine and original context-list lookup matched the portable planner in 384 isolated cases. Cases cover every combination of requested/current activation, sentinel ownership, world presence, group membership, owner bit 36 and auxiliary presence, with three component flag bytes. Registry operations, interface slot `0x140` and the post-unregister helper were recording stubs. Checks compare exact operation order, selected slots, output flags and scalar argument. See the [receipt](kino_activation_validation.json).

Four repository tests cover enable routing, cleanup of both variants, repeated disable and missing-world behavior, and invalid observations. This validation does not execute native lock operations, external helper effects, complete lifecycle callers or gameplay.

Evidence anchors: standalone routine `140ddfc00`; table `141f289d0` slot `0x220` -> `140ddc170`; component flag word+`8` bit 26, active byte+`0x20`, separate flag byte+`0x359`, owner pointer+`0x10`, owner world+`0x60`, owner flags+`0x98` bit 36, auxiliary+`0xb8` flag word+`0xe8`. Group context search `140879820` uses world-held group+`0x1270`. Registry-wide insertion/removal are `14085b840`/`140893a10`. Post-unregister helper is `140de0e30`. Separate table slots `0x1d0`/`0x1d8` bind `140ddc1f0`/`140ddc610`.

The next identity check should retain the player context pointer, resolved KinoComponent pointer, component active/flag state, context-list membership and slot-16 source membership as separate observations. None can substitute for all the others.
