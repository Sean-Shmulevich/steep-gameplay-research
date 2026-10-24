"""Read-only provider join; see CENTRAL_IMPULSE.md, Guarded provider observation.

Fresh dispatcher identity and process/image verification belong to the caller.
Equal endpoint reads detect some changes; they do not pin objects or stop workers.
"""
import struct
from .scheduler_observation import _address


def capture_markup_provider(readv, dispatcher, image_base, image_size, guards):
    """Return bounded scalar records, with all acquired bytes rechecked.

    No nested pairs, animation payloads, heap addresses or game calls are returned.
    At most 64 records are accepted. Rejection publishes no partial observation.
    """
    _address(dispatcher, 0x40)
    if type(image_size) is not int or not 0x2909850 <= image_size <= 0x40000000:
        raise ValueError('invalid image size')
    _address(image_base, image_size)
    retained = list(guards)
    if not 1 <= len(retained) <= 30:
        raise ValueError('fresh external identity guards required')
    for address, expected in retained:
        if type(expected) is not bytes or not 1 <= len(expected) <= 256:
            raise ValueError('invalid guard')
        _address(address, len(expected))

    def read(plan):
        result = []
        for start in range(0, len(plan), 32):
            batch = plan[start:start+32]
            for address, size in batch:
                _address(address, size)
            blocks = list(readv(batch))
            if len(blocks) != len(batch) or any(type(b) is not bytes or len(b) != n
                                               for b, (_, n) in zip(blocks, batch)):
                raise ValueError('incomplete provider read')
            result.extend(blocks)
        return result

    def check():
        if read([(a,len(b)) for a,b in retained]) != [b for _,b in retained]:
            raise ValueError('provider identity or content changed')

    def keep(address, size):
        value = read([(address,size)])[0]
        retained.append((address,value))
        return value

    def pointer(address):
        value = struct.unpack('<Q',keep(address,8))[0]
        _address(value)
        return value

    check()
    owner = pointer(dispatcher+0x38)
    interface = pointer(owner+0xb0)
    table = pointer(interface)
    if table != image_base+0x2909790:
        raise ValueError('unexpected provider table')
    target = pointer(table+0xb8)
    if target != image_base+0x12f2d20:
        raise ValueError('unexpected query target')
    attachment_raw = keep(interface+0x20,8)
    attachment = struct.unpack('<Q',attachment_raw)[0]
    rows = []
    relative = None
    if attachment:
        _address(attachment,0x88)
        graph = pointer(attachment+0x80)
        header = pointer(graph+0x1a10)
        data, flags = struct.unpack('<QQ',keep(header,16))
        count = flags & 0x1fffffff
        if count > 64:
            raise ValueError('oversized provider collection')
        relative = bool(flags & (1 << 62)) and not flags & (1 << 61)
        data = (header+data) & ((1 << 64)-1) if relative else data
        if count:
            _address(data,count*0x68)
        for index in range(count):
            key, extra, start, end, row_flags = struct.unpack('<IIIIB',keep(data+index*0x68+0x50,17))
            rows.append(dict(index=index,key=key,scalar54_bits=extra,
                             start_bits=start,end_bits=end,flags=row_flags))
    check()
    return dict(provider_table_rva=table-image_base,query_target_rva=target-image_base,
                attachment_present=bool(attachment),relative_records=relative,
                records=rows,endpoint_rechecked=True,atomic=False,
                pairs_observed=False,callback_execution_proved=False)
