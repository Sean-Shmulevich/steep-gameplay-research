"""Initializer-installed component bounds, not a snapshot of live globals.

Evidence: docs/systems/body/pose-follower/evidence.md, P3; and
docs/reconstruction/CENTRAL_IMPULSE.md, Shared velocity clamp initializer.
The snow correction shares the linear globals with the physical pose follower.
Angular bounds do not establish player trick limits or main-body actuation.
"""


def initialized_velocity_limits():
    """Return fresh XYZ bound arrays from the decoded native initializer.

    Values are exact float32 literals. Invocation, later writers and live
    configuration remain external. These are component bounds, not vector norms.
    Callers must explicitly select these defaults instead of observed bounds.
    """
    return {
        'linear_lower': [-120.0] * 3,
        'linear_upper': [120.0] * 3,
        'angular_lower': [-100.53096771240234] * 3,
        'angular_upper': [100.53096771240234] * 3,
    }
