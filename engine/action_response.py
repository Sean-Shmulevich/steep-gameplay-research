"""Compose the observed ramp-then-diagonal chain with explicit dependencies.

Evidence: MOTION_MEMBERSHIP_OBSERVATION.md, Composed directional response.
This does not query devices, select the active action, or run motion ingestion.
"""
import struct
from .action_axis_ramp import ramp_axes, f32
from .action_diagonal import correct_diagonal
from .action_processor_chain import process_chain


def directional_response(vector, states, *, previous_clock, duration, axis_mode,
                         start_ticks, end_ticks, curve, ramp_enabled=True,
                         diagonal_enabled=True, global_gate=True,
                         configuration_available=True):
    """Return detached state, clock, output and per-stage publication receipts.

    Stage enable flags use the existing chain's bool-or-None contract. The
    ramp's internal gates are independent. Clock reads are caller-supplied.
    """
    if len(vector) != 4:
        raise ValueError('four lanes required')
    raw = struct.pack('<4f', *(f32(v) for v in vector))
    state = tuple(states)
    clock = f32(previous_clock)
    ramp = None
    def evaluate(index, payload):
        nonlocal ramp, state, clock
        values = struct.unpack('<4f', payload)
        if index == 0:
            ramp = ramp_axes(values, state, duration=duration, axis_mode=axis_mode,
                             previous_clock=clock, start_ticks=start_ticks,
                             end_ticks=end_ticks, curve=curve, active=global_gate,
                             configuration_available=configuration_available)
            state, clock = ramp['states'], ramp['clock']
            values = ramp['output']
        else:
            values = correct_diagonal(values)
        return struct.pack('<4f', *values)
    chain = process_chain(raw, (ramp_enabled, diagonal_enabled), evaluate)
    return dict(output=struct.unpack('<4f', chain.output), states=state,
                clock=clock, curve_inputs=() if ramp is None else ramp['curve_inputs'],
                stages=chain.stages)
