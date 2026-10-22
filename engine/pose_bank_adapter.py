"""Authored pose-to-bank mapping feeding recovered regular byte-bank arithmetic.

Evidence for arithmetic: docs/reconstruction/CENTRAL_IMPULSE.md, Regular
byte-bank traversal and Typed animation channel blending. The 32-byte per-bone
layout, kind-5 translation assignment, full-mask routing, empty supplemental
records and exact-sqrt normalization seed are explicit independent-engine choices.
They do not identify the original rider's descriptor layout or hardware seed.
"""
import math
import struct
from .math3d import vector
from reference.animation_bank_blend import blend_regular_pose_bank, blend_additive_pose_bank, blend_masked_pose_bank


def blend_pose(first, second, weight, *, normalization, operation="regular", mask_bytes=None):
    if operation not in ("regular", "additive", "masked"):
        raise ValueError("Unknown byte pose operation")
    if normalization != 'authored_exact_sqrt':
        raise ValueError('Explicit authored_exact_sqrt normalization required')
    stride = 36 if operation == 'masked' else 32
    if len(first) != len(second) or len(first) > 65536//stride:
        raise ValueError('Matching poses within uint16 descriptor storage required')
    if operation == 'masked':
        if (not isinstance(mask_bytes, list) or len(mask_bytes) != len(first) or
                any(type(v) is not int or not 0<=v<=255 for v in mask_bytes)):
            raise ValueError('One explicit byte weight per bone required')
    elif mask_bytes is not None:
        raise ValueError('Mask bytes require masked operation')
    if type(weight) not in (int, float) or not math.isfinite(weight):
        raise ValueError('Finite blend weight required')
    descriptors = []
    for i in range(len(first)):
        descriptors.append({'offset': i*stride, 'kind': 5, 'key': i})
        if operation == 'masked':
            descriptors.append({'offset': i*stride+32, 'kind': 0, 'key': i})
        descriptors.append({'offset': i*stride+16, 'kind': 6, 'key': i})
    profile = dict(group_count=1, channel_count=len(descriptors),
                   group_words=[0]+[len(descriptors)]*6, descriptors=descriptors)
    def pack(pose):
        data = bytearray()
        for i, bone in enumerate(pose):
            translation = vector(bone['translation'])
            rotation = vector(bone['quaternion_xyzw'], 4)
            data.extend(struct.pack('<8f', *translation, 0., *rotation))
            if operation == 'masked':
                data.extend(bytes([mask_bytes[i], 0, 0, 0]))
        return dict(data=data, profile=profile, flags=0, records=[])
    a, b = pack(first), pack(second)
    destination = dict(data=bytearray(a['data']), profile=profile, flags=0, records=[])
    def seed(length_squared):
        if not math.isfinite(length_squared) or length_squared <= 0:
            raise ValueError('Positive finite normalization length required')
        return 1/math.sqrt(length_squared)
    if operation == 'regular':
        visits = blend_regular_pose_bank(destination, a, b, weight, 0, 65535,
                                        reciprocal_sqrt=seed)
    elif operation == 'masked':
        visits = blend_masked_pose_bank(destination, a, b, weight, 0, 65535,
                                       weight_mode=1, reciprocal_sqrt=seed)
    else:
        # Explicit swap=True routes first=base, second=delta. Native default
        # reverses those sources; do not silently inherit it for this graph.
        visits = blend_additive_pose_bank(destination, a, b, weight, 0, 65535,
                                         swap=True, reciprocal_sqrt=seed)

    result = []
    for i in range(len(first)):
        lanes = struct.unpack_from('<8f', destination['data'], i*stride)
        result.append(dict(translation=list(lanes[:3]), quaternion_xyzw=list(lanes[4:])))
    return result, dict(operation=operation, sources=['base', 'delta'] if operation=='additive' else ['base','overlay'], visits=visits, flags=destination['flags'],
                       layout='authored kind5 translation / kind6 rotation',
                       stride=stride, mask_bytes=mask_bytes.copy() if mask_bytes is not None else None,
                       normalization=normalization,
                       evidence='recovered byte arithmetic with authored pose mapping')
