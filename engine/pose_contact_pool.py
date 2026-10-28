"""288-byte payload pool slot acquisition; LINK_SOLVER.md, Contact payload pool."""
import struct


def acquire_payload_slot(pool, payloads, *, allocate_page, reserve_pages):
    """Recover pool slot selection; allocator and page-table storage are services.

    Returned integer identities support page-base + 288 * slot. The caller owns
    payload initialization and synchronization. Existing payload bytes are retained.
    """
    if pool['free_head']:
        identity=pool['free_head']
        pool['free_head']=struct.unpack_from('<Q',payloads[identity])[0]
        pool['active_count']=(pool['active_count']+1)&0xffffffff
        return identity
    if not pool['current_page']:
        pool['page_index']=pool['page_count']
        pool['current_page']=allocate_page(pool['slots_per_page']*288,pool['alignment'],0x2c)
        if not pool['current_page']:
            raise ValueError('Successful page allocation required')
        if pool['page_count']==pool['page_capacity']:
            capacity=pool['page_capacity']*2 if pool['page_capacity'] else 8
            if capacity>0xffff:raise ValueError('Page-capacity overflow outside supported domain')
            reserve_pages(pool,capacity)
        pool['pages'][pool['page_count']]=pool['current_page']
        pool['page_count']=(pool['page_count']+1)&0xffff
    identity=pool['current_page']+pool['slot_index']*288
    pool['slot_index']=(pool['slot_index']+1)&0xffff
    if pool['slot_index']==pool['slots_per_page']:
        if pool['page_index']<pool['page_count']-1:
            pool['page_index']=(pool['page_index']+1)&0xffff
            pool['current_page']=pool['pages'][pool['page_index']]
        else:
            pool['current_page']=0
            pool['page_index']=0
        pool['slot_index']=0
    pool['active_count']=(pool['active_count']+1)&0xffffffff
    return identity
