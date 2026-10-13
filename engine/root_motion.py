"""Explicit-policy trajectory queries; never write physics or animation inputs.

Recovered facts: docs/systems/animations/pose-assembly/CLIENT_GUIDE.txt,
'Conditional root-motion removal': designated motion channels are not necessarily
Reference; removal is inverse(motion)*bone, endpoint displacement is
rotate(basis,end)-rotate(basis,start). Applying it to physics is unresolved.

DESIGN POLICY: caller designates a channel in engine.animation's clip schema.
SE(3) cycle accumulation, reverse playback and returned relative rotations are
our runtime choices, not decoded original loop/coupling behavior. Sampling uses
the clip's explicit sampling_policy. No asset loop flag is inferred. Quaternion
endpoints cannot reveal completed spins; preserve separately authored winding
metadata if such a future interface needs it.
"""
import copy
import math
from engine import animation
from reference import skeleton


def _identity():
    return {'translation': [0., 0., 0.], 'quaternion_xyzw': [0., 0., 0., 1.]}


def _compose(a, b):
    result = skeleton.native_compose(a, b)
    if not all(math.isfinite(x) for x in result["translation"] + result["quaternion_xyzw"]):
        raise ValueError("Trajectory transform overflow")
    return result


def _power(transform, exponent):
    """Integer rigid-transform power; logarithmic work for many cycles."""
    if exponent < 0:
        transform, exponent = skeleton.inverse(transform), -exponent
    result = _identity()
    while exponent:
        if exponent & 1:
            result = _compose(result, transform)
        exponent >>= 1
        if exponent:
            transform = _compose(transform, transform)
    return result


def _validate(clip, channel):
    if not isinstance(clip, dict) or not isinstance(clip.get('channels'), dict):
        raise ValueError('clip requires a channels mapping')
    if not isinstance(channel, str) or channel not in clip.get('channels', {}):
        raise ValueError('Explicit motion_channel must exist; Reference is not inferred')
    animation.validate_resources({'bones': [{'name': channel, 'parent_index': -1,
                                            'local_bind': _identity()}]}, {'motion': clip})
    track = clip['channels'][channel]
    # Missing transform components need an explicit baseline, not an invented bind.
    if isinstance(track, dict) and set(track) != {'translation', 'rotation'}:
        raise ValueError('Motion channel requires both translation and rotation tracks')


def _sample(clip, time, channel):
    return animation._sample(clip, time, channel, _identity())


def _trajectory(clip, time, channel, policy):
    duration = clip['duration']
    if not clip['loop']:
        phase = min(duration, max(0., time))
        return _sample(clip, phase, channel), phase, 0
    quotient = time/duration
    # Explicit resource bound: double precision cannot retain subframe information
    # for unbounded cycle counts. Reject rather than return plausible wrong motion.
    if not math.isfinite(quotient) or abs(quotient) > 2**40:
        raise ValueError('Trajectory exceeds supported cycle range (2**40)')
    cycles = math.floor(quotient)
    phase = time % duration
    if clip.get('wrap_policy') == 'inclusive' and time > 0 and phase == 0:
        phase, cycles = duration, cycles-1
    sample = _sample(clip, phase, channel)
    if policy == 'reset':
        return sample, phase, cycles
    first = _sample(clip, 0., channel)
    last = _sample(clip, duration, channel)
    cycle = _compose(last, skeleton.inverse(first))
    return _compose(_power(cycle, cycles), sample), phase, cycles


def remove_motion_from_model_pose(model_pose, motion):
    """Return copied MODEL-space bones relative to a designated motion transform.

    This is the recovered local removal formula. Do not pass local transforms:
    applying the inverse to each local bone would remove motion repeatedly.
    Preserve bone metadata; the caller owns re-propagation/local conversion.
    """
    motion = animation._pose(motion)
    inverse = skeleton.inverse(motion)
    output = []
    for bone in model_pose:
        result = copy.deepcopy(bone)
        result.update(_compose(inverse, animation._pose(bone)))
        output.append(result)
    return output


def extract_motion(clip, start_time, end_time, *, motion_channel,
                   loop_policy='accumulate', basis=None, model_pose=None,
                   in_place=False):
    """Query trajectory between arbitrary finite seconds, including reverse time.

    Returns delta_transform = inverse(start_transform)*end_transform in the
    start-motion frame; displacement is end-start in clip/model axes, optionally
    rotated by basis (XYZW). Accumulated cycles compose rigid transforms, so a
    turning loop changes the next cycle's translation direction. reset policy
    exposes the loop discontinuity. Nonloop times clamp to [0,duration].

    in_place requires caller-supplied model_pose at end_time's local phase and
    removes that phase's raw designated motion, NOT accumulated cycle motion.
    Returned pose and diagnostics are independent copies; no physical body input.
    This query describes ONE clip. Crossfade callers must retain unwrapped times
    for both clips and choose a motion-blending policy separately; animation's
    wrapped state.time loses cycle counts. Do not remove one clip's motion from a
    blended model pose. This API cannot detect that semantic mismatch.
    """
    if loop_policy not in ('accumulate', 'reset'):
        raise ValueError('Unknown loop policy')
    for time in (start_time, end_time):
        animation._finite(time, 'trajectory time')
    _validate(clip, motion_channel)
    if in_place and model_pose is None:
        raise ValueError('in_place requires explicit model_pose')
    qbasis = animation._quat([0., 0., 0., 1.] if basis is None else basis)
    start, start_phase, start_cycle = _trajectory(clip, start_time, motion_channel, loop_policy)
    end, end_phase, end_cycle = _trajectory(clip, end_time, motion_channel, loop_policy)
    delta = _compose(skeleton.inverse(start), end)
    displacement = [end['translation'][i]-start['translation'][i] for i in range(3)]
    displacement = list(skeleton.rotate(qbasis, displacement))
    if not all(math.isfinite(x) for x in displacement+delta['translation']+delta['quaternion_xyzw']):
        raise ValueError('Trajectory overflow')
    pose = None
    if model_pose is not None:
        pose = (remove_motion_from_model_pose(model_pose, _sample(clip, end_phase, motion_channel))
                if in_place else copy.deepcopy(model_pose))
    return {'delta_transform': delta, 'displacement': displacement,
            'start_transform': start, 'end_transform': end, 'model_pose': pose,
            'diagnostics': {'motion_channel': motion_channel, 'loop_policy': loop_policy,
                            'start_phase': start_phase, 'end_phase': end_phase,
                            'cycle_crossings': end_cycle-start_cycle,
                            'physics_applied': False, 'in_place': bool(in_place),
                            'crossfade_supported': False, 'requires_unwrapped_times': True,
                            'policy': 'designed trajectory accumulation; recovered conditional removal math',
                            'unresolved': ['original designated-channel binding', 'original gameplay coupling',
                                           'rotation winding beyond quaternion endpoints']}}
