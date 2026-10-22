"""Recovered pool reuse branch; growth and allocation remain explicit gaps.

Evidence: CENTRAL_IMPULSE.md, Animation bank pool reuse.
Field names describe operations and are not recovered original names.
"""

def reuse_pose_bank(entries, request_mask, representation, mode, source, copy_selected):
    """Return first reusable bank, or None to report unresolved allocation path.

    Entries have occupied_mask, initialized_mask, representation_word and bank.
    Mutates the selected entry and bank. copy_selected supplies the native copy
    service with (destination, source, mode, original_uint16_request).
    """
    if type(request_mask) is not int or not 0<=request_mask<=65535:
        raise ValueError('uint16 request mask required')
    if representation not in (0,1) or type(mode) is not int or not 0<=mode<=7:
        raise ValueError('binary representation and three-bit mode required')
    low=request_mask & 0x7fff
    for entry in entries:
        if entry['occupied_mask'] & request_mask & 0x7fff:
            continue
        if entry['representation_word'] & 1 != representation:
            continue
        bank=entry['bank']
        entry['occupied_mask'] |= low
        entry['initialized_mask']=(entry['initialized_mask'] & 0x7fff) | (0x8000 if request_mask==65535 else 0)
        if entry['initialized_mask'] & request_mask & 0x7fff:
            bank['flags']=((bank['flags'] | (1<<26)) & ~request_mask & ~(1<<30)) & 0xffffffff
            copy_selected(bank,source,mode,request_mask)
            bank['flags'] &= ~(1<<27)
        entry['initialized_mask'] |= low
        entry['representation_word']=(entry['representation_word'] & 0xfffe) | representation
        return bank
    return None


def release_pose_bank(entries, bank, request_mask, clear_auxiliary):
    """Release low request bits by bank identity; preserve pool entry/storage.

    Evidence: CENTRAL_IMPULSE.md, Animation bank release.
    auxiliary_mask/count describe separately gated bank state, not pose count.
    clear_auxiliary(bank) supplies the unresolved native container-clear service.
    """
    if type(request_mask) is not int or not 0<=request_mask<=65535:
        raise ValueError('uint16 release mask required')
    for entry in entries:
        if entry['bank'] is not bank:
            continue
        bank['flags'] |= 1<<26
        entry['occupied_mask'] &= (~request_mask | 0x8000) & 0xffff
        if bank['auxiliary_mask'] & request_mask and bank['auxiliary_count']:
            bank['auxiliary_mask'] &= ~request_mask & 0xffff
            if bank['auxiliary_count']<2:
                clear_auxiliary(bank)
                bank['auxiliary_count']=0
            else:
                bank['auxiliary_count']-=1
        return True
    return False


def cleanup_pose_work_wrappers(output, input, release, free_storage):
    """Recovered output-then-input temporary wrapper cleanup ordering.

    Evidence: CENTRAL_IMPULSE.md, Pose-work wrapper cleanup.
    release(pool,bank,mask) and free_storage(storage) are supplied services.
    Wrapper header bit 15 suppresses storage release; pointers remain recorded.
    """
    for wrapper in (output,input):
        primary=wrapper['primary']
        if primary is not None and wrapper['flags'] & 4:
            mask=wrapper['index'] if primary['flags'] & (1<<26) else 65535
            release(wrapper['component']['pool'],primary,mask)
        alternate=wrapper['alternate']
        wrapper['primary']=None
        if alternate is not None:
            mask=wrapper['index'] if alternate['flags'] & (1<<26) else 65535
            release(wrapper['component']['pool'],alternate,mask)
        wrapper['flags'] &= ~2
        wrapper['alternate']=None
        if not wrapper['header'] & 0x8000 and wrapper['storage'] is not None:
            free_storage(wrapper['storage'])


def initialize_pool_entry(raw_slot, request_mask, representation):
    """Initialize a newly appended 16-byte slot before native bank allocation.

    Evidence: CENTRAL_IMPULSE.md, New pool entry initialization.
    Raw backing bytes are supplied because native initialization preserves bits.
    Does not grow a table, allocate a bank or establish pointer lifetime.
    """
    import struct
    if len(raw_slot)!=16 or type(request_mask) is not int or not 0<=request_mask<=65535:
        raise ValueError('16-byte slot and uint16 mask required')
    if representation not in (0,1):raise ValueError('binary representation required')
    result=bytearray(raw_slot)
    occupied,_,kind=struct.unpack_from('<HHH',result)
    low=request_mask & 0x7fff
    struct.pack_into('<HHH',result,0,(occupied & 0x8000)|low,
        low|(0x8000 if request_mask==65535 else 0),(kind & 0xfffe)|representation)
    result[8:16]=bytes(8)
    return bytes(result)


