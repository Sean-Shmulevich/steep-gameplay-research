"""Successful child-request lifecycle model with symbolic object identities.

Evidence: MOTION_MEMBERSHIP_OBSERVATION.md, 'Nested requests and replacement'.
No allocation, locks, callback bodies or native scheduler execution is modeled.
Events describe callback slots; disposal is a role label, not an actual free.
"""
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class ChildSlot:
    current: str | None
    current_mode: int
    pending: str | None = None
    pending_mode: int = 9


def request_mode_zero(slot: ChildSlot, allocated_identity: str):
    """Model a successful mode-zero request after its allocation completes.

    Cancellation precedes allocation in the original; this API assumes allocation
    succeeds and callbacks do not mutate ownership. Caller supplies unique IDs.
    """
    if not isinstance(allocated_identity, str) or not allocated_identity:
        raise ValueError('allocated identity must be a nonempty string')
    if allocated_identity in (slot.current, slot.pending):
        raise ValueError('new allocation must have a distinct identity')
    events = []
    if slot.pending_mode != 9 and slot.pending is not None:
        events.append(['dispose', slot.pending])
    return replace(slot, pending=allocated_identity, pending_mode=0), events


def service_child(slot: ChildSlot):
    """Commit an eligible pending child; caller must establish owner eligibility."""
    if slot.pending is None or slot.pending_mode == 9:
        return slot, []
    events = []
    if slot.current is not None:
        events.extend([['exit', slot.current], ['dispose', slot.current]])
    events.append(['enter', slot.pending])
    return ChildSlot(slot.pending, slot.pending_mode), events
