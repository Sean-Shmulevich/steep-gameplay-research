"""Category22 arithmetic; LINK_SOLVER.md, Two-stage single-body constraint."""
import math
import struct
from reference.central_impulse import f32
from .pose_primary_solver import _read, _dot
from .pose_paired_angular_solver import _transform, _inverse_matrix
from .pose_paired_point_solver import _axes, _apply, _dot4


def _inputs(row, body_data, body_state, results):
    if len(row) != 256:
        raise ValueError('Complete 256-byte two-stage row required')
    body = struct.unpack_from('<H', row)[0]
    index = struct.unpack_from('<I', row, 4)[0]
    return body_data[body], body_state[body], results[index]


def _angular_apply(row, data, state, impulse):
    axes = [_read(row, off) for off in (0x80, 0x90, 0xa0)]
    torque = [_dot4(axis, impulse) for axis in axes] + [0.]
    change = _transform([_read(data, j*16) for j in range(3)], torque)
    struct.pack_into('<4f', state, 16,
                     *[f32(c+o) for c, o in zip(change, _read(state, 16))])


def prepare_pose_two_stage_row(row, *, body_data, body_state, results):
    data, state, result = _inputs(row, body_data, body_state, results)
    mass = _read(data, 48)
    axes = _axes(row, 0)
    tensor = [_read(data, j*16) for j in range(3)]
    weighted = [_transform(axes, column) for column in tensor]
    contribution = [_transform(weighted, [axes[j][i] for j in range(3)])
                    for i in range(3)]
    matrix = [[f32(f32(float(i == j)*mass[j])+contribution[i][j])
               for j in range(4)] for i in range(3)]
    inverse = _inverse_matrix(matrix)
    angular_axes = [_read(row, off) for off in (0x80, 0x90, 0xa0)]
    reciprocals = []
    for lane in (1, 2):
        axis = [column[lane] for column in angular_axes] + [0.]
        denominator = _dot(axis, _transform(tensor, axis))
        if not denominator or not math.isfinite(denominator):
            raise ValueError('Finite nonzero angular response required')
        reciprocals.append(f32(1./denominator))
    for i, column in enumerate(inverse):
        struct.pack_into('<4f', row, 0x50+i*16, *column)
    struct.pack_into('<12f', row, 0xb0,
                     0., 0., 0., 0., 0., reciprocals[0], 0., 0.,
                     0., 0., reciprocals[1], 0.)
    _apply(row, [data], [state], _read(result, 0))
    _angular_apply(row, data, state, _read(row, 0xf0))


def iterate_pose_two_stage_row(row, *, body_data, body_state, results):
    data, state, result = _inputs(row, body_data, body_state, results)
    old = _read(result, 0)
    angular = _transform(_axes(row, 0), _read(state, 16))
    speed = [f32(f32(a+v)+r) for a, v, r in
             zip(angular, _read(state, 0), _read(row, 16))]
    delta = [-x for x in _transform([_read(row, off) for off in
                                     (0x50, 0x60, 0x70)], speed)]
    updated = [f32(o+d) for o, d in zip(old, delta)]
    _apply(row, [data], [state], delta)
    angular = _transform([_read(row, off) for off in (0x80, 0x90, 0xa0)],
                         _read(state, 16))
    speed = [f32(a+r) for a, r in zip(angular, _read(row, 0xe0))]
    delta = [-x for x in _transform([_read(row, off) for off in
                                     (0xb0, 0xc0, 0xd0)], speed)]
    _angular_apply(row, data, state, delta)
    struct.pack_into('<4f', row, 0xf0,
                     *[f32(d+o) for d, o in zip(delta, _read(row, 0xf0))])
    struct.pack_into('<4f', result, 0, *updated)
