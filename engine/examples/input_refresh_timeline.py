"""Synthetic ordering probe joining known cache publication and refresh kernels.

The chosen publish/refresh sequence is a harness input, not measured game cadence.
Timer values are opaque; no original frame or device sample generation is inferred.
"""
import json
import struct
from engine.action_cache_exchange import CACHE_SPAN
from engine.action_cache_directions import publish_derived_and_stamp
from engine.vector_action_refresh import refresh_vector_action


def run_probe():
    root = bytes(CACHE_SPAN)
    action = bytes(192)
    observations = []

    def refresh(label):
        nonlocal action
        result = refresh_vector_action(action, owner_suppressed=False,
            configuration_available=True, kind=0, lane_mode=0,
            ownership_blocked=lambda *_: False,
            read_vector=lambda index: root[0x1f0+16*index:0x200+16*index],
            read_scalar=lambda index: root[0x168+4*index:0x16c+4*index],
            processing_enabled=False, process=None)
        action = result['snapshot']
        observations.append(dict(event=label, sample_x=struct.unpack_from('<f', action, 0x60)[0],
            cache_clock=struct.unpack_from('<Q', root, 0x58)[0],
            positive_x_press_stamp=struct.unpack_from('<Q', root, 0x7d8+3*8)[0],
            sample_generation_established=result['publication']['sample_generation_established']))

    # Explicit synthetic schedule: a refresh before each publication, plus a
    # final refresh. This does not establish one-frame latency in the game.
    for index, (value, timer) in enumerate(((.25, 100), (.25, 200), (.75, 300), (.875, 400))):
        refresh(f'before publication {index+1}')
        selected = bytearray(CACHE_SPAN)
        struct.pack_into('<4f', selected, 0x1f0, value, 0, 0, 0)
        root = publish_derived_and_stamp(root, bytes(selected), timer)
    refresh('after final publication')
    return dict(scope='Synthetic explicit event order; known publication/refresh kernels, bypass processor, stable snapshots, no native polling or scheduler cadence.',
                observations=observations)


if __name__ == '__main__':
    print(json.dumps(run_probe(), indent=2))
