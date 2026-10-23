#!/usr/bin/env python3
"""Decode authored observer diagnostics. Version 2 includes private live addresses."""
import argparse
import json
import struct
from pathlib import Path


def decode(data):
    if len(data) < 20:
        raise ValueError("incomplete trace header")
    version, entries, matches, phase, error = struct.unpack_from("<5i", data)
    if version not in (1, 2):
        raise ValueError("unsupported trace version")
    if len(data) != (20 if version == 1 else 536):
        raise ValueError("wrong trace size for version")
    phases = {
        0: "no_winning_fault_recorded", 1: "winning_fault",
        2: "stack_sampling_returned", 3: "restoration_about_to_run",
        4: "capture_published", 5: "restoration_failed",
    }
    if phase not in phases:
        raise ValueError("invalid trace phase")
    result = dict(version=version, handler_entries=entries, matched_entries=matches,
                phase=phase, phase_name=phases[phase], restore_error=error & 0xffffffff,
                atomic_snapshot=False)
    if version == 2:
        if struct.unpack_from("<i", data, 20)[0] != 8:
            raise ValueError("unsupported event capacity")
        reasons = ("match", "missing_exception_or_context", "not_access_violation",
                   "insufficient_parameters", "noncontinuable", "not_execute_access",
                   "fault_address_outside_page", "instruction_outside_page")
        events = []
        for index in range(8):
            published, code, flags, count, reason, p0, p1, rip = struct.unpack_from("<8Q", data, 24 + index * 64)
            if published == 0:
                continue  # A writer may have reserved but not published this slot.
            if published != 1 or reason >= len(reasons):
                raise ValueError("invalid published event")
            events.append(dict(index=index, code=f"0x{code:08x}", flags=flags,
                               parameter_count=count, reason=reasons[reason],
                               parameter_0=f"0x{p0:x}", parameter_1=f"0x{p1:x}",
                               instruction=f"0x{rip:x}"))
        result["exceptions"] = events
        result["event_capacity"] = 8
        result["private_addresses"] = True
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path)
    args = parser.parse_args()
    print(json.dumps(decode(args.trace.read_bytes()), indent=2))
