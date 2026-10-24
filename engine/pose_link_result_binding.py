"""Recovered result-index publication and conditional cache seeding.

Evidence: CENTRAL_IMPULSE.md, Link result binding and cache seeding.
"""
import struct


def bind_pose_link_results(context, payload_row, solver_rows):
    """Publish three sequential uint32 result indices; row0 is cached feedback.

    Mutable payload_row has64 bytes and solver_rows contains three retained row
    bytearrays. The caller owns row allocation/layout and physical coefficients.
    """
    if len(payload_row)!=64 or len(solver_rows)!=3 or any(len(r)<8 for r in solver_rows):
        raise ValueError('One payload row and three retained solver rows required')
    indices=[]
    for i,row in enumerate(solver_rows):
        index=context['result_count']
        context['result_count']=(index+1)&0xffffffff
        struct.pack_into('<I',row,4,index)
        if i==0:struct.pack_into('<I',payload_row,0x34,index)
        indices.append(index)
    return indices


def seed_pose_link_result(context, payload_row, linked_row, *, primary_index, gate_bits):
    """Publish primary result reference and conditionally broadcast cached bits.

    Native UCOMISS/JNE admits zero or unordered comparison with zero. No physical
    coefficient meaning is assigned to gate_bits. Caller supplies result storage.
    """
    if len(payload_row)!=64 or len(linked_row)<0x54:
        raise ValueError('Retained payload and linked solver row required')
    if type(gate_bits) is not int or not 0<=gate_bits<=0xffffffff:
        raise ValueError('Raw float32 gate bits required')
    struct.pack_into('<I',linked_row,0x50,primary_index)
    magnitude=gate_bits&0x7fffffff
    seed=magnitude==0 or magnitude>0x7f800000
    if seed:
        result=context['result_rows'][primary_index]
        if len(result)!=16:raise ValueError('Complete result row required')
        result[:]=payload_row[0x30:0x34]*4
    return seed
