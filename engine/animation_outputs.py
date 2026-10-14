"""Recovered runtime graph output addressing over caller-owned snapshots.

Runtime order must be supplied explicitly; authored order is not established.
Evidence: docs/systems/animations/conversion/CLIENT_GUIDE.txt.
"""
from dataclasses import dataclass
import struct


@dataclass(frozen=True)
class OutputDescriptor:
    offset: int
    owner: object = None


def _index(value):
    if type(value) is not int or value < 0:
        raise ValueError('expected nonnegative integer')
    return value


def flatten_outputs(nodes):
    """Preserve runtime node order and each node's output order, including empty nodes."""
    result = []
    for outputs in nodes:
        for descriptor in outputs:
            if not isinstance(descriptor, OutputDescriptor):
                raise ValueError('expected OutputDescriptor')
            _index(descriptor.offset)
            result.append(descriptor)
    return tuple(result)


def resolve_output(table, source_index, binding_class):
    """Resolve a graph-local descriptor index and preserve its runtime class."""
    _index(source_index)
    if type(binding_class) is not int or binding_class not in (8, 9):
        raise ValueError('only runtime binding classes 8 and 9 are supported')
    if source_index >= len(table):
        raise ValueError('runtime output index out of bounds')
    descriptor = table[source_index]
    if not isinstance(descriptor, OutputDescriptor):
        raise ValueError('expected OutputDescriptor')
    _index(descriptor.offset)
    return binding_class, descriptor


def read_scalar(binding, arena, timeline=b'', *, evaluate_owner=None):
    """Read after optional owner evaluation; buffers may be updated by the callback.

    Callback shape and bounds rejection are adapter contracts. Native owner
    scheduling, synchronization and pointer lifetime are not reproduced here.
    Class 9 returns a timeline scalar with unproved units, not seconds.
    """
    binding_class, descriptor = binding
    resolve_output((descriptor,), 0, binding_class)
    if descriptor.owner is not None:
        if not callable(evaluate_owner):
            raise ValueError('owned output requires an explicit evaluator')
        evaluate_owner(descriptor.owner)
    def read(fmt, buffer, offset):
        if offset + 4 > len(buffer):
            raise ValueError('output snapshot read out of bounds')
        return struct.unpack_from(fmt, buffer, offset)[0]
    if binding_class == 8:
        return read('<f', arena, descriptor.offset)
    handle = read('<I', arena, descriptor.offset)
    return read('<f', timeline, (handle >> 16) * 160 + 144)
