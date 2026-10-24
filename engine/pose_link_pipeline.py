"""Connected recovered reduction and paired-frame payload update.

Evidence: CENTRAL_IMPULSE.md, Connected record-group payload processing.
"""
from .pose_link_selection import reduce_pose_link_records
from .pose_link_update import update_pose_link_payload


def paired_entry_flag(first, second):
    """Raw entry+0x44 bytes must both contain bits2 and4; meaning unresolved."""
    if any(type(v) is not int or not 0<=v<=255 for v in (first,second)):
        raise ValueError('Two raw entry flag bytes required')
    return first&0x14==0x14 and second&0x14==0x14


def process_pose_link_record_group(previous, records, *, first_frame, second_frame,
                                   first_index, second_index, entry_flag):
    """Process one reached, nonempty key group in copied independent storage.

    Grouping, payload acquisition and the producer of entry_flag remain external.
    Native code mutates storage; this interface returns immutable byte snapshots.
    """
    if type(entry_flag) is not bool:raise ValueError('Explicit resolved entry flag required')
    if len(previous)!=288 or not records or any(len(r)!=48 for r in records):
        raise ValueError('288-byte payload and nonempty 48-byte record group required')
    storage=bytearray(previous);storage[0x114]=(storage[0x114]&0xfe)|int(entry_flag)
    collection=dict(count=len(records),slots=[bytes(r) for r in records])
    selection=reduce_pose_link_records(collection)
    payload=update_pose_link_payload(storage,collection['slots'][:collection['count']],
        first_frame=first_frame,second_frame=second_frame,
        first_index=first_index,second_index=second_index)
    return dict(payload=payload,records=collection['slots'],count=collection['count'],
                selected_indices=selection['indices'] if selection else list(range(len(records))),
                selection=selection)
