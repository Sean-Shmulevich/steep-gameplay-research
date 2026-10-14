"""Caller-owned adapter for the recovered recursive animation sampling wrapper.

Evidence: docs/reconstruction/ANIMATION_SAMPLING_DISPATCH.md. No native pointers
or game payloads are required. Descriptor decoding remains caller supplied.
"""
from dataclasses import dataclass
import math
from typing import Any
from .animation_binding import channel_sample_route
from .animation_endpoints import f32


@dataclass
class Channel:
    descriptor: Any
    payload: Any
    output_width: int


@dataclass
class Resource:
    channels: list[Channel]
    flags: int = 0
    hashes: list[int] | None = None
    alternate: 'Resource | None' = None


@dataclass
class SampleState:
    hint: int
    cursor: int = -1


def sample_channel(resource, index, time, output, state, decoder, *, extra_byte=0):
    """Follow resource routing and call decoder once at the terminal resource.

    decoder(descriptor, payload, width, time_f32, output, state) owns decoding.
    Output and state retain caller identity. The extra byte is forwarded through
    native recursion but unused by its terminal branch. This adapter validates
    finite time, channel bounds and cycles; native code has no such guards here.
    Returns traversed resource count as adapter diagnostics, not a native return.
    """
    if type(index) is not int or not 0 <= index <= 0xffffffff:
        raise ValueError('expected uint32 channel index')
    if type(extra_byte) is not int or not 0 <= extra_byte <= 255:
        raise ValueError('expected uint8 extra_byte')
    time = f32(time)
    if not math.isfinite(time):
        raise ValueError('expected finite float32 sample time')
    visited = set()
    while True:
        identity = id(resource)
        if identity in visited:
            raise ValueError('alternate resource cycle')
        visited.add(identity)
        if len(resource.channels) > 65535:
            raise ValueError('channel count exceeds uint16')
        route = channel_sample_route(index, len(resource.channels),
                                     resource_flags=resource.flags,
                                     alternate_present=resource.alternate is not None,
                                     hashes=resource.hashes)
        if route == 'alternate':
            resource = resource.alternate
            continue
        if index >= len(resource.channels):
            raise ValueError('terminal channel index out of bounds')
        channel = resource.channels[index]
        if type(channel.output_width) is not int or not 0 <= channel.output_width <= 0xffffffff:
            raise ValueError('expected uint32 descriptor output width')
        decoder(channel.descriptor, channel.payload, channel.output_width,
                time, output, state)
        return len(visited)
