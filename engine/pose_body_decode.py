"""Physical-body serialized fields and ordered setter dispatch.

Evidence: LINK_SOLVER.md, Physical-body serialized state.
"""
import struct
from .pose_block_reader import select_pose_block, read_pose_block_bytes


def deserialize_physical_pose_body(body, reader, *, buffers, read_base,
                                   set_scalar, set_vector, set_parameters):
    """Load raw words, motion and optional settings after supplied base loading.

    Services take body plus raw little-endian bytes: set_scalar(body, bytes4),
    set_vector(body, bytes12), set_parameters[index](body, bytes4). Keeping raw
    bytes preserves NaNs and signed zero without assigning unproved units.
    """
    read_base(body, reader)
    def select(tag, size, required):
        return select_pose_block(reader, tag, size, 3, required, buffers=buffers)
    def read(size):
        return read_pose_block_bytes(reader, size, buffers=buffers)
    if select(0x1001, 92, True):
        offsets = list(range(0x120, 0x134, 4))
        offsets += [start + component * 4 for start in range(0x140, 0x1a0, 16)
                    for component in range(3)]
        for offset in offsets:
            body[offset:offset + 4] = read(4)
        cursor, end = struct.unpack_from('<QQ', reader, 0x10)
        body[0x1c8] = read(1)[0] if cursor + 1 <= end else 0
    if select(0x1002, 24, True):
        for offset in range(0x1a0, 0x1b8, 4):
            body[offset:offset + 4] = read(4)
    if select(0x1003, 16, False):
        scalar = read(4)
        vector = read(12)
        set_scalar(body, scalar)
        set_vector(body, vector)
    if select(0x1004, 12, False):
        parameters = [read(4) for _ in range(3)]
        for index, value in enumerate(parameters):
            set_parameters[index](body, value)
