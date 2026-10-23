#!/usr/bin/env python3
"""Decode the authored five-counter execution observer diagnostic, not game data."""
import argparse
import json
import struct
from pathlib import Path


def decode(data):
    if len(data) != 20:
        raise ValueError("expected exactly 20 bytes")
    version, entries, matches, phase, error = struct.unpack("<5i", data)
    if version != 1:
        raise ValueError("unsupported trace version")
    phases = {
        0: "no_winning_fault_recorded", 1: "winning_fault",
        2: "stack_sampling_returned", 3: "restoration_about_to_run",
        4: "capture_published", 5: "restoration_failed",
    }
    if phase not in phases:
        raise ValueError("invalid trace phase")
    return dict(version=version, handler_entries=entries, matched_entries=matches,
                phase=phase, phase_name=phases[phase], restore_error=error & 0xffffffff,
                atomic_snapshot=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    args = parser.parse_args()
    print(json.dumps(decode(args.trace.read_bytes()), indent=2))
