"""Category23 arithmetic; LINK_SOLVER.md, Two-stage paired constraint."""
import math
import struct
from reference.central_impulse import f32
from .pose_primary_solver import _read, _dot
from .pose_paired_angular_solver import _transform, _inverse_matrix
from .pose_paired_point_solver import _dot4


def _inputs(row, body_data, body_state, results):
    if len(row) != 352:
        raise ValueError('Complete 352-byte paired two-stage row required')
    a, b, index = struct.unpack_from('<HHI', row)
    return [body_data[a], body_data[b]], [body_state[a], body_state[b]], results[index]


def _axes(row, endpoint, angular=False):
    start = (0x80 if angular else 0x20) if endpoint == 0 else (0x130 if angular else 0x100)
    return [_read(row, start+j*16) for j in range(3)]


def _apply(row, data, states, impulse, angular=False):
    for endpoint, (d, s) in enumerate(zip(data, states)):
        if not angular:
            change = [f32(m*p) for m, p in zip(_read(d, 48), impulse)]
            old = _read(s, 0)
            struct.pack_into('<4f', s, 0, *[f32(c+o) if endpoint == 0 else f32(o-c)
                                          for c, o in zip(change, old)])
        torque = [_dot4(axis, impulse) for axis in _axes(row, endpoint, angular)] + [0.]
        change = _transform([_read(d, j*16) for j in range(3)], torque)
        struct.pack_into('<4f', s, 16, *[f32(c+o) for c, o in zip(change, _read(s, 16))])


def prepare_pose_paired_two_stage_row(row, *, body_data, body_state, results):
    data, states, result = _inputs(row, body_data, body_state, results)
    matrix = [[f32(float(i == j)*_read(data[0], 48)[j]) for j in range(4)]
              for i in range(3)]
    denominators = []
    for endpoint, d in enumerate(data):
        axes = _axes(row, endpoint)
        tensor = [_read(d, j*16) for j in range(3)]
        if endpoint:
            mass = _read(d, 48)
            matrix = [[f32(f32(float(i == j)*mass[j])+matrix[i][j])
                       for j in range(4)] for i in range(3)]
        weighted = [_transform(axes, column) for column in tensor]
        contribution = [_transform(weighted, [axes[j][i] for j in range(3)])
                        for i in range(3)]
        matrix = [[f32(matrix[i][j]+contribution[i][j]) for j in range(4)]
                  for i in range(3)]
        angular_axes = _axes(row, endpoint, True)
        response = []
        for lane in (1, 2):
            axis = [column[lane] for column in angular_axes] + [0.]
            response.append(_dot(axis, _transform(tensor, axis)))
        denominators.append(response)
    inverse = _inverse_matrix(matrix)
    reciprocals = []
    for a, b in zip(*denominators):
        denominator = f32(a+b)
        if not denominator or not math.isfinite(denominator):
            raise ValueError('Finite nonzero paired angular response required')
        reciprocals.append(f32(1./denominator))
    for i, column in enumerate(inverse):
        struct.pack_into('<4f', row, 0x50+i*16, *column)
    struct.pack_into('<12f', row, 0xb0,
                     0.,0.,0.,0., 0.,reciprocals[0],0.,0., 0.,0.,reciprocals[1],0.)
    _apply(row, data, states, _read(result, 0))
    _apply(row, data, states, _read(row, 0xf0), angular=True)


def iterate_pose_paired_two_stage_row(row, *, body_data, body_state, results):
    data, states, result = _inputs(row, body_data, body_state, results)
    old = _read(result, 0)
    first, second = [_transform(_axes(row, i), _read(s, 16)) for i, s in enumerate(states)]
    v1, v2 = [_read(s, 0) for s in states]
    speed = [f32(f32(f32(f32(a+v)-u)+b)+r) for a, v, u, b, r in
             zip(first, v1, v2, second, _read(row, 16))]
    delta = [-x for x in _transform([_read(row, off) for off in (0x50,0x60,0x70)], speed)]
    updated = [f32(o+d) for o, d in zip(old, delta)]
    _apply(row, data, states, delta)
    first, second = [_transform(_axes(row, i, True), _read(s, 16)) for i, s in enumerate(states)]
    speed = [f32(f32(b+a)+r) for a, b, r in zip(first, second, _read(row, 0xe0))]
    delta = [-x for x in _transform([_read(row, off) for off in (0xb0,0xc0,0xd0)], speed)]
    _apply(row, data, states, delta, angular=True)
    struct.pack_into('<4f', row, 0xf0, *[f32(o+d) for o, d in zip(_read(row, 0xf0), delta)])
    struct.pack_into('<4f', result, 0, *updated)
