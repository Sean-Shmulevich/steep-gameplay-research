"""Recovered pose-context constructor tail and aliased job binding.

Evidence: LINK_SOLVER.md, Context job construction.
"""
import struct
from collections.abc import Sequence


def initialize_pose_jobs(context, *, context_token):
    """Write the32 observed owner/index/table entries, preserving other bytes."""
    for index in range(32):
        offset = 8 + 24*index
        struct.pack_into('<Q', context, offset, context_token)
        struct.pack_into('<I', context, offset+8, index)
        struct.pack_into('<Q', context, 0x308+8*index,
                         (context_token+offset)&0xffffffffffffffff)


def initialize_pose_context_tail(context, *, context_token, mark_inactive):
    """Constructor tail after both special-group pointers have been stored.

    mark_inactive(group_token) supplies the body virtual-call/flag helper. This
    routine initializes fresh storage; it must not reset an active context.
    Gaps, the vtable and special pointers remain unchanged. Allocation and earlier
    constructor side effects are not represented here.
    """
    for offset in (0x418,0x420,0x428,0x430,0x438,0x440,0x450,0x458,
                   0x460,0x470,0x478,0x480,0x488,0x490,0x498):
        struct.pack_into('<Q',context,offset,0)
    struct.pack_into('<I',context,0x448,0)
    context[0x44c] = 1
    struct.pack_into('<I',context,0x468,0)
    mark_inactive(struct.unpack_from('<Q',context,0x408)[0])
    mark_inactive(struct.unpack_from('<Q',context,0x410)[0])
    initialize_pose_jobs(context,context_token=context_token)


class _JobArguments(Sequence):
    def __init__(self,context):
        self.context=context

    def __len__(self):
        return 32

    def __getitem__(self,index):
        if isinstance(index,slice):
            return [self[i] for i in range(*index.indices(32))]
        if index<0:index+=32
        if not 0<=index<32:raise IndexError(index)
        return struct.unpack_from('<Q',self.context,0x308+8*index)[0]


def bind_pose_jobs(context, *, context_token):
    """Return authored zero-copy views, without changing or initializing storage.

    Returns jobs, table_token and arguments for run_retained_pose_batch_pass.
    Fixed-size storage must outlive these views; do not resize its bytearray.
    The raw table can be inspected independently, including later pointer changes.
    """
    view=memoryview(context)
    if len(view)<0x408:raise ValueError('Complete retained job region required')
    return dict(jobs={(context_token+8+24*i)&0xffffffffffffffff:
                      view[8+24*i:8+24*(i+1)] for i in range(32)},
                table_token=(context_token+0x308)&0xffffffffffffffff,
                arguments=_JobArguments(view))
