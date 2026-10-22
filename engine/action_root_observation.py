"""Bracket action observation with a fresh manager-global read.

Evidence: MOTION_MEMBERSHIP_OBSERVATION.md, Fresh manager root observation.
Caller must verify process/build identity. This adds no lifetime or atomicity claim.
"""
import struct
from .action_binding_observation import ActionObservation, observe_action_binding


def observe_rooted_action(read, manager_slot, action_id, fallback):
    """At most two extra 8-byte reads beyond observe_action_binding's budget.

    No saved manager pointer is accepted. If the root changes, discard all
    candidate identities and sample bytes. Read callback errors fail closed.
    """
    if type(manager_slot) is not int or not 0 < manager_slot <= (1 << 64) - 8:
        raise ValueError('manager slot must contain a uint64 address')
    def root():
        data = read(manager_slot, 8)
        if not isinstance(data, bytes) or len(data) != 8:
            raise OSError('short manager-global read')
        return data
    try:
        before = root()
        manager = struct.unpack('<Q', before)[0]
        if not manager:
            return ActionObservation('unavailable', 'manager_not_published')
        result = observe_action_binding(read, manager, action_id, fallback)
        if root() != before:
            return ActionObservation('unstable', 'manager_changed')
        return result
    except (OSError, struct.error):
        return ActionObservation('invalid', 'root_or_transport_read_failed')
