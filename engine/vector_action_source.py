"""Recovered vector-action source selection and masking, preserving raw bits.

Evidence: MOTION_MEMBERSHIP_OBSERVATION.md, Vector-source ownership and masking.
Device-cache production, ownership writers and physical device names are unknown.
"""
ZERO = bytes(16)


def priority_blocks(owner, slots_high_to_low):
    """Seven ownership slots, inspected from highest address downward."""
    if type(owner) is not int or not 0 < owner < 1 << 64:
        raise ValueError('nonzero uint64 owner required')
    if len(slots_high_to_low) != 7 or any(type(x) is not int or not 0 <= x < 1<<64 for x in slots_high_to_low):
        raise ValueError('seven uint64 priority slots required')
    for slot in slots_high_to_low:
        if slot:
            return slot != owner
    return False


def cached_value(value, mask_stack):
    """A nonempty stack with a nonnull last entry suppresses the cached value.

    Earlier nonnull entries do not matter when the last entry is null.
    Lock operations and lifetime are external to this detached calculation.
    """
    if not isinstance(value,bytes) or len(value) not in (4,16):
        raise ValueError('expected scalar or vector raw bytes')
    if len(mask_stack)>65535 or any(type(x) is not int or not 0 <= x < 1<<64 for x in mask_stack):
        raise ValueError('mask stack requires uint64 entries and uint16 count')
    return bytes(len(value)) if mask_stack and mask_stack[-1] else value


def select_vector_source(kind, lane_mode, ownership_blocked, read_vector, read_scalar):
    """Configured vector callback prefix through lane selection.

    Source kind 0/1 selects vector channel 0/1; 2/3 selects scalar 10/12.
    Callbacks implement ownership and masked cache reads. They are invoked only
    on the selected path, in the recovered order. Unknown kind returns zeros.
    """
    for value in (kind,lane_mode):
        if type(value) is not int or not 0 <= value < 1<<32:
            raise ValueError('kind and lane mode must be uint32')
    result=ZERO
    if kind <= 1:
        if not ownership_blocked('vector',kind):
            result=read_vector(kind)
            if not isinstance(result,bytes) or len(result)!=16:
                raise ValueError('vector provider must return 16 bytes')
        if lane_mode == 1:
            result=result[:4]+bytes(4)+result[8:]
        elif lane_mode == 2:
            result=result[4:8]+bytes(4)+result[8:]
    elif kind in (2,3):
        channel=10 if kind==2 else 12
        if not ownership_blocked('scalar',channel):
            scalar=read_scalar(channel)
            if not isinstance(scalar,bytes) or len(scalar)!=4:
                raise ValueError('scalar provider must return four bytes')
            result=scalar+bytes(12)
    return result
