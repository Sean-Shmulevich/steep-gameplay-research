"""Serial reconstruction of the command executor's normal-return control flow.

Evidence: ANIMATION_CONTEXT_RETIREMENT.md, command executor entry paths and
callback tail. Services remain supplied opaque callbacks, not recovered bodies.
Storage uses caller-owned integer slot identities, not native pointers. Registry
mutation is representable for experiments; it is not permission to mutate it.
"""


def execute_commands(manager, *, services, read_slot, invoke, read_global_flag,
                     max_callbacks=4096):
    """Run one executor invocation, preserving stores and dynamic end reloads.

    manager contains executing_byte, array (integer slot base), count (uint16),
    and embedded (opaque service-D receiver). services maps hierarchy/A/B/C/D/
    global to callables. B returns an integer; only its low byte is tested.
    B is the primary queue drain; its result means at least one record processed.
    read_global_flag is called only when that byte is nonzero. Global takes no
    arguments; D receives embedded; the other services receive manager.

    Caller serializes storage. There is no reentrancy guard, snapshot, lifetime
    pin, or exception cleanup. The callback budget is an authored stop condition;
    exhausting it leaves the byte set, as does an exception before normal exit.
    An inner invocation can clear the byte while its caller remains executing.
    """
    if type(max_callbacks) is not int or max_callbacks < 0:
        raise ValueError('nonnegative callback budget required')

    def end():
        base, count = manager['array'], manager['count']
        if type(base) is not int or type(count) is not int or not 0 <= count <= 65535:
            raise ValueError('integer slot base and uint16 count required')
        return base + count

    manager['executing_byte'] = 1
    services['hierarchy'](manager)
    services['A'](manager)
    did_work = services['B'](manager)
    if not (did_work & 255) or read_global_flag() != 0:
        services['C'](manager)
    services['D'](manager['embedded'])
    services['global']()
    cursor = manager['array']
    boundary = end()
    calls = 0
    while cursor != boundary:
        if calls == max_callbacks:
            raise RuntimeError('authored callback budget exhausted')
        invoke(read_slot(cursor))
        calls += 1
        cursor += 1
        boundary = end()
    manager['executing_byte'] = 0
    return {'callbacks': calls, 'native_serialization_proved': False}
