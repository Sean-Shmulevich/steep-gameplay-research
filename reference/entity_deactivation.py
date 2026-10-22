"""Recovered lifecycle ordering with stable, nonnull component collections.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, Entity lifecycle ordering.
Name is a reconstruction label; indirect services and scheduling stay external.
"""


def plan_entity_deactivation(*, component_count, extra_component, registry_matches,
                             registry_contains_entity, task_present, state_byte):
    """Plan original service order under nonmutating callback assumptions.

    Components receive reverse slot-0x110 calls, then forward slot-0x48 calls.
    Component tokens are array indices; 'extra' labels the separate optional
    component. These are not native component IDs. No native calls occur.
    """
    if type(component_count) is not int or not 0<=component_count<=65535:
        raise ValueError('uint16 component count required')
    if any(type(v) is not bool for v in
           (extra_component,registry_matches,registry_contains_entity,task_present)):
        raise ValueError('boolean lifecycle predicates required')
    if type(state_byte) is not int or not 0<=state_byte<=255:
        raise ValueError('uint8 state byte required')
    events=[dict(event='component_before',component=k) for k in reversed(range(component_count))]
    events += [dict(event='component_release',component=k) for k in range(component_count)]
    if extra_component:events.append(dict(event='component_release',component='extra'))
    events.append(dict(event='transform_teardown'))
    if registry_matches:
        events.append(dict(event='registry_enter'))
        if registry_contains_entity:events.append(dict(event='registry_remove'))
        events.append(dict(event='registry_leave'))
    if task_present:events.append(dict(event='task_release'))
    events.append(dict(event='tail_service'))
    return dict(events=events,registry_link_cleared=registry_matches,
                state_byte_after=(state_byte-1)&255)


def plan_entity_collection_drain(slots, collection_service_present):
    """Original drain order for supplied base-entity receivers without accessors.

    Source count clears before lock acquisition. Null entries are skipped and
    duplicates preserved. Temporary allocation and platform locks are external.
    Callback mutation, other receiver tables and actual freeing are unmodeled.
    Tokens must be nonnegative integers or None; these are inspection labels.
    """
    if type(collection_service_present) is not bool:
        raise ValueError('boolean collection service presence required')
    if not isinstance(slots,(list,tuple)) or len(slots)>65535:
        raise ValueError('supplied uint16-size collection required')
    if any(token is not None and (type(token) is not int or token<0) for token in slots):
        raise ValueError('nonnegative entity tokens or null slots required')
    selected=[token for token in slots if token is not None]
    if len(selected)>16383:
        raise ValueError('temporary packed capacity exceeded')
    events=[]
    if collection_service_present:events.append(dict(event='collection_service',lock_depth=0))
    events.append(dict(event='enter',lock_depth=1))
    for token in selected:
        events.append(dict(event='lifecycle',entity=token,lock_depth=1))
        events.append(dict(event='transform_teardown',entity=token,lock_depth=1))
    events.extend([dict(event='leave',lock_depth=0),dict(event='temporary_release',lock_depth=0)])
    return events
