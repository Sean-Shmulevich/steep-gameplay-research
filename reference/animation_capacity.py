"""Recovered packed-array capacity operation used by animation metadata/work.

Evidence: CENTRAL_IMPULSE.md, Animation array capacity replacement.
Allocation/copy/release remain explicit effects, not native memory operations.
"""


def plan_capacity_change(header, requested, stride, force, pointer_present, allocation_succeeds):
    if type(header) is not int or not 0<=header<=0xffffffff or type(requested) is not int or not 0<=requested<=16383 or type(stride) is not int or not 0<=stride<=0xffffffff:
        raise ValueError('bounded capacity and uint32 fields required')
    if any(type(x) is not bool for x in (force,pointer_present,allocation_succeeds)):
        raise ValueError('boolean state required')
    capacity=header&0x3fff;count=header>>16
    if not force and capacity>=requested:
        return dict(action='unchanged',header=header,effects=[])
    effects=[dict(kind='allocate',elements=requested,stride=stride)]
    if not allocation_succeeds:
        return dict(action='allocation_failed',header=header,effects=effects)
    if count:effects.append(dict(kind='copy',bytes=(count*stride)&0xffffffff))
    if pointer_present and not header&(1<<15):effects.append(dict(kind='release_old'))
    effects.append(dict(kind='install'))
    return dict(action='replaced',header=(count<<16)|(requested&0x3fff),effects=effects)
