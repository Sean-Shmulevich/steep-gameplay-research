"""Recovered initialization of the snow normal-Z arccosine lookup.

Evidence: CENTRAL_IMPULSE.md, Normal-Z angle table initialization.
Native vector/scalar acos implementations remain caller-supplied services.
"""
from reference.decay_table import build, sample_arguments
from reference.central_impulse import f32
from reference.runtime_curve import evaluate


def build_slope_angle_table(vector_acos, scalar_acos):
    """Sample 64 four-lane batches and one scalar endpoint; no bundled table.

    Using platform math.acos is a labeled approximation, not native bit fidelity.
    Native initializers use [-1,1] and relative padding float32(0.0005).
    """
    arguments=sample_arguments(-1.,1.)
    samples=[]
    for i in range(0,256,4):
        values=list(vector_acos(arguments[i:i+4]))
        if len(values)!=4:raise ValueError('Four acos lanes required')
        samples.extend(f32(x) for x in values)
    samples.append(f32(scalar_acos(arguments[256])))
    return build(samples,low=-1.,high=1.,padding=.0005)


def evaluate_slope_angle(normal_z, table):
    """Evaluate recovered padded table indexing; do not replace with acos(z)."""
    return evaluate(normal_z,**table)
