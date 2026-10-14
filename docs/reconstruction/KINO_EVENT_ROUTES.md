# KinoComponent routes into the world registry

The world constructor installs a type-specific, unconditional KinoComponent route to event slot 16. This closes the static type-to-source-list question in the [animation registry guide](ANIMATION_EVENT_REGISTRY.md). It also installs a second KinoComponent route selecting slot 22 or 23 from an owning-object mode byte.

## Constructor-installed groups

| Route group | Required component type | Fallback slot | Conditional slot | Predicate |
| --- | --- | ---: | ---: | --- |
| Time group | KinoComponent | 16 | None | Not evaluated |
| Secondary group | KinoComponent | 22 | 23 | Owning object's low three mode bits equal 1 |

The time group uses the ordinary append helper, which stores event 16, conditional sentinel 54, and the metadata pointer returned by KinoComponent's type getter. The secondary group stores events 22/23, a predicate callable, and that same metadata pointer. Sentinel 54 means no conditional route; it is not a valid slot in the 53-entry registry.

The secondary predicate is exactly:

```text
select_secondary_event(component):
    owner = component.owner
    mode = owner.mode_byte
    return 23 if (mode & 7) == 1 else 22
```

The predicate itself does not check whether `owner` is null. Valid owner lifetime is an input requirement. The byte is not identified here as sport, grounded state, ragdoll status or player-control status. Those labels require its writers and consumers. High five bits do not affect this predicate.

## How descriptor routing supplies the listener

The already recovered generic insertion path asks the supplied context for a component matching the group's metadata. If it resolves an object and a world, it evaluates the route and inserts that resolved object pointer uniquely into the world's selected list. It does not insert the context pointer merely because the context owns the component.

```text
register_group(group, context):
    component = context.lookup_component(group.required_type)
    world = context.world
    if component is missing or world is missing:
        return
    for route in group.routes:
        event = route.fallback
        if route.has_conditional and route.predicate(component):
            event = route.conditional
        world.registry[event].insert_unique(component)
```

This is explanatory pseudocode combining the inspected lookup and routing operations. The lookup's subtype rules, iterator validity and component ownership are not reimplemented by the small API below.

Removal visits the conditional slot when present and then the fallback slot, without reevaluating the predicate. Thus cleanup for the secondary group attempts both 23 and 22. It can remove a prior registration even if the owning mode has changed since insertion. The code does not imply that changing the mode automatically migrates registration; the lifecycle caller remains a separate question.

## Portable use

```python
from engine.event_registry import WorldEventRegistry
from engine.kino_event_routes import kino_event_slots, kino_removal_slots

registry = WorldEventRegistry()
resolved_component_token = 100
for slot in kino_event_slots(owner_mode_byte=1):
    registry.register(slot, resolved_component_token)
assert registry.snapshot(16) == [100]
assert registry.snapshot(23) == [100]

# Cleanup attempts both secondary choices, even after the mode changes.
for slot in kino_removal_slots():
    registry.remove(slot, resolved_component_token)
```

`kino_event_slots` returns `(16, selected_secondary_slot)`. Callers supply an explicitly resolved component identity and owning mode; the API does not infer them from a player token. `kino_removal_slots` combines cleanup candidates for the two groups. Its ordering between groups is an adapter choice; conditional-before-fallback within the secondary group follows the inspected removal routine.

## Evidence and validation

The original world-constructor setup slice, metadata getter and unconditional route append helper executed against synthetic preallocated groups. Both metadata pointers and the resulting route records matched the table above. The original predicate callable adapter, thunk and body then matched the portable selection for all 256 mode-byte values. See the [receipt](kino_event_routes_validation.json).

Three tests cover all low-bit combinations, explicit component-token insertion and cleanup after a mode change, and invalid byte inputs. This does not exercise complete world construction, context lookup, native activation/removal callers or live gameplay.

Evidence anchors: world constructor `1408ae9a0`; time-group setup `1408af457..1408af470`, owner-held group+`0x1270`; secondary-group setup through `1408af56b`, owner-held group+`0x1278`. Type getter `140dda5e0` returns the descriptor at `142e915c0` through global `142e908a8`. Route append helper `1408fdc00` supplies the conditional sentinel. Secondary predicate adapter `1408ab380` passes the resolved component to thunk `1408eb230`, then predicate `140de2500` reads component+`0x10` and owner byte+`0x100`. Generic insertion/removal are `14085cd30` and `1408940f0`.

The resulting chain is now concrete at the type level:

```text
context resolves KinoComponent
    -> type-specific route inserts that component into slot 16
    -> pre-action gather copies slot 16
    -> animation range worker claims entries
    -> receiver slot calls KinoComponent time update
```

Still missing: the current player's context-to-KinoComponent association, the lifecycle invocation that installs/removes its routes, native object lifetime, and a live observation of the same component in a claimed batch. The route does not establish that every player component or actor pointer itself belongs in slot 16.
