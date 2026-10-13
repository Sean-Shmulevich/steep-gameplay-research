"""Ordered procedural pose adapter; scheduling and named bindings are our design.

apply(rig, local_pose, stages, state=None) returns copied state, local/model poses
and stage diagnostics. No body is accepted or modified. Stages execute in supplied
order, with hierarchy recomputed after each pose write. All stages use named bones.

Stage schemas:
 orientation: bone, target XYZW, weight, frame ('local' or 'model', required).
 landing_alignment: bone, source/target model-space vectors, elapsed, horizon,
                    minimum_horizon, optional start_marker.
 limb_target: root/middle/end bone names, requested_middle/requested_end MODEL
              positions, middle_weight, alignment_control, end_weight, mix_bias,
              optional end_axis_mask. This emits an intermediate target only.

Missing names skip a stage with diagnostics; malformed requests raise ValueError.
A limb target does NOT complete the remaining IK solve or move a bone. No original
sport mapping, landing activation or procedural layer order is claimed. Position
units follow caller's pose; clocks follow the caller-supplied landing inputs.

Evidence: docs/systems/animations/ik-solve/CLIENT_GUIDE.txt (middle-target and
weighted orientation kernels), reference/landing_pose.py, and
reference/skeleton.py. Adapter frame conversions and binding policy are ours.
"""
import copy
import math
from reference import skeleton
from . import animation, procedural
from .assets import canonical
from .math3d import vector, normalize


_IDENTITY = {'translation': [0., 0., 0.], 'quaternion_xyzw': [0., 0., 0., 1.]}


def _pose(p):
    return {'translation': vector(p['translation']),
            'quaternion_xyzw': normalize(vector(p['quaternion_xyzw'], 4))}


def _models(bones, local):
    out = [None] * len(bones)
    def visit(i):
        if out[i] is None:
            parent = bones[i]['parent_index']
            out[i] = skeleton.native_compose(_IDENTITY if parent == -1 else visit(parent), local[i])
        return out[i]
    return [visit(i) for i in range(len(bones))]


def _model_rotation_to_local(index, rotation, bones, model):
    parent = bones[index]['parent_index']
    if parent == -1:
        return normalize(rotation)
    q = model[parent]['quaternion_xyzw']
    return normalize(skeleton.qmul([-q[0], -q[1], -q[2], q[3]], rotation))


def _basis_quaternion(columns):
    # Standard rotation-matrix conversion. Columns are rotated model axes.
    m = [[columns[j][i] for j in range(3)] for i in range(3)]
    tr = m[0][0] + m[1][1] + m[2][2]
    if tr > 0:
        s = math.sqrt(tr + 1) * 2
        q = [(m[2][1]-m[1][2])/s, (m[0][2]-m[2][0])/s,
             (m[1][0]-m[0][1])/s, s/4]
    else:
        i = max(range(3), key=lambda k: m[k][k])
        j, k = (i+1) % 3, (i+2) % 3
        s = math.sqrt(max(0., 1+m[i][i]-m[j][j]-m[k][k])) * 2
        q = [0., 0., 0., (m[k][j]-m[j][k])/s]
        q[i], q[j], q[k] = s/4, (m[j][i]+m[i][j])/s, (m[k][i]+m[i][k])/s
    return normalize(q)


def _numbers(stage, fields):
    for field in fields:
        vector([stage[field]], 1)


def apply(rig, local_pose, stages, state=None):
    """Apply explicit stages; return independent JSON-compatible values."""
    # Reuse strict hierarchy validation without requiring an authored clip.
    animation.validate_resources(rig, {'validation': {'duration': 1., 'loop': False, 'channels': {}}})
    if len(local_pose) != len(rig['bones']):
        raise ValueError('pose length differs from rig')
    canonical(stages)
    canonical(state)
    bones = rig['bones']
    names = {b['name']: i for i, b in enumerate(bones)}
    local = [_pose(p) for p in local_pose]
    model = _models(bones, local)
    diagnostics = []
    for order, stage in enumerate(stages):
        kind = stage.get('kind')
        fields = {'orientation': ('bone',), 'landing_alignment': ('bone',),
                  'limb_target': ('root', 'middle', 'end')}.get(kind)
        if fields is None:
            raise ValueError('unknown procedural stage kind')
        if any(not isinstance(stage.get(f), str) for f in fields):
            raise ValueError('stage bindings must be bone names')
        missing = [stage[f] for f in fields if stage[f] not in names]
        report = {'order': order, 'kind': kind, 'missing_bindings': missing}
        diagnostics.append(report)
        if missing:
            report['status'] = 'skipped_missing_binding'
            continue
        indices = [names[stage[f]] for f in fields]
        if kind == 'orientation':
            frame = stage.get('frame')
            if frame not in ('local', 'model'):
                raise ValueError('orientation requires explicit local or model frame')
            _numbers(stage, ('weight',))
            target = normalize(vector(stage['target'], 4))
            index = indices[0]
            source = local if frame == 'local' else model
            updated = procedural.orient_bones(source, [{'index': index, 'target': target, 'weight': stage['weight']}])
            rotation = updated['local_pose'][index]['quaternion_xyzw']
            local[index]['quaternion_xyzw'] = (normalize(rotation) if frame == 'local' else
                _model_rotation_to_local(index, rotation, bones, model))
            report.update(status='applied', frame=frame, kernel=updated['diagnostics'][0])
        elif kind == 'landing_alignment':
            _numbers(stage, ('elapsed', 'horizon', 'minimum_horizon'))
            start = stage.get('start_marker', 0.)
            vector([start], 1)
            source, target = vector(stage['source']), vector(stage['target'])
            index = indices[0]
            q = model[index]['quaternion_xyzw']
            basis = [skeleton.rotate(q, axis) for axis in ((1,0,0),(0,1,0),(0,0,1))]
            aligned = procedural.landing_alignment(basis, source, target, stage['elapsed'],
                                                  stage['horizon'], stage['minimum_horizon'], start)
            rotation = _basis_quaternion(aligned['basis'])
            local[index]['quaternion_xyzw'] = _model_rotation_to_local(index, rotation, bones, model)
            report.update(status='applied', frame='model', weight=aligned['weight'])
        else:
            root, middle, end = indices
            if bones[middle]['parent_index'] != root or bones[end]['parent_index'] != middle:
                raise ValueError('limb bindings must be a direct two-segment chain')
            weights = ('middle_weight', 'alignment_control', 'end_weight', 'mix_bias')
            _numbers(stage, weights)
            mask = stage.get('end_axis_mask', [True, True, True])
            if len(mask) != 3 or any(type(x) is not bool for x in mask):
                raise ValueError('end_axis_mask needs three booleans')
            request = {key: stage[key] for key in weights}
            request.update(root=model[root]['translation'], middle=model[middle]['translation'],
                           end=model[end]['translation'], requested_middle=vector(stage['requested_middle']),
                           requested_end=vector(stage['requested_end']), end_axis_mask=mask)
            report.update(status='target_only', frame='model', result=procedural.limb_target(request),
                          pose_written=False, remaining='full limb orientation solve and downstream stages')
        model = _models(bones, local)
    return {'local_pose': local, 'model_pose': model, 'state': copy.deepcopy(state if state is not None else {}),
            'diagnostics': diagnostics, 'policy': 'caller-ordered named bindings; no original equipment selector',
            'body_mutated': False}
