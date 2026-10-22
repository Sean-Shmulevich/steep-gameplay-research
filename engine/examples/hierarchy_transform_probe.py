"""Synthetic parent-to-child composition through recovered numerical APIs.

Run: python3 -m engine.examples.hierarchy_transform_probe
Exact sqrt seeds and scene wiring are authored, not native replay or lock proof.
"""
import json
import math
import struct
from reference.entity_transform_update import TransformEntity, update_entity_transform
from reference.transform_composition import prepare_child_transform_packet


def pack(rows):
    return struct.pack('<16f', *(x for row in rows for x in row))


def rows(data):
    return [list(struct.unpack('<4f', data[i:i+16])) for i in range(0,64,16)]


def run_probe():
    identity = [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
    parent = TransformEntity(pack(identity), ['parent-observer'], accessor_present=True)
    cached = [r[:] for r in identity]; cached[3] = [11,12,13,1]
    children = {mode: TransformEntity(pack(cached), [f'child-{mode}']) for mode in (0,2)}
    local = [[1,0,0,0],[0,2,0,0],[0,0,3,0],[2,3,4,1]]
    incoming = [r[:] for r in identity]; incoming[3] = [7,8,9,1]
    events = []; outgoing_flags = {}
    def notify(phase, component, entity):
        events.append(dict(phase=phase, component=component,
            translation=rows(entity.transform)[3][:3], lock_depth=entity.lock_depth))
    def propagate(entity, flags):
        for mode, child in children.items():
            packet = prepare_child_transform_packet(mode, local, rows(entity.transform),
                rows(child.transform), flags, reciprocal_sqrt=lambda n: 1/math.sqrt(n))
            outgoing_flags[str(mode)] = packet['flags']
            update_entity_transform(child, pack(packet['first_transform']), thread_id=7,
                flags=packet['flags'], notify=notify, publish_cache=lambda e: None)
    update_entity_transform(parent, pack(incoming), thread_id=7, notify=notify,
        propagate=propagate, publish_cache=lambda e: None)
    return dict(evidence='synthetic_reconstruction_composition',
        seed_policy='authored exact reciprocal sqrt, not native rsqrt emulation',
        children={str(k): rows(v.transform) for k,v in children.items()},
        outgoing_flags=outgoing_flags, events=events,
        final_depths=[parent.lock_depth]+[v.lock_depth for v in children.values()])


if __name__ == '__main__':
    print(json.dumps(run_probe(), indent=2))