def construct_pose_bank_fields(prior_flags, default_transform):
    """Fields initialized by the bank constructor; omitted bytes stay unspecified.

    Evidence: CENTRAL_IMPULSE.md, Pose-bank constructor initialization.
    default_transform is caller-supplied, not an inferred identity/asset payload.
    """
    if type(prior_flags) is not int or not 0<=prior_flags<=0xffffffff or len(default_transform)!=32:
        raise ValueError('uint32 prior flags and 32-byte default transform required')
    return dict(flags=(prior_flags & 0x0b000000)|(1<<26),
        cleared_pointer=None,cleared_word=0,secondary_transform=bytes(default_transform),
        secondary_storage='own_inline_storage',secondary_header=32773,secondary_count=0,
        work_word=0,profile=None,data=None,auxiliary_storage=None,
        auxiliary_header=0,auxiliary_mask=0,auxiliary_count=0)


def seed_new_pose_bank(bank, profile, source, default_transform, mode, allocate_data):
    """Post-construction profile/data setup and full-copy seeding.

    Evidence: CENTRAL_IMPULSE.md, Post-construction bank seeding.
    allocate_data(size) supplies storage; allocation failure is not reconstructed.
    """
    from reference.animation_bank_copy import copy_pose_bank
    if len(default_transform)!=32:raise ValueError('32-byte default transform required')
    bank['profile']=profile
    bank['flags']=(bank['flags'] & 0xaf000000)|(1<<26)
    data=allocate_data(profile['total_size'])
    bank['flags'] &= ~(1<<27)
    if data is None or len(data)<profile['total_size']:
        raise ValueError('allocation must supply sufficient storage')
    bank['data']=data
    bank['secondary_transform']=bytes(default_transform)
    # Native secondary initialization sees constructor count zero in this scope.
    if bank['secondary_count']!=0:raise ValueError('constructed empty secondary bank required')
    bank['work_word']=0
    bank['parent_header']=bytes(default_transform)
    bank['flags']=(bank['flags']|(1<<26)) & 0xbfff0000
    result=copy_pose_bank(bank,source,mode,65535)
    bank['flags'] &= ~(1<<27)
    return result


def acquire_pose_bank(entries, request_mask, representation, mode, source, *,
                      profile, default_transform, reserve_slot, allocate_bank,
                      allocate_data, copy_selected):
    """Reuse or construct with caller-supplied allocation services.

    Evidence: CENTRAL_IMPULSE.md, Explicit-service acquisition API.
    reserve_slot(new_count) supplies 16 backing bytes. allocate_bank(448,16)
    supplies a mutable field dictionary including prior flags. No rollback:
    failure can leave an appended slot or a published, partially seeded bank.
    """
    import struct
    bank=reuse_pose_bank(entries,request_mask,representation,mode,source,copy_selected)
    if bank is not None:return dict(bank=bank,created=False)
    if len(entries)>=65535:raise ValueError('pool count overflow refused by adapter')
    slot=initialize_pool_entry(reserve_slot(len(entries)+1),request_mask,representation)
    occupied,initialized,kind=struct.unpack_from('<HHH',slot)
    entry=dict(occupied_mask=occupied,initialized_mask=initialized,
        representation_word=kind,reserved_bytes=slot[6:8],bank=None)
    entries.append(entry)
    bank=allocate_bank(448,16)
    if not isinstance(bank,dict):raise ValueError('bank allocator must supply a mutable field dictionary')
    if any(e['bank'] is bank for e in entries[:-1]):raise ValueError('new bank must not alias an existing bank')
    bank.update(construct_pose_bank_fields(bank['flags'],default_transform))
    entry['bank']=bank
    seed_new_pose_bank(bank,profile,source,default_transform,mode,allocate_data)
    return dict(bank=bank,created=True)
