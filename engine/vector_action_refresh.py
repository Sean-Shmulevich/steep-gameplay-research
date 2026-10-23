"""Compose local reset, vector-source selection, processing and publication.

Evidence: ACTION_RESET_CALLBACK.md; MOTION_MEMBERSHIP_OBSERVATION.md sections
"Live composite has vector-source and directional children" and "Vector-source
ownership and masking"; vector callback RVA 0x4b21d0. This is our finite-value,
immutable adapter, not native synchronization or an active-player binding.
"""
import struct
from .action_refresh import reset_action
from .action_sample import publish_vector
from .vector_action_source import select_vector_source


def refresh_vector_action(snapshot, *, owner_suppressed, configuration_available,
                          kind, lane_mode, ownership_blocked, read_vector,
                          read_scalar, processing_enabled, process,
                          rsqrt_estimate=None):
    """Return detached action bytes and explicit evaluation diagnostics.

    Caller resolves configuration and optional processor gates; no processor is
    silently selected. `process` accepts/returns 16 raw bytes and is called only
    when enabled and evaluation reaches it. Sources are read only on selected,
    unblocked paths. Missing configuration returns after reset, preserving old
    raw input/status while sample, direction and magnitude stay cleared.

    Publication supports finite float32 lanes. Without a supplied RSQRT estimate,
    direction uses action_sample's labeled scalar-seed approximation. Device
    names, source timestamps, pointer validity and sample generations are unknown.
    """
    if type(configuration_available) is not bool or type(processing_enabled) is not bool:
        raise ValueError('configuration and processing gates must be explicit booleans')
    diagnostics = dict(evaluator_called=False, source_evaluated=False,
                       processor_invoked=False, publication=None)

    def evaluate(cleared):
        diagnostics['evaluator_called'] = True
        if not configuration_available:
            return cleared
        raw = select_vector_source(kind, lane_mode, ownership_blocked, read_vector, read_scalar)
        diagnostics['source_evaluated'] = True
        value = raw
        if processing_enabled:
            if not callable(process):
                raise TypeError('enabled processing requires an explicit callback')
            value = process(raw)
            diagnostics['processor_invoked'] = True
            if not isinstance(value, bytes) or len(value) != 16:
                raise ValueError('processor must return 16 bytes')
        publication = publish_vector(list(struct.unpack('<4f', value)),
                                     rsqrt_estimate=rsqrt_estimate)
        updated = bytearray(cleared)
        updated[0x50:0x60] = raw
        updated[0x60:0x70] = value
        updated[0x70:0x80] = struct.pack('<4f', *publication['direction'])
        updated[0x80:0x84] = struct.pack('<f', publication['magnitude'])
        updated[0x30] = int(publication['status'])
        diagnostics['publication'] = publication
        return bytes(updated)

    updated = reset_action(snapshot, owner_suppressed=owner_suppressed, evaluate=evaluate)
    return dict(snapshot=updated, **diagnostics)
