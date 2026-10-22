"""Clock-object selection semantics, excluding registry ownership effects.

Evidence: MOTION_MEMBERSHIP_OBSERVATION.md, Ramp clock object selection.
Objects/identities are caller-supplied uint64 values. No unit or lifetime claim.
"""


def select_ramp_clock(*, manager_present, context_present, context_index,
                      override, candidates, fallback, excluded, identity):
    """Select an object; candidates and override are (object, active) pairs.

    identity(object) supplies the registry identity used by the original's
    exclusion membership test. Registry reference acquisition/release is not
    reproduced. A zero result means no selected object.
    """
    if not manager_present:
        return 0
    if context_present and context_index != -1:
        obj, active = override
        if active and obj:
            return obj
    for obj, active in candidates:
        if active and obj and identity(obj) not in excluded:
            return obj
    return fallback if identity(fallback) not in excluded else 0
