"""Recovered epoch-gated skeleton bank rotation; logical IDs, no synchronization."""


def advance_pose_bank(current, previous, stored_epoch, epoch, bank_flags,
                      component_flags, owner_publication_present,
                      published_bank, publication_flags):
    """Banks 0 and 1 are the two configured slots; other IDs are supplied banks.

    The native method brackets this operation with a component lock. This pure
    model does not emulate locking, pin allocations or prove publication order
    relative to animation jobs. Epoch meaning beyond equality is unresolved.
    """
    if not isinstance(bank_flags, (list, tuple)) or not 2 <= len(bank_flags) <= 16:
        raise ValueError('2..16 supplied bank flags required')
    if any(type(x) is not int or not 0 <= x < 2**32 for x in (*bank_flags, stored_epoch, epoch)):
        raise ValueError('uint32 flags and epochs required')
    if any(type(x) is not int or not 0 <= x < len(bank_flags) for x in (current, previous, published_bank)):
        raise ValueError('bank ID outside supplied banks')
    if type(component_flags) is not int or not 0 <= component_flags <= 255:
        raise ValueError('component flag byte required')
    if type(publication_flags) is not int or not 0 <= publication_flags < 2**64:
        raise ValueError('uint64 publication flags required')
    if type(owner_publication_present) is not bool:
        raise ValueError('boolean publication presence required')
    flags = list(bank_flags)
    rotated = False
    if stored_epoch != epoch:
        previous = current
        if stored_epoch != 0xffffffff or owner_publication_present:
            if current == 0:
                current = 1
                flags[0] |= 1 << 29
                flags[1] &= ~(1 << 29)
            else:
                current = 0
                flags[0] &= ~(1 << 29)
                flags[1] |= 1 << 29
            if owner_publication_present:
                publication_flags |= 8
                published_bank = current
            rotated = True
        flags[current] = (flags[current] & ~(1 << 31)) | ((1 << 31) if component_flags & 0x38 else 0)
        stored_epoch = epoch
    return dict(current=current, previous=previous, stored_epoch=stored_epoch,
                bank_flags=flags, published_bank=published_bank,
                publication_flags=publication_flags, rotated=rotated)


def refresh_then_read_rotation(dirty_byte, channel_index, refresh,
                               selected_bank, read_rotation):
    """Recovered explicit-component accessor order, with supplied services.

    This operation MAY MUTATE through refresh; it is not a passive observation API.
    The bank is selected after refresh returns. No lifetime or synchronization is
    supplied here. The reader owns bounds/missing-index policy and result format.
    """
    if type(dirty_byte) is not int or not 0 <= dirty_byte <= 255:
        raise ValueError('uint8 dirty state required')
    if type(channel_index) is not int or not 0 <= channel_index <= 65535:
        raise ValueError('uint16 channel index required')
    if dirty_byte >= 128:
        refresh(False, False)
    return read_rotation(selected_bank(), channel_index)
