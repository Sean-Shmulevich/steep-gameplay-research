"""Inspect constructor-default histories without game files or a live process.

Run: python3 -m engine.examples.configured_history_probe
Basis, conversion mode, clock and input sequence are explicit synthetic choices.
"""
import json
import math
import struct
from engine.action_history_curve import (
    history_curve_config, evaluate_history_curve, initial_history_snapshot,
)
from engine.action_history_features import update_mode3_history


def inspect():
    rows = []
    for channel in (0, 1):
        config = history_curve_config(channel, alternate_center=False)
        state = initial_history_snapshot(channel, alternate_center=False)
        for now, angle in enumerate((30., None, 30.), start=100):
            raw = bytes(16) if angle is None else struct.pack(
                '<4f', math.sin(math.radians(angle)), math.cos(math.radians(angle)), 0, 0)
            result = update_mode3_history(state, raw, now=now,
                primary=(0,1,0,0), secondary=(1,0,0,0),
                curve=lambda value: evaluate_history_curve(value, config['points']))
            state = result['snapshot']
            rows.append(dict(channel=channel, opaque_timestamp=now,
                input_angle_degrees=angle, curve_input=result['curve_input'],
                curve_output_radians=result['curve_output'],
                mapped_direction=struct.unpack_from('<4f', state, 0x240),
                recent_times=struct.unpack_from('<3Q', state)))
    return dict(scope='Synthetic inputs with constructor-derived curves and explicit mode-3 basis',
                game_process=False, numerical_policy='Derived scalar normalization and trig',
                observations=rows)


if __name__ == '__main__':
    print(json.dumps(inspect(), indent=2))
