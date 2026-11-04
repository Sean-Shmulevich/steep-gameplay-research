"""Contact-flag refresh for a pair link (RVA 0x18dde70).

Evidence: docs/reconstruction/LINK_SOLVER.md, "Pair link worker" (dynamic handler 0x18df770
calls refresh_contact_flag(link) right after generate_contacts), and "Link state reset before
provider queue handling" (the contact span: entry pointer at +0x58, count at +0x60, both of
which are fields of the nested container at +0x48).

Recovered local behavior:

- The container is link+0x48. Its count is read through accessor 0x14144b420, which returns
  the u32 at container+0x18. Element i comes from accessor 0x141958840, which returns the
  pointer at [container+0x10] + 16*i + 8 (the payload of a 16-byte entry).
- For each payload in order, if payload+0x114 has bit0 set, link+0x84 bit0 is set and the
  scan stops. Otherwise, after the whole scan, link+0x84 bit0 is cleared. Other bits of
  +0x84 are untouched.
- A payload pointer that is zero faults natively on the read at +0x114. The model raises
  through the memory layer in the same way (unmapped read), so no value is invented.

Supplied services: contact_count(container) and contact_payload(container, index), the two
accessors above. They are small leaf reads, but they are kept as services so the Python model
does not depend on the container layout of the native accessor.
"""

LINK_FLAG_OFFSET = 0x84
CONTACT_CONTAINER_OFFSET = 0x48
CONTACT_OBJECT_FLAG_OFFSET = 0x114


def refresh_pose_link_contact_flag(mem, link, *, contact_count, contact_payload):
    """Set link+0x84 bit0 when any contact payload has its own flag bit0, else clear it.

    The scan stops at the first flagged payload, as the native loop does. Returns True when
    the flag was set.
    """
    container = link + CONTACT_CONTAINER_OFFSET
    count = contact_count(container)
    found = False
    for index in range(count):
        payload = contact_payload(container, index)
        if mem.b(payload + CONTACT_OBJECT_FLAG_OFFSET) & 1:
            found = True
            break
    flags = mem.b(link + LINK_FLAG_OFFSET)
    if found:
        mem.set_b(link + LINK_FLAG_OFFSET, flags | 1)
    else:
        mem.set_b(link + LINK_FLAG_OFFSET, flags & 0xFE)
    return found
