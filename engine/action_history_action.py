"""Configured history-sector action evaluation, detached snapshot composition.

Evidence: INPUT_TO_ACTION_ROUTE.md, Composed history action evaluation.
Caller selects channel/history and supplies ownership observations and clock.
No resource lookup, reset traversal or gameplay binding is implied.
"""
import struct
from .action_sample import f32
from .action_history_direction import history_direction_matches
from .action_history_timing import advance_history_timing


def evaluate_history_action(snapshot, history, reference, *, direction_kind,
                            magnitude_threshold, mode, hold_delay, repeat_delay,
                            ownership_blocked, read_clock):
    """Evaluate a valid configured action, preserving unrelated action bytes.

    ownership_blocked() is called before detection and again before magnitude
    publication. The second observation does not retroactively alter the event.
    """
    if not isinstance(snapshot, bytes) or len(snapshot) < 0xd0:
        raise ValueError('action snapshot must cover both timestamps')
    if snapshot[0xb8] not in (0, 1):
        raise ValueError('cached predicate must be a canonical boolean byte')
    if not isinstance(history, bytes) or len(history) < 0x2e4:
        raise ValueError('history snapshot must contain newest magnitude')
    if type(direction_kind) is not int or not 0 <= direction_kind <= 0xffffffff:
        raise ValueError('direction kind must be uint32')
    observations=[]
    def blocked():
        value=ownership_blocked()
        if type(value) is not bool:
            raise ValueError('ownership callback must return boolean')
        observations.append(value)
        return value
    detection = None
    current = False
    if not blocked():
        detection = history_direction_matches(history, reference,
            magnitude_threshold=magnitude_threshold,
            sector=direction_kind if direction_kind < 4 else 4)
        current = detection['matches']
    start, repeat = struct.unpack_from('<2Q', snapshot, 0xc0)
    timing = advance_history_timing(current=current, previous=bool(snapshot[0xb8]),
        mode=mode,start_time=start,repeat_time=repeat,hold_delay=hold_delay,
        repeat_delay=repeat_delay,read_clock=read_clock)
    magnitude = 0. if blocked() else f32(struct.unpack_from('<f',history,0x2e0)[0])
    result=bytearray(snapshot)
    result[0x30]=timing['active']
    result[0xb8]=current
    struct.pack_into('<f',result,0x60,magnitude)
    struct.pack_into('<2Q',result,0xc0,timing['start_time'],timing['repeat_time'])
    return dict(snapshot=bytes(result), detection=detection, timing=timing,
                ownership_observations=observations, magnitude=magnitude)
