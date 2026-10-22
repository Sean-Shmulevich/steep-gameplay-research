"""Recovered work-buffer blend clock, before pose application.

Evidence: CENTRAL_IMPULSE.md, Animation work duration and saved-request handoff.
World timestep selection is external; dt and duration share native time units.
"""
import math
from reference.snow import f32


def advance_work_clock(elapsed, duration, dt, count, bank_present=True):
    if type(count) is not int or not 0 <= count <= 65535:
        raise ValueError('uint16 work count required')
    if type(bank_present) is not bool:
        raise ValueError('boolean bank presence required')
    elapsed, duration, dt = map(f32, (elapsed, duration, dt))
    if not all(math.isfinite(x) for x in (elapsed, duration, dt)):
        raise ValueError('finite timing inputs required by inspection adapter')
    if not bank_present:
        return dict(action='no_bank', elapsed=elapsed, duration=duration, count=count)
    elapsed = f32(elapsed + dt)
    if elapsed >= duration:
        return dict(action='expired', elapsed=0., duration=0., count=0)
    return dict(action='apply', elapsed=elapsed, duration=duration, count=count)


def saved_request_handoff(saved_flag):
    if type(saved_flag) is not int or not 0 <= saved_flag <= 255:
        raise ValueError('uint8 saved flag required')
    return dict(invoke=bool(saved_flag), scalar=0., context=None)
