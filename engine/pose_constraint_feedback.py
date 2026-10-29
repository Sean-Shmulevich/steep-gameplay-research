"""Recovered pose result feedback; LINK_SOLVER.md, Pose constraint feedback."""
import struct

# Exact float32 loaded by the inspected feedback routine.
UNBOUNDED_THRESHOLD = struct.unpack('<f', bytes.fromhex('a5d46853'))[0]


def feedback_pose_constraints(context, slots, *, constraints, bodies, metadata,
                              get_kind):
    """Copy solved result bits into eligible kind2 constraints in slot order.

    All storage uses retained native layouts and opaque identity maps. get_kind
    is the virtual type query, not guessed from data. The slot is reloaded after
    that call. Result indices select 16-byte records relative to context178.
    Unsupported indices/storage raise ordinary Python errors; no rollback occurs.
    """
    for i in range(len(slots)):
        token = slots[i]
        record = constraints[token]
        def disabled(body_token):
            meta_token = struct.unpack_from('<Q', bodies[body_token], 0x30)[0]
            return metadata[meta_token][0x52] & 1
        first, second = struct.unpack_from('<2Q', record, 8)
        if disabled(first) or (second and disabled(second)):
            continue
        if get_kind(token) != 2:
            continue
        record = constraints[slots[i]]
        packed = (all(not UNBOUNDED_THRESHOLD > struct.unpack_from('<f',record,off)[0]
                      for off in (0xfc,0x110,0x124)) and
                  all(struct.unpack_from('<I',record,off)[0] == 0
                      for off in (0xf0,0x104,0x118)))
        def copy(index, source_lane, destination):
            result_base = struct.unpack_from('<I',context,0x178)[0]
            source = result_base + index*16 + source_lane*4
            if source+4 > len(context):
                raise ValueError('Complete retained result storage required')
            record[destination:destination+4] = context[source:source+4]
        if packed:
            index = struct.unpack_from('<I',record,0x190)[0]
            if index != 0xffffffff:
                for lane in range(3):copy(index,lane,0x19c+lane*4)
        else:
            for lane in range(3):
                index = struct.unpack_from('<I',record,0x190+lane*4)[0]
                if index != 0xffffffff:copy(index,0,0x19c+lane*4)
