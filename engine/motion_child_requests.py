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


@dataclass(frozen=True)
class ChildEntrySnapshot:
    cached_profile_bits: int
    actor_flag: bool
    within_input_count_threshold: bool


def sample_child_entry(active_count: int, threshold: int,
                       profile_value_bits: int) -> ChildEntrySnapshot:
    """Local effects of mode-zero child entry with a valid profile/owner chain.

    active_count is the ingestion-written consecutive-nonzero XY count, not
    elapsed seconds. Profile value is copied as bits, without assigning units.
    The original compares unsigned count <= threshold and sets the actor flag.
    """
    for value in (active_count, threshold, profile_value_bits):
        if type(value) is not int or not 0 <= value <= 0xffffffff:
            raise ValueError('entry fields must be unsigned 32-bit values')
    return ChildEntrySnapshot(profile_value_bits, True, active_count <= threshold)
