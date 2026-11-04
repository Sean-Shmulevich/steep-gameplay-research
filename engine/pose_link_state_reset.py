"""Link record endpoint clearing, contact retirement and held-payload return.

Evidence: LINK_SOLVER.md, Link state reset before provider queue handling (RVA 0x1958ba0).
"""
import struct

from engine.pose_link_payloads import clear_pose_link_contacts


def reset_pose_link_state(link, *, entry_arrays, release_contact, release_held):
    """Clear endpoints, retire contact payloads and return the held payload.

    link is a raw link record. In order: qwords at +8 and +0x10 (endpoint bodies)
    are zeroed; the contact span (entry pointer +0x58, count +0x60, i.e. nested
    object +0x48 passed to 0x1958720 with a null destination) is cleared through
    engine.pose_link_payloads.clear_pose_link_contacts; then a nonzero qword at
    +0x78 is passed to release_held and only afterward zeroed. A null +0x78 does
    nothing. Both services stand for protected pool-return blocks (different pool
    globals) and observe the link as already modified by earlier steps. Ring
    links +0x20..+0x3f, keys, capacity and every other byte are untouched. No
    exception rollback is invented; endpoints are not required to be valid.
    """
    struct.pack_into('<QQ', link, 8, 0, 0)
    clear_pose_link_contacts(link, entry_arrays=entry_arrays, release=release_contact)
    held = struct.unpack_from('<Q', link, 0x78)[0]
    if held:
        release_held(held)
        struct.pack_into('<Q', link, 0x78, 0)
