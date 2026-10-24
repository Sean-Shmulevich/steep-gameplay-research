"""Recovered per-axis pose spring coefficient conversion.

Evidence: CENTRAL_IMPULSE.md, Pose spring coefficient conversion.
Mass-like inputs are resolved caller values, not inferred rider mass.
"""
import math
from reference.central_impulse import f32


def pose_spring_coefficients(mass_like, frequencies, damping_ratios):
    """Return record order [input Y, input Z, input X] with enabled flags.

    Finite nonnegative mass-like values and finite products only. No force
    application, solver integration or ownership/lifetime behavior is provided.
    """
    if any(len(v)!=3 for v in (mass_like,frequencies,damping_ratios)):
        raise ValueError('Three components required for each input')
    masses,freqs,ratios=[list(map(f32,v)) for v in (mass_like,frequencies,damping_ratios)]
    if not all(math.isfinite(x) for v in (masses,freqs,ratios) for x in v) or any(m<0 for m in masses):
        raise ValueError('Finite inputs and nonnegative mass-like values required')
    records=[]
    for index in (1,2,0):
        m,f,z=masses[index],freqs[index],ratios[index]
        raw=f32(f32(f32(f*m)*f)*f32(39.47842025756836))
        if not math.isfinite(raw):raise ValueError('Finite stiffness product required')
        stiffness=min(f32(999999995904.),max(f32(1.0000000116860974e-7),raw))
        root_input=f32(stiffness*m)
        if not math.isfinite(root_input):raise ValueError('Finite square-root argument required')
        damping=f32(f32(math.sqrt(root_input))*f32(z+z))
        if not math.isfinite(damping):raise ValueError('Finite damping required')
        records.append({'source_axis':index,'disabled':0,'stiffness':stiffness,'damping':damping})
    return records
