"""Byte-storage bridge for recovered owner-bank scale removal.

Evidence: CENTRAL_IMPULSE.md, Byte-bank scale storage bridge.
Primary records share the channel data buffer. Secondary records use a separate
pointer and may alias it. All views write through, retaining overlap order.
"""
import struct
from reference.skeleton_parent_transform import remove_owner_bank_scale


class _RecordView:
    def __init__(self, data, offset):
        self.data, self.offset = data, offset

    def __getitem__(self, lane):
        return struct.unpack_from('<f', self.data, self.offset+4*lane)[0]

    def __setitem__(self, lane, value):
        struct.pack_into('<f', self.data, self.offset+4*lane, value)


def remove_owner_byte_bank_scale(wrapper, bank, get_owner_scalar):
    """Remove scale using bank.profile.primary_count and secondary_count.

    data and secondary_data are mutable byte buffers (memoryviews may alias).
    Only visited records require storage. Existing wrapper schema request_byte
    is retained. Bounds checks are adapter safeguards, not native recovery.
    """
    if not wrapper['request_byte'] & 2:
        return bank
    # Build views lazily: native tolerance/count gates may skip absent storage.
    class Records:
        def __init__(self, key):self.key=key
        def __getitem__(self, index):
            data=bank[self.key];offset=index*32
            if offset<0 or offset+16>len(data):
                raise ValueError('scale lanes outside supplied byte storage')
            return _RecordView(data,offset)
    class Layout(dict):
        def __getitem__(self,key):
            if key=='primary_count':return bank['profile']['primary_count']
            if key=='secondary_count':return bank['secondary_count']
            return super().__getitem__(key)
    layout=Layout(primary_records=Records('data'),secondary_records=Records('secondary_data'))
    remove_owner_bank_scale(wrapper,layout,get_owner_scalar)
    return bank
