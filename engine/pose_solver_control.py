"""Recovered solver wrapper and prepare/iterate control flow.

Evidence: LINK_SOLVER.md, Solver preparation and iteration control.
"""
import struct

RESULT_SLOT='descriptor_result_slot'


def run_pose_solver(context_bytes, *, base_token, prepare, iterate):
    """Invoke supplied numerical services using captured descriptor/count state.

    Tokens identify retained storage only. Cursor.value starts at the descriptor's
    result-pointer slot, represented by RESULT_SLOT rather than a stack address.
    Services receive (descriptor, cursor) and may mutate cursor.value. Normal-return
    behavior only; no native exception unwinding or numerical solve is supplied.
    """
    if len(context_bytes)<0x17c:raise ValueError('Retained context bytes through offset178 required')
    flags=struct.unpack_from('<I',context_bytes,0x38)[0]
    special=(flags&0x18000000)==0x10000000
    count=((flags>>16)&0x7ff) if special else ((flags>>2)&0x3fff)
    saved=bytes(context_bytes[0xc:0x14])
    if special:context_bytes[0xc:0x14]=struct.pack('<2f',1,1)
    def address(offset):return (base_token+struct.unpack_from('<I',context_bytes,offset)[0])&0xffffffffffffffff
    descriptor=dict(layout=(base_token+0x40)&0xffffffffffffffff,
                    rows=address(0x16c),results=address(0x178),
                    body_data=address(0x170),body_state=address(0x174),special=special)
    cursor=dict(value=RESULT_SLOT)
    prepare(descriptor,cursor)
    if count:
        cursor['value']=RESULT_SLOT
        for _ in range(count):iterate(descriptor,cursor)
    if special:context_bytes[0xc:0x14]=saved
