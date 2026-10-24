"""Recovered solver storage layout and retained-buffer initialization.

Evidence: LINK_SOLVER.md, Solver category layout and count initialization.
"""
import struct

STRIDE_UNITS=(7,8,7,8,13,16,7,8,7,8,8,11,5,5,5,6,6,7,4,5,5,6,16,22,57)
MASK=0xffffffff


def plan_pose_solver_layout(row_counts,body_count):
    """Plan25 category ranges using original uint32 arithmetic and uint16 body count."""
    if len(row_counts)!=25:raise ValueError('Exactly25 category counts required')
    if any(type(v) is not int or not 0<=v<=MASK for v in [*row_counts,body_count]):
        raise ValueError('Raw uint32 counts required')
    starts=[];units=0;total=0
    for count,stride in zip(row_counts,STRIDE_UNITS):
        starts.append(units);units=(units+count*stride)&MASK;total=(total+count)&MASK
    def align(value):return ((value+15)&MASK)&0xfffffff0
    body_slots=body_count&0xffff
    body_data=(0x190+align((units<<4)&MASK))&MASK
    body_state=(body_data+align(body_slots<<6))&MASK
    results=(body_state+align(body_slots<<5))&MASK
    result_bytes=(total<<4)&MASK
    size=(results+align(result_bytes))&MASK
    return dict(category_starts=starts,row_counts=list(row_counts),body_slots=body_slots,
                rows_offset=0x190,body_data_offset=body_data,body_state_offset=body_state,
                results_offset=results,result_bytes=result_bytes,size=size)


def initialize_pose_solver_storage(storage,row_counts,body_count):
    """Initialize caller-owned storage, matching the native retained-buffer branch.

    Allocation/release and overflow-corrupted layouts are not supplied. Preserve
    prior row/body bytes and untouched header fields; only result storage is zeroed.
    """
    plan=plan_pose_solver_layout(row_counts,body_count)
    exact=0x190+16*sum(c*s for c,s in zip(row_counts,STRIDE_UNITS))+96*plan['body_slots']+16*sum(row_counts)
    if exact>MASK or len(storage)<exact:raise ValueError('Sufficient nonwrapping retained storage required')
    struct.pack_into('<25I',storage,0x40,*plan['category_starts'])
    storage[0xa4:0x108]=bytes(100)
    struct.pack_into('<25I',storage,0x108,*row_counts)
    storage[0xc:0x14]=bytes(8);storage[0x30:0x38]=bytes(8)
    flags=struct.unpack_from('<I',storage,0x38)[0]
    struct.pack_into('<I',storage,0x38,(flags&0x98000003)|0x18000000)
    struct.pack_into('<5I',storage,0x16c,plan['rows_offset'],plan['body_data_offset'],plan['body_state_offset'],plan['results_offset'],plan['size'])
    struct.pack_into('<I',storage,0x180,0)
    start=plan['results_offset'];storage[start:start+plan['result_bytes']]=bytes(plan['result_bytes'])
    return plan
