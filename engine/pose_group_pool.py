"""Recovered 168-byte group pool acquisition.

Evidence: CENTRAL_IMPULSE.md, Group pool acquisition.
"""


def acquire_pose_group_storage(pool, *, read_next, allocate, grow):
    """Return an opaque storage token; no group construction or locking.

    allocate(size, alignment, 47) supplies a chunk. grow(pool, capacity) supplies
    chunk-list storage. The caller retains pool and all observed tokens.
    """
    free=pool['free_head']
    if free:
        following=read_next(free)
        pool['used']=(pool['used']+1)&0xffffffff
        pool['free_head']=following
        return free
    if not pool['current']:
        pool['chunk_index']=pool['chunk_count']
        pool['current']=allocate(pool['per_chunk']*168,pool['alignment'],47)
        capacity=pool['chunk_capacity']
        if pool['chunk_count']==capacity:
            grow(pool,((capacity*2)&0xffff) if capacity else 8)
        count=pool['chunk_count']
        pool['chunks'][count]=pool['current']
        pool['chunk_count']=(count+1)&0xffff
    index=pool['slot_index']
    result=(pool['current']+index*168)&0xffffffffffffffff
    index=(index+1)&0xffff
    pool['slot_index']=index
    if index==pool['per_chunk']:
        chunk_index=pool['chunk_index']
        if chunk_index<((pool['chunk_count']-1)&0xffffffff):
            chunk_index=(chunk_index+1)&0xffff
            pool['chunk_index']=chunk_index
            pool['current']=pool['chunks'][chunk_index]
            pool['slot_index']=0
        else:
            pool['current']=0
            pool['chunk_index']=0
            pool['slot_index']=0
    pool['used']=(pool['used']+1)&0xffffffff
    return result
